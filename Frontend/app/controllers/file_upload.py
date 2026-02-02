from flask import Blueprint, request, current_app, session, jsonify
from .file_validation import ensure_session_folder, valid_file
from werkzeug.utils import secure_filename
import os, requests


file_upload_bp = Blueprint('file_upload', __name__, template_folder='templates')




# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@file_upload_bp.route('/upload_file_A', methods=['POST'])
def upload_file_A():
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




@file_upload_bp.route('/upload_files_B_C', methods=['POST'])
def upload_files_B_C():
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




@file_upload_bp.route("/try_unify_all_files", methods = ['GET'])
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
