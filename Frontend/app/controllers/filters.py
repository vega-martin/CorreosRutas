from flask import Blueprint, request, current_app, session, jsonify
from .map_generation import create_cluster_map
from pathlib import Path
import os,json, requests, re

filters_bp = Blueprint('filters', __name__, template_folder='templates')




# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@filters_bp.route('/filter_data', methods=['POST'])
def filter_data():
    data = request.get_json()

    # Obtener la ruta del archivo de la sesión
    file_path = Path(os.path.join(current_app.config['UPLOAD_FOLDER'], session['id'], 'table_data.json'))
    datos_completos = []
    url = ''

    # Comprobar si la ruta existe y si el archivo realmente está allí
    if not file_path.exists():
        current_app.logger.error(f"Ruta de archivo no encontrada en sesión o archivo no existe: {file_path}")
        # Retorna una lista vacía si no hay datos disponibles
        return jsonify({"tabla": [], "resumen": {}, "warnings": ["No hay datos cargados para filtrar."]})

    # Cargar los datos desde el archivo JSON
    try:
        current_app.logger.info("Leyendo tabla de datos")
        with open(file_path, 'r', encoding='utf-8') as f:
            datos_completos = json.load(f)
    
    except json.JSONDecodeError:
        current_app.logger.error(f"Error al decodificar el archivo JSON: {file_path}")
        return jsonify({"tabla": [], "resumen": {}, "warnings": ["Error de formato en el archivo de datos."]})
    except Exception as e:
        current_app.logger.error(f"Error desconocido al leer el archivo de datos: {e}")
        return jsonify({"tabla": [], "resumen": {}, "warnings": ["Error al acceder a los datos de la sesión."]})
    
    filtros_numerico_recibidos = [
        {
            "campo": "time_accumulated", 
            "comp": data.get('signoTimeAcc'), 
            "valor_str": data.get('timeAcc')
        },
        {
            "campo": "time_mean", 
            "comp": data.get('signoTimeMean'), 
            "valor_str": data.get('timeMean')
        }
        
    ]
    
    # Preparar los datos para el filtrado
    resultados_filtrados = datos_completos.copy()
    #current_app.logger.info(f"resultados filtrados: {str(resultados_filtrados)}")

    # Filtrar por PDA si se ha proporcionado
    current_app.logger.info("Filtrar PDA si hay")
    signoPda = data.get('signoPDA')
    valorPda = data.get('pda')
    if valorPda != "":
        current_app.logger.info(f"Valor de la PDA {valorPda} y signo {signoPda}")
        if signoPda == "igual" and valorPda is not None:
            resultados_filtrados = [
                    fila for fila in resultados_filtrados
                    if valorPda in (fila.get("cod_pda") or [])
                ] 
        elif signoPda == "no-igual" and valorPda is not None:
            resultados_filtrados = [
                    fila for fila in resultados_filtrados
                    if valorPda not in (fila.get("cod_pda") or [])
                ]

    # Recalcular clusters con nuevos filtros
    current_app.logger.info("Recalcular clusteres si es necesario")
    if data.get('diametro') != "" or data.get('numPts') != "" or data.get('maxTime') != "":
        payload = {
            "id": session.get("id"),
            "diametro": data.get('diametro'),
            "numPts": data.get('numPts'),
            "maxTime": data.get('maxTimeClus'),
            "tabla": datos_completos
        }
        current_app.logger.info(f"Valor del diametro {data.get('diametro')}, numpts {data.get('numPts')}, maxTime {data.get('maxTimeClus')}")
        api_url = current_app.config.get("API_URL")

        try:
            api_response = requests.post(
                f"{api_url}/filtrar_clustering",
                json=payload
            )
            api_response.raise_for_status()
            resultados_filtrados = api_response.json().get("tabla")
            upload_folder = current_app.config.get("UPLOAD_FOLDER")
            processed_filename = 'table_data_filtered.json'
            save_path = os.path.join(upload_folder, session.get("id"), processed_filename)
            
            # Guardar la lista de diccionarios (el valor de 'tabla') en el disco
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(resultados_filtrados, f, ensure_ascii=False, indent=4)
            cod = data.get('cod')
            url = create_cluster_map(cod, data.get('diametro'), data.get('numPts'), data.get('maxTime'))

        except requests.RequestException as e:
            current_app.logger.error(f"Error llamando a la API de diámetro: {e}")
            return jsonify({"error": "Error al procesar agrupación por diámetro"}), 502


    current_app.logger.info("Aplicar filtros generales")

    # Aplicar los filtros numéricos iterativamente
    if data.get('timeAcc') != "" or data.get('timeMean') != "":
        for filtro in filtros_numerico_recibidos:
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
    # Aplicar filtro de tipo
    type_filter = data.get('type')
    if type_filter != "":
        match type_filter:
            case "all":
                resultados_filtrados = resultados_filtrados
            case "even/odd":
                resultados_filtrados = [
                    fila for fila in resultados_filtrados
                    if fila.get("type") == "par/impar"
                ]
            case "zigzag":
                resultados_filtrados = [
                    fila for fila in resultados_filtrados
                    if fila.get("type") == "zigzag"
                ]
    # Aplicar filtro de parada
    stop_filter = data.get('isStop')
    if type_filter != "":
        match stop_filter:
            case "all":
                resultados_filtrados = resultados_filtrados
            case "true":
                resultados_filtrados = [
                    fila for fila in resultados_filtrados
                    if fila.get("is_stop") == True
                ]
            case "false":
                resultados_filtrados = [
                    fila for fila in resultados_filtrados
                    if fila.get("is_stop") == False
                ]

    # Recalcular resumen
    # TODO: Recalcular resumen en caso de que sea necesario
    # resumen_filtrado = calcular_resumen(resultados_filtrados) 
    current_app.logger.info("Devolver informacion")
    # Devolver los resultados
    return jsonify({
        "tabla": resultados_filtrados,
        # "resumen": {"puntos_totales": len(resultados_filtrados), "distancia_total": "...", "tiempo_total": "...", "velocidad_media": "..."}, # Devuelve algo útil o vacío
        "url": url,
        "warnings": []
    })




# ------------------------------------------------------------
# AUXILIARY FUNCTIONS
# ------------------------------------------------------------

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
    current_app.logger.info(f"Condicion: {val} {comp} {ref}")
    if val is None or ref is None:
        return False
    if comp == "menor": return val < ref
    if comp == "menor-igual": return val <= ref
    if comp == "igual": return val == ref
    if comp == "no-igual": return val != ref
    if comp == "mayor": return val > ref
    if comp == "mayor-igual": return val >= ref
    return False
