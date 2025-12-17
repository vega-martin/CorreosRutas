from datetime import timedelta
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'Clave secreta para la sesion :)')
    BASE_DIR = os.path.dirname(__file__)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    GEOJSON_FOLDER = os.path.join(os.path.dirname(__file__), 'app', 'static', 'geojson')
    MAPS_FOLDER = os.path.join(os.path.dirname(__file__), 'app', 'static', 'maps')
    ALLOWED_EXTENSIONS = {'csv'}
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=55)
    SESSION_REFRESH_EACH_REQUEST = True
    API_URL = 'http://0.0.0.0:5001'

class DevConfig(Config):
    DEBUG = True

class ProdConfig(Config):
    DEBUG = False