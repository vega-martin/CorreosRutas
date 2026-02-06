from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash
from .geo_analysis import asociar_direcciones_a_puntos
from .file_upload import ensure_session_folder
from .util import parse_coord
from .map_generation import create_map
from geopy.distance import geodesic
import os, urllib, json
import pandas as pd

data_generation_bp = Blueprint('data_generation', __name__, template_folder='templates')




# ------------------------------------------------------------
# TODO: Esto se elimina, deberia ser una llamada a la API
# OBTENCIÓN DE DATOS
# ------------------------------------------------------------

def calcular_resumen(resultados):
    """
    Calcula resumen global a partir de la lista de resultados generada en calcular_metricas().
    Retorna un diccionario con:
        puntos_totales, distancia_total, tiempo_total, velocidad_media
    """

    # Ignorar el primer punto (que no tiene valores numéricos)
    distancias = []
    tiempos = []

    for r in resultados:
        try:
            if r["distancia"] != "-" and r["tiempo"] != "-":
                # Extraer valores numéricos
                d = float(r["distancia"].replace(" m", ""))
                t_sec = float(r["tiempo"].replace(" sec", ""))
                distancias.append(d)
                tiempos.append(t_sec)
        except Exception:
            continue

    puntos_totales = len(resultados)
    distancia_total = sum(distancias) / 1000.0
    tiempo_total_min = sum(tiempos) / 60.0
    tiempo_total_h = tiempo_total_min / 60.0 if tiempo_total_min > 0 else 0

    velocidad_media = (distancia_total / tiempo_total_h) if tiempo_total_h > 0 else 0

    # Formatear valores legibles
    resumen = {
        "puntos_totales": puntos_totales,
        "distancia_total": f"{distancia_total:.2f} km",
        "tiempo_total": f"{int(tiempo_total_min)} min",
        "velocidad_media": f"{velocidad_media:.2f} km/h"
    }

    return resumen



def calcular_metricas(df_filtrado):
    """
    Calcula distancia, tiempo y velocidad entre mediciones consecutivas.

    Parámetro:
        df_filtrado: DataFrame con columnas 
                     ['fecha_hora', 'solo_fecha', 'solo_hora' 'longitud', 'latitud', 'es_parada', 'cod_pda']

    Retorna:
        Diccionario con los campos:
        tabla: {[{n, hora, longitud, latitud, distancia, tiempo, velocidad, cod_pda, fecha},...]},
        resumen: {puntos_totales, distancia_total, tiempo_total, velocidad_media}
    """

    # Asegurar que el DataFrame esté ordenado por fecha/hora
    df_filtrado = df_filtrado.sort_values(['cod_pda', 'fecha_hora'], ascending=[True, True]).reset_index(drop=True)

    # Obtener todos los dias
    dias = df_filtrado['solo_fecha'].unique()

    resultados = []

    # Recorrer todos los dias
    for dia in dias:
        df_diario = df_filtrado[df_filtrado['solo_fecha'] == dia]
        # Obtener todas las pdas del dia
        pdas = df_filtrado['cod_pda'].unique()
        for pda in pdas:
            df_diario_pda = df_diario[df_diario['cod_pda'] == pda]

            # Generar datos de cada df por dia
            for i in range(len(df_diario_pda)):
                fila = df_diario_pda.iloc[i]

                hora = fila['solo_hora']
                es_parada = fila['es_parada']
                cod_pda = fila['cod_pda']
                fecha = fila['solo_fecha']

                lon = parse_coord(fila['longitud'])
                lat = parse_coord(fila['latitud'])

                # Primer punto
                if i == 0:
                    distancia = "-"
                    tiempo = "-"
                    velocidad = "-"
                else:
                    fila_prev = df_diario_pda.iloc[i - 1]

                    # Calcular distancia (en km)
                    lon2 = parse_coord(fila_prev['longitud'])
                    lat2 = parse_coord(fila_prev['latitud'])

                    punto1 = (lat2, lon2)
                    punto2 = (lat, lon)

                                
                    try:
                        distancia_km = geodesic(punto1, punto2).kilometers
                        distancia_m = geodesic(punto1, punto2).meters
                    except Exception:
                        flash("Error: El punto no es válido", 'warning')
                    

                    # Calcular tiempo en horas
                    hora_i = pd.to_timedelta(fila['solo_hora'])
                    hora_prev = pd.to_timedelta(fila_prev['solo_hora'])
                    delta_t = int((hora_i - hora_prev).total_seconds())
                    tiempo_horas = delta_t / 3600.0

                    # Calcular velocidad (km/h)
                    if tiempo_horas > 0:
                        velocidad_kmh = distancia_km / tiempo_horas
                    else:
                        velocidad_kmh = 0.0

                    # Formatear resultados legibles
                    distancia = f"{distancia_m:.3f} m"
                    tiempo = f"{int(delta_t)} sec"
                    velocidad = f"{velocidad_kmh:.2f} km/h"

                resultados.append({
                    "n": i + 1,
                    "hora": hora,
                    "longitud": lon,
                    "latitud": lat,
                    "distancia": distancia,
                    "tiempo": tiempo,
                    "velocidad": velocidad,
                    "es_parada": bool(es_parada),
                    "cod_pda": cod_pda,
                    "fecha": fecha
                })

    resumen = calcular_resumen(resultados)

    return {"tabla": resultados, "resumen": resumen}



