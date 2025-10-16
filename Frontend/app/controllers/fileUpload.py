from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template
from werkzeug.utils import secure_filename
import pandas as pd
import os, uuid, tempfile

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
    if not session_id:
        session_id = str(uuid.uuid4())
        session["id"] = session_id
        current_app.logger.info(f"Sesion creada: {session["id"]}")

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
        "A": {'fec_lectura_medicion', 'longitud_wgs84_gd', 'latitud_wgs84_gd', 'cod_inv_pda'},
        "B": {'Num Inv', 'Fec Actividad', 'Seg Transcurrido'},
        "C": {'COD_SECCION', 'INSTANTE', 'LONGITUD', 'LATITUD'}
    }

    required_columns = required_columns_map.get(file_type)

    if not required_columns:
        current_app.logger.error('Error: el fichero no cumple con los criterios')
        return jsonify({'error': f'El archivo no cumple con los criterios'}), 400
    
    if not required_columns.issubset(df.columns):
        return jsonify({'error': f'El fichero CSV debe contener las columnas: {", ".join(required_columns)}'}), 400
    
    current_app.logger.info('Archivo subido válido')

    return jsonify({'message': 'Archivo válido'}), 200


# ------------------------------------------------------------
# LECTURA Y DESCARGA DE FICHEROS EN LOCAL
# ------------------------------------------------------------

@fileUpload_bp.route('/fileUpload/<file_type>', methods=['POST'])
def upload_file(file_type):
    if file_type not in ('A', 'B', 'C'):
        flash('Tipo de fichero no reconocido.', 'error')
        return redirect(url_for('main.root'))

    file_key = f'file{file_type}'
    f = request.files.get(file_key)

    if not f or f.filename == '':
        flash('No se ha seleccionado ningún archivo.', 'error')
        return redirect(url_for('main.root'))
    
    data_filename = secure_filename(f.filename)

    if not valid_extension(data_filename):
        flash('Extensión no permitida. Asegúrese de que el archivo tiene extensión CSV, XLS o XLSX', 'error')
        return redirect(url_for('main.root'))

    user_folder = ensure_session_folder()
    save_path = os.path.join(user_folder, data_filename)
    f.save(save_path)

    response = valid_file(save_path, file_type)
    if response[1] != 200:
        os.remove(save_path)
        flash(response[0].json['error'], 'error')
        return redirect(url_for('main.root'))
    
    uploaded = session.get("uploaded_files", {})
    uploaded[file_type] = save_path
    session["uploaded_files"] = uploaded

    if not os.path.exists(save_path):
        current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
    else:
        current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
    
    flash(f'Fichero "{data_filename}" ({file_type}) subido correctamente.', 'success')
    return redirect(url_for('main.root'))
