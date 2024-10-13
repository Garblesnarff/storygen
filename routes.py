@main_bp.route('/edit_scene', methods=['POST'])
@login_required
def edit_scene():
    try:
        data = request.json
        story_id = data['story_id']
        scene_id = data['scene_id']
        paragraph_index = data['paragraph_index']
        new_content = data['content']
        
        story = Story.query.filter_by(id=story_id, user_id=current_user.id).first()
        if not story:
            return jsonify({'success': False, 'error': 'Story not found or you do not have permission to edit it.'}), 404
        
        scene = Scene.query.filter_by(id=scene_id, story_id=story_id).first()
        if not scene:
            return jsonify({'success': False, 'error': 'Scene not found.'}), 404
        
        scene_content = json.loads(scene.content)
        if paragraph_index < 0 or paragraph_index >= len(scene_content):
            return jsonify({'success': False, 'error': 'Invalid paragraph index.'}), 400

        # Update the paragraph content
        scene_content[paragraph_index]['content'] = new_content

        # Regenerate the image for the edited paragraph
        new_image_url = get_flux_image(new_content)
        if new_image_url:
            scene_content[paragraph_index]['image_url'] = new_image_url

        # Update the scene content in the database
        scene.content = json.dumps(scene_content)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'scene_id': scene.id,
            'paragraph_index': paragraph_index,
            'new_content': new_content,
            'new_image_url': new_image_url
        })
    except Exception as e:
        logging.error(f"Error in edit_scene: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
