from flask import Blueprint, current_app, session, jsonify
import pandas as pd
import os, requests


file_validation_bp = Blueprint('file_validation', __name__, template_folder='templates')




# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@file_validation_bp.route("/check_files_status", methods=["GET"])
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




@file_validation_bp.route("/check_mandatory_files_status", methods=["GET"])
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




# ------------------------------------------------------------
# AUXILIARY FUNCTIONS
# ------------------------------------------------------------

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