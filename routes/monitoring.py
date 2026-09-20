import os
import uuid
from flask import Blueprint, request, jsonify, url_for, current_app
from flask_login import login_required, current_user
from extensions import db
from models.monitoring_event import MonitoringEvent
from models.exam_session import ExamSession
from models.candidate_answer import CandidateAnswer
from models.cheating_event import CheatingEvent
from utils.rule_engine import evaluate_session_events, update_integrity_score
from utils.clustering import perform_behaviour_clustering
import base64
import cv2
import numpy as np
from utils.cv_engine import analyze_frame, verify_face
from datetime import datetime

monitoring_bp = Blueprint('monitoring', __name__)

WARNING_EVENT_TYPES = ('TAB_SWITCH', 'FOCUS_LOST', 'FACE_ABSENT', 'EYES_NOT_DETECTED', 'MULTIPLE_FACES')

def auto_submit_after_warning(session):
    update_integrity_score(session.id)
    warning_count = MonitoringEvent.query.filter(
        MonitoringEvent.session_id == session.id,
        MonitoringEvent.event_type.in_(WARNING_EVENT_TYPES)
    ).count()

    if warning_count < 3 or session.status not in ['EXAM STARTED', 'EXAM RESUMED']:
        return False

    answers = CandidateAnswer.query.filter_by(session_id=session.id).all()
    session.status = 'EXAM SUBMITTED'
    session.exam_completed_at = datetime.utcnow()
    session.questions_attempted = sum(1 for answer in answers if answer.selected_answer)
    session.score = sum(1 for answer in answers if answer.is_correct)
    db.session.commit()
    evaluate_session_events(session.id, session.candidate_id)
    perform_behaviour_clustering()
    return True

def get_active_session():
    active_states = ['SESSION CREATED', 'READY TO START', 'EXAM STARTED', 'EXAM PAUSED', 'EXAM RESUMED']
    return ExamSession.query.filter(
        ExamSession.candidate_id == current_user.id,
        ExamSession.status.in_(active_states)
    ).order_by(ExamSession.id.desc()).first()

@monitoring_bp.route('/api/monitoring/browser_event', methods=['POST'])
@login_required
def browser_event():
    session = get_active_session()
    if not session or session.status not in ['EXAM STARTED', 'EXAM RESUMED']:
        return jsonify({'success': False, 'message': 'Exam not active'})
        
    data = request.json
    event_type = data.get('event_type')
    duration = data.get('duration') # might be null
    
    if event_type in ['TAB_SWITCH', 'TAB_RETURN', 'FOCUS_LOST', 'FOCUS_GAINED']:
        event = MonitoringEvent(
            session_id=session.id,
            candidate_id=current_user.id,
            event_type=event_type,
            duration=duration,
            description=f"Browser event: {event_type}"
        )
        db.session.add(event)
        db.session.commit()
        auto_submitted = auto_submit_after_warning(session)
    else:
        auto_submitted = False
        
    return jsonify({
        'success': True,
        'auto_submit': auto_submitted,
        'redirect_url': url_for('dashboard.report', session_id=session.id) if auto_submitted else None
    })

@monitoring_bp.route('/api/monitoring/interaction_event', methods=['POST'])
@login_required
def interaction_event():
    session = get_active_session()
    if not session or session.status not in ['EXAM STARTED', 'EXAM RESUMED']:
        return jsonify({'success': False, 'message': 'Exam not active'})
        
    data = request.json
    event_type = data.get('event_type')
    
    event = MonitoringEvent(
        session_id=session.id,
        candidate_id=current_user.id,
        event_type=event_type,
        description=f"Exam interaction: {event_type}"
    )
    db.session.add(event)
    db.session.commit()
    
    return jsonify({'success': True})

@monitoring_bp.route('/api/monitoring/face_interval', methods=['POST'])
@login_required
def face_interval():
    session = get_active_session()
    if not session or session.status not in ['EXAM STARTED', 'EXAM RESUMED']:
        return jsonify({'success': False, 'message': 'Exam not active'})
        
    data = request.json
    duration = data.get('duration')
    event_type = data.get('event_type', 'FACE_ABSENT')
    
    desc = f"Face missing for {duration} seconds." if event_type == 'FACE_ABSENT' else f"Eyes not detected for {duration} seconds."
    
    event = MonitoringEvent(
        session_id=session.id,
        candidate_id=current_user.id,
        event_type=event_type,
        duration=duration,
        description=desc
    )
    db.session.add(event)
    db.session.commit()
    auto_submitted = auto_submit_after_warning(session)
    return jsonify({
        'success': True,
        'auto_submit': auto_submitted,
        'redirect_url': url_for('dashboard.report', session_id=session.id) if auto_submitted else None
    })

@monitoring_bp.route('/api/monitoring/webcam', methods=['POST'])
@login_required
def webcam():
    session = get_active_session()
    if not session or session.status not in ['EXAM STARTED', 'EXAM RESUMED']:
        return jsonify({'success': False, 'message': 'Exam not active'})
        
    data = request.json
    if not data or 'image' not in data:
        return jsonify({'success': False})
        
    img_data = base64.b64decode(data['image'].split(',')[1])
    nparr = np.frombuffer(img_data, np.uint8)
    live_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    analysis = analyze_frame(live_frame)
    status = analysis['status'] # e.g. 'No Face', 'Multiple Faces', 'Face Present'
    
    frontend_status = status
    
    if status == 'Multiple Faces':
        # Log it directly as a monitoring event
        event = MonitoringEvent(
            session_id=session.id,
            candidate_id=current_user.id,
            event_type='MULTIPLE_FACES',
            description="Multiple faces detected in frame."
        )
        db.session.add(event)
        db.session.commit()
        frontend_status = 'MULTIPLE_FACES'
        evidence_folder = os.path.join(current_app.root_path, 'static', 'cheating_proofs')
        os.makedirs(evidence_folder, exist_ok=True)
        evidence_name = f'{session.id}_{uuid.uuid4().hex}.jpg'
        evidence_path = os.path.join(evidence_folder, evidence_name)
        cv2.imwrite(evidence_path, live_frame)
        db.session.add(CheatingEvent(
            session_id=session.id,
            candidate_id=current_user.id,
            event_type='MULTIPLE_FACES',
            severity='High',
            description='Multiple faces detected in webcam evidence frame.',
            image_path=evidence_name
        ))
        db.session.commit()
        auto_submitted = auto_submit_after_warning(session)
    elif status == 'No Face' or status == 'Looking Away':
        frontend_status = 'NO_FACE'
        auto_submitted = False
    elif status == 'Eyes Not Detected':
        frontend_status = 'EYES_NOT_DETECTED'
        auto_submitted = False
    elif status == 'Face Present':
        frontend_status = 'FACE_PRESENT'
        auto_submitted = False
    else:
        auto_submitted = False

    return jsonify({
        'success': True, 
        'status': frontend_status,
        'auto_submit': auto_submitted,
        'redirect_url': url_for('dashboard.report', session_id=session.id) if auto_submitted else None
    })
