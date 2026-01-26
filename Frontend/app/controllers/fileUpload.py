from flask import Blueprint, request, current_app, session, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import os, requests


fileUpload_bp = Blueprint('fileUpload', __name__, template_folder='templates')


# ------------------------------------------------------------
# AUXILIARY FUNCTIONS
# ------------------------------------------------------------

def valid_extension(name):
    """Check if a file name has a valid extension.

    This function checks whether the file extension of the given
    file name is allowed according to the application's configuration.

    Args:
        name (str): Name of the file to check.

    Returns:
        bool: True if the file has a valid extension, False otherwise.
    """
    valid_ext = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in name and name.rsplit('.', 1)[1].lower() in valid_ext


def ensure_session_folder():
    """Ensure that a unique folder exists for the current user session.

    This function retrieves the current session ID (creating one if
    necessary), constructs a user-specific folder path under the
    configured upload directory, and creates the folder if it does
    not exist. Logs success or failure.

    Returns:
        str: Path to the session-specific folder.

    Side Effects:
        - Creates a directory on the filesystem if it does not exist.
        - Logs success or error messages to the application logger.
    """
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
# FILE VALIDATION
# ------------------------------------------------------------

@fileUpload_bp.route('/validateFile', methods=['POST'])
def valid_file(path, file_type):
    """Validate the structure of an uploaded CSV file.

    This endpoint reads a CSV file from the given path, checks for
    required columns based on the file type, and returns a JSON
    response indicating whether the file is valid. Designed for
    use with files of types 'A', 'B', or 'C'.

    Args:
        path (str): Path to the uploaded CSV file.
        file_type (str): Type of the file, expected values: 'A', 'B', 'C'.

    Returns:
        flask.Response: JSON response with:
            - On success (valid CSV and columns):
                {'message': 'Archivo válido'}, HTTP status 200
            - On missing columns:
                {'error': <description>}, HTTP status 400
            - On CSV read error:
                {'error': <description>}, HTTP status 500

    Side Effects:
        - Logs a message to `current_app.logger` if the file is valid.
    """
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception:
        return jsonify({
            'error': 'Error al leer el archivo: Asegurese de que el archivo es de tipo CSV.'
        }), 500

    required_columns_map = {
        "A": {'fec_lectura_medicion', 'longitud_wgs84_gd', 'latitud_wgs84_gd', 'cod_inv_pda', 'codired'},
        "B": {'Num Inv', 'Fec Actividad', 'Seg Transcurrido', 'Cod Unidad'},
        "C": {'COD_SECCION', 'INSTANTE', 'LONGITUD', 'LATITUD', 'codired'}
    }

    required_columns = required_columns_map.get(file_type)
    
    if not required_columns.issubset(df.columns):
        return jsonify({
            'error': f'El fichero CSV "{file_type}" debe contener las columnas: {", ".join(required_columns)}'
        }), 400
    
    current_app.logger.info('Valid uploaded file')

    return jsonify({'message': 'Archivo válido'}), 200



# ------------------------------------------------------------
# LECTURA Y DESCARGA DE FICHEROS EN LOCAL
# ------------------------------------------------------------

@fileUpload_bp.route('/uploadFileAToBackend', methods=['POST'])
def uploadFileAToBackend():
    """Handle upload, validation, and forwarding of a type-A CSV file.

    This endpoint receives a CSV file of type A from the client,
    stores it in a session-specific folder, validates its structure,
    and forwards it to an external backend API for further processing.

    If validation fails, the file is deleted and an error message
    is returned. On success, the file path is stored in the session
    and the backend response is included in the logs.

    Returns:
        flask.Response: JSON response containing:
            - logs (str): Success or error messages, including
              backend processing logs when available.

    Side Effects:
        - Writes and deletes files on the filesystem.
        - Sends an HTTP POST request to an external backend API.
        - Mutates the Flask session by updating uploaded file metadata.
        - Writes informational and error logs to the application logger.
    """
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
    current_app.logger.info(f"the session dict is {dict(session)}")

    if not os.path.exists(save_path):
        current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
    else:
        current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
    
    final_response = {
        "logs": f'Fichero subido correctamente.\n{backend_response.json().get('logs', '')}' 
    }
    return jsonify(final_response)


