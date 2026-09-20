from extensions import db

class Question(db.Model):
    """Question Bank model."""
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(200), nullable=False)
    difficulty = db.Column(db.String(50), default='Medium')
    category = db.Column(db.String(100), default='General')

    def __repr__(self):
        return f"<Question {self.id}>"
