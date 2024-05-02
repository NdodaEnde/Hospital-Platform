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