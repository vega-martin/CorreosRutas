from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import re
import json
import os

options_bp = Blueprint('options', __name__, template_folder='templates')

@options_bp.route('/options')
def options():
    return render_template('options.html')

def normalizar_fechas(lista_fechas):
    fechas_convertidas = []

    for fecha in lista_fechas:
        try:
            # Convertir con pandas, autodetecta formato
            fecha_convertida = pd.to_datetime(fecha, errors='coerce')
            if pd.isna(fecha_convertida):
                continue  # si no se pudo convertir, se ignora
            fechas_convertidas.append(fecha_convertida.strftime('%Y-%m-%d'))
        except Exception as e:
            print(f"Error al convertir la fecha {fecha}: {e}")

    # Eliminar duplicados y ordenar
    return sorted(list(set(fechas_convertidas)))

def get_fechas_por_pda(df, pda):
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

def get_fechas_por_todas_las_pdas(df):
    posibles_columnas_fecha = ['fec_lectura_medicion', 'Fec Actividad', 'INSTANTE']
    col_fecha = next((col for col in posibles_columnas_fecha if col in df.columns), None)

    if col_fecha:
        fechas = sorted(df[col_fecha].dropna().unique())
        return normalizar_fechas(fechas)
    else:
        print("No se encontró una columna válida de fechas.")
        return []
    
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
    if val is None or ref is None:
        return False
        
    if comp == "menor": return val < ref
    if comp == "menor-igual": return val <= ref
    if comp == "igual": return val == ref
    if comp == "no-igual": return val != ref
    if comp == "mayor": return val > ref
    if comp == "mayor-igual": return val >= ref
    return False

# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@options_bp.route('/pda_por_codired')
def pda_por_codired():
    cod = request.args.get('cod')
    uploaded = session.get('uploaded_files', {})
    path = uploaded.get('A')
    current_app.logger.info("Abriendo fichero A")
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return []

    if not path or not cod:
        return jsonify({'pdas': []})
    
    current_app.logger.info(f"Buscando regsitros perteneciente a la oficina {cod}")
    df = df[df['codired'] == int(cod)]
    current_app.logger.info(f"Se han encotrado {len(df)} registros de la oficina {cod}")
    pdas = df['cod_inv_pda'].dropna().unique()
    pdas = np.sort(pdas).tolist()
    current_app.logger.info(f"Se han encontrado {len(pdas)} pdas en la oficina {cod}")
    return jsonify({'pdas': pdas})


@options_bp.route('/fechas_por_pda')
def fechas_por_pda():
    pda = request.args.get('pda')
    uploaded = session.get('uploaded_files', {})
    path = uploaded.get('A')
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return []

    if not path or not pda:
        return jsonify({'fechas': []})

    if pda == "TODAS":
        fechas = get_fechas_por_todas_las_pdas(df)
    else:
        fechas = get_fechas_por_pda(df, pda)

    return jsonify({'fechas': fechas})


@options_bp.route('/procesar_mapa', methods=['POST'])
def procesar_mapa():
    pda = request.form.get('pda')
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')

    if not (pda and fecha_inicio and fecha_fin):
        flash("Todos los campos son obligatorios", "error")
        return redirect(url_for('generateResults.generar_mapa'))

    if fecha_inicio >= fecha_fin:
        flash("La fecha de fin debe ser mayor que la de inicio", "error")
        return redirect(url_for('generateResults.generar_mapa'))

    return f"Procesando mapa para PDA: {pda} entre {fecha_inicio} y {fecha_fin}"

# ----- FILTRADO DE REGISTROS EN LA TABLA -----
@options_bp.route('/filtrar_registros', methods=['POST'])
def filtrar_registros():
    data = request.get_json()

    # Obtener la ruta del archivo de la sesión
    file_path = session.get('table_path')
    datos_completos = []

    # Comprobar si la ruta existe y si el archivo realmente está allí
    if not file_path or not os.path.exists(file_path):
        current_app.logger.error(f"Ruta de archivo no encontrada en sesión o archivo no existe: {file_path}")
        # Retorna una lista vacía si no hay datos disponibles
        return jsonify({"tabla": [], "resumen": {}, "warnings": ["No hay datos cargados para filtrar."]})

    # Cargar los datos desde el archivo JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            datos_completos = json.load(f)
        
    except json.JSONDecodeError:
        current_app.logger.error(f"Error al decodificar el archivo JSON: {file_path}")
        return jsonify({"tabla": [], "resumen": {}, "warnings": ["Error de formato en el archivo de datos."]})
    except Exception as e:
        current_app.logger.error(f"Error desconocido al leer el archivo de datos: {e}")
        return jsonify({"tabla": [], "resumen": {}, "warnings": ["Error al acceder a los datos de la sesión."]})
    
    filtros_recibidos = [
        {
            "campo": "distancia", 
            "comp": data.get('signoDistancia'), 
            "valor_str": data.get('distancia')
        },
        {
            "campo": "tiempo", 
            "comp": data.get('signoTiempo'), 
            "valor_str": data.get('tiempo')
        },
        {
            "campo": "velocidad", 
            "comp": data.get('signoVelocidad'), 
            "valor_str": data.get('velocidad')
        }
    ]
    
    # Preparar los datos para el filtrado
    resultados_filtrados = datos_completos.copy()
    
    # Aplicar los filtros iterativamente
    for filtro in filtros_recibidos:
        
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

            resultados_filtrados = [
                fila for fila in resultados_filtrados
                if cumple_condicion(
                    extraer_num(fila.get(filtro['campo'])),
                    filtro
                )
            ]

    # Recalcular resumen
    # TODO: Recalcular resumen en caso de que sea necesario
    # resumen_filtrado = calcular_resumen(resultados_filtrados) 

    # Devolver los resultados
    return jsonify({
        "tabla": resultados_filtrados,
        # "resumen": {"puntos_totales": len(resultados_filtrados), "distancia_total": "...", "tiempo_total": "...", "velocidad_media": "..."}, # Devuelve algo útil o vacío
        "warnings": []
    })
    