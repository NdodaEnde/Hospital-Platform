from database import db

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