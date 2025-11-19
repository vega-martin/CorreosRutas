from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template
from werkzeug.utils import secure_filename
import pandas as pd
import os, uuid, tempfile, requests

fileUpload_bp = Blueprint('fileUpload', __name__, template_folder='templates')


# ------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------

def valid_extension(name):
    """Comprueba si la extensión es valida"""

    valid_ext = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in name and name.rsplit('.', 1)[1].lower() in valid_ext


def ensure_session_folder():
    """Crea una carpeta única para cada sesión y crea sesión (si no existe)"""

    session_id = session.get("id")

    base_upload = current_app.config.get("UPLOAD_FOLDER")
    user_folder = os.path.join(base_upload, session_id)
    os.makedirs(user_folder, exist_ok=True)

    if not os.path.exists(user_folder):
        current_app.logger.error(f"Error: no se creó la carpeta {user_folder}")
    else:
        current_app.logger.info(f"Carpeta creada correctamente: {user_folder}")
    
    return user_folder


# ------------------------------------------------------------
# COMPROBACION DE FICHEROS
# ------------------------------------------------------------

@fileUpload_bp.route('/validateFile', methods=['POST'])
def valid_file(path, file_type):
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        return jsonify({'error': f'Error al leer el archivo: {str(e)}'}), 500

    required_columns_map = {
        "A": {'fec_lectura_medicion', 'longitud_wgs84_gd', 'latitud_wgs84_gd', 'cod_inv_pda', 'codired'},
        "B": {'Num Inv', 'Fec Actividad', 'Seg Transcurrido', 'Cod Unidad'},
        "C": {'COD_SECCION', 'INSTANTE', 'LONGITUD', 'LATITUD', 'codired'}
    }

    required_columns = required_columns_map.get(file_type)

    if not required_columns:
        current_app.logger.error('Error: el fichero no cumple con los criterios')
        return jsonify({'error': f'El archivo no cumple con los criterios'}), 400
    
    if not required_columns.issubset(df.columns):
        return jsonify({'error': f'El fichero CSV \"{file_type}\" debe contener las columnas: {", ".join(required_columns)}'}), 400
    
    current_app.logger.info('Archivo subido válido')

    return jsonify({'message': 'Archivo válido'}), 200


# ------------------------------------------------------------
# LECTURA Y DESCARGA DE FICHEROS EN LOCAL
# ------------------------------------------------------------

@fileUpload_bp.route('/uploadFileToBackend', methods=['POST'])
def uploadFileToBackend():
    for file_type in ('A', 'B', 'C'):
        file_key = f'file{file_type}'
        f = request.files.get(file_key)
        data_filename = secure_filename(f.filename)
        user_folder = ensure_session_folder()
        save_path = os.path.join(user_folder, data_filename)
        f.save(save_path)

        response = valid_file(save_path, file_type)
        if response[1] != 200:
            os.remove(save_path)
            flash(response[0].json['error'], 'error')
            return redirect(url_for('main.root'))
        
        with open(save_path, 'rb') as y:
            data = {
                "id": session.get("id"),
                "type": file_type
                }
            files = {'file': y}
            api_url = current_app.config.get("API_URL")
            requests.post(f"{api_url}/upload_file", data=data, files=files)

        uploaded = session.get("uploaded_files", {})
        uploaded[file_type] = save_path
        session["uploaded_files"] = uploaded

        if not os.path.exists(save_path):
            current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
        else:
            current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
        
    flash(f'Ficheros subidos correctamente.', 'success')
    return redirect(url_for('main.root'))

