from datetime import datetime
from extensions import db

class ExamSession(db.Model):
    """Exam session model to track candidate sessions."""
    __tablename__ = 'exam_sessions'

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    session_token = db.Column(db.String(100), unique=True, nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='SESSION CREATED')  # LOGIN, SESSION CREATED, READY TO START, EXAM STARTED, EXAM PAUSED, EXAM RESUMED, EXAM SUBMITTED, SESSION COMPLETED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # New Columns for Exam Module
    exam_name = db.Column(db.String(100), default='General Assessment')
    exam_started_at = db.Column(db.DateTime, nullable=True)
    exam_completed_at = db.Column(db.DateTime, nullable=True)
    integrity_score = db.Column(db.Integer, default=100)
    risk_level = db.Column(db.String(50), default='Low') # Low, Medium, High, Critical
    total_cheating_events = db.Column(db.Integer, default=0)
    verification_status = db.Column(db.String(50), default='Pending') # Pending, Verified, Failed
    questions_attempted = db.Column(db.Integer, default=0)
    score = db.Column(db.Integer, default=0)
    exam_data = db.Column(db.Text, nullable=True) # Optional JSON
    behaviour_cluster = db.Column(db.String(50), nullable=True) # E.g., Cluster 0, Cluster 1

    # Relationships
    session_logs = db.relationship('SessionLog', backref='exam_session', lazy=True)
    cheating_events = db.relationship('CheatingEvent', backref='exam_session', lazy=True)
    monitoring_events = db.relationship('MonitoringEvent', backref='exam_session', lazy=True)
    violations = db.relationship('Violation', backref='exam_session', lazy=True)

    def __repr__(self):
        return f"<ExamSession {self.session_token}>"
