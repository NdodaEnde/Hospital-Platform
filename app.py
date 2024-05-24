import logging
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from models import Patient, Entity
from database import db, init_app
from werkzeug.utils import secure_filename
import boto3
import tempfile
import os
from pathlib import Path
from flask_cors import CORS
import json
from datetime import datetime
from pathlib import Path
import requests
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
from flask_migrate import Migrate
import uuid
from botocore.exceptions import ClientError
import csv
from io import StringIO
from models import SequentialNumber
from models import Dashboard
from models import DataSource

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

textract = boto3.client('textract')
comprehend_medical = boto3.client('comprehendmedical')

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
init_app(app)
migrate = Migrate(app, db)

# Import models after creating app and db
from models import Patient, Entity

# OpenSearch configuration
OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST')
OPENSEARCH_INDEX = os.environ.get('OPENSEARCH_INDEX')
OPENSEARCH_REGION = os.environ.get('OPENSEARCH_REGION')
OPENSEARCH_SERVICE = os.environ.get('OPENSEARCH_SERVICE')

# Create an AWS4Auth instance for signing requests
credentials = boto3.Session().get_credentials()
aws4auth = AWS4Auth(credentials.access_key, credentials.secret_key, OPENSEARCH_REGION, OPENSEARCH_SERVICE)

AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID')

