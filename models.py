from database import db
from datetime import datetime

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=True)
    unique_id = db.Column(db.String(50), unique=True, nullable=False, info={'constraint_name': 'unique_patient_id'})
    
    conditions = db.Column(db.String(200))
    surgeries = db.Column(db.String(200))
    allergies = db.Column(db.String(200))
    medications = db.Column(db.String(200))
    family_history = db.Column(db.String(200))
    
    blood_pressure = db.Column(db.String(20))
    heart_rate = db.Column(db.String(20))
    temperature = db.Column(db.String(20))
    height = db.Column(db.String(20))
    weight = db.Column(db.String(20))
    bmi = db.Column(db.String(20))
    
    documents = db.Column(db.JSON)
    
    upcoming_appointments = db.Column(db.String(200))
    past_visits = db.Column(db.String(200))
    
    entities = db.relationship('Entity', backref='patient', lazy=True)

class Entity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    type = db.Column(db.String(50))
    text = db.Column(db.String(200))
    score = db.Column(db.Float)
    category = db.Column(db.String(50))
    attributes = db.Column(db.JSON)

class SequentialNumber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    current_number = db.Column(db.Integer, default=1)

class Dashboard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dashboard_id = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Dashboard {self.name}>'

class DataSource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(100), nullable=False)
    arn = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<DataSource {self.file_name}>'