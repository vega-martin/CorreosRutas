from flask import current_app, request, jsonify
import pandas as pd
import numpy as np
import os, datetime, json


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




def rename_file_columns(df, file_type):
    if (file_type == "A"):
        df.rename(columns={
                "cod_inv_pda": "cod_pda",
                "fec_lectura_medicion": "fecha_hora",
                "longitud_wgs84_gd": "longitud",
                "latitud_wgs84_gd": "latitud",
                "codired": "cod_unidad"
            }, inplace=True)
    elif (file_type == "B"):
        df.rename(columns={
                "Num Inv": "cod_pda",
                "Cod Unidad": "cod_unidad",
                "Cod Actividad": "cod_actividad",
                "Seccion": "seccion",
                "Turno": "turno",
                "Fec Actividad": "fecha_hora",
                "Seg Transcurrido": "seg_transcurridos",
            }, inplace=True)
    elif (file_type == "C"):
        df.rename(columns={
                "COD_NODOEMI": "cod_unidad",
                "COD_SECCION": "seccion",
                "IND_TURNO": "turno",
                "INSTANTE_EVENTO": "fecha_hora",
                "NUM_GEO_LONGITUD": "longitud",
                "NUM_GEO_LATITUD": "latitud"
            }, inplace=True)
    
    current_app.logger.info(f"Archivo {file_type} renombrado con éxito")
    return df




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




def get_statistics_A(path):
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception:
        return jsonify({'info': 'No se pudo leer el fichero.'})

    df_length = len(df)
    df['esParada'] = False
    df.to_csv(path, sep=';', index=False)
    info = f'Nº elementos iniciales: {df_length}.\n'

    df = df.drop_duplicates(ignore_index=True)
    duplicates_count = df_length - len(df)
    info += f'Nº elementos duplicados: {duplicates_count}.\n'
    info += f'Nº elementos finales: {len(df)}.\n'

    final_response = {
        'info': info
    }
    return jsonify(final_response)




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




def extractBCDataframes(pathB, pathC):
    current_app.logger.info("+++++++++++++++ ABRIENDO FICHEROS +++++++++++++++++++")
    try:
        df_B = pd.read_csv(pathB, delimiter=';', low_memory=False)
        df_C = pd.read_csv(pathC, delimiter=';', low_memory=False)
    except Exception:
        df_B = pd.DataFrame()
        df_C = pd.DataFrame()
        current_app.logger.error(f"Error al leer archivo CSV")
        return df_B, df_C, jsonify({'error' : 'Not able to ope files'})
    
    current_app.logger.info("+++++++++++++++ FILTRANDO CODIGO DE UNIDAD +++++++++++++++++++")
    df_B_length = len(df_B)
    df_C_length = len(df_C)
    total_length =  + df_B_length + df_C_length
    read_info = {
        "Registros_totales": total_length,
        "Registros_B": df_B_length,
        "Registros_C": df_C_length
    }

    return df_B, df_C, jsonify(read_info)




def delete_columns(df, file_type):
    if (file_type == "A"):
        used_columns = ["cod_pda", "fecha_hora", "longitud", "latitud", "cod_unidad"]
    elif (file_type == "B"):
        used_columns = ["cod_pda", "fecha_hora", "cod_unidad", "cod_actividad", "seccion", "turno", "seg_transcurridos"]
    elif (file_type == "C"):
        used_columns = ["cod_unidad", "seccion", "turno", "fecha_hora", "longitud", "latitud"]
    else:
        used_columns = []

    df = df[used_columns]

    return df



