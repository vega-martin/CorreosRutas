from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template
from geopy.distance import geodesic
import pandas as pd
import folium
import os
import pytz
import requests

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

    # Lista de nombres de columnas posibles que pueden contener las PDAs
    posibles_columnas = ['cod_inv_pda', 'Num Inv', 'COD_SECCION']

    for col in posibles_columnas:
        if col in df.columns:
            pdas = sorted(df[col].dropna().unique())
            current_app.logger.info(f'Se encontraron {len(pdas)} PDAs.')
            return pdas  # Devuelve al encontrar la primera columna válida

    # Si no se encuentra ninguna columna válida
    print("No se encontró ninguna columna válida para extraer PDAs.")
    current_app.logger.info('No se encontró ninguna columna válida para extraer PDAs.')
    return []


def get_fechas(path):
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return []

    # Lista de nombres de columnas posibles que pueden contener las fechas
    posibles_columnas = ['fec_lectura_medicion', 'Fec Actividad', 'INSTANTE']

    for col in posibles_columnas:
        if col in df.columns:
            fechas = sorted(df[col].dropna().unique())
            current_app.logger.info(f'Se encontraron {len(fechas)} fechas.')
            return fechas  # Devuelve al encontrar la primera columna válida

    # Si no se encuentra ninguna columna válida
    print("No se encontró ninguna columna válida para extraer fechas.")
    current_app.logger.info('No se encontró ninguna columna válida para extraer fechas.')
    return []

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
                     ['fec_lectura_medicion', 'longitud_wgs84_gd', 'latitud_wgs84_gd']

    Retorna:
        Lista de diccionarios con los campos:
        n, hora, longitud, latitud, distancia, tiempo, velocidad
    """

    # Asegurar que el DataFrame esté ordenado por fecha/hora
    df_filtrado = df_filtrado.sort_values('fec_lectura_medicion').reset_index(drop=True)

    resultados = []

    for i in range(len(df_filtrado)):
        fila = df_filtrado.iloc[i]

        hora = fila['fec_lectura_medicion'].strftime('%H:%M:%S')
        lon = float(str(fila['longitud_wgs84_gd']).replace(',', '.'))
        lat = float(str(fila['latitud_wgs84_gd']).replace(',', '.'))

        # Primer punto
        if i == 0:
            distancia = "-"
            tiempo = "-"
            velocidad = "-"
        else:
            fila_prev = df_filtrado.iloc[i - 1]

            # Calcular distancia (en km)
            punto1 = (float(str(fila_prev['latitud_wgs84_gd']).replace(',', '.')), float(str(fila_prev['longitud_wgs84_gd']).replace(',', '.')))
            punto2 = (lat, lon)
            distancia_km = geodesic(punto1, punto2).kilometers
            distancia_m = geodesic(punto1, punto2).meters

            # Calcular tiempo en horas
            delta_t = (fila['fec_lectura_medicion'] - fila_prev['fec_lectura_medicion']).total_seconds()
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
            "velocidad": velocidad
        })

    resumen = calcular_resumen(resultados)

    return {"tabla": resultados, "resumen": resumen}



def get_datos(cod, pda, fecha):
    # Obtener fichero
    uploaded = session.get('uploaded_files', {})
    path = uploaded.get('A')
    
    # Abrir fichero
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        current_app.logger.error(f"Error al leer el archivo CSV: {e}")
        return []
    
    df = df[df['codired'] == cod]

    if 'fec_lectura_medicion' not in df.columns:
        current_app.logger.error("No se encontró la columna 'fec_lectura_medicion' en el CSV.")
        return []
    # Convertir columna de fecha-hora a tipo datetime (UTC con zona)
    try:
        df['fec_lectura_medicion'] = pd.to_datetime(df['fec_lectura_medicion'], utc=True, errors='coerce')
        df['fec_lectura_medicion'] = df['fec_lectura_medicion'].dt.tz_convert(pytz.timezone('Europe/Paris'))
    except Exception as e:
        current_app.logger.error(f"Error al convertir las fechas: {e}")
        return []

    # Filtrar por PDA y fecha (ignorando hora)
    df_filtrado = df[
        (df['cod_inv_pda'] == pda) &
        (df['fec_lectura_medicion'].dt.strftime('%Y-%m-%d') == fecha)
    ].copy()

    if df_filtrado.empty:
        current_app.logger.error(f"No hay datos para PDA={pda} y fecha={fecha}")
        return []

    # Extraer solo las columnas que interesan
    columnas = ['fec_lectura_medicion', 'longitud_wgs84_gd', 'latitud_wgs84_gd']
    df_filtrado = df_filtrado[columnas].dropna()
    resultados = calcular_metricas(df_filtrado)

    return resultados


# ------------------------------------------------------------
# TODO: Esto se elimina, deberia ser una llamada a la API
# CREACION DE MAPA
# ------------------------------------------------------------


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
    path = uploaded.get('A')
    
    # Abrir fichero
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        current_app.logger.error(f"Error al leer el archivo CSV: {e}")
        return []
    
    df = df[df['codired'] == cod]
    current_app.logger.info(f"Encontrados {len(df)} en la oficina {cod}")


    current_app.logger.info(f"Buscando fecha especifica en el df")
    if 'fec_lectura_medicion' not in df.columns:
        current_app.logger.error("No se encontró la columna 'fec_lectura_medicion' en el CSV.")
        return []
    # Convertir columna de fecha-hora a tipo datetime (UTC con zona)
    try:
        df['fec_lectura_medicion'] = pd.to_datetime(df['fec_lectura_medicion'], utc=True, errors='coerce')
        df['fec_lectura_medicion'] = df['fec_lectura_medicion'].dt.tz_convert(pytz.timezone('Europe/Paris'))
    except Exception as e:
        current_app.logger.error(f"Error al convertir las fechas: {e}")
        return []

    # Filtrar por PDA y fecha (ignorando hora)
    df_filtrado = df[
        (df['cod_inv_pda'] == pda) &
        (df['fec_lectura_medicion'].dt.strftime('%Y-%m-%d') == fecha)
    ].copy()

    if df_filtrado.empty:
        current_app.logger.error(f"No hay datos para PDA={pda} y fecha={fecha}")
        return []

    df_filtrado = df_filtrado.sort_values('fec_lectura_medicion')

    current_app.logger.info(f"Creando mapa")
    # Pasar de string a num
    df_filtrado['latitud_wgs84_gd'] = df_filtrado['latitud_wgs84_gd'].astype(str).str.replace(',', '.')
    df_filtrado['longitud_wgs84_gd'] = df_filtrado['longitud_wgs84_gd'].astype(str).str.replace(',', '.')

    df_filtrado['latitud_wgs84_gd'] = pd.to_numeric(df_filtrado['latitud_wgs84_gd'], errors='coerce')
    df_filtrado['longitud_wgs84_gd'] = pd.to_numeric(df_filtrado['longitud_wgs84_gd'], errors='coerce')

    # Centrar mapa en promedio lat/lon
    lat_promedio = df_filtrado['latitud_wgs84_gd'].mean()
    lon_promedio = df_filtrado['longitud_wgs84_gd'].mean()

    mapa = folium.Map(location=[lat_promedio, lon_promedio], zoom_start=15, control_scale=True)
    folium.TileLayer('CartoDB positron', name='Carto claro').add_to(mapa)

    coordenadas = []

    for _, fila in df_filtrado.iterrows():
        coord = [fila['latitud_wgs84_gd'], fila['longitud_wgs84_gd']]
        coordenadas.append(coord)
        folium.CircleMarker(
            location=coord,
            radius=4,
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.7,
            popup=f"Fecha: {fila['fec_lectura_medicion']}<br>Coordenada: {fila['latitud_wgs84_gd']}, {fila['longitud_wgs84_gd']}"
        ).add_to(mapa)

    for i in range(len(coordenadas)-1):
        folium.PolyLine(
            locations=[coordenadas[i], coordenadas[i+1]],
            color='blue',
            weight=3,
            opacity=0.7
        ).add_to(mapa)
    
    inicio = df_filtrado.iloc[0]
    folium.Marker(
        location=[inicio['latitud_wgs84_gd'], fila['longitud_wgs84_gd']],
        icon=folium.Icon(color='green', icon='play', prefix='fa'),
        popup="INICIO"
    ).add_to(mapa)

    fin = df_filtrado.iloc[-1]
    folium.Marker(
        location=[fin['latitud_wgs84_gd'], fin['longitud_wgs84_gd']],
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

    # Comprobar que el fichero A existe en la sesión
    file_A_path = uploaded.get('A')
    if not file_A_path or not os.path.exists(file_A_path):
        flash("Error: Necesitas subir el fichero A para generar el mapa.", 'error')
        return redirect(url_for('main.root'))

    pdas = get_pdas(file_A_path)

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


@generateResults_bp.route('/unifyFiles')
def unifyFiles():
    data = {"id": session.get("id")}
    api_url = current_app.config.get("API_URL")
    requests.post(f"{api_url}/unifyFiles", data=data)
    flash(f'Unificando ficheros. Proceso experimental (pueden ocurrir fallos)', 'info')
    return redirect(url_for('main.root'))