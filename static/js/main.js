document.addEventListener('DOMContentLoaded', () => {
    const storyForm = document.getElementById('story-form');
    const storyContainer = document.getElementById('story-container');
    const sceneContainer = document.getElementById('scene-container');
    let storyData;

    storyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const topic = document.getElementById('topic').value;
        
        try {
            const response = await fetch('/generate_story', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topic }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to generate story');
            }
            
            storyData = await response.json();
            displayStory(storyData);
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to generate story. Please try again.');
        }
    });

    function displayStory(data) {
        storyData = data;
        const bookSpec = storyData.book_spec.split('\n');
        const logLine = bookSpec[1].replace('Log Line: ', '');
        
        storyContainer.innerHTML = `
            <h2>Story Concept</h2>
            <p><strong>Log Line:</strong> ${logLine}</p>
            <h3>5-Act Structure</h3>
            <div class="act-structure">${storyData.outline}</div>
            <button id="generate-scene">Generate Next Scene</button>
        `;

        document.getElementById('generate-scene').addEventListener('click', generateNextScene);

        const loadingIndicator = document.createElement('div');
        loadingIndicator.id = 'loading-indicator';
        loadingIndicator.className = 'mt-4 text-blue-600 font-bold hidden';
        loadingIndicator.textContent = 'Generating scene...';
        storyContainer.appendChild(loadingIndicator);
    }

    async function generateNextScene() {
        if (!storyData) {
            alert('Please generate a story first.');
            return;
        }

        try {
            toggleLoadingIndicator(true);
            
            const nextSceneResponse = await fetch('/get_next_scene', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    story_id: storyData.story_id,
                }),
            });
            
            if (!nextSceneResponse.ok) {
                const errorData = await nextSceneResponse.json();
                throw new Error(errorData.error || 'Failed to get next scene');
            }
            
            const nextSceneData = await nextSceneResponse.json();
            
            if (nextSceneData.message === 'All scenes have been generated') {
                alert('Story complete!');
                return;
            }
            
            const response = await fetch('/generate_scene', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    story_id: storyData.story_id,
                    act: nextSceneData.act,
                    chapter: nextSceneData.chapter,
                    scene_number: nextSceneData.scene_number,
                }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to generate scene');
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const data = JSON.parse(line);
                            handleStreamedData(data);
                        } catch (error) {
                            console.error('Error parsing JSON:', error, 'Raw data:', line);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error:', error);
            alert(`Failed to generate scene: ${error.message}`);
        } finally {
            toggleLoadingIndicator(false);
        }
    }

    function handleStreamedData(data) {
        if (!data || typeof data !== 'object') {
            console.error('Invalid data received:', data);
            return;
        }

        switch (data.status) {
            case 'generating_paragraphs':
                updateProgressMessage('Generating paragraphs...');
                break;
            case 'paragraphs_generated':
                updateProgressMessage('Paragraphs generated. Generating images and audio...');
                break;
            case 'image_generated':
                if (data.paragraph && typeof data.index === 'number') {
                    displayParagraph(data.paragraph, data.index);
                } else {
                    console.error('Invalid paragraph data:', data);
                }
                break;
            case 'complete':
                updateProgressMessage('Scene generation complete');
                toggleLoadingIndicator(false);
                break;
            default:
                console.warn('Unknown status:', data.status);
        }
    }

    function updateProgressMessage(message) {
        const progressElement = document.getElementById('progress-message') || createProgressElement();
        progressElement.textContent = message;
    }

    function createProgressElement() {
        const progressElement = document.createElement('div');
        progressElement.id = 'progress-message';
        progressElement.className = 'mt-4 text-blue-600 font-bold';
        sceneContainer.appendChild(progressElement);
        return progressElement;
    }

    function displayParagraph(paragraph, index) {
        if (!paragraph || typeof paragraph !== 'object') {
            console.error('Invalid paragraph data:', paragraph);
            return;
        }

        const paragraphElement = document.createElement('div');
        paragraphElement.className = 'card';
        paragraphElement.dataset.sceneId = paragraph.scene_id;
        paragraphElement.innerHTML = `
            <div class="card-content">
                <img src="${paragraph.image_url || '/static/images/placeholder.svg'}" alt="Scene Image" class="scene-image">
                <p class="paragraph-text">${paragraph.content || 'No content available'}</p>
                ${paragraph.audio_url ? `
                    <audio controls class="audio-player">
                        <source src="${paragraph.audio_url}" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                ` : ''}
                <button class="edit-paragraph-btn" data-index="${index}">Edit Paragraph</button>
                <button class="regenerate-image-btn" data-index="${index}">Regenerate Image</button>
            </div>
        `;
        sceneContainer.appendChild(paragraphElement);

        paragraphElement.querySelector('.edit-paragraph-btn').addEventListener('click', () => editParagraph(index));
        paragraphElement.querySelector('.regenerate-image-btn').addEventListener('click', () => regenerateImage(index));
    }

    function editParagraph(index) {
        const paragraphElement = sceneContainer.querySelectorAll('.card')[index];
        const paragraphText = paragraphElement.querySelector('.paragraph-text');
        const currentContent = paragraphText.textContent;

        const textarea = document.createElement('textarea');
        textarea.value = currentContent;
        textarea.className = 'form-control';
        paragraphText.replaceWith(textarea);

        const saveButton = document.createElement('button');
        saveButton.textContent = 'Save';
        saveButton.className = 'btn btn-primary mt-2';
        saveButton.addEventListener('click', async () => {
            const newContent = textarea.value;
            paragraphText.textContent = newContent;
            textarea.replaceWith(paragraphText);
            saveButton.remove();

            const sceneId = paragraphElement.dataset.sceneId;
            try {
                const response = await fetch(`/edit_scene/${sceneId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ content: newContent }),
                });

                if (!response.ok) {
                    throw new Error('Failed to save edited content');
                }

                alert('Content saved successfully!');
            } catch (error) {
                console.error('Error saving content:', error);
                alert('Failed to save content. Please try again.');
            }
        });

        paragraphElement.querySelector('.card-content').appendChild(saveButton);
    }

    async function regenerateImage(index) {
        const paragraphElement = sceneContainer.querySelectorAll('.card')[index];
        const paragraphText = paragraphElement.querySelector('.paragraph-text').textContent;
        const imageElement = paragraphElement.querySelector('img');
        const sceneId = paragraphElement.dataset.sceneId;

        if (!sceneId) {
            console.error('Scene ID is undefined');
            alert('Failed to regenerate image: Scene ID is missing.');
            return;
        }

        try {
            const response = await fetch(`/regenerate_image/${sceneId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: paragraphText,
                }),
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Server response:', response.status, errorText);
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            if (data.image_url) {
                imageElement.src = data.image_url;
                alert('Image regenerated successfully!');
            } else {
                throw new Error('No image URL returned from server');
            }
        } catch (error) {
            console.error('Error in regenerateImage:', error);
            alert(`Failed to regenerate image: ${error.message}`);
        }
    }

    function toggleLoadingIndicator(show) {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.className = `mt-4 text-blue-600 font-bold ${show ? '' : 'hidden'}`;
        }
    }
});