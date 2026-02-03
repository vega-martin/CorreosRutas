from flask import Blueprint, request, current_app, session, jsonify
from .map_generation import create_cluster_map
from .data_generation import calcular_resumen
from pathlib import Path
import os,json, requests
import pandas as pd

data_clusterization_bp = Blueprint('data_clusterization', __name__, template_folder='templates')




# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@data_clusterization_bp.route('/agrupar_por_tipo', methods=['POST'])
def agrupar_por_tipo():
    """
    Endpoint que recibe una tabla de puntos y los agrupa dependiendo del algoritmo seleccionado
    """
    data = request.get_json()
    algoritmo = data.get('agrupamiento')
    cod = data.get('cod')

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

    tabla = datos_completos

    if not tabla:
        return jsonify({"error": "No hay datos para agrupar"}), 400

    match algoritmo:
        case "tiempo":
            # Agrupar puntos duplicados
            datos_agrupados = cluster_por_tiempo(tabla)

            # Reescribir json de la tabla con los portales
            upload_folder = current_app.config.get("UPLOAD_FOLDER")
            processed_filename = 'table_data_filtered.json'
            save_path = os.path.join(upload_folder, session.get("id"), processed_filename)
            
            # Guardar la lista de diccionarios (el valor de 'tabla') en el disco
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(datos_agrupados, f, ensure_ascii=False, indent=4)
            
            # Recalcular resumen con puntos agrupados
            resumen_actualizado = calcular_resumen(datos_agrupados)
            map_path = create_cluster_map(cod)

            return jsonify({
                        "url": map_path,
                        "tabla": datos_agrupados,
                        "resumen": resumen_actualizado
                    })
        case "diametro":
            payload = {
                "id": session.get("id"),
                "tabla": tabla
            }

            api_url = current_app.config.get("API_URL")

            try:
                api_response = requests.post(
                    f"{api_url}/agrupar_diametro",
                    json=payload,
                    timeout=30
                )
                api_response.raise_for_status()
            except requests.RequestException as e:
                current_app.logger.error(f"Error llamando a la API de diámetro: {e}")
                return jsonify({"error": "Error al procesar agrupación por diámetro"}), 502

            resultado = api_response.json().get("tabla")
            # Reescribir json de la tabla con los portales
            upload_folder = current_app.config.get("UPLOAD_FOLDER")
            processed_filename = 'table_data_filtered.json'
            save_path = os.path.join(upload_folder, session.get("id"), processed_filename)
            
            # Guardar la lista de diccionarios (el valor de 'tabla') en el disco
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, ensure_ascii=False, indent=4)

            map_path = create_cluster_map(cod)
            return jsonify({"url": map_path, "tabla": resultado})
        case _:
            return jsonify({"error": f"Error al especificar un algoritmo de agrupacion"}), 406




# ------------------------------------------------------------
# AUXILIARY FUNCTIONS
# ------------------------------------------------------------

def cluster_por_tiempo(tabla):
    """
    Aplica un filtro donde elimina todos los registros que no superen un tiempo mínimo.
    
    Parámetro:
        tabla: lista de diccionarios con campos [n, hora, longitud, latitud, distancia, tiempo, velocidad, esParada, cod_pda, fecha, ...]
    
    Retorna:
        lista de diccionarios con puntos filtrados
    """
    THRESHOLD = 100

    if not tabla:
        return []
    
    # Crear dataframe
    df = pd.DataFrame(tabla)

    df_filtrado = df[df['tiempo'] >= THRESHOLD]

    return df_filtrado.to_dict('records')