import logging
from flask import Blueprint, render_template, request, jsonify, Response
from models import db, Story, Scene
from utils.story_generator import generate_book_spec, generate_outline, generate_scene
from utils.image_generator import generate_images_for_paragraphs
from utils.text_to_speech import generate_audio_for_scene
import json

main_bp = Blueprint('main', __name__)
logging.basicConfig(level=logging.INFO)

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
    try:
        story_id = request.json['story_id']
        chapter = request.json['chapter']
        scene_number = request.json['scene_number']
        
        story = Story.query.get(story_id)
        if not story:
            return jsonify({'error': 'Story not found'}), 404
        
        def generate():
            yield json.dumps({"status": "generating_paragraphs"}) + "\n"
            logging.info("Starting scene generation")
            paragraphs = generate_scene(story.book_spec, story.outline, chapter, scene_number)
            yield json.dumps({"status": "paragraphs_generated"}) + "\n"

            logging.info("Generating images for paragraphs")
            paragraphs_with_images = generate_images_for_paragraphs([{'content': p} for p in paragraphs])
            for i, para in enumerate(paragraphs_with_images):
                yield json.dumps({"status": "image_generated", "paragraph": para, "index": i}) + "\n"

            logging.info("Generating audio for scene")
            yield json.dumps({"status": "generating_audio"}) + "\n"
            scene_content = " ".join([p['content'] for p in paragraphs_with_images])
            audio_url = generate_audio_for_scene(scene_content)
            yield json.dumps({"status": "audio_generated", "audio_url": audio_url}) + "\n"
            
            # Save to database
            new_scene = Scene(story_id=story_id, chapter=chapter, scene_number=scene_number,
                              content=scene_content, audio_url=audio_url)
            db.session.add(new_scene)
            db.session.commit()
            
            yield json.dumps({"status": "complete", "scene_id": new_scene.id}) + "\n"
        
        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        logging.error(f"Error in generate_scene_route: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
