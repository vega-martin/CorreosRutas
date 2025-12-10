from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template, Response
from pathlib import Path
from .geoAnalysis import asociar_direcciones_a_puntos
import pandas as pd
import numpy as np
import re
import json
import os, io, csv

options_bp = Blueprint('options', __name__, template_folder='templates')

@options_bp.route('/options')
def options():
    return render_template('options.html')


def get_fechas_por_pda(df, pda):
    df_filtrado = df[df['cod_pda'] == pda]
    fechas = sorted(df_filtrado['solo_fecha'].dropna().unique())
    return fechas

def get_fechas_por_todas_las_pdas(df):
    fechas = sorted(df['solo_fecha'].dropna().unique())
    return fechas
    
def extraer_num(text):
    """Busca el primer número (entero o decimal) en un string y lo devuelve como float."""
    if text is None:
        return None
    # Usa re.search para encontrar el patrón de dígitos y puntos
    match = re.search(r'[\d\.]+', str(text)) 
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None

def cumple_condicion(val, comp, ref):
    """Comprueba si el valor de la fila (val) cumple la condición (comp) con la referencia (ref)."""
    # Si los valores no son numéricos, no se puede comparar
    if val is None or ref is None:
        return False
        
    if comp == "menor": return val < ref
    if comp == "menor-igual": return val <= ref
    if comp == "igual": return val == ref
    if comp == "no-igual": return val != ref
    if comp == "mayor": return val > ref
    if comp == "mayor-igual": return val >= ref
    return False

# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------
@options_bp.route('/codireds', methods=['GET'])
def codireds():
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

@options_bp.route('/pda_por_codired')
def pda_por_codired():
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


@options_bp.route('/fechas_por_pda')
def fechas_por_pda():
    pda = request.args.get('pda')
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
        fechas = get_fechas_por_todas_las_pdas(df)
    else:
        fechas = get_fechas_por_pda(df, pda)

    return jsonify({'fechas': fechas})


@options_bp.route('/procesar_mapa', methods=['POST'])
def procesar_mapa():
    pda = request.form.get('pda')
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')

    if not (pda and fecha_inicio and fecha_fin):
        flash("Todos los campos son obligatorios", "error")
        return redirect(url_for('generateResults.generar_mapa'))

    if fecha_inicio >= fecha_fin:
        flash("La fecha de fin debe ser mayor que la de inicio", "error")
        return redirect(url_for('generateResults.generar_mapa'))

    return f"Procesando mapa para PDA: {pda} entre {fecha_inicio} y {fecha_fin}"

# ----- FILTRADO DE REGISTROS EN LA TABLA -----
@options_bp.route('/filtrar_registros', methods=['POST'])
def filtrar_registros():
    data = request.get_json()

    # Obtener la ruta del archivo de la sesión
    file_path = Path(os.path.join(current_app.config['UPLOAD_FOLDER'], session['id'], 'table_data.json'))
    datos_completos = []

    # Comprobar si la ruta existe y si el archivo realmente está allí
    if not file_path.exists():
        current_app.logger.error(f"Ruta de archivo no encontrada en sesión o archivo no existe: {file_path}")
        # Retorna una lista vacía si no hay datos disponibles
        return jsonify({"tabla": [], "resumen": {}, "warnings": ["No hay datos cargados para filtrar."]})

    # Cargar los datos desde el archivo JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            datos_completos = json.load(f)
        
    except json.JSONDecodeError:
        current_app.logger.error(f"Error al decodificar el archivo JSON: {file_path}")
        return jsonify({"tabla": [], "resumen": {}, "warnings": ["Error de formato en el archivo de datos."]})
    except Exception as e:
        current_app.logger.error(f"Error desconocido al leer el archivo de datos: {e}")
        return jsonify({"tabla": [], "resumen": {}, "warnings": ["Error al acceder a los datos de la sesión."]})
    
    filtros_recibidos = [
        {
            "campo": "distancia", 
            "comp": data.get('signoDistancia'), 
            "valor_str": data.get('distancia')
        },
        {
            "campo": "tiempo", 
            "comp": data.get('signoTiempo'), 
            "valor_str": data.get('tiempo')
        },
        {
            "campo": "velocidad", 
            "comp": data.get('signoVelocidad'), 
            "valor_str": data.get('velocidad')
        }
    ]
    
    # Preparar los datos para el filtrado
    resultados_filtrados = datos_completos.copy()
    
    # Aplicar los filtros iterativamente
    for filtro in filtros_recibidos:
        
        try:
            # Convertir el valor de referencia a float de forma segura
            valor_ref = float(filtro['valor_str']) if filtro['valor_str'] else None
        except (ValueError, TypeError):
            valor_ref = None 

        if valor_ref is not None and filtro['comp']:
            current_app.logger.info(f"valores de los filtros puestos: {str(filtro)}")
            # Se aplica la función cumple_condicion sobre los datos cargados
            resultados_filtrados = [
                fila for fila in resultados_filtrados
                if cumple_condicion(
                    extraer_num(fila.get(filtro['campo'])),
                    filtro['comp'],
                    valor_ref
                )
            ]

    # Recalcular resumen
    # TODO: Recalcular resumen en caso de que sea necesario
    # resumen_filtrado = calcular_resumen(resultados_filtrados) 

    # Devolver los resultados
    return jsonify({
        "tabla": resultados_filtrados,
        # "resumen": {"puntos_totales": len(resultados_filtrados), "distancia_total": "...", "tiempo_total": "...", "velocidad_media": "..."}, # Devuelve algo útil o vacío
        "warnings": []
    })


