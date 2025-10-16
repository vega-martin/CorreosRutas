from flask import Flask
from app.controllers.main import main_bp
from app.controllers.fileUpload import fileUpload_bp
from app.controllers.generateResults import generateResults_bp
from app.controllers.options import options_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.DevConfig')
    app.logger.info(f"Localizacion de descargar para la aplicación {app.config.get("UPLOAD_FOLDER")}")

    # Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(fileUpload_bp)
    app.register_blueprint(generateResults_bp)
    app.register_blueprint(options_bp)

    return app