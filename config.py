import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
    
    # Database
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'database.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'photos')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit

    # Monitoring Thresholds
    MAX_TAB_SWITCHES = 3
    MAX_FOCUS_LOSS = 3
    FACE_ABSENCE_WARNING_SECONDS = 5
    FACE_ABSENCE_HIGH_SECONDS = 30
    MULTIPLE_FACE_THRESHOLD = 1
    COMBINED_EVENT_WINDOW_SECONDS = 60
