from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename
from app.utils.socketClient import send_data_for_processing
import pandas as pd
import os

generateResults_bp = Blueprint('generateResults', __name__, template_folder='templates')


@generateResults_bp.route('/generateMap', methods=['POST'])
def generate_map():
    response = send_data_for_processing("hola".encode('utf-8'))
    print(f"Respuesta del server: {response}")

    return redirect(url_for('main.root'))


@generateResults_bp.route('/detectStops', methods=['POST'])
def detect_stops():
    response = send_data_for_processing("hola".encode('utf-8'))
    print(f"Respuesta del server: {response}")

    return redirect(url_for('main.root'))


@generateResults_bp.route('/generateStops', methods=['POST'])
def generate_stops():
    response = send_data_for_processing("hola".encode('utf-8'))
    print(f"Respuesta del server: {response}")

    return redirect(url_for('main.root'))


@generateResults_bp.route('/generateGraph', methods=['POST'])
def generate_graph():
    response = send_data_for_processing("hola".encode('utf-8'))
    print(f"Respuesta del server: {response}")

    return redirect(url_for('main.root'))