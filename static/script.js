document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.getElementById('file-input');
  const uploadBtn = document.getElementById('upload-btn');
  const extractedTextContainer = document.getElementById('extracted-text');

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
          extractedTextContainer.textContent = extractedText; // Update extracted text
      } catch (error) {
          console.error('Error:', error);
          alert('An error occurred while processing the file.');
      }
  });
});
