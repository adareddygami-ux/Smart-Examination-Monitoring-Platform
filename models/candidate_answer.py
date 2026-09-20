from extensions import db

class CandidateAnswer(db.Model):
    """Tracks individual answers for a specific exam session."""
    __tablename__ = 'candidate_answers'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('exam_sessions.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    selected_answer = db.Column(db.String(200), nullable=True)
    is_correct = db.Column(db.Boolean, default=False)

    # Relationships
    question = db.relationship('Question')
    session = db.relationship('ExamSession')

    def __repr__(self):
        return f"<CandidateAnswer session={self.session_id} q={self.question_id}>"
