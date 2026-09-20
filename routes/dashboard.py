import csv
import io
from flask import render_template, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from extensions import db
from models.exam_session import ExamSession
from models.session_log import SessionLog
from models.cheating_event import CheatingEvent
from models.monitoring_event import MonitoringEvent
from models.violation import Violation
from models.authentication_log import AuthenticationLog
from models.candidate_answer import CandidateAnswer
from utils.rule_engine import evaluate_session_events, update_integrity_score
from utils.clustering import perform_behaviour_clustering
from . import dashboard_bp
from datetime import datetime

@dashboard_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('index.html', title='Home')

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    # Fetch active session using new states
    active_states = ['SESSION CREATED', 'READY TO START', 'EXAM STARTED', 'EXAM PAUSED', 'EXAM RESUMED']
    active_session = ExamSession.query.filter(
        ExamSession.candidate_id == current_user.id,
        ExamSession.status.in_(active_states)
    ).order_by(ExamSession.id.desc()).first()
    
    # Fetch all sessions for history (Newest first)
    all_sessions = ExamSession.query.filter_by(
        candidate_id=current_user.id
    ).order_by(ExamSession.id.desc()).all()
    
    # Pre-calculate stats for all sessions
    for session in all_sessions:
        events = MonitoringEvent.query.filter_by(session_id=session.id).all()
        session.tab_switches = sum(1 for e in events if e.event_type == 'TAB_SWITCH')
        session.focus_losses = sum(1 for e in events if e.event_type == 'FOCUS_LOST')
        session.face_absences = sum(1 for e in events if e.event_type == 'FACE_ABSENT')
        session.multiple_faces = sum(1 for e in events if e.event_type == 'MULTIPLE_FACES')
        session.eyes_not_detected = sum(1 for e in events if e.event_type == 'EYES_NOT_DETECTED')
        session.violation_count = Violation.query.filter_by(session_id=session.id).count()

    completed_sessions = [s for s in all_sessions if s.status in ['SESSION COMPLETED', 'EXAM SUBMITTED']]
    
    # Calculate Summary Stats
    total_sessions = len(all_sessions)
    avg_integrity = sum(s.integrity_score for s in completed_sessions) / len(completed_sessions) if completed_sessions else 100
    
    # Highest Risk Session
    highest_risk_session = None
    if completed_sessions:
        # Sort by integrity score ascending (lowest score = highest risk)
        highest_risk_session = sorted(completed_sessions, key=lambda x: x.integrity_score)[0]
        
    latest_exam = all_sessions[0] if all_sessions else None
    
    summary = {
        'total': total_sessions,
        'completed': len(completed_sessions),
        'avg_integrity': round(avg_integrity, 1),
        'highest_risk': highest_risk_session,
        'latest_exam': latest_exam
    }
    
    # Fetch ALL violations for the main violations panel
    all_violations = Violation.query.filter_by(candidate_id=current_user.id).order_by(Violation.id.desc()).all()
    recent_violations = all_violations[:5]  # keep for stat card count

    # Sessions with available reports
    sessions_with_reports = completed_sessions

    # Fetch recent login history
    recent_logins = AuthenticationLog.query.filter_by(candidate_id=current_user.id).order_by(AuthenticationLog.id.desc()).limit(5).all()
    
    # Monitoring Summary for Active Session (if any)
    active_monitoring = None
    if active_session:
        events = MonitoringEvent.query.filter_by(session_id=active_session.id).all()
        active_monitoring = {
            'tab_switches': sum(1 for e in events if e.event_type == 'TAB_SWITCH'),
            'focus_loss': sum(1 for e in events if e.event_type == 'FOCUS_LOST'),
            'face_absence': sum(1 for e in events if e.event_type == 'FACE_ABSENT'),
            'multiple_faces': sum(1 for e in events if e.event_type == 'MULTIPLE_FACES'),
            'eyes_not_detected': sum(1 for e in events if e.event_type == 'EYES_NOT_DETECTED'),
            'total_violations': Violation.query.filter_by(session_id=active_session.id).count()
        }

    # Behaviour Clusters Summary
    cluster_counts = {}
    if completed_sessions:
        for s in completed_sessions:
            if s.behaviour_cluster:
                cluster_counts[s.behaviour_cluster] = cluster_counts.get(s.behaviour_cluster, 0) + 1


    # All monitoring events for this candidate
    all_monitoring_events = MonitoringEvent.query.filter_by(
        candidate_id=current_user.id
    ).order_by(MonitoringEvent.id.desc()).all()

    # Questions & Answers for Assessments tab
    from models.question import Question
    from models.candidate_answer import CandidateAnswer
    questions = Question.query.all()
    candidate_answers = CandidateAnswer.query.filter(
        CandidateAnswer.session_id.in_([s.id for s in all_sessions])
    ).all() if all_sessions else []

    # Analytics trend data (last 10 sessions)
    sessions_rev = list(reversed(all_sessions[-10:]))
    analytics_data = {
        'session_dates': [s.login_time.strftime('%b %d') for s in sessions_rev],
        'integrity_scores': [s.integrity_score for s in sessions_rev],
        'scores': [s.score or 0 for s in sessions_rev],
        'tab_switches': [s.tab_switches for s in sessions_rev],
        'focus_losses': [s.focus_losses for s in sessions_rev],
        'face_absences': [s.face_absences for s in sessions_rev],
        'violation_counts': [s.violation_count for s in sessions_rev],
    }

    # Monitoring summary counts
    monitoring_summary = {
        'tab_switch': sum(1 for e in all_monitoring_events if e.event_type == 'TAB_SWITCH'),
        'focus_lost': sum(1 for e in all_monitoring_events if e.event_type == 'FOCUS_LOST'),
        'face_absent': sum(1 for e in all_monitoring_events if e.event_type == 'FACE_ABSENT'),
        'multiple_faces': sum(1 for e in all_monitoring_events if e.event_type == 'MULTIPLE_FACES'),
        'eyes_not_detected': sum(1 for e in all_monitoring_events if e.event_type == 'EYES_NOT_DETECTED'),
        'total': len(all_monitoring_events),
    }

    return render_template('dashboard.html',
                           title='Dashboard',
                           active_session=active_session,
                           all_sessions=all_sessions,
                           summary=summary,
                           all_violations=all_violations,
                           recent_violations=recent_violations,
                           sessions_with_reports=sessions_with_reports,
                           recent_logins=recent_logins,
                           active_monitoring=active_monitoring,
                           cluster_counts=cluster_counts,
                           all_monitoring_events=all_monitoring_events,
                           monitoring_summary=monitoring_summary,
                           analytics_data=analytics_data,
                           questions=questions,
                           candidate_answers=candidate_answers)


