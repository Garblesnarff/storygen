import os
import requests

UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY')

def get_image_for_scene(scene_content):
    # Extract keywords from the scene content
    keywords = extract_keywords(scene_content)
    
    # Search Unsplash for an image
    url = f"https://api.unsplash.com/photos/random?query={keywords}&client_id={UNSPLASH_ACCESS_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        return data['urls']['regular']
    else:
        # Return a placeholder image if the API call fails
        return "/static/images/placeholder.svg"

def extract_keywords(scene_content):
    # This is a simple keyword extraction. In a real application, you might want to use NLP techniques.
    words = scene_content.split()
    keywords = [word for word in words if len(word) > 5][:5]  # Get the first 5 words with more than 5 characters
    return " ".join(keywords)
