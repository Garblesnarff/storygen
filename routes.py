import logging
from flask import Blueprint, render_template, request, jsonify, Response, current_app
from models import db, Story, Scene
from utils.story_generator import generate_book_spec, generate_outline, generate_scene, generate_chapter_scenes
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
    
    # Generate book specification using BrainstormingAgent
    book_spec = generate_book_spec(topic)
    
    # Generate story outline using StoryStructureAgent
    outline = generate_outline(book_spec)
    
    # Save to database
    new_story = Story(topic=topic, book_spec=book_spec, outline=outline)
    db.session.add(new_story)
    db.session.commit()
    
    # Create initial scenes
    acts = 5
    chapters_per_act = 5
    scenes_per_chapter = 3
    
    for act in range(1, acts + 1):
        for chapter in range(1, chapters_per_act + 1):
            for scene in range(1, scenes_per_chapter + 1):
                new_scene = Scene(
                    story_id=new_story.id,
                    act=act,
                    chapter=chapter,
                    scene_number=scene,
                    content="",
                    is_generated=False
                )
                db.session.add(new_scene)
    
    db.session.commit()
    
    return jsonify({
        'story_id': new_story.id,
        'book_spec': book_spec,
        'outline': outline
    })

@main_bp.route('/get_next_scene', methods=['POST'])
def get_next_scene():
    story_id = request.json['story_id']
    story = Story.query.get(story_id)
    if not story:
        return jsonify({'error': 'Story not found'}), 404

    # Find the next scene that hasn't been generated
    next_scene = Scene.query.filter_by(story_id=story_id, is_generated=False).order_by(Scene.act, Scene.chapter, Scene.scene_number).first()

    if next_scene:
        return jsonify({
            'act': next_scene.act,
            'chapter': next_scene.chapter,
            'scene_number': next_scene.scene_number
        })
    else:
        return jsonify({'message': 'All scenes have been generated'}), 200

@main_bp.route('/generate_scene', methods=['POST'])
def generate_scene_route():
    try:
        story_id = request.json['story_id']
        act = request.json['act']
        chapter = request.json['chapter']
        scene_number = request.json['scene_number']
        
        def generate():
            with current_app.app_context():
                yield json.dumps({"status": "generating_paragraphs"}) + "\n"
                logging.info("Starting scene generation")
                
                story = Story.query.get(story_id)
                if not story:
                    yield json.dumps({"error": "Story not found"}) + "\n"
                    return

                paragraphs = generate_scene(story.book_spec, story.outline, act, chapter, scene_number)
                yield json.dumps({"status": "paragraphs_generated"}) + "\n"

                logging.info("Generating images and audio for paragraphs")
                paragraphs_with_images = generate_images_for_paragraphs([{'content': p} for p in paragraphs])
                for i, para in enumerate(paragraphs_with_images):
                    logging.info(f"Generating audio for paragraph {i+1}")
                    audio_url = generate_audio_for_scene(para['content'])
                    para['audio_url'] = audio_url
                    yield json.dumps({"status": "image_generated", "paragraph": para, "index": i}) + "\n"

                # Save to database
                scene_content = json.dumps(paragraphs_with_images)
                scene = Scene.query.filter_by(story_id=story_id, act=act, chapter=chapter, scene_number=scene_number).first()
                if scene:
                    scene.content = scene_content
                    scene.is_generated = True
                    db.session.commit()
                
                yield json.dumps({"status": "complete", "scene_id": scene.id}) + "\n"
        
        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        logging.error(f"Error in generate_scene_route: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/generate_chapter_scenes', methods=['POST'])
def generate_chapter_scenes_route():
    try:
        story_id = request.json['story_id']
        act = request.json['act']
        chapter = request.json['chapter']
        
        with current_app.app_context():
            story = Story.query.get(story_id)
            if not story:
                return jsonify({'error': 'Story not found'}), 404
        
            scenes = generate_chapter_scenes(story.book_spec, story.outline, act, chapter)
        
        return jsonify({
            'act': act,
            'chapter': chapter,
            'scenes': scenes
        })
    except Exception as e:
        logging.error(f"Error in generate_chapter_scenes_route: {str(e)}")
        return jsonify({'error': str(e)}), 500
