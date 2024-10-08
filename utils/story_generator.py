import os
from groq import Groq
import google.generativeai as genai

groq_api_key = os.environ.get('GROQ_API_KEY')
gemini_api_key = os.environ.get('GEMINI_API_KEY')

groq_client = Groq(api_key=groq_api_key)
genai.configure(api_key=gemini_api_key)

def generate_book_spec(topic):
    prompt = f"Create a book specification for a story about {topic}. Include genre, setting, main characters, and a brief premise."
    completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful assistant for fiction writing."},
            {"role": "user", "content": prompt}
        ],
        model="mixtral-8x7b-32768",
    )
    return completion.choices[0].message.content

def generate_outline(book_spec):
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"Based on this book specification, create a detailed chapter-by-chapter outline for the story:\n\n{book_spec}"
    response = model.generate_content(prompt)
    return response.text

def generate_scene(book_spec, outline, chapter, scene_number):
    prompt = f"""
    Given this book specification and outline, write a detailed scene for Chapter {chapter}, Scene {scene_number}.
    
    Book Specification:
    {book_spec}
    
    Outline:
    {outline}
    
    Write a vivid, engaging scene with dialogue and description. Divide the scene into 3-5 paragraphs.
    For each paragraph, return a dictionary with 'content' and a placeholder 'image_url'.
    """
    completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are an expert fiction writer. Write detailed scenes with lively dialogue."},
            {"role": "user", "content": prompt}
        ],
        model="mixtral-8x7b-32768",
    )
    
    scene_content = completion.choices[0].message.content
    paragraphs = [p.strip() for p in scene_content.split('\n\n') if p.strip()]
    
    return [{'content': p, 'image_url': ''} for p in paragraphs]
