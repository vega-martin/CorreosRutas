from flask import current_app, session
from .util import parse_coord
import folium, statistics, os, json
import pandas as pd
import numpy as np

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
    
    df = df[df['cod_unidad'] == int(cod)]
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

    latitud_centrada = float(pd.to_numeric(parse_coord(df['latitud'].iloc[0]), errors="coerce"))
    longitud_centrada = float(pd.to_numeric(parse_coord(df['longitud'].iloc[0]), errors="coerce"))


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
                if bool(fila['es_parada']):
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


def create_cluster_map(cod, diameter = 1000.0, num_pts = 10):
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    processed_filename = 'table_data_filtered.json'
    cluster_table_path = os.path.join(upload_folder, session.get("id"), processed_filename)
    # Leer el JSON de clusters
    with open(cluster_table_path, "r", encoding="utf-8") as f:
        clusters = json.load(f)

    if not clusters:
        print("No hay clusters en el JSON.")
        return

    # Coordenada media de los puntos centrales para centrar el mapa
    lats = [c["latitud"] for c in clusters if c.get("latitud") is not None]
    lons = [c["longitud"] for c in clusters if c.get("longitud") is not None]

    if not lats or not lons:
        print("No hay coordenadas válidas para centrar el mapa.")
        return

    center_lat = statistics.mean(lats)
    center_lon = statistics.mean(lons)

    # Mapa base OpenStreetMap
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
        tiles="OpenStreetMap"  # capa base OSM
    )
    folium.TileLayer('CartoDB positron', name='Carto claro').add_to(m)

    # Asignar colores por calle para diferenciar visualmente
    color_por_calle = {}
    colors = [
        "red", "blue", "green", "purple", "orange",
        "darkred", "lightred", "beige", "darkblue",
        "darkgreen", "cadetblue", "darkpurple",
        "white", "pink", "lightblue", "lightgreen",
        "gray", "black", "lightgray"
    ]
    color_index = 0

    def color_para_calle(calle):
        nonlocal color_index
        if calle not in color_por_calle:
            color_por_calle[calle] = colors[color_index % len(colors)]
            color_index += 1
        return color_por_calle[calle]

    # Crear un marcador (seleccionable) por cluster
    for c in clusters:
        lat = c.get("latitud")
        lon = c.get("longitud")
        if lat is None or lon is None:
            continue

        calle = c.get("street", "SIN_CALLE")
        numero = c.get("number")
        tiempo_total = c.get("tiempo", 0)
        puntos_cluster = c.get("puntos_cluster", [])

        num_unificados = len(puntos_cluster)

        # Tarjeta (popup) con la info que necesitas
        popup_html = f"""
        <b>Calle:</b> {calle}<br>
        <b>Número (central):</b> {numero}<br>
        <b>Nº puntos unificados:</b> {num_unificados}<br>
        <b>Puntos unificados (n):</b> {puntos_cluster}<br>
        <b>Tiempo total cluster:</b> {tiempo_total}
        """

        color = color_para_calle(calle)

        # Marcador tipo círculo, clicable
        folium.CircleMarker(
            location=[lat, lon],
            radius=7,
            color="black",            # borde negro
            weight=2,
            fill=True,
            fill_color=color,        # color según la calle
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(m)

    # Guardar el mapa
    current_app.logger.info(f"Guardando mapa")
    base_dir = current_app.config.get("BASE_DIR")
    map_folder = os.path.join(base_dir, "app", "static", "maps", cod)
    os.makedirs(map_folder, exist_ok=True)
    if not os.path.exists(map_folder):
        current_app.logger.error(f"Error: no se creó la carpeta {map_folder}")
    else:
        current_app.logger.info(f"Carpeta creada correctamente: {map_folder}")

    map_name = "cluster_d" + str(int(diameter)) + "_p" + str(num_pts) + ".html"
    save_path = os.path.join(map_folder, map_name)
    m.save(save_path)

    if not os.path.exists(save_path):
        current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
    else:
        current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
    
    current_app.logger.info(f"Mapa guardado en {save_path}")

    current_app.logger.info(f"Ruta absoluta del mapa: {save_path}")
    base_dir = os.path.join(base_dir, "app")
    path = os.path.relpath(save_path, base_dir)
    current_app.logger.info(f"Ruta relativa del mapa: {path}")

    return path
