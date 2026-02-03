from flask import Blueprint, request, current_app, session, jsonify
from .geoAnalysis import asociar_direcciones_a_puntos
from pathlib import Path
import os,json

data_aggregation_bp = Blueprint('data_aggregation', __name__, template_folder='templates')




# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@data_aggregation_bp.route('/clusterizar_portales', methods=['POST'])
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
