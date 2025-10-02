import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'Clave secreta para la sesion :)')
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    ALLOWED_EXTENSIONS = {'csv'}

class DevConfig(Config):
    DEBUG = True

class ProdConfig(Config):
    DEBUG = False