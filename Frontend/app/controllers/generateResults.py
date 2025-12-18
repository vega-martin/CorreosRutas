from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template, Response
from geopy.distance import geodesic
import pandas as pd
import numpy as np
import folium
import os
import urllib
import json
import requests
from app.controllers.fileUpload import ensure_session_folder
from .geoAnalysis import asociar_direcciones_a_puntos
from pathlib import Path

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

    pdas = sorted(df['cod_pda'].dropna().unique())
    current_app.logger.info(f'Se encontraron {len(pdas)} PDAs.')
    return pdas



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
                     ['fecha_hora', 'solo_fecha', 'solo_hora' 'longitud', 'latitud', 'esParada', 'cod_pda']

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
                esParada = fila['esParada']
                cod_pda = fila['cod_pda']
                fecha = fila['solo_fecha']

                if ((fila['longitud'].count('.') <= 1) and (fila['latitud'].count('.') <= 1)):
                    lon = float(str(fila['longitud']).replace(',', '.'))
                    lat = float(str(fila['latitud']).replace(',', '.'))
                else:
                    lon_int = fila['longitud'].replace('.', '')
                    lon_float = lon_int[:2] + '.' + lon_int[2:]
                    lon = float(lon_float)
                    lat_int = fila['latitud'].replace('.', '')
                    lat_float = lat_int[:2] + '.' + lat_int[2:]
                    lat = float(lat_float)

                # Primer punto
                if i == 0:
                    distancia = "-"
                    tiempo = "-"
                    velocidad = "-"
                else:
                    fila_prev = df_diario_pda.iloc[i - 1]

                    # Calcular distancia (en km)
                    if ((fila_prev['longitud'].count('.') <= 1) and (fila_prev['latitud'].count('.') <= 1)):
                        punto1 = (float(str(fila_prev['latitud']).replace(',', '.')), float(str(fila_prev['longitud']).replace(',', '.')))
                    else:
                        lon_int = ''.join(fila_prev['longitud'].split('.'))
                        lon_float = lon_int[:2] + '.' + lon_int[2:]
                        lon2 = float(lon_float)
                        lat_int = ''.join(fila_prev['latitud'].split('.'))
                        lat_float = lat_int[:2] + '.' + lat_int[2:]
                        lat2 = float(lat_float)
                        punto1 = (lat2, lon2)
                    punto2 = (lat, lon)

                                
                    try:
                        distancia_km = geodesic(punto1, punto2).kilometers
                        distancia_m = geodesic(punto1, punto2).meters
                    except Exception:
                        flash("Error: El punto no es válido", 'warning')
                    

                    # Calcular tiempo en horas
                    hora_i = pd.to_datetime(fila['solo_hora'], format='%H:%M:%S')
                    hora_prev = pd.to_datetime(fila_prev['solo_hora'], format='%H:%M:%S')
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
                    "esParada": bool(esParada),
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
    
    df = df[df['codired'] == int(cod)]

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
    columnas = ['fecha_hora', 'solo_fecha', 'solo_hora', 'longitud', 'latitud', 'esParada','cod_pda']
    df_filtrado = df_filtrado[columnas].dropna()
    resultados = calcular_metricas(df_filtrado)

    return resultados


# ------------------------------------------------------------
# TODO: Esto se elimina, deberia ser una llamada a la API
# CREACION DE MAPA
# ------------------------------------------------------------

def corregir_coordenada(series):
    def corregir(x):
        try:
            # Reinsertamos el punto después de los 2 primeros dígitos
            s = x[:2] + '.' + x[2:]
            #current_app.logger.info(f"Convirtiendo numero de {x} a {s}")
            return float(s)
        except Exception:
            return np.nan
    return series.apply(corregir)


def save_map(cod, pda, fecha, map):
    """Guardar el mapa"""
    current_app.logger.info(f"Guardando mapa")
    base_dir = current_app.config.get("BASE_DIR")
    map_folder = os.path.join(base_dir, "app", "static", "maps", cod)
    os.makedirs(map_folder, exist_ok=True)
    if not os.path.exists(map_folder):
        current_app.logger.error(f"Error: no se creó la carpeta {map_folder}")
    else:
        current_app.logger.info(f"Carpeta creada correctamente: {map_folder}")

    map_name = pda + "_" + fecha + ".html"
    save_path = os.path.join(map_folder, map_name)
    map.save(save_path)

    if not os.path.exists(save_path):
        current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
    else:
        current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
    
    current_app.logger.info(f"Mapa guardado en {save_path}")
    return save_path




