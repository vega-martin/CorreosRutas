from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template
from werkzeug.utils import secure_filename
from app.utils.socketClient import send_data_for_processing
import pandas as pd

generateResults_bp = Blueprint('generateResults', __name__, template_folder='templates')

# ------------------------------------------------------------
# OBTENCIÓN DE OPCIONES
# ------------------------------------------------------------

def get_pdas(path):
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return []

    # Lista de nombres de columnas posibles que pueden contener las PDAs
    posibles_columnas = ['cod_inv_pda', 'Num Inv', 'COD_SECCION']

    for col in posibles_columnas:
        if col in df.columns:
            pdas = sorted(df[col].dropna().unique())
            return pdas  # Devuelve al encontrar la primera columna válida

    # Si no se encuentra ninguna columna válida
    print("No se encontró ninguna columna válida para extraer PDAs.")
    return []


def get_fechas(path):
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return []

    # Lista de nombres de columnas posibles que pueden contener las PDAs
    posibles_columnas = ['fec_lectura_medicion', 'Fec Actividad', 'INSTANTE']

    for col in posibles_columnas:
        if col in df.columns:
            fechas = sorted(df[col].dropna().unique())
            return fechas  # Devuelve al encontrar la primera columna válida

    # Si no se encuentra ninguna columna válida
    print("No se encontró ninguna columna válida para extraer PDAs.")
    return []



@generateResults_bp.route('/generar_mapa')
def generar_mapa():
    if not current_app.config['UPLOADED_FILES']['A']:
        flash("Error: Necesitas subir el fichero A para generar el mapa.", 'error')
        return redirect(url_for('main.root'))
    # Aquí iría la lógica de generar el mapa
    pdas = get_pdas(current_app.config['UPLOADED_FILES']['A'])
    fechas = get_fechas(current_app.config['UPLOADED_FILES']['A'])
    return render_template('options.html', pdas=pdas, fechas=fechas)



@generateResults_bp.route('/detectar_paradas')
def detectar_paradas():
    if not current_app.config['UPLOADED_FILES']['B'] or not current_app.config['UPLOADED_FILES']['C']:
        flash("Error: Necesitas subir los ficheros B y C para detectar paradas.", 'error')
        return redirect(url_for('main.root'))
    # Lógica de detección de paradas
    return "Paradas detectadas correctamente."

@generateResults_bp.route('/generar_paradas')
def generar_paradas():
    if not all([current_app.config['UPLOADED_FILES']['A'], current_app.config['UPLOADED_FILES']['B'], current_app.config['UPLOADED_FILES']['C']]):
        flash("Error: Necesitas subir los ficheros A, B y C para generar paradas.", 'error')
        return redirect(url_for('main.root'))
    # Lógica para generar paradas
    return "Paradas generadas correctamente."

@generateResults_bp.route('/grafica_vel_tiempo')
def grafica_vel_tiempo():
    if not current_app.config['UPLOADED_FILES']['A']:
        flash("Error: Necesitas subir el fichero A para generar la gráfica velocidad/tiempo.", 'error')
        return redirect(url_for('main.root'))
    # Lógica para gráfica
    return "Gráfica velocidad/tiempo generada."