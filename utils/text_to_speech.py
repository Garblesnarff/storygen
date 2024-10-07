import os
from google.cloud import texttospeech
import time

google_credentials = os.environ.get('GOOGLE_CLOUD_TTS_CREDENTIALS')

if not google_credentials:
    print("WARNING: GOOGLE_CLOUD_TTS_CREDENTIALS is not set. Text-to-speech functionality may not work.")
    tts_client = None
else:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_credentials
    tts_client = texttospeech.TextToSpeechClient()

def generate_audio_for_scene(scene_content):
    if not tts_client:
        print("Error: Google Cloud Text-to-Speech credentials are not set. Unable to generate audio.")
        return "/static/audio/placeholder.mp3"
    
    synthesis_input = texttospeech.SynthesisInput(text=scene_content)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Wavenet-D",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    
    # Save the audio file
    filename = f"scene_audio_{int(time.time())}.mp3"
    filepath = os.path.join('static', 'audio', filename)
    with open(filepath, "wb") as out:
        out.write(response.audio_content)
    
    return f"/static/audio/{filename}"
