from datetime import datetime
from extensions import db

class MonitoringEvent(db.Model):
    """Model for logging continuous monitoring events (webcam and browser)."""
    __tablename__ = 'monitoring_events'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('exam_sessions.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Integer, nullable=True) # Duration in seconds
    severity = db.Column(db.String(50), nullable=True) # Ignore, Low, Medium, High, Critical
    description = db.Column(db.Text, nullable=True)
    metadata_info = db.Column(db.Text, nullable=True) # Renamed from metadata to avoid SQLAlchemy conflicts

    def __repr__(self):
        return f"<MonitoringEvent {self.event_type} - {self.timestamp}>"
