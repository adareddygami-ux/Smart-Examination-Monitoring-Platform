from flask import current_app
from extensions import db
from models.monitoring_event import MonitoringEvent
from models.violation import Violation
from models.exam_session import ExamSession

WARNING_EVENT_TYPES = {
    'TAB_SWITCH', 'FOCUS_LOST', 'FACE_ABSENT', 'EYES_NOT_DETECTED', 'MULTIPLE_FACES'
}

def update_integrity_score(session_id):
    events = MonitoringEvent.query.filter_by(session_id=session_id).all()
    session = ExamSession.query.get(session_id)
    if not session:
        return None

    warning_events = [e for e in events if e.event_type in WARNING_EVENT_TYPES]
    penalty = 0
    face_absent_high = current_app.config.get('FACE_ABSENCE_HIGH_SECONDS', 30)
    for event in warning_events:
        if event.event_type == 'MULTIPLE_FACES':
            penalty += 25
        elif event.event_type == 'FACE_ABSENT':
            penalty += 20 if (event.duration or 0) >= face_absent_high else 10
        elif event.event_type == 'EYES_NOT_DETECTED':
            penalty += 8
        else:
            penalty += 10

    session.integrity_score = max(0, 100 - penalty)
    session.total_cheating_events = len(warning_events)
    if session.integrity_score >= 75:
        session.risk_level = 'Low'
    elif session.integrity_score >= 50:
        session.risk_level = 'Medium'
    else:
        session.risk_level = 'High'
    db.session.commit()
    return session.integrity_score

def evaluate_session_events(session_id, candidate_id):
    """
    Evaluates all MonitoringEvents for a session against configured thresholds
    and generates Violations. Returns the list of generated Violations.
    """
    violations = []
    
    # Retrieve thresholds from config
    max_tabs = current_app.config.get('MAX_TAB_SWITCHES', 3)
    max_focus = current_app.config.get('MAX_FOCUS_LOSS', 3)
    face_absent_warn = current_app.config.get('FACE_ABSENCE_WARNING_SECONDS', 5)
    face_absent_high = current_app.config.get('FACE_ABSENCE_HIGH_SECONDS', 30)
    max_multi_face = current_app.config.get('MULTIPLE_FACE_THRESHOLD', 1)
    
    # Fetch events
    events = MonitoringEvent.query.filter_by(session_id=session_id).order_by(MonitoringEvent.timestamp).all()
    
    tab_switch_count = sum(1 for e in events if e.event_type == 'TAB_SWITCH')
    focus_loss_count = sum(1 for e in events if e.event_type == 'FOCUS_LOST')
    face_absences = [e for e in events if e.event_type == 'FACE_ABSENT']
    multi_faces = [e for e in events if e.event_type == 'MULTIPLE_FACES']
    
    # Rule 1: Tab Switching
    if tab_switch_count > max_tabs:
        violations.append(Violation(
            session_id=session_id, candidate_id=candidate_id,
            violation_type='EXCESSIVE_TAB_SWITCH',
            severity='Medium' if tab_switch_count <= max_tabs + 2 else 'High',
            description=f"Candidate switched tabs {tab_switch_count} times (Threshold: {max_tabs})."
        ))

    # Rule 2: Focus Loss
    if focus_loss_count > max_focus:
        violations.append(Violation(
            session_id=session_id, candidate_id=candidate_id,
            violation_type='EXCESSIVE_FOCUS_LOSS',
            severity='Medium' if focus_loss_count <= max_focus + 2 else 'High',
            description=f"Browser lost focus {focus_loss_count} times (Threshold: {max_focus})."
        ))

    # Rule 3: Face Absence
    for fa in face_absences:
        if fa.duration is not None:
            if fa.duration >= face_absent_high:
                violations.append(Violation(
                    session_id=session_id, candidate_id=candidate_id, event_id=fa.id,
                    violation_type='EXTENDED_FACE_ABSENCE', severity='High', duration=fa.duration,
                    description=f"Face was absent for {fa.duration} seconds."
                ))
            elif fa.duration >= face_absent_warn:
                violations.append(Violation(
                    session_id=session_id, candidate_id=candidate_id, event_id=fa.id,
                    violation_type='FACE_ABSENCE_WARNING', severity='Low', duration=fa.duration,
                    description=f"Face was absent for {fa.duration} seconds."
                ))

    # Rule 4: Multiple Faces
    if len(multi_faces) >= max_multi_face:
        violations.append(Violation(
            session_id=session_id, candidate_id=candidate_id,
            violation_type='MULTIPLE_FACE_DETECTION', severity='High',
            description=f"Multiple faces detected {len(multi_faces)} times."
        ))

    # Rule 5: Combined Behaviour (Example: tab switch + focus loss + face absent)
    if tab_switch_count > 0 and focus_loss_count > 0 and len(face_absences) > 0:
        violations.append(Violation(
            session_id=session_id, candidate_id=candidate_id,
            violation_type='COMBINED_SUSPICIOUS_ACTIVITY', severity='High',
            description="Candidate exhibited a combination of tab switching, focus loss, and face absence."
        ))

    # Save to database
    if violations:
        db.session.bulk_save_objects(violations)

    update_integrity_score(session_id)
        
    return violations
