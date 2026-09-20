from datetime import datetime
from flask_login import UserMixin
from extensions import db

class Candidate(UserMixin, db.Model):
    """Candidate model for storing user details."""
    __tablename__ = 'candidates'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    photo_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sessions = db.relationship('ExamSession', backref='candidate', lazy=True)
    auth_logs = db.relationship('AuthenticationLog', backref='candidate', lazy=True)

    def __repr__(self):
        return f"<Candidate {self.email}>"
