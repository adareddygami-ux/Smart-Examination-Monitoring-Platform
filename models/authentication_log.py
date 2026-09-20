from datetime import datetime
from extensions import db

class AuthenticationLog(db.Model):
    """Model for logging authentication events."""
    __tablename__ = 'authentication_logs'

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), nullable=False)  # SUCCESS, FAILED, LOGOUT

    def __repr__(self):
        return f"<AuthLog {self.candidate_id} - {self.status}>"
