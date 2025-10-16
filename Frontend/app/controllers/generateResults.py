from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template
from werkzeug.utils import secure_filename
from geopy.distance import geodesic
from datetime import timedelta
import pandas as pd
import os

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
                d = float(r["distancia"].replace(" km", ""))
                t_min = float(r["tiempo"].replace(" min", ""))
                distancias.append(d)
                tiempos.append(t_min)
        except Exception:
            continue

    puntos_totales = len(resultados)
    distancia_total = sum(distancias)
    tiempo_total_min = sum(tiempos)
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

            # Calcular tiempo en horas
            delta_t = (fila['fec_lectura_medicion'] - fila_prev['fec_lectura_medicion']).total_seconds()
            tiempo_horas = delta_t / 3600.0

            # Calcular velocidad (km/h)
            if tiempo_horas > 0:
                velocidad_kmh = distancia_km / tiempo_horas
            else:
                velocidad_kmh = 0.0

            # Formatear resultados legibles
            distancia = f"{distancia_km:.3f} km"
            tiempo = f"{int(delta_t // 60)} min"
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



def get_datos(pda, fecha):
    # Obtener fichero
    uploaded = session.get('uploaded_files', {})
    path = uploaded.get('A')
    print(path)
    # Abrir fichero
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return []
    # Convertir columna de fecha-hora a tipo datetime (UTC con zona)
    if 'fec_lectura_medicion' not in df.columns:
        print("No se encontró la columna 'fec_lectura_medicion' en el CSV.")
        return []

    try:
        df['fec_lectura_medicion'] = pd.to_datetime(df['fec_lectura_medicion'], utc=False, errors='coerce')
    except Exception as e:
        print(f"Error al convertir las fechas: {e}")
        return []

    # Filtrar por PDA y fecha (ignorando hora)
    df_filtrado = df[
        (df['cod_inv_pda'] == pda) &
        (df['fec_lectura_medicion'].dt.strftime('%Y-%m-%d') == fecha)
    ].copy()

    if df_filtrado.empty:
        print(f"No hay datos para PDA={pda} y fecha={fecha}")
        return []

    # Extraer solo las columnas que interesan
    columnas = ['fec_lectura_medicion', 'longitud_wgs84_gd', 'latitud_wgs84_gd']
    df_filtrado = df_filtrado[columnas].dropna()
    resultados = calcular_metricas(df_filtrado)

    return resultados


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
    fechas = get_fechas(file_A_path)

    return render_template('options.html', pdas=pdas, fechas=fechas)



@generateResults_bp.route('/generar_mapa/datos_tabla', methods=['GET', 'POST'])
def datos_tabla():
    data = request.get_json()
    pda = data.get('pda')
    ini = data.get('ini')

    # TODO: cambiar para que llame a la API del backend y no lo haga aqui

    # Los argumentos son strings, por ejemplo
    # pda = "PDA01"
    # ini = "2025-10-18"
    resultados = get_datos(pda, ini)

    return jsonify(resultados)



@generateResults_bp.route('/detectar_paradas')
def detectar_paradas():
    uploaded = session.get('uploaded_files', {})
    file_B = uploaded.get('B')
    file_C = uploaded.get('C')

    if not file_B or not os.path.exists(file_B) or not file_C or not os.path.exists(file_C):
        flash("Error: Necesitas subir los ficheros B y C para detectar paradas.", 'error')
        return redirect(url_for('main.root'))
    
    # Lógica de detección de paradas
    return "Paradas detectadas correctamente."


@generateResults_bp.route('/generar_paradas')
def generar_paradas():
    uploaded = session.get('uploaded_files', {})
    file_A = uploaded.get('A')
    file_B = uploaded.get('B')
    file_C = uploaded.get('C')

    if not all([file_A and os.path.exists(file_A),
                file_B and os.path.exists(file_B),
                file_C and os.path.exists(file_C)]):
        flash("Error: Necesitas subir los ficheros A, B y C para generar paradas.", 'error')
        return redirect(url_for('main.root'))
    
    # Lógica para generar paradas
    return "Paradas generadas correctamente."


@generateResults_bp.route('/grafica_vel_tiempo')
def grafica_vel_tiempo():
    uploaded = session.get('uploaded_files', {})
    file_A = uploaded.get('A')

    if not file_A or not os.path.exists(file_A):
        flash("Error: Necesitas subir el fichero A para generar la gráfica velocidad/tiempo.", 'error')
        return redirect(url_for('main.root'))
    
    # Lógica para generar la gráfica
    return "Gráfica velocidad/tiempo generada."