from datetime import datetime
from extensions import db

class SessionLog(db.Model):
    """Model for logging events during an exam session."""
    __tablename__ = 'session_logs'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('exam_sessions.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<SessionLog {self.session_id} - {self.event_type}>"
