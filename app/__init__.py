from flask import Flask
from app.controllers.main import main_bp
from app.controllers.fileUpload import fileUpload_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.DevConfig')

    # Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(fileUpload_bp)

    return app