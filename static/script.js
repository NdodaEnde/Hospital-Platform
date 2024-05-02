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

        entityElement.appendChild(typeElement);
        entityElement.appendChild(textElement);
        entityElement.appendChild(scoreElement);

        if (entity.attributes.length > 0) {
          const attributesElement = document.createElement('ul');
          attributesElement.classList.add('entity-attributes');
          entity.attributes.forEach(attribute => {
            const attributeItem = document.createElement('li');
            attributeItem.textContent = attribute;
            attributesElement.appendChild(attributeItem);
          });
          entityElement.appendChild(attributesElement);
        }

        entitiesContainer.appendChild(entityElement);
      });
    } catch (error) {
      console.error('Error:', error);
      alert('An error occurred while processing the file.');
    }
  });
});