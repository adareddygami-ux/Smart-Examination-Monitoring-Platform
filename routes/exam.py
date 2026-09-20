import os
import base64
import cv2
import numpy as np
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user

from extensions import db
from models.exam_session import ExamSession
from models.question import Question
from models.candidate_answer import CandidateAnswer
from utils.cv_engine import verify_face, analyze_frame
from utils.rule_engine import evaluate_session_events
from utils.clustering import perform_behaviour_clustering

exam_bp = Blueprint('exam', __name__)

def get_active_session():
    active_states = ['SESSION CREATED', 'READY TO START', 'EXAM STARTED', 'EXAM PAUSED', 'EXAM RESUMED']
    return ExamSession.query.filter(
        ExamSession.candidate_id == current_user.id,
        ExamSession.status.in_(active_states)
    ).order_by(ExamSession.id.desc()).first()

@exam_bp.route('/exam/verify', methods=['GET', 'POST'])
@login_required
def verify():
    session = get_active_session()
    if not session or session.status != 'SESSION CREATED':
        flash('No new session to verify.', 'warning')
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        try:
            data = request.get_json(silent=True)
            if not data or 'image' not in data:
                return jsonify({'success': False, 'message': 'No live camera image provided.'}), 400

            image_parts = data['image'].split(',', 1)
            if len(image_parts) != 2:
                return jsonify({'success': False, 'message': 'Invalid camera image format.'}), 400

            img_data = base64.b64decode(image_parts[1])
            nparr = np.frombuffer(img_data, np.uint8)
            live_frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if live_frame is None:
                return jsonify({'success': False, 'message': 'The live camera frame could not be read.'}), 400

            is_verified = verify_face(current_user.photo_path, live_frame)
        except Exception as error:
            current_app.logger.exception('Live identity verification failed: %s', error)
            return jsonify({'success': False, 'message': 'Camera verification is temporarily unavailable. Please try again.'}), 500

        if is_verified:
            session.verification_status = 'Verified'
            session.status = 'READY TO START'
            db.session.commit()
            return jsonify({'success': True, 'message': 'Identity verified successfully!'})
        else:
            session.verification_status = 'Failed'
            db.session.commit()
            return jsonify({'success': False, 'message': 'Identity verification failed.'})
            
    return render_template('exam_verify.html', title='Face Verification')

@exam_bp.route('/exam/start', methods=['POST'])
@login_required
def start():
    session = get_active_session()
    if not session or session.status != 'READY TO START':
        flash('Cannot start exam.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
        
    session.status = 'EXAM STARTED'
    session.exam_started_at = datetime.utcnow()
    
    # Generate 3 random questions from DB
    all_questions = Question.query.all()
    import random
    selected = random.sample(all_questions, 3) if len(all_questions) >= 3 else all_questions
    
    # Store initial placeholder CandidateAnswers for ordering
    for q in selected:
        ans = CandidateAnswer(
            session_id=session.id,
            candidate_id=current_user.id,
            question_id=q.id
        )
        db.session.add(ans)
    
    db.session.commit()
    
    return redirect(url_for('exam.play', idx=0))

@exam_bp.route('/exam/play/<int:idx>', methods=['GET', 'POST'])
@login_required
def play(idx):
    session = get_active_session()
    if not session or session.status not in ['EXAM STARTED', 'EXAM RESUMED']:
        flash('Exam is not active.', 'warning')
        return redirect(url_for('dashboard.dashboard'))

    answers = CandidateAnswer.query.filter_by(session_id=session.id).order_by(CandidateAnswer.id).all()
    total = len(answers)

    if idx < 0 or idx >= total:
        return redirect(url_for('exam.play', idx=0))

    current_ans = answers[idx]
    current_q = current_ans.question
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        selected_option = request.form.get('answer')
        if selected_option:
            current_ans.selected_answer = selected_option
            current_ans.is_correct = (selected_option == current_q.correct_answer)
            db.session.commit()

        if 'next' in request.form and idx < total - 1:
            if is_ajax:
                next_idx = idx + 1
                next_ans = answers[next_idx]
                next_q = next_ans.question
                return jsonify({
                    'success': True,
                    'current_idx': next_idx,
                    'total': total,
                    'question': {
                        'question': next_q.question,
                        'option_a': next_q.option_a,
                        'option_b': next_q.option_b,
                        'option_c': next_q.option_c,
                        'option_d': next_q.option_d,
                        'category': next_q.category,
                        'difficulty': next_q.difficulty,
                    },
                    'saved_answer': next_ans.selected_answer,
                    'form_action': url_for('exam.play', idx=next_idx)
                })
            return redirect(url_for('exam.play', idx=idx + 1))
        elif 'prev' in request.form and idx > 0:
            if is_ajax:
                prev_idx = idx - 1
                prev_ans = answers[prev_idx]
                prev_q = prev_ans.question
                return jsonify({
                    'success': True,
                    'current_idx': prev_idx,
                    'total': total,
                    'question': {
                        'question': prev_q.question,
                        'option_a': prev_q.option_a,
                        'option_b': prev_q.option_b,
                        'option_c': prev_q.option_c,
                        'option_d': prev_q.option_d,
                        'category': prev_q.category,
                        'difficulty': prev_q.difficulty,
                    },
                    'saved_answer': prev_ans.selected_answer,
                    'form_action': url_for('exam.play', idx=prev_idx)
                })
            return redirect(url_for('exam.play', idx=idx - 1))
        elif 'submit' in request.form:
            session.status = 'EXAM SUBMITTED'
            session.exam_completed_at = datetime.utcnow()

            correct_count = sum(1 for a in answers if a.is_correct)
            session.questions_attempted = sum(1 for a in answers if a.selected_answer)
            session.score = correct_count

            db.session.commit()

            evaluate_session_events(session.id, session.candidate_id)
            perform_behaviour_clustering()

            if is_ajax:
                return jsonify({'success': True, 'redirect_url': url_for('dashboard.report', session_id=session.id)})
            return redirect(url_for('dashboard.report', session_id=session.id))

    from models.monitoring_event import MonitoringEvent
    events = MonitoringEvent.query.filter_by(session_id=session.id).all()
    stats = {
        'tab_switches': sum(1 for e in events if e.event_type == 'TAB_SWITCH'),
        'focus_losses': sum(1 for e in events if e.event_type == 'FOCUS_LOST'),
        'eyes_not_detected': sum(1 for e in events if e.event_type == 'EYES_NOT_DETECTED')
    }

    return render_template(
        'exam_play.html',
        title='Examination',
        question=current_q,
        current_idx=idx,
        total=total,
        saved_answer=current_ans.selected_answer,
        session_id=session.id,
        stats=stats
    )


