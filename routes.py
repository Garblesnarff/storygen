from flask import Blueprint, render_template, request, jsonify
from models import db, Story, Scene
from utils.story_generator import generate_book_spec, generate_outline, generate_scene
from utils.image_generator import get_image_for_scene
from utils.text_to_speech import generate_audio_for_scene

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/generate_story', methods=['POST'])
def generate_story():
    topic = request.json['topic']
    
    # Generate book specification using Groq
    book_spec = generate_book_spec(topic)
    
    # Generate story outline using Gemini
    outline = generate_outline(book_spec)
    
    # Save to database
    new_story = Story(topic=topic, book_spec=book_spec, outline=outline)
    db.session.add(new_story)
    db.session.commit()
    
    return jsonify({
        'story_id': new_story.id,
        'book_spec': book_spec,
        'outline': outline
    })

@main_bp.route('/generate_scene', methods=['POST'])
def generate_scene_route():
    story_id = request.json['story_id']
    chapter = request.json['chapter']
    scene_number = request.json['scene_number']
    
    story = Story.query.get(story_id)
    if not story:
        return jsonify({'error': 'Story not found'}), 404
    
    # Generate scene content using Groq
    scene_content = generate_scene(story.book_spec, story.outline, chapter, scene_number)
    
    # Get image for scene
    image_url = get_image_for_scene(scene_content)
    
    # Generate audio for scene
    audio_url = generate_audio_for_scene(scene_content)
    
    # Save to database
    new_scene = Scene(story_id=story_id, chapter=chapter, scene_number=scene_number,
                      content=scene_content, image_url=image_url, audio_url=audio_url)
    db.session.add(new_scene)
    db.session.commit()
    
    return jsonify({
        'scene_id': new_scene.id,
        'content': scene_content,
        'image_url': image_url,
        'audio_url': audio_url
    })
