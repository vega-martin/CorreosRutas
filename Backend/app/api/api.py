from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request, jsonify
from datetime import timedelta, datetime
from werkzeug.utils import secure_filename
import uuid
import os

api_bp = Blueprint('api', __name__, template_folder='templates')



@api_bp.route('/upload_file', methods=['POST'])
def upload_file():
    # Descargar fichero en local
    current_app.logger.info('Se va a iniciar la descarga en local en el backend')
    base_upload = current_app.config.get("UPLOAD_FOLDER")
    f = request.files.get('file')
    data_filename = secure_filename(f.filename)

    save_path = os.path.join(base_upload, data_filename)
    f.save(save_path)

    if not os.path.exists(save_path):
        current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
        return jsonify({'error': f'El archivo no se guardó correctamente'}), 400
    
    current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
    
    return jsonify({'error': f'Archivo guardado correctamente'}), 200