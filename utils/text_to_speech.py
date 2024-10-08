import os
from gtts import gTTS
import time

def generate_audio_for_scene(scene_content):
    # Generate audio using gTTS
    tts = gTTS(text=scene_content, lang='en')
    
    # Save the audio file
    filename = f"scene_audio_{int(time.time())}.mp3"
    filepath = os.path.join('static', 'audio', filename)
    tts.save(filepath)
    
    return f"/static/audio/{filename}"