# Create an OpenSearch client
opensearch_client = OpenSearch(
    hosts=[OPENSEARCH_HOST],
    http_auth=aws4auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

# Configure the QuickSight client
quicksight = boto3.client('quicksight', region_name=OPENSEARCH_REGION)

@app.before_request
def log_request_info():
    logging.debug(f"Received request: {request.method} {request.path}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path, conditional=True)

@app.route('/dashboard', endpoint='view_dashboard')
def view_dashboard():
    dashboard_name = request.args.get('name')  # Retrieve the dashboard name from the request parameters
    dashboard = Dashboard.query.filter_by(name=dashboard_name).first()

    if dashboard:
        dashboard_id = dashboard.dashboard_id
        return render_template('dashboard.html', dashboard_id=dashboard_id)
    else:
        return "Dashboard not found", 404

@app.route('/create-dashboard', methods=['GET'], endpoint='create_dashboard_page')
def create_dashboard_page():
    return render_template('create_dashboard.html')

@app.route('/patients', methods=['POST'])
def create_patient():
    data = request.get_json()
    date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() 
    patient = Patient(
        name=data['name'],
        date_of_birth=date_of_birth
    )
    db.session.add(patient)
    db.session.commit()

    for entity_data in data['entities']:
        entity = Entity(
            patient_id=patient.id,
            type=entity_data['type'],
            text=entity_data['text'],
            score=entity_data['score'],
            category=entity_data['category'],
            attributes=entity_data['attributes']
        )
        db.session.add(entity)

    db.session.commit()
    return jsonify({'message': 'Patient created successfully'}), 201

@app.route('/patients', methods=['GET'])
def get_patients():
    patients = Patient.query.all()
    result = []
    for patient in patients:
        patient_data = {
            'id': None,
            'name': None,
            'date_of_birth': None,
            'entities': [
                {
                    'id': entity.id,
                    'type': entity.type,
                    'text': entity.text,
                    'score': entity.score,
                    'category': entity.category,
                    'attributes': entity.attributes
                }
                for entity in patient.entities
            ]
        }

        for entity in patient.entities:
            if entity.category == 'PROTECTED_HEALTH_INFORMATION':
                if entity.type == 'NAME':
                    patient_data['name'] = entity.text
                elif entity.type == 'DATE':
                    patient_data['date_of_birth'] = entity.text
                elif entity.type == 'ID':
                    patient_data['id'] = entity.text

        result.append(patient_data)

    return jsonify(result)

@app.route('/patients/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if patient:
        patient_data = {
            'id': patient.id,
            'name': patient.name,
            'date_of_birth': patient.date_of_birth.strftime('%Y-%m-%d'),
            'gender': patient.gender,
            'unique_id': patient.unique_id,
            'conditions': [],
            'surgeries': [],
            'allergies': [],
            'medications': [],
            'family_history': [],
            'blood_pressure': None,
            'heart_rate': None,
            'temperature': None,
            'height': None,
            'weight': None,
            'bmi': None,
            'upcoming_appointments': [],
            'past_visits': [],
            'documents': []
        }

        for entity in patient.entities:
            if entity.category == 'MEDICAL_CONDITION':
                if entity.type == 'DX_NAME':
                    patient_data['conditions'].append(entity.text)
            elif entity.category == 'MEDICATION':
                if entity.type == 'GENERIC_NAME':
                    medication = {
                        'name': entity.text,
                        'dosage': None,
                        'frequency': None
                    }
                    for attr in entity.attributes:
                        if attr['Type'] == 'DOSAGE':
                            medication['dosage'] = attr['Text']
                        elif attr['Type'] == 'FREQUENCY':
                            medication['frequency'] = attr['Text']
                    patient_data['medications'].append(medication)
            elif entity.category == 'TEST_TREATMENT_PROCEDURE':
                if entity.type == 'TEST_NAME':
                    test = {
                        'name': entity.text,
                        'value': None
                    }
                    for attr in entity.attributes:
                        if attr['Type'] == 'TEST_VALUE':
                            test['value'] = attr['Text']
                    patient_data['documents'].append(test)

        return jsonify(patient_data)
    else:
        return jsonify({'message': 'Patient not found'}), 404

@app.route('/patient-profile/<int:patient_id>')
def patient_profile(patient_id):
    patient = Patient.query.get(patient_id)
    if patient:
        return render_template('patient_profile.html', patient=patient)
    else:
        return "Patient not found", 404

@app.route('/patients/<int:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if patient:
        data = request.get_json()
        patient.name = data['name']
        patient.date_of_birth = data['date_of_birth']

        # Delete existing entities for the patient
        Entity.query.filter_by(patient_id=patient_id).delete()

        # Add updated entities
        for entity_data in data['entities']:
            entity = Entity(
                patient_id=patient_id,
                type=entity_data['type'],
                text=entity_data['text'],
                score=entity_data['score'],
                category=entity_data['category'],
                attributes=entity_data['attributes']
            )
            db.session.add(entity)

        db.session.commit()
        return jsonify({'message': 'Patient updated successfully'})
    else:
        return jsonify({'message': 'Patient not found'}), 404

@app.route('/patients/<int:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if patient:
        db.session.delete(patient)
        db.session.commit()
        return jsonify({'message': 'Patient deleted successfully'})
    else:
        return jsonify({'message': 'Patient not found'}), 404

@app.route('/upload', methods=['POST'])
def upload_file():
    logging.debug("upload_file function called")

    file = request.files.get('file')

    if not file:
        logging.error("No file provided")
        return jsonify({'error': 'No file provided'}), 400

    if file.filename == '':
        logging.error("No file selected")
        return jsonify({'error': 'No file selected'}), 400

    logging.debug(f"Received file: {file.filename}")

    # Get the project directory path
    project_dir = Path(__file__).resolve().parent
    logging.debug(f"Project directory: {project_dir}")

    # Save the file to a temporary location in the project directory
    try:
        with tempfile.NamedTemporaryFile(dir=str(project_dir), delete=False) as temp_file:
            file.save(temp_file.name)
            temp_filename = temp_file.name
            logging.debug(f"Temporary file created: {temp_filename}")

        try:
            # Extract text from the PDF file using Amazon Textract
            logging.debug(f"Calling Textract with file: {temp_filename}")
            with open(temp_filename, 'rb') as file:
                response = textract.detect_document_text(
                    Document={'Bytes': file.read()}
                )
            logging.debug(f"Textract response: {response}")

            text = ''
            for item in response['Blocks']:
                if item['BlockType'] == 'LINE':
                    text += item['Text'] + '\n'

            # Analyze the extracted text using Comprehend Medical
            logging.debug("Calling Comprehend Medical...")
            medical_response = comprehend_medical.detect_entities(
                Text=text
            )
            logging.debug(f"Comprehend Medical response: {medical_response}")

            # Parse the Comprehend Medical response and store entities in the database
            patient_name = None
            patient_dob = None
            patient_gender = None

            for entity in medical_response['Entities']:
                if entity['Type'] == 'NAME' and entity['Category'] == 'PROTECTED_HEALTH_INFORMATION':
                    patient_name = entity['Text']
                elif entity['Type'] == 'DATE' and entity['Category'] == 'PROTECTED_HEALTH_INFORMATION':
                    patient_dob = entity['Text']
                elif entity['Type'] == 'GENDER' and entity['Category'] == 'PROTECTED_HEALTH_INFORMATION':
                    patient_gender = entity['Text']

            if patient_name and patient_dob:
                patient_dob = datetime.strptime(patient_dob, '%Y-%m-%d').date()
                patient = Patient(
                    name=patient_name,
                    date_of_birth=patient_dob,
                    gender=patient_gender,
                    unique_id=str(uuid.uuid4())  # Generate a unique identifier
                )
                db.session.add(patient)
                db.session.commit()

                entities = []
                for entity in medical_response['Entities']:
                    entity_data = {
                        'patient_id': patient.id,
                        'type': entity['Type'],
                        'text': entity['Text'],
                        'score': entity['Score'],
                        'category': entity['Category'],
                        'attributes': entity.get('Attributes', [])
                    }
                    entity_record = Entity(**entity_data)
                    db.session.add(entity_record)
                    entities.append(entity_data)

                db.session.commit()
            else:
                logging.warning("Patient name or date of birth not found in the extracted entities.")

            # Index entities in OpenSearch (optional)
            for entity in entities:
                url = f'{OPENSEARCH_HOST}/{OPENSEARCH_INDEX}/_doc'
                headers = {'Content-Type': 'application/json'}
                response = requests.post(url, auth=aws4auth, headers=headers, json=entity)

                if response.status_code == 201:
                    logging.debug(f"Entity indexed successfully: {response.json()['_id']}")
                else:
                    logging.error(f"Error indexing entity: {response.text}")

            # Return the extracted text and entities
            return jsonify({'text': text, 'entities': entities, 'patient_id': patient.id})

        except Exception as e:
            logging.error(f"Error processing file: {str(e)}")
            return jsonify({'error': str(e)}), 500

    except Exception as e:
        logging.error(f"Error creating temporary file: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        # Remove the temporary file
        os.unlink(temp_filename)
        logging.debug(f"Temporary file removed: {temp_filename}")

# Create a route for generating an embed URL for a QuickSight dashboard
@app.route('/quicksight-embed-url', methods=['GET'])
def get_quicksight_embed_url():
    dashboard_id = request.args.get('dashboard_id')
    if not dashboard_id:
        return jsonify({'error': 'Dashboard ID is required'}), 400

    try:
        response = quicksight.get_dashboard_embed_url(
            AwsAccountId=AWS_ACCOUNT_ID,
            DashboardId=dashboard_id,
            IdentityType='IAM',
            SessionLifetimeInMinutes=30,
            UndoRedoDisabled=True,
            ResetDisabled=True
        )
        return jsonify({'embed_url': response['EmbedUrl']})
    except ClientError as e:
        return jsonify({'error': str(e)}), 500

# Create a route for creating a new QuickSight dashboard
from models import DataSource

@app.route('/create-dashboard', methods=['POST'], endpoint='create_dashboard')
def create_dashboard():
    data = request.get_json()
    dashboard_name = data['name']

    try:
        # Retrieve the most recent data source from the database
        data_source = DataSource.query.order_by(DataSource.created_at.desc()).first()

        if data_source:
            data_source_arn = data_source.arn

            response = quicksight.create_dashboard(
                AwsAccountId=AWS_ACCOUNT_ID,
                DashboardId=str(uuid.uuid4()),
                Name=dashboard_name,
                SourceEntity={
                    'SourceTemplate': {
                        'DataSetReferences': [
                            {
                                'DataSetPlaceholder': 'patient_data_dataset',
                                'DataSetArn': data_source_arn
                            }
                        ]
                    }
                },
                VersionDescription='Initial version',
                DashboardPublishOptions={
                    'AdHocFilteringOption': {
                        'AvailabilityStatus': 'ENABLED'
                    },
                    'ExportToCSVOption': {
                        'AvailabilityStatus': 'ENABLED'
                    },
                    'SheetControlsOption': {
                        'VisibilityState': 'EXPANDED'
                    }
                }
            )

            dashboard_id = response['DashboardId']
            dashboard = Dashboard(
                name=dashboard_name,
                dashboard_id=dashboard_id
            )
            db.session.add(dashboard)
            db.session.commit()

            return jsonify({'status': 'success', 'dashboardId': dashboard_id}), 201
        else:
            return jsonify({'status': 'error', 'message': 'No data source found'}), 404

    except ClientError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Add a new route for exporting data to CSV and uploading to S3
@app.route('/export-data', methods=['POST'])
def export_data():
    try:
        # Retrieve patient data from the database
        patients = Patient.query.all()

        # Create a StringIO object to store the CSV data
        csv_data = StringIO()
        writer = csv.writer(csv_data)

        # Write the header row
        writer.writerow(['Name', 'Date of Birth', 'Gender', 'Unique ID', 'Conditions', 'Surgeries', 'Allergies', 'Medications', 'Family History', 'Blood Pressure', 'Heart Rate', 'Temperature', 'Height', 'Weight', 'BMI', 'Documents', 'Upcoming Appointments', 'Past Visits'])

        # Write patient data to the CSV
        for patient in patients:
            writer.writerow([patient.name, patient.date_of_birth, patient.gender, patient.unique_id, ...])

        # Generate a unique file name for the CSV file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        sequential_number = get_next_sequential_number()
        file_name = f'patient_data_{timestamp}_{sequential_number:04d}.csv'

        # Upload the CSV data to S3
        s3 = boto3.client('s3')
        s3.put_object(Body=csv_data.getvalue(), Bucket='hospital-patients-records-bucket', Key=file_name)

        # Create a manifest file
        manifest = {
            "fileLocations": [
                {
                    "URIs": [
                        f"s3://hospital-patients-records-bucket/{file_name}"
                    ]
                }
            ],
            "globalUploadSettings": {
                "format": "CSV",
                "delimiter": ",",
                "textqualifier": "'",
                "containsHeader": "true"
            }
        }

        # Upload the manifest file to S3
        manifest_file_name = f'manifest_{timestamp}_{sequential_number:04d}.json'
        s3.put_object(Body=json.dumps(manifest), Bucket='hospital-patients-records-bucket', Key=manifest_file_name)

        # Create a data source in QuickSight using the manifest file
        quicksight = boto3.client('quicksight')
        response = quicksight.create_data_source(
            AwsAccountId=AWS_ACCOUNT_ID,
            DataSourceId=str(uuid.uuid4()),
            Name='Patient Data',
            Type='S3',
            DataSourceParameters={
                'S3Parameters': {
                    'ManifestFileLocation': {
                        'Bucket': 'hospital-patients-records-bucket',
                        'Key': manifest_file_name
                    }
                }
            }
        )
        data_source_arn = response['Arn']

        return jsonify({'message': 'Data exported and uploaded to S3 successfully', 'data_source_arn': data_source_arn}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add a new route for listing data sources in QuickSight
@app.route('/list-data-sources', methods=['GET'])
def list_data_sources():
    try:
        quicksight = boto3.client('quicksight')
        response = quicksight.list_data_sources(
            AwsAccountId=AWS_ACCOUNT_ID
        )
        data_sources = response['DataSources']
        return jsonify({'data_sources': data_sources}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_next_sequential_number():
    # Retrieve the current sequential number from the database
    sequential_number = SequentialNumber.query.first()

    if sequential_number is None:
        # If no sequential number exists in the database, create a new one
        sequential_number = SequentialNumber(current_number=1)
        db.session.add(sequential_number)
    else:
        # Increment the current sequential number
        sequential_number.current_number += 1

    db.session.commit()

    return sequential_number.current_number

# Create tables based on models within the application context
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run()