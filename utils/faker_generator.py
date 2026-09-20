import random
from datetime import datetime, timedelta
from faker import Faker
from werkzeug.security import generate_password_hash
from extensions import db
from models.candidate import Candidate
from models.exam_session import ExamSession
from models.session_log import SessionLog

fake = Faker()

def generate_fake_data(app):
    """Generates synthetic candidates and session logs."""
    with app.app_context():
        print("Generating fake candidates...")
        
        candidates = []
        for _ in range(100):
            # Create Candidate
            candidate = Candidate(
                full_name=fake.name(),
                email=fake.unique.email(),
                password_hash=generate_password_hash('password123'),
                photo_path=None, # Mocking without actual photos
                created_at=fake.date_time_between(start_date='-1y', end_date='now')
            )
            db.session.add(candidate)
            candidates.append(candidate)
            
        db.session.commit()
        print(f"Generated 100 fake candidates.")
        
        print("Generating fake session logs...")
        events = ['LOGIN', 'LOGOUT', 'SESSION_CREATED', 'SESSION_ACTIVE', 'SESSION_TIMEOUT']
        
        for _ in range(50):
            # Create a mock session for a random candidate
            candidate = random.choice(candidates)
            session_start = fake.date_time_between(start_date=candidate.created_at, end_date='now')
            
            exam_session = ExamSession(
                candidate_id=candidate.id,
                session_token=fake.uuid4(),
                login_time=session_start,
                status='Logged Out',
                created_at=session_start
            )
            db.session.add(exam_session)
            db.session.flush() # To get the session ID
            
            # Generate about 10 logs per session
            for _ in range(10):
                log_time = session_start + timedelta(minutes=random.randint(1, 120))
                event_type = random.choice(events)
                session_log = SessionLog(
                    session_id=exam_session.id,
                    timestamp=log_time,
                    event_type=event_type,
                    description=f"System generated {event_type} event"
                )
                db.session.add(session_log)
                
            exam_session.logout_time = session_start + timedelta(minutes=random.randint(30, 180))
            
        db.session.commit()
        print("Generated synthetic sessions and 500+ session logs.")