def format_date_new(df, file_type):
    # Convert to datetime
    if file_type == "A":
        date_format = '%Y-%m-%d %H:%M:%S.%f %z'
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], format=date_format, utc=True, errors='coerce')
    elif file_type == "B" or file_type == "C":
        date_format = '%d/%m/%Y %H:%M'
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], format=date_format, errors='coerce')
    else:
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], errors='coerce')

    # Localize date
    if df['fecha_hora'].dt.tz is not None:
        df['fecha_hora'] = df['fecha_hora'].dt.tz_convert('Europe/Paris')
    else:
        df['fecha_hora'] = df['fecha_hora'].dt.tz_localize('Europe/Paris')
    
    # Unify date format
    df['fecha_hora_formateada'] = pd.to_datetime(df['fecha_hora'], format='%Y/%m/%d_%H:%M:%S', errors='coerce')

    return df




def separate_date(df):
    df['solo_fecha'] = df['fecha_hora_formateada'].dt.date
    df['solo_hora'] = df['fecha_hora_formateada'].dt.time
    return df




def preprocess_data(save_path, file_type):
    # Read file
    try:
        df = pd.read_csv(save_path, delimiter=';', low_memory=False)
    except Exception:
        return
    
    # Rename columns
    df_rename = rename_file_columns(df, file_type)
    initial_length = len(df_rename)
    info = f"Número elementos iniciales: {initial_length}.\n"

    # Delete unused columns
    df_limited = delete_columns(df_rename, file_type)

    # Delete duplicates
    df_wout_dup = df_limited.drop_duplicates()
    wout_dup_length = len(df_wout_dup)
    duplicates = initial_length - wout_dup_length
    info += f"Número elementos duplicados: {duplicates}.\n"

    # Delete invalid values
    invalid_values = [
        "#N/A", "#N/D", "#N/A N/A", "#NA", "-N/A",
        "#NULL!", "#DIV/0!", "#NUM!", "#NAME?", "#VALUE!",
        "NULL", "null", "Nil", "nil", "",
        "nan", "NaN", "NAN", "<NA>",
        "#n/a", "N/A", "n/a", "NA", "na", "NULL", "-",
        "?", "*", " ", ".."
    ]
    df_clean = df_wout_dup.replace(invalid_values, np.nan)
    df_clean = df_clean.dropna()
    if "longitud" in df.columns:
        df_clean["longitud"] = pd.to_numeric(df_clean["longitud"].astype(str).str.replace(',', '.'), errors='coerce')
        df_clean["latitud"] = pd.to_numeric(df_clean["latitud"].astype(str).str.replace(',', '.'), errors='coerce')

        df_clean = df_clean[df_clean["longitud"] != 0.0]
        df_clean = df_clean[df_clean["latitud"] != 0.0]
    invalid = wout_dup_length - len(df_clean)
    info += f"Número elementos inválidos: {invalid}.\n"

    # Add "es_parada" column
    df_stop = df_clean.copy()
    df_stop["es_parada"] = (file_type != "A")
    
    # Format date
    df_formatted = format_date_new(df_stop, file_type)

    # Separate date and time
    df_final = separate_date(df_formatted)
    final_length = len(df_final)
    info += f"Número elementos finales: {final_length}.\n"

    # Save as pickle and csv
    df_final.to_csv(save_path, sep=';', index=False)

    pkl_path = save_path.replace(".csv", ".pkl")
    df_final.to_pickle(pkl_path)

    # Save statistics in JSON
    info_dic = {
        "initial" : initial_length,
        "duplicates" : duplicates,
        "invalid" : invalid,
        "final" : final_length
    }
    preprocess_info = {
        f"{file_type}_preprocess" : info_dic
    }
    json_path = save_path.replace(os.path.basename(save_path), "statistics.json")
    current_app.logger.info(f"la ruta base es {json_path}")
    # Load existing data if the file exists
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = {}
    else:
        existing_data = {}
    # Update (add or overwrite only this key)
    existing_data.update(preprocess_info)
    # Write back
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)

    # Return statistics
    final_response = {
        "info": info
    }

    return jsonify(final_response)




def getDataframes(path_b, path_c):
    df_B = pd.read_pickle(path_b)
    df_C = pd.read_pickle(path_c)
    return df_B, df_C