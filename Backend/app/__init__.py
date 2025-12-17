from flask import Flask
from flask_apscheduler import APScheduler  
from app.api.api import api_bp
from app.services.tasks import ejecutar_limpieza_carpeta 

scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.DevConfig')
    
    app.config['SCHEDULER_API_ENABLED'] = True 
    
    upload_folder = app.config.get("UPLOAD_FOLDER")
    app.logger.info(f"Localizacion de descarga para la aplicación {upload_folder}")

    scheduler.init_app(app)
    scheduler.start()

    @scheduler.task('cron', id='limpieza_diaria_job', hour=3, minute=0)
    def scheduled_cleaning():
        with app.app_context():
            ejecutar_limpieza_carpeta(upload_folder)

    app.register_blueprint(api_bp)

    return app