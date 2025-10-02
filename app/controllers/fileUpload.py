from flask import Blueprint, request, current_app, redirect, url_for, session
from werkzeug.utils import secure_filename
import pandas as pd
import os

fileUpload_bp = Blueprint('fileUpload', __name__, template_folder='templates')


def valid_extension(name):
    valid_ext = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in name and name.rsplit('.', 1)[1].lower() in valid_ext


# FIXME: hacer que lance alerta
@fileUpload_bp.route('/validateFile')
def valid_file(path, file):
    df = pd.read_csv(path, delimiter=';', low_memory=False)
    match file:
        case "A":
            required_columns = {'fec_lectura_medicion', 'longitud_wgs84_gd', 'latitud_wgs84_gd', 'cod_inv_pda'}
            if not required_columns.issubset(set(df.columns)):
                df = None
                return 'El fichero CSV debe contener las columnas:\nfec_lectura_medicion, longitud_wgs84_gd, latitud_wgs84_gd, cod_inv_pda', 400
        case "B":
            required_columns = {'Num Inv', 'Fec Actividad', 'Seg Transcurrido'}
            if not required_columns.issubset(set(df.columns)):
                df = None
                return 'El fichero CSV debe contener las columnas:\nNum Inv, Fec Actividad, Seg Transcurrido', 400
        case "C":
            required_columns = {'COD_SECCION', 'INSTANTE', 'LONGITUD', 'LATITUD'}
            if not required_columns.issubset(set(df.columns)):
                df = None
                return 'El fichero CSV debe contener las columnas:\nCOD_SECCION, INSTANTE, LONGITUD, LATITUD', 400
        case _:
            return 'El fichero CSV no cumple ningún requisito de columnas', 400


# TODO: cabiar el error para que salga una alerta
@fileUpload_bp.route('/fileUploadA', methods=['POST'])
def upload_file_A():
    f = request.files['fileA']
    data_filename = secure_filename(f.filename)
    if f and valid_extension(data_filename):
        f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename))
        session['uploaded_data_A_file_path'] = os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename)
        valid_file(session['uploaded_data_A_file_path'], "A")
        return redirect(url_for('main.root'))
    return 'Extensión no permitida. Asegurese de que el archivo tiene extensión CSV, XLS o XLSX', 400


# TODO: cabiar el error para que salga una alerta
@fileUpload_bp.route('/fileUploadB', methods=['POST'])
def upload_file_B():
    f = request.files['fileB']
    data_filename = secure_filename(f.filename)
    if f and valid_extension(data_filename):
        f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename))
        session['uploaded_data_B_file_path'] = os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename)
        valid_file(session['uploaded_data_B_file_path'], "B")
        return redirect(url_for('main.root'))
    return 'Extensión no permitida. Asegurese de que el archivo tiene extensión CSV, XLS o XLSX', 400


# TODO: cabiar el error para que salga una alerta
@fileUpload_bp.route('/fileUploadC', methods=['POST'])
def upload_file_C():
    f = request.files['fileC']
    data_filename = secure_filename(f.filename)
    if f and valid_extension(data_filename):
        f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename))
        session['uploaded_data_C_file_path'] = os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename)
        valid_file(session['uploaded_data_C_file_path'], "C")
        return redirect(url_for('main.root'))
    return 'Extensión no permitida. Asegurese de que el archivo tiene extensión CSV, XLS o XLSX', 400