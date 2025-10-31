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
                "Seg Transcurrido": "seg_transcurridos"
            }, inplace=True)
    elif (file_type == "C"):
        df.rename(columns={
                "COD_SECCION": "cod_pda",
                "INSTANTE": "fecha_hora",
                "LONGITUD": "logitud",
                "LATITUD": "latitud"
            }, inplace=True)
    df.to_csv(path, index=False)
    current_app.logger.info(f"Archivo {file_type} renombrado con éxito")


def standardize_date(date):
    try:
        date = pd.to_datetime(date, utc=True, errors='raise')
        date = date.tz_convert('Europe/Paris')
    except Exception:
        try:
            date = pd.to_datetime(date, format='%y-%m-%d %H:%M:%S', errors='raise')
            date = date.tz_localize('Europe/Paris')
        except Exception:
            return pd.NaT

    return date

def split_date(date):
    try:
        date = pd.to_datetime(date)
        return pd.Series({
            'solo_fecha': date.date(),
            'solo_hora': date.time()
        })
    except Exception:
        return pd.Series({
            'solo_fecha': pd.NaT,
            'solo_hora': pd.NaT
        })