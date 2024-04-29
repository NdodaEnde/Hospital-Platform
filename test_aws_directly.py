import boto3

# Create the boto3 clients
textract = boto3.client('textract')
comprehend_medical = boto3.client('comprehendmedical')

# Open the PDF file
with open('/Users/luzuko/military-hospital-platform/patientfile.pdf', 'rb') as file:
    # Call the Textract service
    response = textract.detect_document_text(
        Document={'Bytes': file.read()}
    )
    print("Textract response:", response)

    # Extract the text from the Textract response
    text = ''
    for item in response['Blocks']:
        if item['BlockType'] == 'LINE':
            text += item['Text'] + '\n'

    # Call the Comprehend Medical service
    medical_response = comprehend_medical.detect_entities(
        Text=text
    )
    print("Comprehend Medical response:", medical_response)