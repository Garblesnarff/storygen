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
        storyData = data;  // Store the story data
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
    }

    async function generateNextScene() {
        if (!storyData) {
            alert('Please generate a story first.');
            return;
        }

        try {
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
                <button class="regenerate-image-btn" data-index="${index}">Regenerate Image</button>
                <p class="paragraph-text">${paragraph.content || 'No content available'}</p>
                <textarea class="edit-paragraph-text" rows="5">${paragraph.content || ''}</textarea>
                <button class="save-edit-btn" data-index="${index}">Save Edit</button>
                ${paragraph.audio_url ? `
                    <audio controls class="audio-player">
                        <source src="${paragraph.audio_url}" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                ` : ''}
            </div>
        `;
        sceneContainer.appendChild(paragraphElement);

        const regenerateBtn = paragraphElement.querySelector('.regenerate-image-btn');
        regenerateBtn.addEventListener('click', () => regenerateImage(index));

        const saveEditBtn = paragraphElement.querySelector('.save-edit-btn');
        saveEditBtn.addEventListener('click', () => saveEdit(index));
    }

    async function regenerateImage(index) {
        try {
            const response = await fetch('/regenerate_image', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    story_id: storyData.story_id,
                    paragraph_index: index,
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to regenerate image');
            }

            const data = await response.json();
            const paragraphElement = sceneContainer.querySelectorAll('.card')[index];
            const imageElement = paragraphElement.querySelector('.scene-image');
            imageElement.src = data.new_image_url;
        } catch (error) {
            console.error('Error in regenerateImage:', error);
            alert('Failed to regenerate image. Please try again.');
        }
    }

    async function saveEdit(index) {
        try {
            const paragraphElement = sceneContainer.querySelectorAll('.card')[index];
            const editTextarea = paragraphElement.querySelector('.edit-paragraph-text');
            const newContent = editTextarea.value;

            const response = await fetch('/edit_scene', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    story_id: storyData.story_id,
                    scene_id: index + 1, // Assuming scene_id starts from 1
                    content: newContent,
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to save edit');
            }

            const data = await response.json();
            const paragraphText = paragraphElement.querySelector('.paragraph-text');
            paragraphText.textContent = newContent;

            if (data.new_image_url) {
                const imageElement = paragraphElement.querySelector('.scene-image');
                imageElement.src = data.new_image_url;
            }

            alert('Edit saved successfully!');
        } catch (error) {
            console.error('Error in saveEdit:', error);
            alert('Failed to save edit. Please try again.');
        }
    }

    // Add CSS styles
    const style = document.createElement('style');
    style.textContent = `
        .edit-paragraph-text {
            width: 100%;
            min-height: 100px;
            margin-top: 10px;
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-family: inherit;
            font-size: inherit;
            resize: vertical;
        }
        .regenerate-image-btn, .save-edit-btn {
            margin-top: 5px;
            margin-bottom: 10px;
        }
    `;
    document.head.appendChild(style);
});
