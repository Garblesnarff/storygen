document.addEventListener('DOMContentLoaded', () => {
    const storyForm = document.getElementById('story-form');
    const storyContainer = document.getElementById('story-container');
    const sceneContainer = document.getElementById('scene-container');

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
            
            if (!response.ok) throw new Error('Failed to generate story');
            
            const data = await response.json();
            displayStory(data);
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to generate story. Please try again.');
        }
    });

    function displayStory(storyData) {
        storyContainer.innerHTML = `
            <h2 class="text-2xl font-bold mb-4">Story Outline</h2>
            <pre class="bg-gray-100 p-4 rounded">${storyData.outline}</pre>
            <button id="generate-scene" class="mt-4 bg-blue-500 text-white px-4 py-2 rounded">Generate First Scene</button>
        `;

        let currentChapter = 1;
        let currentScene = 1;

        document.getElementById('generate-scene').addEventListener('click', async () => {
            try {
                const response = await fetch('/generate_scene', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        story_id: storyData.story_id,
                        chapter: currentChapter,
                        scene_number: currentScene,
                    }),
                });
                
                if (!response.ok) {
                    throw new Error('Failed to generate scene');
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
                            const data = JSON.parse(line);
                            handleStreamedData(data);
                        }
                    }
                }
                
                currentScene++;
                if (currentScene > 3) {  // Assuming 3 scenes per chapter
                    currentChapter++;
                    currentScene = 1;
                }
            } catch (error) {
                console.error('Error:', error);
                alert(`Failed to generate scene: ${error.message}`);
            }
        });
    }

    function handleStreamedData(data) {
        switch (data.status) {
            case 'generating_paragraphs':
                updateProgressMessage('Generating paragraphs...');
                break;
            case 'image_generated':
                displayParagraph(data.paragraph, data.index);
                break;
            case 'audio_generated':
                displayAudio(data.audio_url);
                break;
            case 'complete':
                updateProgressMessage('Scene generation complete!');
                break;
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
        const paragraphElement = document.createElement('div');
        paragraphElement.className = 'mb-8 p-4 border rounded';
        paragraphElement.innerHTML = `
            <div class="bg-white p-4 rounded shadow">
                <img src="${paragraph.image_url}" alt="Paragraph Image" class="w-full h-48 object-cover mb-4" onerror="this.onerror=null; this.src='/static/images/placeholder.svg';">
                <p class="paragraph-text">${paragraph.content}</p>
            </div>
        `;
        sceneContainer.appendChild(paragraphElement);
    }

    function displayAudio(audioUrl) {
        const audioElement = document.createElement('audio');
        audioElement.controls = true;
        audioElement.className = 'audio-player mt-4 w-full';
        audioElement.innerHTML = `
            <source src="${audioUrl}" type="audio/mpeg">
            Your browser does not support the audio element.
        `;
        sceneContainer.appendChild(audioElement);
    }
});