@fileUpload_bp.route('/uploadFileAToBackend', methods=['POST'])
def uploadFileAToBackend():
    file_type = 'A'
    file_key = 'fileA'
    f = request.files.get(file_key)
    data_filename = secure_filename(f.filename)
    user_folder = ensure_session_folder()
    save_path = os.path.join(user_folder, data_filename)
    f.save(save_path)

    response = valid_file(save_path, file_type)
    if response[1] != 200:
        os.remove(save_path)
        flash(response[0].json['error'], 'error')
        return jsonify({"logs": response[0].json['error']})
    
    with open(save_path, 'rb') as y:
        data = {
            "id": session.get("id"),
            "type": file_type
            }
        files = {'file': y}
        api_url = current_app.config.get("API_URL")
        backend_response = requests.post(f"{api_url}/upload_A_file", data=data, files=files)

    uploaded = session.get("uploaded_files", {})
    uploaded[file_type] = save_path
    session["uploaded_files"] = uploaded

    if not os.path.exists(save_path):
        current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
    else:
        current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
    
    flash(f'Fichero subido correctamente.', 'success')
    final_response = {
        "logs": f'Fichero subido correctamente.\n{backend_response.json().get('logs', '')}' 
    }
    return jsonify(final_response)


@fileUpload_bp.route('/uploadFilesBCToBackend', methods=['POST'])
def uploadFilesBCToBackend():
    for file_type in ('B', 'C'):
        file_key = f'file{file_type}'
        f = request.files.get(file_key)
        data_filename = secure_filename(f.filename)
        user_folder = ensure_session_folder()
        save_path = os.path.join(user_folder, data_filename)
        f.save(save_path)

        response = valid_file(save_path, file_type)
        if response[1] != 200:
            os.remove(save_path)
            flash(response[0].json['error'], 'error')
            return jsonify({"logs": response[0].json['error']})
        
        with open(save_path, 'rb') as y:
            data = {
                "id": session.get("id"),
                "type": file_type
                }
            files = {'file': y}
            api_url = current_app.config.get("API_URL")
            requests.post(f"{api_url}/upload_file", data=data, files=files)

        uploaded = session.get("uploaded_files", {})
        uploaded[file_type] = save_path
        session["uploaded_files"] = uploaded

        if not os.path.exists(save_path):
            current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
        else:
            current_app.logger.info(f"Archivo guardado correctamente en {save_path}")

    data = {
        "id": session.get("id")
        }
    api_url = current_app.config.get("API_URL")
    #backend_unify_response = requests.post(f"{api_url}/unifyFilesBC", data=data)
    #flash(f'Unificando ficheros. Proceso experimental (pueden ocurrir fallos)', 'info')
    #unify_response = f'Unificando ficheros.\n{backend_unify_response.json().get('logs', '')}\n'

    try:
        backend_unify_response = requests.post(f"{api_url}/unifyFilesBC", data=data)
        backend_unify_response.raise_for_status()  # Raises HTTPError if status != 2xx

        # Check if the response has content
        if backend_unify_response.content:
            unify_data = backend_unify_response.json()  # parse JSON
        else:
            unify_data = {"logs": "No se recibió respuesta del backend."}

    except requests.exceptions.RequestException as e:
        unify_data = {"logs": f"Error al llamar al backend: {e}"}

    unify_response = f"Unificando ficheros.\n{unify_data.get('logs', '')}\n"

    flash(f'Ficheros subidos correctamente.', 'success')
    final_response = {
        "logs": f'Ficheros subidos correctamente.\n\n{unify_response}\n'
    }

    return jsonify(final_response)



@fileUpload_bp.route("/check_files_status", methods=["POST"])
def check_files_status():
    """
    Comprueba si todos los ficheros requeridos ya están subidos.
    """
    # Comprobar si estan o no todos los ficheros
    uploaded_files = session.get("uploaded_files", {})
    ready = all(f in uploaded_files and uploaded_files[f] != '' for f in ('A', 'B', 'C'))
    # Mandar a unificar los 3 ficheros
    #data = {
    #    "id": session.get("id")
    #    }
    #api_url = current_app.config.get("API_URL")
    #requests.post(f"{api_url}/unifyFiles", data=data)
    return jsonify({"ready": ready})