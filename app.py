import logging
from flask import Flask, jsonify, request
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
from flask import render_template
import json
from datetime import datetime
from pathlib import Path
import requests
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
from flask_migrate import Migrate
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

textract = boto3.client('textract')
comprehend_medical = boto3.client('comprehendmedical')

print(f"OPENSEARCH_HOST: {os.environ.get('OPENSEARCH_HOST')}")
print(f"OPENSEARCH_INDEX: {os.environ.get('OPENSEARCH_INDEX')}")
print(f"OPENSEARCH_REGION: {os.environ.get('OPENSEARCH_REGION')}")
print(f"OPENSEARCH_SERVICE: {os.environ.get('OPENSEARCH_SERVICE')}")

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

# Create an OpenSearch client
opensearch_client = OpenSearch(
    hosts=[OPENSEARCH_HOST],
    http_auth=aws4auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

@app.before_request
def log_request_info():
    logging.debug(f"Received request: {request.method} {request.path}")

@app.route('/')
def index():
    return render_template('index.html')

from flask import send_from_directory

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path, conditional=True)

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

# Define routes and other configurations
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

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'No search query provided'}), 400

    try:
        # Perform the search
        search_response = opensearch_client.search(
            index=OPENSEARCH_INDEX,
            body={
                'query': {
                    'multi_match': {
                        'query': query,
                        'fields': ['text', 'type', 'category']
                    }
                }
            }
        )

        # Parse the search results
        search_results = []
        for hit in search_response['hits']['hits']:
            result = {
                'text': hit['_source']['text'],
                'score': hit['_score']
            }
            search_results.append(result)

        return jsonify({'results': search_results})

    except Exception as e:
        logging.error(f"Error performing search: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/patients/<int:patient_id>')
def patient_profile(patient_id):
    patient = Patient.query.get(patient_id)
    if patient:
        return render_template('patient_profile.html', patient=patient)
    else:
        return "Patient not found", 404

# Create tables based on models within the application context
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run()
"""
if __name__ == '__main__':
    app.run(debug=True)

import logging
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from models import Patient
from database import db, init_app
from werkzeug.utils import secure_filename
import boto3
import tempfile
import os
from pathlib import Path
from flask_cors import CORS
from flask import render_template
import json
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

textract = boto3.client('textract')
comprehend_medical = boto3.client('comprehendmedical')

app = Flask(__name__)
CORS(app) 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
init_app(app)

# Import models after creating app and db
from models import Patient
@app.before_request
def log_request_info():
    logging.debug(f"Received request: {request.method} {request.path}")

@app.route('/')
def index():
    return render_template('index.html')

from flask import send_from_directory

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path, conditional=True)

# Define routes and other configurations
@app.route('/patients', methods=['GET'])
def get_patients():
    try:
        patients = Patient.query.all()
        output = []
        for patient in patients:
            patient_data = {'id': patient.id, 'name': patient.name, 'date_of_birth': patient.date_of_birth}
            output.append(patient_data)
        return jsonify({'patients': output})
    except Exception as e:
        logging.error(f"Error retrieving patients: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])

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

            # Inspect the uploaded file
            with open(temp_filename, 'rb') as temp_file:
                file_contents = temp_file.read()
                logging.debug(f"File contents (truncated): {file_contents[:50]}...")

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

            # Parse the Comprehend Medical response
            entities = []
            for entity in medical_response['Entities']:
                entity_data = {
                    'type': entity['Type'],
                    'text': entity['Text'],
                    'score': entity['Score'],
                    'category': entity['Category'],
                    'attributes': entity.get('Attributes', [])
                }
                entities.append(entity_data)

            # Save entities to a JSON file
            entities_file = project_dir / 'entities.json'
            with open(entities_file, 'w') as f:
                json.dump(entities, f, indent=2)

            # Return the extracted text and entities
            return jsonify({'text': text, 'entities': entities})

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
"""
'''
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

            # Inspect the uploaded file
            with open(temp_filename, 'rb') as temp_file:
                file_contents = temp_file.read()
                logging.debug(f"File contents (truncated): {file_contents[:50]}...")

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

            # Return the extracted text
            return jsonify({'text': text})

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
'''

'''
def upload_file():
    # Get the uploaded file
    logging.debug(f"Request data: {request.data}")
    logging.debug(f"Request files: {request.files}")
    file = request.files['file']
    logging.debug(f"Received file: {file.filename}")

    # Get the project directory path
    project_dir = Path(__file__).resolve().parent
    logging.debug(f"Project directory: {project_dir}")

    # Save the file to a temporary location in the project directory
    with tempfile.NamedTemporaryFile(dir=str(project_dir), delete=False) as temp_file:
        file.save(temp_file.name)
        temp_filename = temp_file.name
        logging.debug(f"Temporary file created: {temp_filename}")

    try:
        # Extract text from the PDF file using Amazon Textract
        with open(temp_filename, 'rb') as file:
            logging.debug(f"Calling Textract with file: {temp_filename}")
            response = textract.detect_document_text(
                Document={'Bytes': file.read()}
            )
            logging.debug(f"Textract response: {response}")

        text = ''
        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                text += item['Text'] + '\n'

        # Analyze the extracted text using Comprehend Medical
        medical_response = comprehend_medical.detect_entities(
            Text=text
        )
        logging.debug(f"Comprehend Medical response: {medical_response}")

        # Return the extracted text
        return {'text': text}

    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Remove the temporary file
        os.unlink(temp_filename)
        logging.debug(f"Temporary file removed: {temp_filename}")
'''
# Create tables based on models within the application context
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run()


"""
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from models import Patient
from database import db, init_app
from werkzeug.utils import secure_filename
import boto3
import tempfile
import os

textract = boto3.client('textract')
comprehend_medical = boto3.client('comprehendmedical')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
init_app(app)

# Import models after creating app and db
from models import Patient

# Define routes and other configurations
@app.route('/patients', methods=['GET'])
def get_patients():
    try:
        patients = Patient.query.all()
        output = []
        for patient in patients:
            patient_data = {'id': patient.id, 'name': patient.name, 'date_of_birth': patient.date_of_birth}
            output.append(patient_data)
        return jsonify({'patients': output})
    except Exception as e:
        return jsonify({'error': str(e)}), 500  # Return a 500 Internal Server Error with the error message

from pathlib import Path

@app.route('/upload', methods=['POST'])
def upload_file():
    # Get the uploaded file
    file = request.files['file']

    # Get the project directory path
    project_dir = Path(__file__).resolve().parent

    # Save the file to a temporary location in the project directory
    with tempfile.NamedTemporaryFile(dir=str(project_dir), delete=False) as temp_file:
        file.save(temp_file.name)
        temp_filename = temp_file.name

    try:
        # Extract text from the PDF file using Amazon Textract
        with open(temp_filename, 'rb') as file:
            response = textract.detect_document_text(
                Document={'Bytes': file.read()}
            )

        text = ''
        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                text += item['Text'] + '\n'

        # Analyze the extracted text using Comprehend Medical
        medical_response = comprehend_medical.detect_entities(
            Text=text
        )

        # Return the extracted text
        return {'text': text}

    finally:
        # Remove the temporary file
        os.unlink(temp_filename)



@app.route('/upload', methods=['POST'])
def upload_file():
    # Get the uploaded file
    file = request.files['file']

    # Save the file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        file.save(temp_file.name)
        temp_filename = temp_file.name

    try:
        # Extract text from the PDF file using Amazon Textract
        with open(temp_filename, 'rb') as file:
            response = textract.detect_document_text(
                Document={'Bytes': file.read()}
            )

        text = ''
        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                text += item['Text'] + '\n'

        # Analyze the extracted text using Comprehend Medical
        medical_response = comprehend_medical.detect_entities(
            Text=text
        )

        # Return the extracted text
        return {'text': text}

    finally:
        # Remove the temporary file
        os.unlink(temp_filename)


@app.route('/upload', methods=['POST'])
def upload_file():
    # Get the uploaded file
    file = request.files['file']
    # Secure the filename
    filename = secure_filename(file.filename)
    # Save the file to a temporary location
    file.save(filename)
    # Extract text from the PDF file using Amazon Textract
    with open(filename, 'rb') as file:
        response = textract.detect_document_text(
            Document={'Bytes': file.read()}
        )
        text = ''
        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                text += item['Text'] + '\n'
    # Analyze the extracted text using Comprehend Medical
    medical_response = comprehend_medical.detect_entities(
        Text=text
    )

    # Return the extracted text
    return {'text': text}

# Create tables based on models within the application context
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run()
"""