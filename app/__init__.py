from flask import Flask
from app.controllers.main import main_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.DevConfig')

    # Blueprints
    app.register_blueprint(main_bp)

    return app