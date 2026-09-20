import os
from flask import Flask
from config import Config
from extensions import db, login_manager, migrate
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.camera import camera_bp
from routes.exam import exam_bp
from routes.monitoring import monitoring_bp
from models.candidate import Candidate
import models
from utils.faker_generator import generate_fake_data

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(exam_bp)
    app.register_blueprint(monitoring_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return Candidate.query.get(int(user_id))

    return app

if __name__ == '__main__':
    app = create_app()
    
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()
        
        # Optionally populate with fake data if empty (Checking Candidate count)
        if Candidate.query.count() == 0:
            generate_fake_data(app)
            
    app.run(debug=True, port=5000)
