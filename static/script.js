document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.getElementById('file-input');
  const uploadBtn = document.getElementById('upload-btn');
  const extractedTextContainer = document.getElementById('extracted-text');
  const entitiesContainer = document.getElementById('entities');

  uploadBtn.addEventListener('click', async () => {
    const file = fileInput.files[0];
    if (!file) {
      alert('Please select a file.');
      return;
    }
  
    const formData = new FormData();
    formData.append('file', file);
  
    try {
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData
      });
  
      if (!response.ok) {
        throw new Error('Failed to upload file.');
      }
  
      const data = await response.json();
      const extractedText = data.text;
      const entities = data.entities;
      const patientId = data.patient_id; // Get the patient_id from the server response
  
      extractedTextContainer.textContent = extractedText; // Update extracted text
  
      // Clear previous entities
      entitiesContainer.innerHTML = '';
  
      // Render entities
      entities.forEach(entity => {
        const entityElement = document.createElement('div');
        entityElement.classList.add('entity');
  
        const typeElement = document.createElement('span');
        typeElement.classList.add('entity-type');
        typeElement.textContent = `Type: ${entity.type}`;
  
        const textElement = document.createElement('span');
        textElement.classList.add('entity-text');
        textElement.textContent = `Text: ${entity.text}`;
  
        const scoreElement = document.createElement('span');
        scoreElement.classList.add('entity-score');
        scoreElement.textContent = `Score: ${entity.score.toFixed(2)}`;
  
        const categoryElement = document.createElement('span');
        categoryElement.classList.add('entity-category');
        categoryElement.textContent = `Category: ${entity.category}`;
  
        entityElement.appendChild(typeElement);
        entityElement.appendChild(textElement);
        entityElement.appendChild(scoreElement);
        entityElement.appendChild(categoryElement);
  
        if (entity.attributes.length > 0) {
          const attributesElement = document.createElement('ul');
          attributesElement.classList.add('entity-attributes');
          entity.attributes.forEach(attribute => {
            const attributeItem = document.createElement('li');
            attributeItem.textContent = `Type: ${attribute.Type}, Score: ${attribute.Score}, Text: ${attribute.Text}`;
            attributesElement.appendChild(attributeItem);
          });
          entityElement.appendChild(attributesElement);
        }
  
        entitiesContainer.appendChild(entityElement);
      });
  
      // Fetch patient data and populate the profile
      const patientData = await fetchPatientData(patientId);
      populatePatientProfile(patientData);
    } catch (error) {
      console.error('Error:', error);
      alert('An error occurred while processing the file.');
    }
  });

  // Search and query functionality
  const searchForm = document.getElementById('search-form');
  const searchInput = document.getElementById('search-input');
  const searchResultsContainer = document.getElementById('search-results');

  searchForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const query = searchInput.value;

    try {
      const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
      if (!response.ok) {
        throw new Error('Failed to perform search.');
      }

      const data = await response.json();
      const searchResults = data.results;

      // Clear previous search results
      searchResultsContainer.innerHTML = '';

      // Render search results
      searchResults.forEach(result => {
        const resultElement = document.createElement('div');
        resultElement.classList.add('search-result');
        resultElement.textContent = `${result.text} (Score: ${result.score.toFixed(2)})`;
        searchResultsContainer.appendChild(resultElement);
      });
    } catch (error) {
      console.error('Error:', error);
      alert('An error occurred while performing the search.');
    }
  });

  // Function to fetch all patient profiles
  async function fetchPatientProfiles() {
    try {
      const response = await fetch('/patients');
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching patient profiles:', error);
    }
  }

  // Function to create a new patient profile
  async function createPatientProfile(profileData) {
    try {
      const response = await fetch('/patients', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(profileData)
      });
      const data = await response.json();
      console.log(data.message);
    } catch (error) {
      console.error('Error creating patient profile:', error);
    }
  }

  // Function to update a patient profile
  async function updatePatientProfile(patientId, profileData) {
    try {
      const response = await fetch(`/patients/${patientId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(profileData)
      });
      const data = await response.json();
      console.log(data.message);
    } catch (error) {
      console.error('Error updating patient profile:', error);
    }
  }

  // Function to delete a patient profile
  async function deletePatientProfile(patientId) {
    try {
      const response = await fetch(`/patients/${patientId}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      console.log(data.message);
    } catch (error) {
      console.error('Error deleting patient profile:', error);
    }
  }

  // Function to fetch patient data from the server
  async function fetchPatientData(patientId) {
    try {
      const response = await fetch(`/patients/${patientId}`);
      if (response.ok) {
        const patientData = await response.json();
        return patientData;
      } else {
        throw new Error('Failed to fetch patient data');
      }
    } catch (error) {
      console.error('Error fetching patient data:', error);
      throw error;
    }
  }

  
  // Function to populate patient profile with data
function populatePatientProfile(patientData) {
  document.getElementById('patient-name').textContent = patientData.name;
  document.getElementById('patient-dob').textContent = patientData.date_of_birth;
  document.getElementById('patient-gender').textContent = patientData.gender || 'Not available';
  document.getElementById('patient-id').textContent = patientData.unique_id;
  
  // Populate conditions
  const conditionsContainer = document.getElementById('patient-conditions');
  conditionsContainer.innerHTML = '';
  if (patientData.conditions && patientData.conditions.length > 0) {
    patientData.conditions.forEach(condition => {
      const listItem = document.createElement('li');
      listItem.textContent = condition;
      conditionsContainer.appendChild(listItem);
    });
  } else {
    conditionsContainer.textContent = 'Not available';
  }
  
  // Populate medications
  const medicationsContainer = document.getElementById('patient-medications');
  medicationsContainer.innerHTML = '';
  if (patientData.medications && patientData.medications.length > 0) {
    patientData.medications.forEach(medication => {
      const listItem = document.createElement('li');
      listItem.textContent = `${medication.name} (Dosage: ${medication.dosage || 'Not available'}, Frequency: ${medication.frequency || 'Not available'})`;
      medicationsContainer.appendChild(listItem);
    });
  } else {
    medicationsContainer.textContent = 'Not available';
  }
  
  // Populate documents
  const documentsContainer = document.getElementById('patient-documents');
  documentsContainer.innerHTML = '';
  if (patientData.documents && patientData.documents.length > 0) {
    patientData.documents.forEach(doc => {
      const listItem = document.createElement('li');
      listItem.textContent = `${doc.name} (Value: ${doc.value || 'Not available'})`;
      documentsContainer.appendChild(listItem);
    });
  } else {
    documentsContainer.textContent = 'No documents available';
  }
  
  // Populate other fields
  document.getElementById('patient-surgeries').textContent = patientData.surgeries.join(', ') || 'Not available';
  document.getElementById('patient-allergies').textContent = patientData.allergies.join(', ') || 'Not available';
  document.getElementById('patient-family-history').textContent = patientData.family_history.join(', ') || 'Not available';
  document.getElementById('patient-blood-pressure').textContent = patientData.blood_pressure || 'Not available';
  document.getElementById('patient-heart-rate').textContent = patientData.heart_rate || 'Not available';
  document.getElementById('patient-temperature').textContent = patientData.temperature || 'Not available';
  document.getElementById('patient-height').textContent = patientData.height || 'Not available';
  document.getElementById('patient-weight').textContent = patientData.weight || 'Not available';
  document.getElementById('patient-bmi').textContent = patientData.bmi || 'Not available';
  document.getElementById('patient-upcoming-appointments').textContent = patientData.upcoming_appointments.join(', ') || 'Not available';
  document.getElementById('patient-past-visits').textContent = patientData.past_visits.join(', ') || 'Not available';
}

// Function to navigate to the dashboard page
function navigateToDashboard(dashboardId) {
  // Update the URL or redirect to the dashboard page with the dashboardId
  window.location.href = `/dashboard?id=${dashboardId}`;
}
// Export data button click event
document.getElementById('export-data-btn').addEventListener('click', async () => {
  try {
      const response = await fetch('/export-data', {
          method: 'POST'
      });

      if (response.ok) {
          const data = await response.json();
          console.log('Data exported and uploaded to S3 successfully');
          console.log('Data Source ARN:', data.data_source_arn);

          // Create a new dashboard after exporting data
          const dashboardName = 'New Dashboard';
          const dashboardConfig = {
              name: dashboardName
          };

          const createResponse = await fetch('/create-dashboard', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json'
              },
              body: JSON.stringify(dashboardConfig)
          });

          if (createResponse.ok) {
              const createData = await createResponse.json();
              const dashboardId = createData.dashboardId;
              console.log('Dashboard created successfully. ID:', dashboardId);

              // Navigate to the dashboard page or perform any other necessary actions
          } else {
              console.error('Error creating dashboard:', createResponse.statusText);
          }
      } else {
          console.error('Error exporting data:', response.statusText);
      }
  } catch (error) {
      console.error('Error exporting data:', error);
  }
});

// Load QuickSight dashboard
async function loadQuickSightDashboard() {
  try {
    const embedUrl = await getQuickSightEmbedUrl(dashboardId);
    const quicksightDashboard = document.getElementById('quicksight-dashboard');
    quicksightDashboard.innerHTML = `<iframe src="${embedUrl}" width="100%" height="600"></iframe>`;
  } catch (error) {
    console.error('Error loading QuickSight dashboard:', error);
  }
}
// Function to fetch the embed URL for a QuickSight dashboard
async function getQuickSightEmbedUrl(dashboardId) {
  try {
      const response = await fetch(`/quicksight-embed-url?dashboard_id=${dashboardId}`);
      if (!response.ok) {
          throw new Error('Failed to get QuickSight embed URL');
      }
      const data = await response.json();
      return data.embed_url;
  } catch (error) {
      console.error('Error:', error);
      throw error;
  }
}

});