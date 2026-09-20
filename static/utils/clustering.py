try:
    import pandas as pd
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
except Exception:
    pd = None
    StandardScaler = None
    KMeans = None

from models.monitoring_event import MonitoringEvent
from models.exam_session import ExamSession
from extensions import db
import logging

def perform_behaviour_clustering():
    """
    Extracts features from all completed exam sessions and applies K-Means clustering.
    Updates the behaviour_cluster field for each session.
    """
    if pd is None or StandardScaler is None or KMeans is None:
        logging.warning('Behaviour clustering skipped because pandas/scikit-learn are unavailable in this environment.')
        return False

    try:
        # Fetch completed sessions
        completed_sessions = ExamSession.query.filter(
            ExamSession.status.in_(['SESSION COMPLETED', 'EXAM SUBMITTED'])
        ).all()

        if len(completed_sessions) < 3:
            # Not enough data for meaningful clustering
            return False

        data = []
        for session in completed_sessions:
            events = MonitoringEvent.query.filter_by(session_id=session.id).all()
            
            # Extract features
            tab_switches = sum(1 for e in events if e.event_type == 'TAB_SWITCH')
            focus_losses = sum(1 for e in events if e.event_type == 'FOCUS_LOST')
            face_absences = [e for e in events if e.event_type == 'FACE_ABSENT']
            face_absence_count = len(face_absences)
            total_face_absence_duration = sum((e.duration or 0) for e in face_absences)
            multiple_face_count = sum(1 for e in events if e.event_type == 'MULTIPLE_FACES')
            question_interactions = sum(1 for e in events if e.event_type in ['QUESTION_VIEWED', 'NEXT_QUESTION', 'PREVIOUS_QUESTION'])
            answer_changes = sum(1 for e in events if e.event_type in ['ANSWER_SELECTED', 'ANSWER_CHANGED'])
            
            session_duration = 0
            if session.exam_started_at and session.exam_completed_at:
                session_duration = (session.exam_completed_at - session.exam_started_at).total_seconds()

            data.append({
                'session_id': session.id,
                'tab_switch_count': tab_switches,
                'focus_loss_count': focus_losses,
                'face_absence_count': face_absence_count,
                'total_face_absence_duration': total_face_absence_duration,
                'multiple_face_count': multiple_face_count,
                'question_interaction_count': question_interactions,
                'answer_change_count': answer_changes,
                'session_duration': session_duration
            })

        df = pd.DataFrame(data)
        
        # Prepare feature matrix
        features = df.drop(columns=['session_id'])
        
        # Normalize
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)
        
        # Determine number of clusters (max 3 or less if not enough samples)
        n_clusters = min(3, len(df))
        
        # Apply KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
        clusters = kmeans.fit_predict(scaled_features)
        
        # Update database
        for i, row in df.iterrows():
            session = next((s for s in completed_sessions if s.id == row['session_id']), None)
            if session:
                session.behaviour_cluster = f"Cluster {clusters[i]}"
                
        db.session.commit()
        return True
        
    except Exception as e:
        logging.error(f"Error in behaviour clustering: {e}")
        return False
