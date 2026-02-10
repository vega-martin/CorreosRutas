from flask import Blueprint, request, current_app, session, jsonify
from .data_generation import calcular_resumen
from pathlib import Path
import pandas as pd
import os, json

data_aggregation_bp = Blueprint('data_aggregation', __name__, template_folder='templates')




# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@data_aggregation_bp.route('/agrupar_puntos', methods=['POST'])
def agrupar_puntos():
    """
    Endpoint que recibe una tabla de puntos y los agrupa si tienen coordenadas duplicadas
    """

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

    try:
        # Agrupar puntos duplicados
        datos_agrupados = agrupar_puntos_duplicados(tabla)

        # Reescribir json de la tabla con los portales
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        processed_filename = 'table_data.json'
        save_path = os.path.join(upload_folder, session.get("id"), processed_filename)
        
        # Guardar la lista de diccionarios (el valor de 'tabla') en el disco
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(datos_agrupados, f, ensure_ascii=False, indent=4)
        
        # Recalcular resumen con puntos agrupados
        resumen_actualizado = calcular_resumen(datos_agrupados)

        return jsonify({
            "tabla": datos_agrupados,
            "resumen": resumen_actualizado
        })

    except Exception as e:
        current_app.logger.error(f"Error al agrupar puntos: {e}")
        return jsonify({"error": f"Error al agrupar puntos: {str(e)}"}), 500




@data_aggregation_bp.route('/agrupar_portales', methods=['POST'])
def agrupar_portales():
    """
    Endpoint que recibe una tabla de puntos y los agrupa si tienen portales duplicados
    """

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

    try:
        # Agrupar puntos duplicados
        datos_agrupados = agrupar_portales_duplicados(tabla)

        # Reescribir json de la tabla con los portales
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        processed_filename = 'table_data.json'
        save_path = os.path.join(upload_folder, session.get("id"), processed_filename)
        
        # Guardar la lista de diccionarios (el valor de 'tabla') en el disco
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(datos_agrupados, f, ensure_ascii=False, indent=4)
        
        # Recalcular resumen con puntos agrupados
        resumen_actualizado = calcular_resumen(datos_agrupados)

        return jsonify({
            "tabla": datos_agrupados,
            "resumen": resumen_actualizado
        })

    except Exception as e:
        current_app.logger.error(f"Error al agrupar portales: {e}")
        return jsonify({"error": f"Error al agrupar portales: {str(e)}"}), 500




# ------------------------------------------------------------
# AUXILIARY FUNCTIONS
# ------------------------------------------------------------

def agrupar_puntos_duplicados(resultados):
    """
    Agrupa puntos consecutivos con las mismas coordenadas y suma sus tiempos.
    
    Parámetro:
        resultados: lista de diccionarios con campos [n, hora, longitud, latitud, distancia, tiempo, velocidad, es_parada, cod_pda, fecha, ...]
    
    Retorna:
        lista de diccionarios con puntos agrupados y tiempos acumulados
    """
    
    if not resultados:
        return resultados
    
    resultados_agrupados = []
    tiempo_acumulado = 0
    velocidad_acumulada = 0
    punto_anterior = None
    indice = 1

    for r in resultados:
        # Crear tupla de coordenadas actual
        coord_actual = (r['street'], r['number'])
        
        # Si es el primer punto o es diferente al anterior
        if punto_anterior is None or coord_actual != punto_anterior:
            # Si hay un punto anterior, actualizar su tiempo con el acumulado
            if punto_anterior is not None and resultados_agrupados:
                if tiempo_acumulado > 0:
                    resultados_agrupados[-1]["tiempo"] = f"{int(tiempo_acumulado)} sec"
                    resultados_agrupados[-1]["velocidad"] = f"{round(velocidad_acumulada / indice,2)} km/h"
            
            # Añadir el punto actual como nuevo punto
            nuevo_punto = r.copy()
            nuevo_punto["n"] = indice
            resultados_agrupados.append(nuevo_punto)
            tiempo_acumulado = 0
            velocidad_acumulada = 0
            punto_anterior = coord_actual
            indice += 1
        else:
            # Mismo punto que el anterior, acumular tiempo
            if r["tiempo"] != "-":
                try:
                    tiempo_sec = float(r["tiempo"].replace(" sec", ""))
                    tiempo_acumulado += tiempo_sec
                    velocidad_km_h = float(r["velocidad"].replace(" km/h",""))
                    velocidad_acumulada += velocidad_km_h
                except ValueError:
                    pass

    # No olvidar el último grupo
    if resultados_agrupados and tiempo_acumulado > 0:
        resultados_agrupados[-1]["tiempo"] = f"{int(tiempo_acumulado)} sec"

    return resultados_agrupados




def agrupar_portales_duplicados(tabla):
    """
    Agrupa los portales que hayan sido visitados varias veces y suma sus tiempos.
    
    Parámetro:
        tabla: lista de diccionarios con campos [n, hora, longitud, latitud, distancia, tiempo, velocidad, es_parada, cod_pda, fecha, ...]
    
    Retorna:
        lista de diccionarios con puntos agrupados y tiempos acumulados
    """
    if not tabla:
        return []
    
    # Crear dataframe
    df = pd.DataFrame(tabla)

    # Limpiar datos
    df.loc[df['tiempo'] == "-", 'tiempo'] = "0 sec"
    df['tiempo_seg'] = df['tiempo'].str.replace(" sec", "", regex=False).astype(float)
    df['tiempo_signed'] = df['tiempo_seg'].where(~df['es_parada'], -df['tiempo_seg'])
    df.loc[df['distancia'] == "-", 'distancia'] = "0 m"
    df['distancia'] = df['distancia'].str.replace(" m", "", regex=False).astype(float)

    # Agrupar puntos
    df_agrupado = df.groupby(['street', 'number']).agg(
        #n = ('n', 'first'),
        cod_pda = ('cod_pda', lambda x: list(set(x))),
        #latitud_pt = ('latitud', 'mean'),
        #longitud_pt = ('longitud', 'mean'),
        #distance_last_pt = ('distancia', 'mean'),
        time_accumulated = ('tiempo_signed', 'sum'),
        time_mean = ('tiempo_signed', 'mean'),
        distance_portal = ('distance', 'mean'),
        latitud_portal = ('nearest_latitud', 'first'),
        longitud_portal = ('nearest_longitud', 'first'),
        post_code = ('post_code', lambda x: x.mode().iloc[0]),
        even_odd_count = ('conteo_par_impar', 'sum'),
        zigzag_count = ('conteo_zigzag', 'sum'),
        type = ('tipo', lambda x: x.mode().iloc[0]),
        is_stop = ('es_parada', 'any'),
        times_visited = ('tiempo_seg', 'count')
    ).reset_index()

    # Eliminar registros con tiempo negativo
    df_agrupado = df_agrupado[df_agrupado['time_accumulated'] > 0]

    # Add constant columns
    #df_agrupado['hora'] = '-'
    #df_agrupado['fecha'] = '-'
    #df_agrupado['velocidad'] = '-'

    return df_agrupado.to_dict('records')
