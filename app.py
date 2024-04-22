from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from models import Patient
from database import db, init_app
from werkzeug.utils import secure_filename
import boto3

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
