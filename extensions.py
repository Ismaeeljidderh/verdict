"""
extensions.py
Centralized Flask extension instances, initialized here and
bound to the app in app.py via init_app(). Keeps app.py clean
and avoids circular imports between modules that need db/bcrypt.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
bcrypt = Bcrypt()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
oauth = OAuth()
