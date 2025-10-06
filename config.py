import os

HOST = '127.0.0.1'
PORT = 5001

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'Clave secreta para la sesion :)')
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    UPLOADED_FILES = {'A': None, 'B': None, 'C': None}
    ALLOWED_EXTENSIONS = {'csv'}

class DevConfig(Config):
    DEBUG = True

class ProdConfig(Config):
    DEBUG = False