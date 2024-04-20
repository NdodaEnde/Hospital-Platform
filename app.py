from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from models import Patient
from database import db, init_app

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

# Create tables based on models within the application context
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run()
