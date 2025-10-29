from flask import Flask
from app.api.api import api_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.DevConfig')
    app.logger.info(f"Localizacion de descarga para la aplicación {app.config.get("UPLOAD_FOLDER")}")

    # Blueprints
    app.register_blueprint(api_bp)

    return app