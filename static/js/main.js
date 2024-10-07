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
                
                if (!response.ok) throw new Error('Failed to generate scene');
                
                const sceneData = await response.json();
                displayScene(sceneData);
                
                currentScene++;
                if (currentScene > 3) {  // Assuming 3 scenes per chapter
                    currentChapter++;
                    currentScene = 1;
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to generate scene. Please try again.');
            }
        });
    }

    function displayScene(sceneData) {
        const sceneElement = document.createElement('div');
        sceneElement.className = 'mb-8 p-4 border rounded';
        sceneElement.innerHTML = `
            <h3 class="text-xl font-bold mb-2">Chapter ${sceneData.chapter}, Scene ${sceneData.scene_number}</h3>
            <img src="${sceneData.image_url}" alt="Scene Image" class="scene-image mb-4">
            <p class="mb-4">${sceneData.content}</p>
            <audio controls class="audio-player">
                <source src="${sceneData.audio_url}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
        `;
        sceneContainer.appendChild(sceneElement);
    }
});
