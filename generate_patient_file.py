import random
from faker import Faker
import requests
from PIL import Image
from fpdf import FPDF
import io
import json

# Initialize Faker
fake = Faker()

# Function to generate synthetic patient data
def generate_patient_data():
    patient_data = {
        "Name": fake.name(),
        "Date of Birth": fake.date_of_birth(minimum_age=1, maximum_age=100).strftime('%Y-%m-%d'),
        "Gender": random.choice(["Male", "Female"]),
        "Medical History": fake.text(max_nb_chars=200),
        "Current Diagnosis": fake.text(max_nb_chars=100),
        "Treatment Plan": fake.text(max_nb_chars=150)
    }
    return patient_data

# Function to create doctor's notes
def create_doctors_notes(patient_data):
    notes = f"""
    Patient Name: {patient_data['Name']}
    Date of Birth: {patient_data['Date of Birth']}
    Gender: {patient_data['Gender']}

    Medical History:
    {patient_data['Medical History']}

    Current Diagnosis:
    {patient_data['Current Diagnosis']}

    Treatment Plan:
    {patient_data['Treatment Plan']}
    """
    return notes

# Function to fetch available handwriting styles
def fetch_handwriting_styles(api_key):
    api_url = 'https://api.handwrite.io/v1/handwriting'
    headers = {
        'authorization': api_key,
        'content-type': 'application/json'
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        return json.loads(response.content)
    else:
        print(f"Error fetching handwriting styles: {response.status_code}")
        print(f"Response content: {response.content}")
        return None

# Function to convert text to handwritten image using Handwrite.io API
def text_to_handwritten_image(text, api_key, handwriting_id):
    api_url = 'https://api.handwrite.io/v1/render'
    headers = {
        'authorization': api_key,
        'content-type': 'application/json'
    }
    data = {
        'text': text,
        'handwriting_id': handwriting_id,
        'handwriting_size': 14,
        'width': 800,
        'height': 1000
    }
    response = requests.post(api_url, headers=headers, json=data)
    
    # Check if the response is successful
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print(f"Response content: {response.content}")
        return None
    
    try:
        image = Image.open(io.BytesIO(response.content))
        return image
    except Exception as e:
        print(f"Error: {e}")
        print(f"Response content: {response.content}")
        return None

# Function to create PDF from images
def create_pdf(images, output_path):
    pdf = FPDF()
    for image in images:
        pdf.add_page()
        pdf.image(image, x=10, y=10, w=190)
    pdf.output(output_path)

# Main function to generate patient file
def generate_patient_file(api_key, output_path):
    patient_data = generate_patient_data()
    doctors_notes = create_doctors_notes(patient_data)
    
    # Fetch available handwriting styles
    handwriting_styles = fetch_handwriting_styles(api_key)
    if not handwriting_styles:
        print("Failed to fetch handwriting styles.")
        return
    
    # Log the available handwriting styles
    print("Available handwriting styles:")
    for style in handwriting_styles:
        print(f"ID: {style['_id']}, Name: {style['name']}")
    
    # Select a handwriting style (e.g., the first one)
    handwriting_id = handwriting_styles[0]['_id']
    
    handwritten_image = text_to_handwritten_image(doctors_notes, api_key, handwriting_id)
    
    if handwritten_image is not None:
        handwritten_image_path = 'handwritten_notes.png'
        handwritten_image.save(handwritten_image_path)
        create_pdf([handwritten_image_path], output_path)
    else:
        print("Failed to generate handwritten image.")

# Handwrite.io API key
api_key = 'test_hw_0b8a7402e420be0d98f1'
output_path = 'patient_file.pdf'

generate_patient_file(api_key, output_path)