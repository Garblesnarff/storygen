import os
from langchain_community.chat_models import ChatOpenAI

openai_api_key = os.environ.get('OPENAI_API_KEY')

if not openai_api_key:
    print("WARNING: OPENAI_API_KEY is not set. Some features may not work.")
    llm = None
else:
    llm = ChatOpenAI(openai_api_key=openai_api_key)

def generate_book_spec(topic):
    if not llm:
        return "Error: OpenAI API key is not set. Unable to generate book specification."
    prompt = f"Create a book specification for a story about {topic}. Include genre, setting, main characters, and a brief premise."
    response = llm.predict(prompt)
    return response

def generate_outline(book_spec):
    if not llm:
        return "Error: OpenAI API key is not set. Unable to generate outline."
    prompt = f"Based on this book specification, create a detailed chapter-by-chapter outline for the story:\n\n{book_spec}"
    response = llm.predict(prompt)
    return response

def generate_scene(book_spec, outline, chapter, scene_number):
    if not llm:
        return "Error: OpenAI API key is not set. Unable to generate scene."
    prompt = f"""
    Given this book specification and outline, write a detailed scene for Chapter {chapter}, Scene {scene_number}.
    
    Book Specification:
    {book_spec}
    
    Outline:
    {outline}
    
    Write a vivid, engaging scene with dialogue and description.
    """
    response = llm.predict(prompt)
    return response