def get_datos(cod, pda, fecha_ini, fecha_fin):
    """
    Devuelve un diccionario con los cambios tabla y resumen
    """
    # Obtener fichero
    uploaded = session.get('uploaded_files', {})
    path = uploaded.get('E')
    
    # Abrir fichero
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        current_app.logger.error(f"Error al leer el archivo CSV: {e}")
        return []
    
    df = df[df['cod_unidad'] == int(cod)]

    # --- FILTRO POR PDA ---
    if pda == "TODAS":
        df_aux = df
    else:
        df_aux = df[df['cod_pda'] == pda]

    # --- FILTRO POR FECHA SIN HORA
    if fecha_fin:  
        # rango de fechas
        df_filtrado = df_aux[
            (df_aux['solo_fecha'] >= fecha_ini) &
            (df_aux['solo_fecha'] <= fecha_fin)
        ].copy()
    else:
        # solo una fecha
        df_filtrado = df_aux[df_aux['solo_fecha'] == fecha_ini].copy()

    if df_filtrado.empty:
        current_app.logger.error(f"No hay datos para PDA={pda} y fecha={fecha_ini}")
        return []

    # Extraer solo las columnas que interesan
    # CAMBIO: se añade cod_pda
    columnas = ['fecha_hora', 'solo_fecha', 'solo_hora', 'longitud', 'latitud', 'es_parada','cod_pda']
    df_filtrado = df_filtrado[columnas].dropna()
    resultados = calcular_metricas(df_filtrado)

    return resultados




def conteo_tipo_de_calles(datos):
    """
    Funcion que cuenta el num de par/impar y zigzag por cada calle
    de la tabla.
    Devuleve un diccionario con la siugiente estructura:
    resultado = {
        "nombre_calle": {
            "par/impar": num1,
            "zigzag": num2
            "tipo": "par/impar o zigzag"
        }
    }
    """
    resultado = {}

    # Recorremos pares consecutivos
    for i in range(1, len(datos)):
        actual = datos[i]
        anterior = datos[i - 1]

        calle_act = actual["street"]
        calle_ant = anterior["street"]

        # Solo comparamos si es la misma calle
        if calle_act != calle_ant:
            continue

        # Convertir números a enteros
        try:
            num_act = int(actual["number"])
            num_ant = int(anterior["number"])
        except ValueError:
            # Si algún número no es válido, saltamos comparación
            continue

        # Inicializar estructura si no existe
        if calle_act not in resultado:
            resultado[calle_act] = {
                "par/impar": 0,
                "zigzag": 0,
                "tipo": ""
            }

        mismo_tipo = (num_act % 2) == (num_ant % 2)

        if mismo_tipo:
            resultado[calle_act]["par/impar"] += 1
        else:
            resultado[calle_act]["zigzag"] += 1

    # Determinar tipo dominante por cada calle
    for calle, valores in resultado.items():
        if valores["par/impar"] >= valores["zigzag"]:
            valores["tipo"] = "par/impar"
        else:
            valores["tipo"] = "zigzag"

    return resultado


def asignar_tipo_de_calle(datos, conteo):
    """
    A partir del conteo asignar el tipo de calle a cada uno de los pts
    """
    for dato in datos:
        calle = dato["street"]
        if calle in conteo:
            dato["conteo_par_impar"] = conteo[calle]["par/impar"]
            dato["conteo_zigzag"] = conteo[calle]["zigzag"]
            dato["tipo"] = conteo[calle]["tipo"]
        else:
            dato["conteo_par_impar"] = "-"
            dato["conteo_zigzag"] = "-"
            dato["tipo"] = "-"
    return datos




# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@data_generation_bp.route('/generar_mapa/datos_tabla', methods=['GET', 'POST'])
def datos_tabla():
    data = request.get_json()
    cod = data.get('cod')
    pda = data.get('pda')
    ini = data.get('ini')
    fin = data.get('fin')

    # TODO: cambiar para que llame a la API del backend y no lo haga aqui

    # Los argumentos son strings, por ejemplo
    # pda = "PDA01"
    # ini = "2025-10-18"
    resultados = get_datos(cod, pda, ini, fin)

    # Almacenar datos tabla en carpeta del usuario
    if not isinstance(resultados, dict) or 'tabla' not in resultados:
        current_app.logger.error("get_datos no devolvió el diccionario esperado con la clave 'tabla'.")
        return jsonify({"error": "Error al obtener los datos procesados."}), 500
    
    try:
        # 2. Preparar la Clusterización (Lógica traída de clusterizar_portales)
        static_dir = current_app.config.get("GEOJSON_FOLDER")
        file_geojson = os.path.join(static_dir, f'{cod}.geojson')

        # Verificar si existe el GeoJSON antes de procesar
        if not os.path.exists(file_geojson):
            current_app.logger.warning(f"No se encontró archivo GeoJSON en: {file_geojson}. Se devolverán datos sin clusterizar.")
            # Si no hay mapa, usamos los datos originales sin procesar geometría
            datos_finales = resultados['tabla']
        else:
            current_app.logger.error(f"Empezando asignacion de portales...")
            # Llamamos a la función de geoAnalysis directamente pasando la lista 'tabla'
            puntos_asociados = asociar_direcciones_a_puntos(resultados['tabla'], file_geojson, cod)

            # Manejo de errores de la función de clusterización
            if isinstance(puntos_asociados, dict) and 'error' in puntos_asociados:
                current_app.logger.error(f"Error en clusterización: {puntos_asociados['error']}")
                return jsonify({"error": f"Error al procesar mapa: {puntos_asociados['error']}"}), 500
            
            datos_finales = puntos_asociados
            current_app.logger.error(f"Empezando conteo de par/impar y zigzag...")
            conteo = conteo_tipo_de_calles(resultados['tabla'])
            asignar_tipo_de_calle(resultados['tabla'], conteo)


        
        
        # datos_agrupados = agrupar_puntos_duplicados(datos_finales)
        
        # # Recalcular resumen con puntos agrupados
        # resumen_actualizado = calcular_resumen(datos_agrupados)

        # Obtener la ruta de la carpeta única del usuario
        user_folder = ensure_session_folder() 
        
        # Definir la ruta del archivo JSON donde guardaremos los datos
        processed_filename = 'table_data.json'
        save_path = os.path.join(user_folder, processed_filename)
        
        # Guardar la lista de diccionarios (el valor de 'tabla') en el disco
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(resultados['tabla'], f, ensure_ascii=False, indent=4)
        
        current_app.logger.info(f"Tabla procesada guardada en disco en: {str(save_path)}")

        # 4. Actualizar el objeto resultados con la tabla procesada para el retorno
        # resultados['tabla'] = datos_agrupados
        # resultados['resumen'] = resumen_actualizado

        # Devolvemos todo junto: tabla procesada + resumen + warnings
        return jsonify(resultados)

    except Exception as e:
        current_app.logger.error(f"Excepción en el proceso datos_tabla: {e}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

@data_generation_bp.route('/generar_mapa/get_mapa', methods=['GET', 'POST'])
def get_mapa():
    data = request.get_json()
    cod = data.get('cod')
    pda = data.get('pda')
    ini = data.get('ini')
    fin = data.get('fin')

    # TODO: cambiar para que llame a la API del backend y no lo haga aqui

    #created_maps = session.get('created_maps', [])
    #map = pda + "_" + ini
    #if map in created_maps:
    #    path = "/static/maps/" + cod + "/" + map + ".html"
    #    current_app.logger.info(f"Mapa ya creado. Url del mapa para la {pda}: {path}")
    #    return jsonify({'url': path})

    if pda == "TODAS" and ini != fin:
        html = """
        <html><body style="font-family:sans-serif;text-align:center;padding:20px;">
            <h2>Mapa no disponible</h2>
            <p>No se puede generar un mapa para varias fechas cuando PDA = TODAS.</p>
        </body></html>
        """
        data_url = "data:text/html," + urllib.parse.quote(html)
        return jsonify({'url': data_url})

    abs_path = create_map(cod, pda, ini, fin)
    current_app.logger.info(f"Ruta absoluta del mapa: {abs_path}")
    base_dir = current_app.config.get("BASE_DIR")
    base_dir = os.path.join(base_dir, "app")
    path = os.path.relpath(abs_path, base_dir)
    #created_maps.append(map)
    #session["created_maps"] = created_maps
    #current_app.logger.info(f"Nuevo mapa creado. Mapas creados: {created_maps}")
    current_app.logger.info(f"Url del mapa para la {pda}: {path}")
    return jsonify({'url': path})