def create_map(cod, pda, fecha_ini, fecha_fin):
    """Crea un archivo html temporal con el mapa y agrega la dirección a la sesion"""
    # Obtener fichero
    uploaded = session.get('uploaded_files', {})
    path = uploaded.get('E')
    
    # Abrir fichero
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        current_app.logger.error(f"Error al leer el archivo CSV: {e}")
        return []
    
    df = df[df['codired'] == int(cod)]
    current_app.logger.info(f"Encontrados {len(df)} en la oficina {cod}")

    if (pda == "TODAS"):
        pdas_unicas = df['cod_pda'].unique().tolist()
    else:
        pdas_unicas = [pda]
    
    if (fecha_ini != fecha_fin):
        fechas_unicas = df['solo_fecha'].unique().tolist()
    else:
        fechas_unicas = [fecha_ini]
    
    colores = ['black', 'lightblue', 'blue', 'darkred', 'lightgreen',
               'purple', 'red', 'green', 'lightred', 'darkblue', 'darkpurple',
               'cadetblue', 'orange', 'pink', 'darkgreen']

    if pda == "TODAS":
        # color per PDA
        color_map = {pda_unica: colores[i % len(colores)]
                    for i, pda_unica in enumerate(pdas_unicas)}
        color_mode = "pda"
    else:
        # only one PDA -> color per date if multiple dates
        color_map = {dia: colores[i % len(colores)]
                    for i, dia in enumerate(fechas_unicas)}
        color_mode = "date"

    latitud_centrada = float(pd.to_numeric(df['latitud'].iloc[0].replace(",", "."), errors="coerce"))
    longitud_centrada = float(pd.to_numeric(df['longitud'].iloc[0].replace(",", "."), errors="coerce"))


    mapa = folium.Map(location=[latitud_centrada, longitud_centrada], zoom_start=15, control_scale=True)
    folium.TileLayer('CartoDB positron', name='Carto claro').add_to(mapa)

    for idx, pda_unica in enumerate(pdas_unicas):
        current_app.logger.info(f"Buscando fecha especifica en el df")

        # Filtrar por PDA y fecha (ignorando hora)
        df_aux = df[df['cod_pda'] == pda_unica].copy()

        df_aux = df_aux[
            (df_aux['solo_fecha'] >= fecha_ini) &
            (df_aux['solo_fecha'] <= fecha_fin)
        ].copy()

        dias = df_aux['solo_fecha'].unique()
        for dia in dias:
            if color_mode == "pda":
                ruta_color = color_map[pda_unica]
            else:
                ruta_color = color_map[dia]

            df_filtrado = df_aux[df_aux['solo_fecha'] == dia].copy()
            if df_filtrado.empty:
                current_app.logger.error(f"No hay datos para PDA={pda_unica} y fecha={dia}")
                continue

            df_filtrado = df_filtrado.sort_values('solo_hora')

            current_app.logger.info(f"Creando mapa con {len(df_filtrado)} registros")

            # Contamos cuántos puntos hay en cada valor
            df_filtrado['num_pts_lon'] = df_filtrado['longitud'].astype(str).str.count(r'\.')
            df_filtrado['num_pts_lat'] = df_filtrado['latitud'].astype(str).str.count(r'\.')

            # Comprobamos la media (o el valor típico) de puntos
            media_lon = df_filtrado['num_pts_lon'].mean()
            media_lat = df_filtrado['num_pts_lat'].mean()

            if ((media_lon <= 1) and (media_lat <= 1)):
                current_app.logger.info(f"Probando formato correcto de coordenadas")
                # Pasar de string a num
                df_filtrado['latitud'] = df_filtrado['latitud'].astype(str).str.replace(',', '.')
                df_filtrado['longitud'] = df_filtrado['longitud'].astype(str).str.replace(',', '.')

                df_filtrado['latitud'] = pd.to_numeric(df_filtrado['latitud'], errors='coerce')
                df_filtrado['longitud'] = pd.to_numeric(df_filtrado['longitud'], errors='coerce')
            else:
                df_filtrado['latitud'] = df_filtrado['latitud'].astype(str).str.replace('.', '', regex=False)
                df_filtrado['longitud'] = df_filtrado['longitud'].astype(str).str.replace('.', '', regex=False)

                current_app.logger.info(f"Probando a corregir coordenadas")
                # Corregir coordenadas ----------------------------
                df_filtrado['latitud'] = corregir_coordenada(df_filtrado['latitud'])
                df_filtrado['longitud'] = corregir_coordenada(df_filtrado['longitud'])

            df_filtrado.dropna()
            current_app.logger.info(f"Quedan {len(df_filtrado)} registros para generar el mapa")

            coordenadas = []

            for _, fila in df_filtrado.iterrows():
                coord = [fila['latitud'], fila['longitud']]
                coordenadas.append(coord)
                if bool(fila['esParada']):
                    my_color = ruta_color
                    my_opcacity = 1
                else:
                    my_color = ruta_color
                    my_opcacity = 0.7
                my_radius = 4
                folium.CircleMarker(
                    location=coord,
                    radius=my_radius,
                    stroke=False,
                    fill=True,
                    fill_color=my_color,
                    fill_opacity=my_opcacity,
                    popup=f"{my_radius}px",
                    tooltip=f"PDA: {pda_unica}<br>Fecha: {fila['fecha_hora']}<br>Coordenada: {fila['latitud']}, {fila['longitud']}"
                ).add_to(mapa)

            for i in range(len(coordenadas)-1):
                folium.PolyLine(
                    locations=[coordenadas[i], coordenadas[i+1]],
                    color=ruta_color,
                    weight=2,
                    opacity=0.4
                ).add_to(mapa)
            
            inicio = df_filtrado.iloc[0]
            folium.Marker(
                location=[inicio['latitud'], fila['longitud']],
                icon=folium.Icon(color='green', icon='play', prefix='fa'),
                popup="INICIO"
            ).add_to(mapa)

            fin = df_filtrado.iloc[-1]
            folium.Marker(
                location=[fin['latitud'], fin['longitud']],
                icon=folium.Icon(color='red', icon='play', prefix='fa'),
                popup="FIN"
            ).add_to(mapa)
            current_app.logger.info(f"Mapa creado")
    fecha = f"{fecha_ini}-{fecha_fin}"
    return save_map(cod, pda, fecha, mapa)

