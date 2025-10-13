from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template
from werkzeug.utils import secure_filename
import pandas as pd

options_bp = Blueprint('options', __name__, template_folder='templates')

@options_bp.route('/options')
def options():
    return render_template('options.html')


def normalizar_fechas(lista_fechas):
    fechas_convertidas = []

    for fecha in lista_fechas:
        try:
            # Convertir con pandas, autodetecta formato
            fecha_convertida = pd.to_datetime(fecha, dayfirst=True, errors='coerce')
            if pd.isna(fecha_convertida):
                continue  # si no se pudo convertir, se ignora
            fechas_convertidas.append(fecha_convertida.strftime('%Y-%m-%d'))
        except Exception as e:
            print(f"Error al convertir la fecha {fecha}: {e}")

    # Eliminar duplicados y ordenar
    return sorted(list(set(fechas_convertidas)))



def get_fechas_por_pda(path, pda):
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return []

    posibles_columnas_fecha = ['fec_lectura_medicion', 'Fec Actividad', 'INSTANTE']
    posibles_columnas_pda = ['cod_inv_pda', 'Num Inv', 'COD_SECCION']

    col_fecha = next((col for col in posibles_columnas_fecha if col in df.columns), None)
    col_pda = next((col for col in posibles_columnas_pda if col in df.columns), None)

    if col_fecha and col_pda:
        df_filtrado = df[df[col_pda] == pda]
        fechas = sorted(df_filtrado[col_fecha].dropna().unique())
        return normalizar_fechas(fechas)
    else:
        print("No se encontraron columnas válidas para fechas o PDAs.")
        return []

@options_bp.route('/fechas_por_pda')
def fechas_por_pda():
    pda = request.args.get('pda')
    path = current_app.config['UPLOADED_FILES']['A']

    if not path or not pda:
        return jsonify({'fechas': []})

    fechas = get_fechas_por_pda(path, pda)
    return jsonify({'fechas': fechas})

@options_bp.route('/procesar_mapa', methods=['POST'])
def procesar_mapa():
    pda = request.form.get('pda')
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')

    if not (pda and fecha_inicio and fecha_fin):
        flash("Todos los campos son obligatorios", "error")
        return redirect(url_for('options_bp.generar_mapa'))

    if fecha_inicio >= fecha_fin:
        flash("La fecha de fin debe ser mayor que la de inicio", "error")
        return redirect(url_for('options_bp.generar_mapa'))

    # Procesar datos (mapa, gráfico, etc.)
    return f"Procesando mapa para PDA {pda} entre {fecha_inicio} y {fecha_fin}"
