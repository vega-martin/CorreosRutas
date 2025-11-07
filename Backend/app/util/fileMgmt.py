from flask import current_app, request, jsonify
import pandas as pd
import os,pytz


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
                "longitud_wgs84_gd": "logitud",
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
                "LONGITUD": "logitud",
                "LATITUD": "latitud"
            }, inplace=True)
    df.to_csv(path, sep=';', index=False)
    current_app.logger.info(f"Archivo {file_type} renombrado con éxito")


def standardize_df_date(df, column):
    df[column] = standardize_date(df[column])
    return df

def standardize_date(series):
    try:
        date = pd.to_datetime(series, utc=True, errors='raise')
        date = date.tz_convert('Europe/Paris')
    except Exception:
        try:
            date = pd.to_datetime(series, format='%y-%m-%d %H:%M:%S', errors='coerce')
            date = date.tz_localize('Europe/Paris')
        except Exception:
            return pd.NaT

    return date.dt.strftime('%Y-%m-%d %H:%M:%S')

def split_date(df, column = 'fecha_hora'):
    df[column] = pd.to_datetime(df[column], errors='coerce')
    df['solo_fecha'] = df[column].dt.date
    df['solo_hora'] = df[column].dt.time
    return df


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