import os
from groq import Groq
import google.generativeai as genai

groq_api_key = os.environ.get('GROQ_API_KEY')
gemini_api_key = os.environ.get('GEMINI_API_KEY')

groq_client = Groq(api_key=groq_api_key)
genai.configure(api_key=gemini_api_key)

class BrainstormingAgent:
    def __init__(self):
        self.model = "gemma2-9b-it"

    def generate_log_line(self, topic):
        prompt = f"Generate a log line for a story based on the topic: '{topic}'. Use Blake Snyder's format: On the verge of a stasis=death moment, a flawed protagonist has a catalyst and breaks into Act Two; but when the midpoint happens, they must learn the theme stated, before Act Three leads to the finale where the flawed protagonist defeats (or doesn't defeat) the antagonistic force."
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an expert storyteller."},
                {"role": "user", "content": prompt}
            ],
            model=self.model,
        )
        return completion.choices[0].message.content

class StoryStructureAgent:
    def __init__(self):
        self.model = "llama-3.1-70b-versatile"

    def generate_5_act_structure(self, log_line):
        prompt = f"Based on this log line: '{log_line}', generate a 5-act story structure. Include a brief description for each act: Exposition, Rising Action, Climax, Falling Action, and Resolution."
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an expert story structure creator."},
                {"role": "user", "content": prompt}
            ],
            model=self.model,
        )
        return completion.choices[0].message.content

class SceneCreationAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_scene(self, act_structure, act_number, scene_number):
        prompt = f"""
        Based on this 5-act story structure:
        {act_structure}
        
        Generate a detailed scene for Act {act_number}, Scene {scene_number}. 
        Include character interactions, dialogue, and vivid descriptions. 
        Aim for 3-5 paragraphs.
        """
        response = self.model.generate_content(prompt)
        return response.text
