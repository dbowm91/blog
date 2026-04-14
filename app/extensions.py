from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "admin.login"
login_manager.login_message = "Please log in to access this page."
login_manager.session_protection = "strong"
migrate = Migrate()
