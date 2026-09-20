from flask import Blueprint

auth_bp = Blueprint('auth', __name__)
dashboard_bp = Blueprint('dashboard', __name__)
camera_bp = Blueprint('camera', __name__)

from . import auth
from . import dashboard
from . import camera
