import os
import requests
import base64
import time
from together import Together
from io import BytesIO
from PIL import Image

UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY')
TOGETHER_API_KEY = os.environ.get('TOGETHER_API_KEY')

together_client = Together(api_key=TOGETHER_API_KEY)

def get_image_for_scene(scene_content):
    try:
        # Try Unsplash API first
        unsplash_image_url = get_unsplash_image(scene_content)
        if unsplash_image_url:
            return unsplash_image_url
        
        # If Unsplash fails, use Flux API
        flux_image_url = get_flux_image(scene_content)
        if flux_image_url:
            return flux_image_url
    except Exception as e:
        print(f"Error generating image: {e}")
    
    # If both APIs fail, return the placeholder image
    return "/static/images/placeholder.svg"

def get_unsplash_image(keywords):
    url = f"https://api.unsplash.com/photos/random?query={keywords}&client_id={UNSPLASH_ACCESS_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['urls']['regular']
    except requests.exceptions.RequestException as e:
        print(f"Unsplash API error: {e}")
        return None

def get_flux_image(scene_content):
    try:
        response = together_client.images.generate(
            prompt=f"A scene depicting: {scene_content}",
            model="black-forest-labs/FLUX.1-schnell-Free",
            width=1024,
            height=768,
            steps=4,
            n=1,
            response_format="b64_json"
        )
        image_data = response.data[0].b64_json
        image = Image.open(BytesIO(base64.b64decode(image_data)))
        
        # Save the image to a file in the static/images directory
        image_filename = f"generated_image_{int(time.time())}.png"
        image_path = os.path.join('static', 'images', image_filename)
        image.save(image_path)
        
        return f"/static/images/{image_filename}"
    except Exception as e:
        print(f"Flux API error: {e}")
        return None

def extract_keywords(scene_content):
    # This is a simple keyword extraction. In a real application, you might want to use NLP techniques.
    words = scene_content.split()
    keywords = [word for word in words if len(word) > 5][:5]  # Get the first 5 words with more than 5 characters
    return " ".join(keywords)
