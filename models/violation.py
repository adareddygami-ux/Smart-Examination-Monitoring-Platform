from datetime import datetime
from extensions import db

class Violation(db.Model):
    """Model for logging rule-based violations derived from monitoring events."""
    __tablename__ = 'violations'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('exam_sessions.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('monitoring_events.id'), nullable=True) # Link to triggering event, if any
    violation_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(50), nullable=False)  # Low, Medium, High, Critical
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='NEW') # NEW, REVIEWED, DISMISSED

    # Relationship to potentially fetch the underlying event details
    triggering_event = db.relationship('MonitoringEvent', backref='violations', lazy=True)

    def __repr__(self):
        return f"<Violation {self.violation_type} - {self.severity}>"
