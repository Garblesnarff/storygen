import logging
from flask import Blueprint, render_template, request, jsonify, Response, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from models import db, User, Story, Scene
from utils.story_generator import generate_book_spec, generate_outline, generate_scene, generate_chapter_scenes
from utils.image_generator import generate_images_for_paragraphs, generate_image_for_paragraph
from utils.text_to_speech import generate_audio_for_scene
import json

main_bp = Blueprint('main', __name__)
logging.basicConfig(level=logging.INFO)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter((User.username == username) | (User.email == email)).first()
        if user:
            flash('Username or email already exists.')
            return redirect(url_for('main.register'))
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful. Please log in.')
        return redirect(url_for('main.login'))
    
    return render_template('register.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Logged in successfully.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password.')
    
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.')
    return redirect(url_for('main.index'))

@main_bp.route('/generate_story', methods=['POST'])
def generate_story():
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to generate a story.'}), 401
    
    topic = request.json['topic']
    
    book_spec = generate_book_spec(topic)
    outline = generate_outline(book_spec)
    
    new_story = Story(user_id=session['user_id'], topic=topic, book_spec=book_spec, outline=outline)
    db.session.add(new_story)
    db.session.commit()
    
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
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to get the next scene.'}), 401
    
    story_id = request.json['story_id']
    story = Story.query.filter_by(id=story_id, user_id=session['user_id']).first()
    if not story:
        return jsonify({'error': 'Story not found or you do not have permission to access it.'}), 404

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
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to generate a scene.'}), 401
    
    try:
        story_id = request.json['story_id']
        act = request.json['act']
        chapter = request.json['chapter']
        scene_number = request.json['scene_number']
        
        story = Story.query.filter_by(id=story_id, user_id=session['user_id']).first()
        if not story:
            return jsonify({"error": "Story not found or you do not have permission to access it."}), 404

        def generate():
            yield json.dumps({"status": "generating_paragraphs"}) + "\n"
            logging.info("Starting scene generation")

            paragraphs = generate_scene(story.book_spec, story.outline, act, chapter, scene_number)
            yield json.dumps({"status": "paragraphs_generated"}) + "\n"

            logging.info("Generating images and audio for paragraphs")
            paragraphs_with_images = generate_images_for_paragraphs([{'content': p} for p in paragraphs])
            for i, para in enumerate(paragraphs_with_images):
                logging.info(f"Generating audio for paragraph {i+1}")
                audio_url = generate_audio_for_scene(para['content'])
                para['audio_url'] = audio_url
                yield json.dumps({"status": "image_generated", "paragraph": para, "index": i}) + "\n"

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
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to generate chapter scenes.'}), 401
    
    try:
        story_id = request.json['story_id']
        act = request.json['act']
        chapter = request.json['chapter']
        
        story = Story.query.filter_by(id=story_id, user_id=session['user_id']).first()
        if not story:
            return jsonify({'error': 'Story not found or you do not have permission to access it.'}), 404
        
        scenes = generate_chapter_scenes(story.book_spec, story.outline, act, chapter)
        
        return jsonify({
            'act': act,
            'chapter': chapter,
            'scenes': scenes
        })
    except Exception as e:
        logging.error(f"Error in generate_chapter_scenes_route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/my_stories')
def my_stories():
    if 'user_id' not in session:
        flash('You must be logged in to view your stories.')
        return redirect(url_for('main.login'))
    
    user = User.query.get(session['user_id'])
    stories = Story.query.filter_by(user_id=user.id).order_by(Story.created_at.desc()).all()
    return render_template('my_stories.html', stories=stories)

@main_bp.route('/story/<int:story_id>')
def view_story(story_id):
    if 'user_id' not in session:
        flash('You must be logged in to view a story.')
        return redirect(url_for('main.login'))
    
    story = Story.query.filter_by(id=story_id, user_id=session['user_id']).first()
    if not story:
        flash('Story not found or you do not have permission to view it.')
        return redirect(url_for('main.my_stories'))
    
    scenes = Scene.query.filter_by(story_id=story.id).order_by(Scene.act, Scene.chapter, Scene.scene_number).all()
    return render_template('view_story.html', story=story, scenes=scenes)

@main_bp.route('/edit_scene/<int:scene_id>', methods=['GET', 'POST'])
def edit_scene(scene_id):
    if 'user_id' not in session:
        flash('You must be logged in to edit a scene.')
        return redirect(url_for('main.login'))
    
    scene = Scene.query.get_or_404(scene_id)
    story = Story.query.get(scene.story_id)
    
    if story.user_id != session['user_id']:
        flash('You do not have permission to edit this scene.')
        return redirect(url_for('main.my_stories'))
    
    if request.method == 'POST':
        content = request.form.get('content')
        scene.content = json.dumps([{'content': content, 'image_url': scene.image_url, 'audio_url': scene.audio_url}])
        db.session.commit()
        flash('Scene updated successfully.')
        return redirect(url_for('main.view_story', story_id=story.id))
    
    scene_content = json.loads(scene.content)[0]['content'] if scene.content else ''
    return render_template('edit_scene.html', scene=scene, content=scene_content)

@main_bp.route('/regenerate_image/<int:scene_id>', methods=['POST'])
def regenerate_image_route(scene_id):
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to regenerate an image.'}), 401
    
    scene = Scene.query.get_or_404(scene_id)
    story = Story.query.get(scene.story_id)
    
    if story.user_id != session['user_id']:
        return jsonify({'error': 'You do not have permission to regenerate this image.'}), 403
    
    try:
        logging.info(f'Raw scene content: {scene.content}')
        scene_data = json.loads(scene.content)
        if not isinstance(scene_data, list) or len(scene_data) == 0:
            raise ValueError('Invalid scene data format')
        
        scene_content = scene_data[0]['content']
        new_image_url = generate_image_for_paragraph(scene_content)
        
        scene_data[0]['image_url'] = new_image_url
        scene.content = json.dumps(scene_data)
        db.session.commit()
        
        return jsonify({'new_image_url': new_image_url})
    except json.JSONDecodeError as e:
        logging.error(f'JSON parsing error in regenerate_image: {str(e)}')
        return jsonify({'error': 'Invalid scene data format'}), 400
    except ValueError as e:
        logging.error(f'Value error in regenerate_image: {str(e)}')
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f'Error in regenerate_image: {str(e)}')
        return jsonify({'error': 'An unexpected error occurred'}), 500