import uuid
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

from extensions import db
from models.candidate import Candidate
from models.exam_session import ExamSession
from models.authentication_log import AuthenticationLog
from models.session_log import SessionLog
from . import auth_bp

# Forms
class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        candidate = Candidate.query.filter_by(email=email.data).first()
        if candidate:
            raise ValidationError('Email is already registered. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Routes
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if photo was captured (will be handled via session or form hidden field logic if integrated directly in one page)
        # For simplicity, we create the user without a photo first, then redirect to photo capture.
        hashed_password = generate_password_hash(form.password.data)
        candidate = Candidate(
            full_name=form.full_name.data,
            email=form.email.data,
            password_hash=hashed_password
        )
        db.session.add(candidate)
        db.session.commit()
        session['pending_capture_candidate_id'] = candidate.id
        
        flash('Registration successful! Please capture your photo next.', 'success')
        return redirect(url_for('camera.capture', candidate_id=candidate.id))
        
    return render_template('register.html', title='Register', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        candidate = Candidate.query.filter_by(email=form.email.data).first()
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')
        
        if candidate and check_password_hash(candidate.password_hash, form.password.data):
            login_user(candidate, remember=True)
            
            # Log successful authentication
            auth_log = AuthenticationLog(
                candidate_id=candidate.id,
                ip_address=ip_address,
                user_agent=user_agent,
                status='SUCCESS'
            )
            
            # Check if candidate already has an active session
            active_states = ['SESSION CREATED', 'READY TO START', 'EXAM STARTED', 'EXAM PAUSED', 'EXAM RESUMED']
            active_session = ExamSession.query.filter(
                ExamSession.candidate_id == candidate.id,
                ExamSession.status.in_(active_states)
            ).order_by(ExamSession.id.desc()).first()
            
            db.session.add(auth_log)
            
            if active_session:
                # Log that they resumed an existing session
                s_log = SessionLog(
                    session_id=active_session.id,
                    event_type='LOGIN',
                    description='Resumed existing active session upon login.'
                )
                db.session.add(s_log)
            else:
                # Create a new Exam Session
                session_token = str(uuid.uuid4())
                new_session = ExamSession(
                    candidate_id=candidate.id,
                    session_token=session_token,
                    status='SESSION CREATED'
                )
                db.session.add(new_session)
                db.session.flush() # To get the ID
                
                s_log = SessionLog(
                    session_id=new_session.id,
                    event_type='LOGIN',
                    description='Session created successfully upon login.'
                )
                db.session.add(s_log)
                
            db.session.commit()
            
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            # Log failed authentication
            if candidate:
                auth_log = AuthenticationLog(
                    candidate_id=candidate.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='FAILED'
                )
                db.session.add(auth_log)
                db.session.commit()
            flash('Login unsuccessful. Please check email and password.', 'danger')
            
    return render_template('login.html', title='Login', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    # Fetch active session but DO NOT complete it if they are in the middle of an exam
    active_states = ['SESSION CREATED', 'READY TO START', 'EXAM STARTED', 'EXAM PAUSED', 'EXAM RESUMED']
    active_session = ExamSession.query.filter(
        ExamSession.candidate_id == current_user.id,
        ExamSession.status.in_(active_states)
    ).order_by(ExamSession.id.desc()).first()
    
    if active_session:
        active_session.logout_time = datetime.utcnow()
        # If they log out during an active exam, automatically pause it
        if active_session.status in ['EXAM STARTED', 'EXAM RESUMED']:
            active_session.status = 'EXAM PAUSED'
            
        # Log session logout
        s_log = SessionLog(
            session_id=active_session.id,
            event_type='LOGOUT',
            description='User explicitly logged out.'
        )
        db.session.add(s_log)
        
    # Log authentication logout
    auth_log = AuthenticationLog(
        candidate_id=current_user.id,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        status='LOGOUT'
    )
    db.session.add(auth_log)
    db.session.commit()
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
