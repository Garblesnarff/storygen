import logging
from flask import Blueprint, render_template, request, jsonify, Response, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from models import db, User, Story, Scene
from utils.story_generator import generate_book_spec, generate_outline, generate_scene, generate_chapter_scenes
from utils.image_generator import generate_images_for_paragraphs, get_flux_image
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
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password.')
    
    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))

@main_bp.route('/generate_story', methods=['POST'])
@login_required
def generate_story():
    topic = request.json['topic']
    
    book_spec = generate_book_spec(topic)
    outline = generate_outline(book_spec)
    
    new_story = Story(user_id=current_user.id, topic=topic, book_spec=book_spec, outline=outline)
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
@login_required
def get_next_scene():
    story_id = request.json['story_id']
    story = Story.query.filter_by(id=story_id, user_id=current_user.id).first()
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
@login_required
def generate_scene_route():
    try:
        story_id = request.json['story_id']
        act = request.json['act']
        chapter = request.json['chapter']
        scene_number = request.json['scene_number']
        
        story = Story.query.filter_by(id=story_id, user_id=current_user.id).first()
        if not story:
            return jsonify({"error": "Story not found or you do not have permission to access it."}), 404

        def generate():
            yield json.dumps({"status": "generating_paragraphs"}) + "\n"
            logging.info("Starting scene generation")

            paragraphs = generate_scene(story.book_spec, story.outline, act, chapter, scene_number)
            yield json.dumps({"status": "paragraphs_generated"}) + "\n"

            logging.info("Generating images and audio for paragraphs")
            paragraphs_with_images = generate_images_for_paragraphs([{'content': p} for p in paragraphs])
            scene = Scene.query.filter_by(story_id=story_id, act=act, chapter=chapter, scene_number=scene_number).first()
            if not scene:
                scene = Scene(story_id=story_id, act=act, chapter=chapter, scene_number=scene_number)
                db.session.add(scene)
                db.session.commit()

            for i, para in enumerate(paragraphs_with_images):
                logging.info(f"Generating audio for paragraph {i+1}")
                audio_url = generate_audio_for_scene(para['content'])
                para['audio_url'] = audio_url
                para['scene_id'] = scene.id
                yield json.dumps({"status": "image_generated", "paragraph": para, "index": i}) + "\n"

            scene_content = json.dumps(paragraphs_with_images)
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
@login_required
def generate_chapter_scenes_route():
    try:
        story_id = request.json['story_id']
        act = request.json['act']
        chapter = request.json['chapter']
        
        story = Story.query.filter_by(id=story_id, user_id=current_user.id).first()
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
@login_required
def my_stories():
    stories = Story.query.filter_by(user_id=current_user.id).order_by(Story.created_at.desc()).all()
    return render_template('my_stories.html', stories=stories)

@main_bp.route('/story/<int:story_id>')
@login_required
def view_story(story_id):
    story = Story.query.filter_by(id=story_id, user_id=current_user.id).first()
    if not story:
        flash('Story not found or you do not have permission to view it.')
        return redirect(url_for('main.my_stories'))
    
    scenes = Scene.query.filter_by(story_id=story.id).order_by(Scene.act, Scene.chapter, Scene.scene_number).all()
    return render_template('view_story.html', story=story, scenes=scenes)

@main_bp.route('/continue_story/<int:story_id>')
@login_required
def continue_story(story_id):
    story = Story.query.filter_by(id=story_id, user_id=current_user.id).first()
    if not story:
        flash('Story not found or you do not have permission to continue it.')
        return redirect(url_for('main.my_stories'))
    
    return render_template('continue_story.html', story=story)

@main_bp.route('/edit_scene/<int:scene_id>', methods=['GET', 'POST'])
@login_required
def edit_scene(scene_id):
    scene = Scene.query.get_or_404(scene_id)
    story = Story.query.get_or_404(scene.story_id)
    
    if story.user_id != current_user.id:
        flash('You do not have permission to edit this scene.')
        return redirect(url_for('main.my_stories'))
    
    if request.method == 'POST':
        content = request.form.get('content')
        scene.content = json.dumps([{'content': content}])
        db.session.commit()
        flash('Scene updated successfully.')
        return redirect(url_for('main.view_story', story_id=story.id))
    
    scene_content = json.loads(scene.content)[0]['content'] if scene.content else ''
    return render_template('edit_scene.html', scene=scene, content=scene_content)

@main_bp.route('/regenerate_image/<int:scene_id>', methods=['POST'])
@login_required
def regenerate_image(scene_id):
    try:
        logging.info(f'Regenerating image for scene {scene_id}')
        scene = Scene.query.get_or_404(scene_id)
        story = Story.query.get_or_404(scene.story_id)
        
        if story.user_id != current_user.id:
            logging.warning(f'Unauthorized access attempt for scene {scene_id}')
            return jsonify({'error': 'You do not have permission to edit this scene.'}), 403
        
        content = request.json.get('content', '')
        logging.info(f'Generating new image for content: {content[:50]}...')
        new_image_url = get_flux_image(content)
        
        if new_image_url:
            scene_content = json.loads(scene.content)
            scene_content[0]['image_url'] = new_image_url
            scene.content = json.dumps(scene_content)
            db.session.commit()
            logging.info(f'Image regenerated successfully for scene {scene_id}')
            return jsonify({'success': True, 'image_url': new_image_url})
        else:
            logging.error(f'Failed to generate new image for scene {scene_id}')
            return jsonify({'error': 'Failed to generate new image'}), 500
    except Exception as e:
        logging.error(f'Error in regenerate_image: {str(e)}')
        return jsonify({'error': str(e)}), 500
