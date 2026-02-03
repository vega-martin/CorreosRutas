from flask import Blueprint, request, current_app, session, jsonify
import pandas as pd
import numpy as np
import os

options_bp = Blueprint('options', __name__, template_folder='templates')




# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@options_bp.route('/get_unit_code', methods=['GET'])
def get_unit_code():
    """
    JSON: Devuelve un JSON con la lista de códigos de las oficinas de los ficheros
    Error: En caso de error, devuelve la razón
    {'codireds': [], 'error': ...}
    """

    uploaded = session.get('uploaded_files', {})
    path = uploaded.get('E')
    current_app.logger.info("Abriendo fichero E")

    if not path or not os.path.exists(path):
        current_app.logger.warning("Ruta de Fichero E no disponible o archivo no encontrado en disco.")
        return jsonify({'codireds': [], 'error': 'Ruta de Fichero E no disponible o no válido.'})

    try:
        current_app.logger.info(f"Abriendo fichero E desde: {path}")
        df = pd.read_csv(path, delimiter=';', low_memory=False)
        
    except Exception as e:
        current_app.logger.error(f"Error al leer el archivo CSV: {e}")
        return jsonify({'codireds': [], 'error': f'Error de procesamiento en Pandas: {str(e)}'})
    
    # PROCESAMIENTO
    try:
        cods = np.sort(df['codired'].dropna().unique()).tolist()
        current_app.logger.info(f"Se han encontrado {len(cods)} códigos de oficinas")

        return jsonify({'codireds' : cods})

    except KeyError:
        # Si la columna 'codired' no existe en el CSV
        current_app.logger.error("La columna 'codired' no fue encontrada en el CSV.")
        return jsonify({'codireds': [], 'error': "La columna 'codired' no fue encontrada."})




@options_bp.route('/get_pdas_per_unit_code')
def get_pdas_per_unit_code():
    cod = request.args.get('cod')
    uploaded = session.get('uploaded_files', {})
    path = uploaded.get('E')
    current_app.logger.info("Abriendo fichero E")
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return []

    if not path or not cod:
        return jsonify({'pdas': []})
    
    current_app.logger.info(f"Buscando regsitros perteneciente a la oficina {cod}")
    df = df[df['codired'] == int(cod)]
    current_app.logger.info(f"Se han encotrado {len(df)} registros de la oficina {cod}")
    pdas = df['cod_pda'].dropna().unique()
    pdas = np.sort(pdas).tolist()
    current_app.logger.info(f"Se han encontrado {len(pdas)} pdas en la oficina {cod}")
    return jsonify({'pdas': pdas})




@options_bp.route('/get_dates_per_pda_and_unit_code')
def get_dates_per_pda_and_unit_code():
    pda = request.args.get('pda')
    unit_code = request.args.get('unit_code')
    uploaded = session.get('uploaded_files', {})
    path = uploaded.get('E')
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return []

    if not path or not pda:
        return jsonify({'fechas': []})

    if pda == "TODAS":
        fechas = get_dates_for_all_pdas(df, unit_code)
    else:
        fechas = get_dates_per_pda(df, pda, unit_code)

    current_app.logger.info(f"fechas encontradas en {unit_code} para {pda}:\n{fechas}")

    return jsonify({'fechas': fechas})




# ------------------------------------------------------------
# AUXILIARY FUNCTIONS
# ------------------------------------------------------------

def get_dates_per_pda(df, pda, unit_code):
    df_filtered = df[(df['codired'] == int(unit_code)) & (df['cod_pda'] == pda)]
    return sorted(df_filtered['solo_fecha'].dropna().unique())




def get_dates_for_all_pdas(df, unit_code):
    df_filtered = df[df['codired'] == int(unit_code)]
    return (sorted(df_filtered['solo_fecha'].dropna().unique()))