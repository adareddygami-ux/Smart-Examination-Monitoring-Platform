from datetime import datetime
from extensions import db

class CheatingEvent(db.Model):
    """Model for logging cheating and integrity events during an exam session."""
    __tablename__ = 'cheating_events'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('exam_sessions.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    event_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(50), nullable=False)  # Low, Medium, High, Critical
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"<CheatingEvent {self.event_type} - {self.severity}>"
