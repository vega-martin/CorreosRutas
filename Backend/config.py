import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'Clave secreta para la sesion del backend :)')
    BASE_DIR = os.path.dirname(__file__)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'csv'}

class DevConfig(Config):
    DEBUG = True

class ProdConfig(Config):
    DEBUG = False