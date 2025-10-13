from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template
from werkzeug.utils import secure_filename
import pandas as pd
import os

fileUpload_bp = Blueprint('fileUpload', __name__, template_folder='templates')


# ------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------

def valid_extension(name):
    valid_ext = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in name and name.rsplit('.', 1)[1].lower() in valid_ext


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
        return jsonify({'error': f'El archivo no cumple con los criterios'}), 400
    
    if not required_columns.issubset(df.columns):
        return jsonify({'error': f'El fichero CSV debe contener las columnas: {", ".join(required_columns)}'}), 400
    
    return jsonify({'message': 'Archivo válido'}), 200


# ------------------------------------------------------------
# LECTURA Y DESCARGA DE FICHEROS EN LOCAL
# ------------------------------------------------------------

@fileUpload_bp.route('/fileUploadA', methods=['POST'])
def upload_file_A():
    f = request.files['fileA']
    data_filename = secure_filename(f.filename)

    if f and valid_extension(data_filename):
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename)
        f.save(save_path)

        response = valid_file(save_path, "A")
        if response[1] != 200:
            os.remove(save_path)
            flash(response[0].json['error'], 'error')
        current_app.config['UPLOADED_FILES']['A'] = save_path

        return redirect(url_for('main.root'))
    
    flash('Extensión no permitida. Asegurese de que el archivo tiene extensión CSV, XLS o XLSX', 'error')
    return redirect(url_for('main.root'))


@fileUpload_bp.route('/fileUploadB', methods=['POST'])
def upload_file_B():
    f = request.files['fileB']
    data_filename = secure_filename(f.filename)

    if f and valid_extension(data_filename):
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename)
        f.save(save_path)
        session['uploaded_data_B_file_path'] = save_path

        response = valid_file(save_path, "B")
        if response[1] != 200:
            os.remove(save_path)
            flash(response[0].json['error'], 'error')
        current_app.config['UPLOADED_FILES']['B'] = save_path
        
        return redirect(url_for('main.root'))
    
    flash('Extensión no permitida. Asegurese de que el archivo tiene extensión CSV, XLS o XLSX', 'error')
    return redirect(url_for('main.root'))


@fileUpload_bp.route('/fileUploadC', methods=['POST'])
def upload_file_C():
    f = request.files['fileC']
    data_filename = secure_filename(f.filename)

    if f and valid_extension(data_filename):
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename)
        f.save(save_path)
        session['uploaded_data_C_file_path'] = save_path

        response = valid_file(save_path, "C")
        if response[1] != 200:
            os.remove(save_path)
            flash(response[0].json['error'], 'error')
        current_app.config['UPLOADED_FILES']['C'] = save_path
        
        return redirect(url_for('main.root'))
    
    flash('Extensión no permitida. Asegurese de que el archivo tiene extensión CSV, XLS o XLSX', 'error')
    return redirect(url_for('main.root'))