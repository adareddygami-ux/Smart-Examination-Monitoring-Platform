import unittest
import os
import sys

# Add the project root to the sys.path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models.candidate import Candidate
from models.exam_session import ExamSession
from werkzeug.security import generate_password_hash

class ValidationTestCase(unittest.TestCase):
    def setUp(self):
        # Create a test client
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for testing forms
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Setup the database
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_registration_and_duplicate_email(self):
        # 1. Registration Test
        response = self.client.post('/register', data=dict(
            full_name='Test User',
            email='test@example.com',
            password='Password123',
            confirm_password='Password123'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Check DB
        candidate = Candidate.query.filter_by(email='test@example.com').first()
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.full_name, 'Test User')
        
        # 2. Duplicate Email Test
        response2 = self.client.post('/register', data=dict(
            full_name='Test User 2',
            email='test@example.com', # Same email
            password='Password123',
            confirm_password='Password123'
        ), follow_redirects=True)
        self.assertIn(b'Email is already registered.', response2.data)

    def test_password_hashing(self):
        candidate = Candidate(
            full_name='Hash Test',
            email='hash@example.com',
            password_hash=generate_password_hash('Secret123')
        )
        db.session.add(candidate)
        db.session.commit()
        
        saved_candidate = Candidate.query.filter_by(email='hash@example.com').first()
        self.assertNotEqual(saved_candidate.password_hash, 'Secret123')
        self.assertTrue(saved_candidate.password_hash.startswith('scrypt:')) # Werkzeug default

    def test_login_and_session_creation(self):
        # Setup candidate
        candidate = Candidate(
            full_name='Login Test',
            email='login@example.com',
            password_hash=generate_password_hash('Login123')
        )
        db.session.add(candidate)
        db.session.commit()
        
        # 3. Login Test
        response = self.client.post('/login', data=dict(
            email='login@example.com',
            password='Login123'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data) # Check if redirected to dashboard
        
        # 4. Session Creation Test
        active_session = ExamSession.query.filter_by(candidate_id=candidate.id).first()
        self.assertIsNotNone(active_session)
        self.assertEqual(active_session.status, 'Active')
        
        # 5. Logout & Session Expiry Test
        response_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response_logout.status_code, 200)
        self.assertIn(b'You have been logged out.', response_logout.data)
        
        # Check if session is logged out
        ended_session = ExamSession.query.filter_by(candidate_id=candidate.id).first()
        self.assertEqual(ended_session.status, 'Logged Out')
        self.assertIsNotNone(ended_session.logout_time)

if __name__ == '__main__':
    unittest.main()
