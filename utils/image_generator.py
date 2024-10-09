import os
import requests
import base64
import time
import logging
from together import Together
from io import BytesIO
from PIL import Image

UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY')
TOGETHER_API_KEY = os.environ.get('TOGETHER_API_KEY')

together_client = Together(api_key=TOGETHER_API_KEY)

logging.basicConfig(level=logging.INFO)

def get_unsplash_image(keywords):
    url = f"https://api.unsplash.com/photos/random?query={keywords}&client_id={UNSPLASH_ACCESS_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['urls']['regular']
    except requests.exceptions.RequestException as e:
        logging.error(f"Unsplash API error: {e}")
        return None

def get_flux_image(prompt):
    try:
        logging.info(f"Generating image for prompt: {prompt}")
        response = together_client.images.generate(
            prompt=f"A scene depicting: {prompt}",
            model="black-forest-labs/FLUX.1-schnell-Free",
            width=1024,
            height=768,
            steps=4,
            n=1,
            response_format="b64_json"
        )
        logging.info("Image generated successfully")
        
        image_data = response.data[0].b64_json
        image = Image.open(BytesIO(base64.b64decode(image_data)))
        
        # Save the image to a file in the static/images directory
        image_filename = f"generated_image_{int(time.time())}_{hash(prompt)}.png"
        image_path = os.path.join('static', 'images', image_filename)
        image.save(image_path)
        logging.info(f"Image saved to {image_path}")
        
        return f"/static/images/{image_filename}"
    except Exception as e:
        logging.error(f"Flux API error: {e}")
        return None

def generate_images_for_paragraphs(paragraphs):
    logging.info(f"Generating images for {len(paragraphs)} paragraphs")
    for i, paragraph in enumerate(paragraphs):
        logging.info(f"Generating image for paragraph {i + 1}")
        image_url = get_flux_image(paragraph['content'])
        if image_url:
            paragraph['image_url'] = image_url
            logging.info(f"Image URL set for paragraph {i + 1}: {image_url}")
        else:
            paragraph['image_url'] = "/static/images/placeholder.svg"
            logging.warning(f"Using placeholder image for paragraph {i + 1}")
    return paragraphs

def extract_keywords(scene_content):
    words = scene_content.split()
    keywords = [word for word in words if len(word) > 5][:5]
    return " ".join(keywords)
