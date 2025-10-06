from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename
from app.utils.socketClient import send_data_for_processing
import pandas as pd
import os

generateResults_bp = Blueprint('generateResults', __name__, template_folder='templates')



@generateResults_bp.route('/generar_mapa')
def generar_mapa():
    if not current_app.config['UPLOADED_FILES']['A']:
        flash("Error: Necesitas subir el fichero A para generar el mapa.", 'error')
        return redirect(url_for('main.root'))
    # Aquí iría la lógica de generar el mapa
    return "Mapa generado con éxito."

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