from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request, jsonify, Response
from app.util.fileMgmt import ensure_folder, rename_file_columns, extractDataframes, format_date
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
    format_date(save_path, type)

    if not os.path.exists(save_path):
        current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
        return jsonify({'error': f'El archivo no se guardó correctamente'}), 400
    
    current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
    
    return jsonify({'error': f'Archivo guardado correctamente'}), 200


@api_bp.route('/unifyFiles', methods=['POST'])
def unifyFiles():
    cod = request.form.get('codired')
    id = request.form.get('id')
    files_paths = {}
    base_upload = current_app.config.get("UPLOAD_FOLDER")
    id_path = os.path.join(base_upload, str(id))

    for root, _, files in os.walk(id_path):
        for file in files:
            if file.endswith('.csv') and 'Fichero_' in file:
                wout_extension = os.path.splitext(file)[0]
                parts = wout_extension.split('_')
                if len(parts) == 2:
                    type = parts[1]
                    files_paths[type] = os.path.join(root, file)
    
    current_app.logger.info(f"Se han encontrado {len(files_paths)} archivos en la carperta de la sesion {id}")
    df_A, df_B, df_C, read_info = extractDataframes(files_paths['A'], files_paths['B'], files_paths['C'], cod)
    if ((len(df_A) == 0) or (len(df_B) == 0) or (len(df_C) == 0)):
        return jsonify({"Registros totales: 0"})
    erased_info = unifyAllFiles(df_A, df_B, df_C, id_path)
    
    if isinstance(read_info, Response):
        read_info = read_info.get_json()

    if isinstance(erased_info, Response):
        erased_info = erased_info.get_json()

    return_information = {
        "Registros_leidos": read_info,
        "Registros_eliminados": erased_info
    }

    return jsonify(return_information)