@dashboard_bp.route('/session/<action>', methods=['POST'])
@login_required
def session_action(action):
    # Fetch current session for the user
    active_states = ['SESSION CREATED', 'READY TO START', 'EXAM STARTED', 'EXAM PAUSED', 'EXAM RESUMED']
    active_session = ExamSession.query.filter(
        ExamSession.candidate_id == current_user.id,
        ExamSession.status.in_(active_states)
    ).order_by(ExamSession.id.desc()).first()
    
    if not active_session:
        flash('No active session to modify.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
        
    if action == 'pause' and active_session.status in ['EXAM STARTED', 'EXAM RESUMED']:
        active_session.status = 'EXAM PAUSED'
        log = SessionLog(session_id=active_session.id, event_type='SESSION_PAUSED', description='Candidate paused the session.')
        db.session.add(log)
        flash('Session paused successfully.', 'info')
    elif action == 'resume' and active_session.status == 'EXAM PAUSED':
        active_session.status = 'EXAM RESUMED'
        log = SessionLog(session_id=active_session.id, event_type='SESSION_RESUMED', description='Candidate resumed the session.')
        db.session.add(log)
        flash('Session resumed successfully.', 'success')
    elif action == 'submit':
        active_session.status = 'SESSION COMPLETED'
        active_session.logout_time = datetime.utcnow()
        if not active_session.exam_completed_at:
            active_session.exam_completed_at = datetime.utcnow()
        log = SessionLog(session_id=active_session.id, event_type='SESSION_SUBMITTED', description='Candidate submitted and ended the session.')
        db.session.add(log)
        answers = CandidateAnswer.query.filter_by(session_id=active_session.id).all()
        active_session.questions_attempted = sum(1 for answer in answers if answer.selected_answer)
        active_session.score = sum(1 for answer in answers if answer.is_correct)
        flash('Exam submitted successfully. Session ended.', 'success')
    else:
        flash('Invalid action for current session state.', 'danger')
        
    db.session.commit()
    if action == 'submit':
        evaluate_session_events(active_session.id, active_session.candidate_id)
        update_integrity_score(active_session.id)
        perform_behaviour_clustering()
    return redirect(url_for('dashboard.dashboard'))

@dashboard_bp.route('/session/<int:session_id>/export/<export_format>')
@login_required
def export_session(session_id, export_format):
    session = ExamSession.query.get_or_404(session_id)
    if session.candidate_id != current_user.id or export_format not in ['json', 'csv']:
        return jsonify({'success': False, 'message': 'Export not available.'}), 403

    events = MonitoringEvent.query.filter_by(session_id=session.id).order_by(MonitoringEvent.timestamp).all()
    violations = Violation.query.filter_by(session_id=session.id).order_by(Violation.timestamp).all()
    answers = CandidateAnswer.query.filter_by(session_id=session.id).order_by(CandidateAnswer.id).all()
    payload = {
        'session': {
            'id': session.id,
            'exam_name': session.exam_name,
            'status': session.status,
            'score': session.score,
            'integrity_score': session.integrity_score,
            'risk_level': 'Low' if session.integrity_score >= 75 else ('Medium' if session.integrity_score >= 50 else 'High'),
            'total_cheating_events': session.total_cheating_events,
        },
        'answers': [
            {'question_id': answer.question_id, 'selected_answer': answer.selected_answer, 'is_correct': answer.is_correct}
            for answer in answers
        ],
        'monitoring_events': [
            {'event_type': event.event_type, 'timestamp': event.timestamp.isoformat() if event.timestamp else None, 'duration': event.duration, 'description': event.description}
            for event in events
        ],
        'violations': [
            {'type': violation.violation_type, 'severity': violation.severity, 'timestamp': violation.timestamp.isoformat() if violation.timestamp else None, 'description': violation.description}
            for violation in violations
        ],
    }
    if export_format == 'json':
        return jsonify(payload)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['record_type', 'event_type', 'severity', 'timestamp', 'duration', 'description'])
    for event in payload['monitoring_events']:
        writer.writerow(['monitoring_event', event['event_type'], '', event['timestamp'], event['duration'], event['description']])
    for violation in payload['violations']:
        writer.writerow(['violation', violation['type'], violation['severity'], violation['timestamp'], '', violation['description']])
    return Response(output.getvalue(), mimetype='text/csv', headers={
        'Content-Disposition': f'attachment; filename=session_{session.id}_export.csv'
    })