@fileUpload_bp.route('/uploadFilesBCToBackend', methods=['POST'])
def uploadFilesBCToBackend():
    """Handle upload, validation, and backend processing of type-B and type-C files.

    This endpoint processes two uploaded CSV files (types B and C) in
    sequence. Each file is saved to a session-specific directory,
    validated for required structure, and forwarded to an external
    backend API. After both files are successfully uploaded, a final
    backend call is made to unify the processed data.

    If any file fails validation, the operation is aborted and an
    error response is returned.

    Returns:
        flask.Response: JSON response containing:
            - logs (str): Status and processing messages, including
              backend unification output.

    Side Effects:
        - Writes and deletes files on the filesystem.
        - Sends multiple HTTP POST requests to external backend APIs.
        - Mutates the Flask session with uploaded file metadata.
        - Logs file handling results to the application logger.
    """
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

    final_response = {
        "logs": f'Ficheros subidos correctamente.\n\n{unify_response}\n'
    }

    return jsonify(final_response)



@fileUpload_bp.route("/check_files_status", methods=["POST"])
def check_files_status():
    """Check whether all required files and generated outputs are ready.

    This endpoint verifies that all mandatory user-uploaded files
    (types A, B, and C) are present in the current session and that
    the backend has successfully completed the unification process
    (e.g., PDF generation or equivalent final artifact).

    The file presence check is performed locally using session data,
    while the unification status is validated by calling a backend
    API endpoint.

    Returns:
        flask.Response: JSON response containing:
            - ready (bool): True if all required files are uploaded
              and the backend confirms successful unification;
              False otherwise.

    Side Effects:
        - Sends an HTTP POST request to the backend API to check
          unification status.
    """
    # Comprobar si estan o no todos los ficheros
    uploaded_files = session.get("uploaded_files", {})
    files = all(f in uploaded_files and uploaded_files[f] != '' for f in ('A', 'B', 'C'))

    # Comprobar si existe el pdf
    data = {
        "id": session.get("id")
        }
    api_url = current_app.config.get("API_URL")

    try:
        backend_unify_response = requests.post(f"{api_url}/estan_unificados", data=data)
        backend_unify_response.raise_for_status()

        # Check if the response has content
        if backend_unify_response.content:
            unify_data = backend_unify_response.json()
        else:
            unify_data = {"logs": "No se recibió respuesta del backend."}

    except requests.exceptions.RequestException as e:
        unify_data = {"logs": f"Error al llamar al backend: {e}"}
    ready = files & unify_data.get('logs', '')
    return jsonify({"ready": ready})



@fileUpload_bp.route("/check_mandatory_files_status", methods=["POST"])
def check_mandatory_files_status():
    """Check whether mandatory files have been uploaded.

    This endpoint verifies that the mandatory file (type A) has been
    successfully uploaded and registered in the current user session.

    The validation is performed exclusively using session data and
    does not involve any backend API calls.

    Returns:
        flask.Response: JSON response containing:
            - ready (bool): True if the mandatory file is present in
              the session; False otherwise.
    """
    # Comprobar si estan o no todos los ficheros
    uploaded_files = session.get("uploaded_files", {})
    ready = bool(uploaded_files.get("A"))
    return jsonify({"ready": ready})



@fileUpload_bp.route("/try_unify_all_files", methods = ['POST'])
def try_unify_all_files():
    """Attempt to unify all required uploaded files.

    This endpoint checks whether all required files (types A, B, and C)
    have been successfully uploaded in the current session. If so, it
    triggers a backend process to unify all files into a consolidated
    result.

    The function returns a readiness flag based on local validation
    and backend response status.

    Returns:
        flask.Response: JSON response containing:
            - ready (bool): True if all required files are present and
              the backend unification request is successfully triggered;
              False otherwise.

    Side Effects:
        - Sends an HTTP POST request to the backend API to initiate
          file unification.
    """
    # Comprobar si estan o no todos los ficheros
    uploaded_files = session.get("uploaded_files", {})
    ready = all(f in uploaded_files and uploaded_files[f] != '' for f in ('A', 'B', 'C'))

    if ready:
        # Mandar a unificar los 3 ficheros
        data = {
            "id": session.get("id")
            }
        api_url = current_app.config.get("API_URL")

        # Comprobar si ya estan unificados

        try:
            backend_unify_response = requests.post(f"{api_url}/unifyAllFiles", data=data)
            backend_unify_response.raise_for_status()

            if backend_unify_response.status_code != 200:
                return jsonify({"ready": False})

            # Check if the response has content
            if backend_unify_response.content:
                unify_data = backend_unify_response.json()
            else:
                unify_data = {"logs": "No se recibió respuesta del backend."}

        except requests.exceptions.RequestException as e:
            unify_data = {"logs": f"Error al llamar al backend: {e}"}

    return jsonify({"ready": ready})
