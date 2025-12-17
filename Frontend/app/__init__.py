from flask import Flask
from flask_apscheduler import APScheduler
from app.controllers.main import main_bp
from app.controllers.fileUpload import fileUpload_bp
from app.controllers.generateResults import generateResults_bp
from app.controllers.options import options_bp
from app.controllers.tasks import ejecutar_limpieza_carpeta

scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.DevConfig')
    app.logger.info(f"Localizacion de descargar para la aplicación {app.config.get("UPLOAD_FOLDER")}")

    app.config['SCHEDULER_API_ENABLED'] = True 
    maps_folder = app.config.get("MAPS_FOLDER")
    app.logger.info(f"Localizacion de descarga para la aplicación {maps_folder}")

    scheduler.init_app(app)
    scheduler.start()

    @scheduler.task('cron', id='limpieza_diaria_job', hour=3, minute=0)
    def scheduled_cleaning():
        with app.app_context():
            ejecutar_limpieza_carpeta(maps_folder)

    # Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(fileUpload_bp)
    app.register_blueprint(generateResults_bp)
    app.register_blueprint(options_bp)

    return app
