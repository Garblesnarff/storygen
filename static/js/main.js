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
                
                const data = await response.json();
                console.log('Received scene data:', data);
                
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to generate scene');
                }
                
                displayScene(data);
                
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

    function displayScene(sceneData) {
        console.log('Displaying scene:', sceneData);
        const sceneElement = document.createElement('div');
        sceneElement.className = 'mb-8 p-4 border rounded';
        sceneElement.innerHTML = `
            <h3 class="text-xl font-bold mb-2">Chapter ${sceneData.chapter}, Scene ${sceneData.scene_number}</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                ${sceneData.paragraphs.map(paragraph => `
                    <div class="bg-white p-4 rounded shadow">
                        <img src="${paragraph.image_url}" alt="Paragraph Image" class="w-full h-48 object-cover mb-4" onerror="this.onerror=null; this.src='/static/images/placeholder.svg';">
                        <p>${paragraph.content}</p>
                    </div>
                `).join('')}
            </div>
            <audio controls class="audio-player mt-4 w-full">
                <source src="${sceneData.audio_url}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
        `;
        sceneContainer.appendChild(sceneElement);
    }
});
