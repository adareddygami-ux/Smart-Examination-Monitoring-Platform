import os
import base64
from datetime import datetime
import cv2
import numpy as np
from flask import render_template, redirect, url_for, flash, current_app, request, session
from flask_login import login_required, current_user
from extensions import db
from models.candidate import Candidate
from utils.camera import capture_photo
from utils.cv_engine import extract_face
from . import camera_bp

@camera_bp.route('/capture/<int:candidate_id>', methods=['GET', 'POST'])
def capture(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    pending_candidate_id = session.get('pending_capture_candidate_id')
    if current_user.is_authenticated:
        if current_user.id != candidate.id:
            flash('Unauthorized photo access.', 'danger')
            return redirect(url_for('dashboard.dashboard'))
    elif pending_candidate_id != candidate.id:
        flash('Please complete registration before capturing a photo.', 'warning')
        return redirect(url_for('auth.register'))
    
    if request.method == 'POST':
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        photo_data = request.form.get('photo_data')
        if photo_data and ',' in photo_data:
            image_bytes = base64.b64decode(photo_data.split(',', 1)[1])
            image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

            if image is None:
                flash('The uploaded photo could not be read. Please try again.', 'danger')
                return redirect(url_for('camera.capture', candidate_id=candidate.id))

            if extract_face(image) is None:
                flash('Please capture a clear photo with exactly one face visible.', 'warning')
                return redirect(url_for('camera.capture', candidate_id=candidate.id))

            safe_name = ''.join(
                char for char in candidate.full_name
                if char.isalpha() or char.isdigit() or char == ' '
            ).rstrip().replace(' ', '_').lower()
            filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(os.path.join(upload_folder, filename), image)
        else:
            # Keep the existing desktop-camera fallback available.
            filename = capture_photo(upload_folder, candidate.full_name)
            if filename:
                full_path = os.path.join(upload_folder, filename)
                image = cv2.imread(full_path)
                if image is None or extract_face(image) is None:
                    os.remove(full_path) if os.path.exists(full_path) else None
                    flash('Please capture a photo with exactly one face visible.', 'warning')
                    return redirect(url_for('camera.capture', candidate_id=candidate.id))
        
        if filename:
            old_photo = candidate.photo_path
            candidate.photo_path = filename
            db.session.commit()
            session.pop('pending_capture_candidate_id', None)

            if old_photo and old_photo != filename:
                old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], old_photo)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass

            if current_user.is_authenticated:
                flash('Profile photo updated successfully!', 'success')
                return redirect(url_for('dashboard.dashboard'))

            flash('Photo captured successfully! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Photo capture canceled or failed. Please try again.', 'danger')
            return redirect(url_for('camera.capture', candidate_id=candidate.id))
            
    return render_template('capture.html', title='Capture Photo', candidate=candidate)