def agrupar_puntos_duplicados(resultados):
    """
    Agrupa puntos consecutivos con las mismas coordenadas y suma sus tiempos.
    
    Parámetro:
        resultados: lista de diccionarios con campos [n, hora, longitud, latitud, distancia, tiempo, velocidad, esParada, cod_pda, fecha, ...]
    
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

def agrupar_portales_duplicados(tabla):
    """
    Agrupa los portales que hayan sido visitados varias veces y suma sus tiempos.
    
    Parámetro:
        tabla: lista de diccionarios con campos [n, hora, longitud, latitud, distancia, tiempo, velocidad, esParada, cod_pda, fecha, ...]
    
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
    df.loc[df['distancia'] == "-", 'distancia'] = "0 m"
    df['distancia'] = df['distancia'].str.replace(" m", "", regex=False).astype(float)

    # Agrupar puntos
    df_agrupado = df.groupby(['street', 'number']).agg(
        n = ('n', 'first'),
        cod_pda = ('cod_pda', lambda x: list(set(x))),
        latitud = ('latitud', 'mean'),
        longitud = ('longitud', 'mean'),
        distancia = ('distancia', 'mean'),
        tiempo = ('tiempo_seg', 'sum'),
        distance = ('distance', 'mean'),
        nearest_latitud = ('nearest_latitud', 'first'),
        nearest_longitud = ('nearest_longitud', 'first'),
        post_code = ('post_code', lambda x: x.mode().iloc[0]),
        conteo_par_impar = ('conteo_par_impar', 'sum'),
        conteo_zigzag = ('conteo_zigzag', 'sum'),
        tipo = ('tipo', lambda x: x.mode().iloc[0]),
        esParada = ('esParada', 'any'),
        vecesVisitado = ('tiempo_seg', 'count')
    ).reset_index()

    # Add constant columns
    df_agrupado['hora'] = '-'
    df_agrupado['fecha'] = '-'
    df_agrupado['velocidad'] = '-'

    return df_agrupado.to_dict('records')

# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@generateResults_bp.route('/generar_mapa')
def generar_mapa():
    uploaded = session.get('uploaded_files', {})
    api_url = current_app.config.get("API_URL")
    data = {"id": session.get("id")}

    response = requests.post(f"{api_url}/get_fichero_unificado", data=data)
    save_path=""

    if response.status_code == 200:
        upload_dir = current_app.config.get("UPLOAD_FOLDER")
        save_path = os.path.join(upload_dir, session.get("id"), "Fichero_E.csv")
        with open(save_path, "wb") as f:
            f.write(response.content)
        uploaded["E"] = save_path
        current_app.logger.info("Se ha descargado el fichero unificado")
    else:
        current_app.logger.error("Error:", response.text)

    if not os.path.exists(save_path):
        #flash(f"El fichero A o el fichero D (union de los ficheros B y C) no tiene suficientes registros para trabajar.")
        return redirect(url_for('main.root'))

    pdas = get_pdas(save_path)

    return render_template('options.html', pdas=pdas)

@generateResults_bp.route('/generar_mapa/datos_tabla', methods=['GET', 'POST'])
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

@generateResults_bp.route('/generar_mapa/get_mapa', methods=['GET', 'POST'])
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


@generateResults_bp.route('/unifyFiles/')
def unifyFiles():
    cod = request.args.get('codiredMain')
    data = {
        "id": session.get("id"),
        "codired": cod
        }
    api_url = current_app.config.get("API_URL")
    requests.post(f"{api_url}/unifyFiles", data=data)
    flash(f'Unificando ficheros. Proceso experimental (pueden ocurrir fallos)', 'info')
    return redirect(url_for('main.root'))


@generateResults_bp.route('/getStadistics')
def getStadistics():
    # Preparar datos
    data = {
        "id": session.get("id"),
    }

    api_url = current_app.config.get("API_URL")
    
    # Llamar a la API
    api_response = requests.post(f"{api_url}/descargar_estadisticas", data=data)

    # Verificar éxito
    if api_response.status_code != 200:
        return f"Error en la API: {api_response.status_code}", 500

    # Reenviar el contenido del PDF al cliente
    return Response(
        api_response.content,           # contenido binario
        mimetype="application/pdf",     # tipo MIME correcto
        headers={"Content-Disposition": "attachment; filename=estadisticas.pdf"}
    )

@generateResults_bp.route('/agrupar_puntos', methods=['POST'])
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

@generateResults_bp.route('/agrupar_portales', methods=['POST'])
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