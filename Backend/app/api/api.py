from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request, jsonify
from app.util.fileMgmt import ensure_folder, rename_file_columns
from app.services.unifyFiles import unifyAllFiles
from datetime import timedelta, datetime
import uuid
import os

api_bp = Blueprint('api', __name__, template_folder='templates')



@api_bp.route('/upload_file', methods=['POST'])
def upload_file():
    # Descargar fichero en local
    current_app.logger.info('Se va a iniciar la descarga en local en el backend')
    base_upload = current_app.config.get("UPLOAD_FOLDER")

    id = request.form.get('id')
    type = request.form.get('type')
    f = request.files.get('file')

    data_filename = f"Fichero_{type}.csv"
    id_path = ensure_folder(id)
    save_path_temp = os.path.join(base_upload, id_path)
    save_path = os.path.join(save_path_temp, data_filename)
    f.save(save_path)

    rename_file_columns(save_path, type)

    if not os.path.exists(save_path):
        current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
        return jsonify({'error': f'El archivo no se guardó correctamente'}), 400
    
    current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
    
    return jsonify({'error': f'Archivo guardado correctamente'}), 200


@api_bp.route('/unifyFiles', methods=['POST'])
def unifyFiles():
    id = request.form.get('id')
    files_paths = {}
    base_upload = current_app.config.get("UPLOAD_FOLDER")
    id_path = os.path.join(base_upload, id)

    for root, _, files in os.walk(id_path):
        for file in files:
            if file.endswith('.csv') and 'Fichero_' in file:
                wout_extension = os.path.splitext(file)[0]
                parts = wout_extension.split('_')
                if len(parts) == 2:
                    type = parts[1]
                    files_paths[type] = os.path.join(root, file)
    
    current_app.logger.info(f"Se han encontrado {len(files_paths)} archivos en la carperta de la sesion {id}")

    erased_info = unifyAllFiles(files_paths['A'], files_paths['B'], files_paths['C'])
    print(erased_info)
    
    return erased_info