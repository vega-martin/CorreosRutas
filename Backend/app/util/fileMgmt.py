from flask import current_app, request, jsonify
import pandas as pd
import os, datetime


def valid_extension(name):
    """Comprueba si la extensión es valida"""

    valid_ext = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in name and name.rsplit('.', 1)[1].lower() in valid_ext


def ensure_folder(name):
    """Crea una carpeta única para cada conexión"""


    base_upload = current_app.config.get("UPLOAD_FOLDER")
    id_folder = os.path.join(base_upload, name)
    os.makedirs(id_folder, exist_ok=True)

    if not os.path.exists(id_folder):
        current_app.logger.error(f"Error: no se creó la carpeta {id_folder}")
    else:
        current_app.logger.info(f"Carpeta creada correctamente: {id_folder}")
    
    return id_folder


def rename_file_columns(path, file_type):
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception:
        return

    if (file_type == "A"):
        df.rename(columns={
                "fec_lectura_medicion": "fecha_hora",
                "longitud_wgs84_gd": "longitud",
                "latitud_wgs84_gd": "latitud",
                "cod_inv_pda": "cod_pda"
            }, inplace=True)
    elif (file_type == "B"):
        df.rename(columns={
                "Num Inv": "cod_pda",
                "Fec Actividad": "fecha_hora",
                "Seg Transcurrido": "seg_transcurridos",
                "Cod Unidad": "codired"
            }, inplace=True)
    elif (file_type == "C"):
        df.rename(columns={
                "COD_SECCION": "cod_pda",
                "INSTANTE": "fecha_hora",
                "LONGITUD": "longitud",
                "LATITUD": "latitud"
            }, inplace=True)
    df.to_csv(path, sep=';', index=False)
    current_app.logger.info(f"Archivo {file_type} renombrado con éxito")


def format_date(path, file_type):
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception:
        return
    
    if file_type == "A":
        date_format = '%Y-%m-%d %H:%M:%S.%f %z'
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], format=date_format, utc=True, errors='coerce')
    elif file_type == "B":
        date_format1 = '%d/%m/%Y %H:%M'
        date_format2 = '%d-%m-%y %H:%M:%S'
        date1 = pd.to_datetime(df['fecha_hora'], format=date_format1, errors='coerce')
        date2 = pd.to_datetime(df['fecha_hora'], format=date_format2, errors='coerce')
        df['fecha_hora'] = date1.fillna(date2)

    elif file_type == "C":
        date_format = '%Y-%m-%d %H:%M:%S.%f %z'
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], format=date_format, utc=True, errors='coerce')
    else:
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], errors='coerce')
    
    current_app.logger.info(f"El tipo de dato de la columna es {df['fecha_hora'].dtype}")

    if not pd.api.types.is_datetime64_any_dtype(df['fecha_hora']):
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], errors='coerce')

    if df['fecha_hora'].dt.tz is not None:
        df['fecha_hora'] = df['fecha_hora'].dt.tz_convert('Europe/Paris')
    else:
        df['fecha_hora'] = df['fecha_hora'].dt.tz_localize('Europe/Paris')
    

    df['formatted_fecha_hora'] = df['fecha_hora'].dt.strftime('%Y/%m/%d_%H:%M:%S')
    df['formatted_fecha_hora'] = pd.to_datetime(df['formatted_fecha_hora'], format='%Y/%m/%d_%H:%M:%S', errors='coerce')
    df['solo_fecha'] = df['formatted_fecha_hora'].dt.date
    df['solo_hora'] = df['formatted_fecha_hora'].dt.time

    df.to_csv(path, sep=';', index=False)
    current_app.logger.info(f"Se han convertido las fechas del archivo {file_type} correctamente.")


def extractDataframes(pathA, pathB, pathC, cod):
    current_app.logger.info("+++++++++++++++ ABRIENDO FICHEROS +++++++++++++++++++")
    try:
        df_A = pd.read_csv(pathA, delimiter=';', low_memory=False)
        df_B = pd.read_csv(pathB, delimiter=';', low_memory=False)
        df_C = pd.read_csv(pathC, delimiter=';', low_memory=False)
    except Exception:
        df_A = pd.DataFrame()
        df_B = pd.DataFrame()
        df_C = pd.DataFrame()
        current_app.logger.error(f"Error al leer archivo CSV")
        return df_A, df_B, df_C, jsonify({'error' : 'Not able to ope files'})
    
    current_app.logger.info("+++++++++++++++ FILTRANDO CODIGO DE UNIDAD +++++++++++++++++++")
    df_A = df_A[df_A['codired'] == int(cod)]
    df_B = df_B[df_B['codired'] == int(cod)]
    df_C = df_C[df_C['codired'] == int(cod)]
    df_A_length = len(df_A)
    df_B_length = len(df_B)
    df_C_length = len(df_C)
    total_length = df_A_length + df_B_length + df_C_length
    read_info = {
        "Registros_totales": total_length,
        "Registros_A": df_A_length,
        "Registros_B": df_B_length,
        "Registros_C": df_C_length
    }

    return df_A, df_B, df_C, jsonify(read_info)