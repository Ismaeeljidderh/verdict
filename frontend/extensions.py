from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth

db      = SQLAlchemy()
bcrypt  = Bcrypt()
csrf    = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["300 per hour"])
oauth   = OAuth()