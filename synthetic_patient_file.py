import random
from faker import Faker
from faker.providers import person, address, medical
from transformers import pipeline
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from faker.providers import medical


# Initialize Faker with medical data providers
fake = Faker()
fake.add_provider(person)
fake.add_provider(address)
fake.add_provider(medical)

# Generate synthetic patient data
def generate_patient_data():
    patient_data = {
        'name': fake.name(),
        'age': random.randint(18, 80),
        'gender': random.choice(['Male', 'Female']),
        'address': fake.address(),
        'contact': fake.phone_number(),
        'medical_history': {
            'past_illnesses': fake.text(),
            'medications': fake.text(),
            'allergies': fake.text(),
            'family_history': fake.text(),
            'vital_signs': {
                'blood_pressure': f"{random.randint(90, 140)}/{random.randint(60, 90)} mmHg",
                'heart_rate': f"{random.randint(60, 100)} bpm",
                'temperature': f"{random.uniform(36.0, 37.5):.1f} °C",
                'weight': f"{random.uniform(50.0, 100.0):.1f} kg"
            }
        }
    }
    return patient_data

# Generate doctor's notes using NLG
def generate_doctor_notes(patient_data):
    nlg = pipeline('text-generation', model='gpt2')
    doctor_notes = nlg(patient_data['medical_history']['vital_signs'], max_length=150)[0]['generated_text']
    return doctor_notes

# Convert text to handwritten format and save as image
def convert_to_handwritten(text, output_file):
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    x, y = 50, 50
    line_height = 30
    for line in text.split('\n'):
        draw.text((x, y), line, fill='black', font=font)
        y += line_height

    img.save(output_file)

# Generate PDF report with patient data and handwritten notes
def generate_pdf_report(patient_data, doctor_notes, output_file):
    pdf_canvas = canvas.Canvas(output_file, pagesize=letter)

    # Write patient data to PDF
    pdf_canvas.setFont("Helvetica-Bold", 12)
    pdf_canvas.drawString(50, 750, "Patient Data:")
    y_pos = 730
    for key, value in patient_data.items():
        if isinstance(value, dict):
            pdf_canvas.setFont("Helvetica", 10)
            pdf_canvas.drawString(70, y_pos, f"{key.capitalize()}:")
            y_pos -= 15
            for k, v in value.items():
                pdf_canvas.drawString(90, y_pos, f"{k.replace('_', ' ').capitalize()}: {v}")
                y_pos -= 12
            y_pos -= 5
        else:
            pdf_canvas.drawString(70, y_pos, f"{key.capitalize()}: {value}")
            y_pos -= 15
    y_pos -= 20

    # Add handwritten doctor's notes to PDF
    pdf_canvas.setFont("Helvetica-Bold", 12)
    pdf_canvas.drawString(50, y_pos, "Doctor's Notes:")
    y_pos -= 20
    pdf_canvas.setFont("Courier", 10)
    for line in doctor_notes.split('\n'):
        pdf_canvas.drawString(70, y_pos, line)
        y_pos -= 12

    pdf_canvas.save()

if __name__ == '__main__':
    # Generate synthetic patient data
    print("Generating synthetic patient data...")
    patient_data = generate_patient_data()
    print("Generated Patient Data:")
    print(patient_data)
    
    # Generate doctor's notes
    doctor_notes = generate_doctor_notes(patient_data)
    
    # Convert doctor's notes to handwritten format and save as image
    convert_to_handwritten(doctor_notes, 'handwritten_notes.png')
    
    # Generate PDF report with patient data and handwritten notes
    generate_pdf_report(patient_data, doctor_notes, 'patient_report.pdf')
