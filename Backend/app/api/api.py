from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request, jsonify, Response
from app.util.fileMgmt import ensure_folder, rename_file_columns, extractDataframes, format_date, get_statistics_A, extractBCDataframes
from app.services.unifyFiles import unifyAllFiles, unifyBCFiles, unifyADFiles
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


@api_bp.route('/upload_A_file', methods=['POST'])
def upload_A_file():
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
    
    statistics_response = get_statistics_A(save_path)

    if isinstance(statistics_response, Response):
        statistics = statistics_response.get_json()

    final_response = {
        "logs": f'Archivo guardado correctamente.\n{statistics.get('info', '')}'
    }

    return jsonify(final_response), 200


@api_bp.route('/unifyFilesBC', methods=['POST'])
def unifyFilesBC():
    #cod = request.form.get('codired')
    id = request.form.get('id')
    files_paths = {}
    base_upload = current_app.config.get("UPLOAD_FOLDER")
    id_path = os.path.join(base_upload, str(id))

    for file_type in ('B', 'C'):
        for root, _, files in os.walk(id_path):
            for file in files:
                if file.endswith('.csv') and f'Fichero_{file_type}' in file:
                    wout_extension = os.path.splitext(file)[0]
                    parts = wout_extension.split('_')
                    if len(parts) == 2:
                        type = parts[1]
                        files_paths[type] = os.path.join(root, file)
    
    current_app.logger.info(f"Se han encontrado {len(files_paths)} archivos en la carperta de la sesion {id}")
    df_B, df_C, read_info = extractBCDataframes(files_paths['B'], files_paths['C'])
    if ((len(df_B) == 0) or (len(df_C) == 0)):
        return jsonify({"Registros totales: 0"})
    erased_info = unifyBCFiles(df_B, df_C, id_path)
    
    if isinstance(read_info, Response):
        read_info = read_info.get_json()

    if isinstance(erased_info, Response):
        erased_info = erased_info.get_json()

    #unify_info = {
    #    "Duplicados": f'Duplicados totales: {erased_info["Duplicados"]["Duplicados totales"]}.\nDuplicados fichero B: {erased_info["Duplicados"]["Duplicados B"]}.\nDuplicados fichero C: {erased_info["Duplicados"]["Duplicados C"]}.\n',
    #    "PDAs_encontradas": f'Num PDAs encontradas:\n\tFichero B: {erased_info["PDAs_encontradas"]["PDAs_B"]}.\n\tFichero C: {erased_info["PDAs_encontradas"]["PDAs_C"]}.\n',
    #    "PDAs_utilizables": f'Num PDAs en ambos ficheros: {erased_info["PDAs_utilizables"]["PDAs_B"]}.\n',
    #    "Registros_no_usados": f'Registros no correspondidos:\n\tFichero B: {erased_info["Registros_no_usados"]["B_no_usados"]}.\n\tFichero C: {erased_info["Registros_no_usados"]["C_no_usados"]}.\n',
    #    "Registros_finales": f'Registros finales: {erased_info["Registros_finales"]}.\n'
    #}

    #return_information = {
    #    "Registros_leidos": f'Registros totales: {read_info['Registros_totales']}.\nRegistros fichero B: {read_info['Registros_B']}.\nRegistros fichero C: {read_info['Registros_C']}.\n',
    #    "Registros_eliminados": f'Informacion de la union de los ficheros:\n{unify_info["Duplicados"]}{unify_info["PDAs_encontradas"]}{unify_info["PDAs_utilizables"]}{unify_info["Registros_no_usados"]}{unify_info["Registros_finales"]}'
    #}



    final_response = {"logs": f'{erased_info}'}

    return jsonify(final_response)



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

@api_bp.route('/unifyAllFiles', methods=['POST'])
def unifyAllFiles():
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
    df_A, df_D, read_info = extractBCDataframes(files_paths['A'], files_paths['D'])
    if ((len(df_A) == 0) or (len(df_D) == 0)):
        return jsonify({"Registros totales: 0"})
    erased_info = unifyADFiles(df_A, df_D, id_path)
    
    if isinstance(read_info, Response):
        read_info = read_info.get_json()

    if isinstance(erased_info, Response):
        erased_info = erased_info.get_json()

    final_response = {"logs": f'{erased_info}'}

    return jsonify(final_response)