@dashboard_bp.route('/report/<int:session_id>')
@login_required
def report(session_id):
    session = ExamSession.query.get_or_404(session_id)
    if session.candidate_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
        
    if session.status not in ['SESSION COMPLETED', 'EXAM SUBMITTED']:
        flash('Report not available yet.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
        
    # Fetch questions and candidate answers
    from models.candidate_answer import CandidateAnswer
    answers = CandidateAnswer.query.filter_by(session_id=session.id).order_by(CandidateAnswer.id).all()
    
    # Fetch violations and events
    violations = Violation.query.filter_by(session_id=session.id).order_by(Violation.id).all()
    events = MonitoringEvent.query.filter_by(session_id=session.id).order_by(MonitoringEvent.id).all()
    
    monitoring_stats = {
        'face_present_duration': 0, # Could be calculated based on total session time - face absence time
        'total_face_absence': sum((e.duration or 0) for e in events if e.event_type == 'FACE_ABSENT'),
        'face_absence_intervals': sum(1 for e in events if e.event_type == 'FACE_ABSENT'),
        'multiple_face_events': sum(1 for e in events if e.event_type == 'MULTIPLE_FACES'),
        'eyes_not_detected_intervals': sum(1 for e in events if e.event_type == 'EYES_NOT_DETECTED'),
        'total_eyes_not_detected': sum((e.duration or 0) for e in events if e.event_type == 'EYES_NOT_DETECTED'),
        'tab_switch_count': sum(1 for e in events if e.event_type == 'TAB_SWITCH'),
        'focus_loss_count': sum(1 for e in events if e.event_type == 'FOCUS_LOST'),
        'total_focus_loss_duration': sum((e.duration or 0) for e in events if e.event_type == 'FOCUS_GAINED')
    }
    
    return render_template('monitoring_report.html', 
                           title='Session Monitoring Report', 
                           session=session, 
                           answers=answers,
                           violations=violations,
                           events=events,
                           monitoring_stats=monitoring_stats)