# ----------- Llamada geoAnalysis ---------------- #
@options_bp.route('/upload_geojson', methods=['POST'])
def upload_geojson():
    cod = request.form.get('cod')
    file = request.files.get('geojson_file')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    static_path = current_app.config.get("GEOJSON_FOLDER")
    geojson_path = Path(os.path.join(static_path, f'{cod}.geojson'))
    file.save(geojson_path)

    return jsonify({'success': True})

@options_bp.route('/existsGeoJSON', methods=['POST'])
def existsGeoJSON():
    data = request.get_json()
    cod = data.get("cod")
    static_path = current_app.config.get("GEOJSON_FOLDER")
    geojson_path = Path(os.path.join(static_path, f'{cod}.geojson'))
    current_app.logger.info(f"existe el geojson? {geojson_path.exists()}")
    return jsonify(exists=geojson_path.exists())


@options_bp.route('/clusterizar_portales', methods=['POST'])
def clusterizar_portales():
    data = request.get_json()
    cod = data.get("cod")
    # Por el momento, solo se pasa los datos de la sesión.
    # Los datos de geojson los proporcionarán ellos.

    # Obtener la ruta del archivo de la sesión
    file_path = Path(os.path.join(current_app.config['UPLOAD_FOLDER'], session['id'], 'table_data.json'))
    current_app.logger.info(f"La ruta donde se encuentran los datos es {file_path}")

    datos_completos = []

    # Comprobar si la ruta existe y si el archivo realmente está allí
    if not file_path.exists():
        current_app.logger.error(f"Ruta de archivo no encontrada en sesión o archivo no existe: {file_path}")
        # Retorna una lista vacía si no hay datos disponibles
        return jsonify({"tabla": [], "resumen": {}, "warnings": ["No hay datos cargados para filtrar mostrar."]})

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            datos_completos = json.load(f)
        
    except Exception as e:
        current_app.logger.error(f"Error al leer o decodificar datos de usuario: {e}")
        return jsonify({"tabla": [], "resumen": {}, "warnings": ["Error al cargar datos de usuario."]})
    
    static_dir = current_app.config.get("GEOJSON_FOLDER")
    file_geojson = os.path.join(static_dir, f'{cod}.geojson')
    current_app.logger.error(f"Ruta del archivo geojson {file_geojson}")

    puntos_asociados = asociar_direcciones_a_puntos(datos_completos,file_geojson)

    # Manejo de errores devuelto por la función de servicio (e.g., error al cargar GeoJSON)
    if isinstance(puntos_asociados, dict) and 'error' in puntos_asociados:
        current_app.logger.error(f"Error en servicio geoAnalysis: {puntos_asociados['error']}")
        return jsonify({"tabla": [], "resumen": {}, "warnings": [puntos_asociados['error']]}), 500
    
    # Reescribir json de la tabla con los portales
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    processed_filename = 'table_data.json'
    save_path = os.path.join(upload_folder, session.get("id"), processed_filename)
    
    # Guardar la lista de diccionarios (el valor de 'tabla') en el disco
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(puntos_asociados, f, ensure_ascii=False, indent=4)

    # Retorno Final: Devolvemos la lista de puntos de usuario enriquecidos
    return jsonify({"tabla": puntos_asociados, "resumen": {}, "warnings": []}), 200


@options_bp.route("/getTable", methods=["GET"])
def get_table():
    # Ruta del JSON local
    json_path = os.path.join(current_app.config["UPLOAD_FOLDER"], session.get("id"), "table_data.json")

    if not os.path.exists(json_path):
        return "JSON file not found", 404

    # Leer JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        return "JSON empty or invalid", 400
    
    for dato in data:
        dato['longitud'] = str(dato['longitud']).replace('.', ',')
        dato['latitud'] = str(dato['latitud']).replace('.', ',')
        dato['distance'] = str(dato['distance']).replace('.', ',')
        dato['nearest_latitud'] = str(dato['nearest_latitud']).replace('.', ',')
        dato['nearest_longitud'] = str(dato['nearest_longitud']).replace('.', ',')
        dato['distancia'] = str(dato['distancia']).replace(' m', '').replace('.', ',')
        dato['tiempo'] = str(dato['tiempo']).replace(' sec', '')
        dato['velocidad'] = str(dato['velocidad']).replace(' km/h', '').replace('.', ',')
        


    # Convertir a CSV en memoria
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys(), delimiter=';')
    writer.writeheader()
    writer.writerows(data)
    csv_data = output.getvalue()

    # Ponerle el BOM a los datos
    csv_text = '\ufeff' + output.getvalue()

    # Enviar a frontend como archivo descargable
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=tabla.csv"
        }
    )