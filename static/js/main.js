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
                <button class="edit-content" data-scene-id="${storyData.story_id}">Edit Content</button>
                <button class="regenerate-image" data-scene-id="${storyData.story_id}">Regenerate Image</button>
            </div>
        `;
        sceneContainer.appendChild(paragraphElement);

        const editButton = paragraphElement.querySelector('.edit-content');
        const regenerateButton = paragraphElement.querySelector('.regenerate-image');
        editButton.addEventListener('click', () => editContent(storyData.story_id, index));
        regenerateButton.addEventListener('click', () => regenerateImage(storyData.story_id, index));
    }

    async function editContent(sceneId, index) {
        const paragraphElement = sceneContainer.querySelectorAll('.card')[index];
        const paragraphText = paragraphElement.querySelector('.paragraph-text');
        const currentContent = paragraphText.textContent;

        const newContent = prompt('Edit the content:', currentContent);
        if (newContent !== null && newContent !== currentContent) {
            try {
                const response = await fetch(`/edit_scene/${sceneId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ content: newContent }),
                });

                if (!response.ok) {
                    throw new Error('Failed to update content');
                }

                paragraphText.textContent = newContent;
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to update content. Please try again.');
            }
        }
    }

    async function regenerateImage(sceneId, index) {
        const paragraphElement = sceneContainer.querySelectorAll('.card')[index];
        const imageElement = paragraphElement.querySelector('.scene-image');

        try {
            const response = await fetch(`/regenerate_image/${sceneId}`, {
                method: 'POST',
            });

            if (!response.ok) {
                throw new Error('Failed to regenerate image');
            }

            const data = await response.json();
            imageElement.src = data.new_image_url;
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to regenerate image. Please try again.');
        }
    }

    function toggleLoadingIndicator(show) {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.className = `mt-4 text-blue-600 font-bold ${show ? '' : 'hidden'}`;
        }
    }
});