from flask import Flask
from flask_apscheduler import APScheduler
from .controllers.main import main_bp
from .controllers.file_upload import file_upload_bp
from .controllers.file_validation import file_validation_bp
from .controllers.file_provider import file_provider_bp
from .controllers.generateResults import generateResults_bp
from .controllers.options import options_bp
from .controllers.tasks import clean_user_files

scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.DevConfig')
    uploads = app.config.get("UPLOAD_FOLDER")
    app.logger.info(f"Uplaods location for the user files: {uploads}")

    app.config['SCHEDULER_API_ENABLED'] = True 
    maps_folder = app.config.get("MAPS_FOLDER")
    app.logger.info(f"Maps location folder: {maps_folder}")

    scheduler.init_app(app)
    scheduler.start()

    @scheduler.task('cron', id='limpieza_diaria_job', hour=3, minute=0)
    def scheduled_cleaning():
        with app.app_context():
            clean_user_files(maps_folder)
            clean_user_files(uploads)

    # Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(file_upload_bp)
    app.register_blueprint(file_validation_bp)
    app.register_blueprint(file_provider_bp)
    app.register_blueprint(generateResults_bp)
    app.register_blueprint(options_bp)

    return app
