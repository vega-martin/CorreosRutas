from flask import Blueprint, request, current_app, redirect, url_for, session
from werkzeug.utils import secure_filename
import os

subidaArchivos_bp = Blueprint('subidaArchivos', __name__, template_folder='templates')

def extension_valida(nombre):
    ext_permitidas = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in ext_permitidas

@subidaArchivos_bp.route('/subirArchivoA', methods=['POST'])
def subir_archivo_A():
    f = request.files['FicheroA']
    if f and extension_valida(f):
        data_filename = secure_filename(f.filename)
        f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename))
        session['uploaded_data_A_file_path'] = os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename)
        return redirect(url_for('main.inicio'))
    return 'Extensión no permitida. Asegurese de que el archivo tiene extensión CSV, XLS o XLSX', 400

@subidaArchivos_bp.route('/subirArchivoB', methods=['POST'])
def subir_archivo_B():
    f = request.files['FicheroB']
    if f and extension_valida(f):
        data_filename = secure_filename(f.filename)
        f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename))
        session['uploaded_data_B_file_path'] = os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename)
        return redirect(url_for('main.inicio'))
    return 'Extensión no permitida. Asegurese de que el archivo tiene extensión CSV, XLS o XLSX', 400

@subidaArchivos_bp.route('/subirArchivoC', methods=['POST'])
def subir_archivo_C():
    f = request.files['FicheroC']
    if f and extension_valida(f):
        data_filename = secure_filename(f.filename)
        f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename))
        session['uploaded_data_C_file_path'] = os.path.join(current_app.config['UPLOAD_FOLDER'], data_filename)
        return redirect(url_for('main.inicio'))
    return 'Extensión no permitida. Asegurese de que el archivo tiene extensión CSV, XLS o XLSX', 400