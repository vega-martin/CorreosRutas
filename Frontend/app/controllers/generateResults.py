from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template, Response
from geopy.distance import geodesic
import pandas as pd
import numpy as np
import folium
import os
import pytz
import json
import requests
from app.controllers.fileUpload import ensure_session_folder

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
                     ['fecha_hora', 'solo_fecha', 'solo_hora' 'longitud', 'latitud', 'esParada']

    Retorna:
        Diccionario con los campos:
        tabla: {[{n, hora, longitud, latitud, distancia, tiempo, velocidad},...]},
        resumen: {puntos_totales, distancia_total, tiempo_total, velocidad_media}
    """

    # Asegurar que el DataFrame esté ordenado por fecha/hora
    df_filtrado = df_filtrado.sort_values('fecha_hora').reset_index(drop=True)

    resultados = []

    for i in range(len(df_filtrado)):
        fila = df_filtrado.iloc[i]

        hora = fila['solo_hora']
        esParada = fila['esParada']

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
            fila_prev = df_filtrado.iloc[i - 1]

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
            "esParada": bool(esParada)
        })

    resumen = calcular_resumen(resultados)

    return {"tabla": resultados, "resumen": resumen}



def get_datos(cod, pda, fecha):
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

    # Filtrar por PDA y fecha (ignorando hora)
    df_filtrado = df[
        (df['cod_pda'] == pda) &
        (df['solo_fecha'] == fecha)
    ].copy()

    if df_filtrado.empty:
        current_app.logger.error(f"No hay datos para PDA={pda} y fecha={fecha}")
        return []

    # Extraer solo las columnas que interesan
    columnas = ['fecha_hora', 'solo_fecha', 'solo_hora', 'longitud', 'latitud', 'esParada']
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




def create_map(cod, pda, fecha):
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


    current_app.logger.info(f"Buscando fecha especifica en el df")

    # Filtrar por PDA y fecha (ignorando hora)
    df_filtrado = df[
        (df['cod_pda'] == pda) &
        (df['solo_fecha'] == fecha)
    ].copy()

    if df_filtrado.empty:
        current_app.logger.error(f"No hay datos para PDA={pda} y fecha={fecha}")
        return []

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


    # Centrar mapa en promedio lat/lon
    lat_promedio = df_filtrado['latitud'].mean()
    lon_promedio = df_filtrado['longitud'].mean()
    current_app.logger.info(f"Mapa centrado en coordenadas {lat_promedio},{lon_promedio}")

    mapa = folium.Map(location=[lat_promedio, lon_promedio], zoom_start=15, control_scale=True)
    folium.TileLayer('CartoDB positron', name='Carto claro').add_to(mapa)

    coordenadas = []

    for _, fila in df_filtrado.iterrows():
        coord = [fila['latitud'], fila['longitud']]
        coordenadas.append(coord)
        if bool(fila['esParada']):
            my_color = 'darkpurple'
            my_opcacity = 0.8
        else:
            my_color = 'blue'
            my_opcacity = 0.6
        my_radius = 4
        folium.CircleMarker(
            location=coord,
            radius=my_radius,
            stroke=False,
            fill=True,
            fill_color=my_color,
            fill_opacity=my_opcacity,
            popup=f"{my_radius}px",
            tooltip=f"Fecha: {fila['fecha_hora']}<br>Coordenada: {fila['latitud']}, {fila['longitud']}"
        ).add_to(mapa)

    for i in range(len(coordenadas)-1):
        folium.PolyLine(
            locations=[coordenadas[i], coordenadas[i+1]],
            color='blue',
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
    return save_map(cod, pda, fecha, mapa)

# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@generateResults_bp.route('/generar_mapa')
def generar_mapa():
    uploaded = session.get('uploaded_files', {})
    api_url = current_app.config.get("API_URL")
    data = {"id": session.get("id")}

    response = requests.post(f"{api_url}/get_fichero_unificado", data=data)

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
        return redirect(url_for('main.root'))

    pdas = get_pdas(save_path)

    return render_template('options.html', pdas=pdas)

@generateResults_bp.route('/generar_mapa/datos_tabla', methods=['GET', 'POST'])
def datos_tabla():
    data = request.get_json()
    cod = data.get('cod')
    pda = data.get('pda')
    ini = data.get('ini')

    # TODO: cambiar para que llame a la API del backend y no lo haga aqui

    # Los argumentos son strings, por ejemplo
    # pda = "PDA01"
    # ini = "2025-10-18"
    resultados = get_datos(cod, pda, ini)

    # Almacenar datos tabla en carpeta del usuario
    if not isinstance(resultados, dict) or 'tabla' not in resultados:
        current_app.logger.error("get_datos no devolvió el diccionario esperado con la clave 'tabla'.")
        return jsonify({"error": "Error al obtener los datos procesados."}), 500
    
    try:
        # Obtener la ruta de la carpeta única del usuario
        user_folder = ensure_session_folder() 
        
        # Definir la ruta del archivo JSON donde guardaremos los datos
        processed_filename = 'table_data.json'
        save_path = os.path.join(user_folder, processed_filename)
        
        # Guardar la lista de diccionarios (el valor de 'tabla') en el disco
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(resultados['tabla'], f, ensure_ascii=False, indent=4)
        
        current_app.logger.info(f"Tabla procesada guardada en disco en: {str(save_path)}")


    except Exception as e:
        current_app.logger.error(f"Error al guardar datos procesados en disco: {e}")
        return jsonify({"error": f"Error interno del servidor al guardar datos: {str(e)}"}), 500

    return jsonify(resultados)

@generateResults_bp.route('/generar_mapa/get_mapa', methods=['GET', 'POST'])
def get_mapa():
    data = request.get_json()
    cod = data.get('cod')
    pda = data.get('pda')
    ini = data.get('ini')

    # TODO: cambiar para que llame a la API del backend y no lo haga aqui

    created_maps = session.get('created_maps', [])
    map = pda + "_" + ini
    if map in created_maps:
        path = "/static/maps/" + cod + "/" + map + ".html"
        current_app.logger.info(f"Mapa ya creado. Url del mapa para la {pda}: {path}")
        return jsonify({'url': path})

    abs_path = create_map(cod, pda, ini)
    current_app.logger.info(f"Ruta absoluta del mapa: {abs_path}")
    base_dir = current_app.config.get("BASE_DIR")
    base_dir = os.path.join(base_dir, "app")
    path = os.path.relpath(abs_path, base_dir)
    created_maps.append(map)
    session["created_maps"] = created_maps
    current_app.logger.info(f"Nuevo mapa creado. Mapas creados: {created_maps}")
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
