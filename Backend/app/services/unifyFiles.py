from flask import jsonify, current_app
from collections import defaultdict
import pandas as pd
import numpy as np
import os, json

def count_and_drop_duplicates(df):
    df_length = len(df)
    df = df.drop_duplicates(ignore_index=True)
    duplicates_count = df_length - len(df)
    return df, duplicates_count


def create_dict(df):
    df_dict = {}
    for pda, group_pda in df.groupby('cod_pda'):
        df_dict[pda] = {}
        for fecha, group_fecha in group_pda.groupby('solo_fecha'):
            #current_app.logger.info(f"Encontrado {pda}: {fecha}")
            df_dict[pda][fecha] = group_fecha
    return df_dict


def sinconize_dicts(df_A_dict, df_B_dict, df_C_dict):
    current_app.logger.info("+++++++++++++++ SINCORNIZANDO FICHEROS FUNCION +++++++++++++++++++")
    # Sincronizar pdas
    shared_pdas = df_A_dict.keys() & df_B_dict.keys() & df_C_dict.keys()
    current_app.logger.info(f"Nº pdas comunes: {len(shared_pdas)}")

    # Eliminar las pdas no comunes
    for dict, name in zip([df_A_dict, df_B_dict, df_C_dict], ['Fichero_A', 'Fichero_B', 'Fichero_C']):
        for pda in list(dict.keys()):
            #current_app.logger.info(f"Analizando {pda} de {name} con {len(dict[pda].keys())} fechas")
            if pda not in shared_pdas:
                #current_app.logger.info(f"Eliminando {pda} de {name} ya que no se encuentra en otros ficheros")
                del dict[pda]
    
    # Eliminar las fechas no comunes
    for pda in shared_pdas:
        shared_dates = df_A_dict[pda].keys() & df_B_dict[pda].keys() & df_C_dict[pda].keys()
        for dict, name in zip([df_A_dict, df_B_dict, df_C_dict], ['Fichero_A', 'Fichero_B', 'Fichero_C']):
            for date in list(dict[pda].keys()):
                if date not in shared_dates:
                    #current_app.logger.info(f"Eliminando {date} de {pda} de {name} ya que no se encuentra en otros ficheros")
                    del dict[pda][date]
    
    return df_A_dict, df_B_dict, df_C_dict


def remove_empty_entries(d):
    return {key: value for key, value in d.items() if len(value) > 0}



def unifyAllFiles(df_A, df_B, df_C, save_path):
    """
        Calls necesary functions for creating new files from unifying the files
        Args:
            df_A : dataframe with data from file A
            df_B : dataframe with data from file B
            df_C : dataframe with data from file C
        Returns:
            JSON with all the erased data and its related information
    """
    
    # 1 - Eliminar duplicados
    current_app.logger.info("+++++++++++++++ ELIMINANDO DUPLICADOS +++++++++++++++++++")
    current_app.logger.info("--------------- Procesando Fichero A")
    df_A, duplicates_A = count_and_drop_duplicates(df_A)
    current_app.logger.info(f"Duplicados: {duplicates_A}")

    current_app.logger.info("--------------- Procesando Fichero B")
    df_B, duplicates_B = count_and_drop_duplicates(df_B)
    current_app.logger.info(f"Duplicados: {duplicates_B}")

    current_app.logger.info("--------------- Procesando Fichero C")
    df_C, duplicates_C = count_and_drop_duplicates(df_C)
    current_app.logger.info(f"Duplicados: {duplicates_C}")

    total_duplicates = duplicates_A + duplicates_B + duplicates_C
    current_app.logger.info(f"Duplicados totales: {total_duplicates}")
    duplicates_info = {
        "Duplicados_totales": total_duplicates,
        "Duplicados_A": duplicates_A,
        "Duplicados_B": duplicates_B,
        "Duplicados_C": duplicates_C
    }


    # 2 - Ordenar y dividir por PDA -> Fichero_A_PDA01, Fichero_B_PDA01, Fichero_C_PDA01
    # 3 - Ordenar y dividir por fecha -> Fichero_A_PDA01_2025-05-29 se junta con Fichero_B_PDA01_2025-05-29 y Fichero_C_PDA01_2025-05-29
    current_app.logger.info("+++++++++++++++ SEPARANDO FICHEROS POR PDAS Y POR FECHAS +++++++++++++++++++")
    current_app.logger.info("--------------- Procesando Fichero A")
    df_A_dict = create_dict(df_A)
    df_A_dict_length = len(df_A_dict)

    current_app.logger.info("--------------- Procesando Fichero B")
    df_B_dict = create_dict(df_B)
    df_B_dict_length = len(df_B_dict)

    current_app.logger.info("--------------- Procesando Fichero C")
    df_C_dict = create_dict(df_C)
    df_C_dict_length = len(df_C_dict)

    found_pdas = {
        "PDAs_A": df_A_dict_length,
        "PDAs_B": df_B_dict_length,
        "PDAs_C": df_C_dict_length
    }

    # Obtener pdas y fechas comunes en los 3 ficheros y descartar el resto
    current_app.logger.info("+++++++++++++++ SINCORNIZANDO FICHEROS +++++++++++++++++++")
    df_A_dict, df_B_dict, df_C_dict = sinconize_dicts(df_A_dict, df_B_dict, df_C_dict)


    current_app.logger.info("+++++++++++++++ ELIMINANDO ELEMENTOS RESIDUALES +++++++++++++++++++")
    current_app.logger.info("--------------- Procesando Fichero A")
    df_A_dict = remove_empty_entries(df_A_dict)
    df_A_dict_length = len(df_A_dict)
                                
    current_app.logger.info("--------------- Procesando Fichero B")
    df_B_dict = remove_empty_entries(df_B_dict)
    df_B_dict_length = len(df_B_dict)

    current_app.logger.info("--------------- Procesando Fichero C")
    df_C_dict = remove_empty_entries(df_C_dict)
    df_C_dict_length = len(df_C_dict)

    shared_pdas = {
        "PDAs_A": df_A_dict_length,
        "PDAs_B": df_B_dict_length,
        "PDAs_C": df_C_dict_length
    }
    

    # 4 - Ordenar por hora
    current_app.logger.info("+++++++++++++++ ORDENANDO POR HORA +++++++++++++++++++")
    current_app.logger.info("--------------- Procesando Fichero A")
    for pda, dates in df_A_dict.items():
        for date, df in dates.items():
            df_A_dict[pda][date] = df.sort_values('solo_hora').reset_index(drop=True)

                                
    current_app.logger.info("--------------- Procesando Fichero B")
    for pda, dates in df_B_dict.items():
        for date, df in dates.items():
            df_B_dict[pda][date] = df.sort_values('solo_hora').reset_index(drop=True)

    current_app.logger.info("--------------- Procesando Fichero C")
    for pda, dates in df_C_dict.items():
        for date, df in dates.items():
            df_C_dict[pda][date] = df.sort_values('solo_hora').reset_index(drop=True)
    

    # 5 - Crear Fichero_D = unificar ficheros B y C (PDA;fecha_hora;fecha;hora;longitud;latitud;segundosTranscurridos)
    #   a - Fijar umbral de tiempo
    #   b - Tomar un fichero como referencia (va a ser el B por que lo digo yo)
    #   c - Establecer un "puntero" al principio de ambos ficheros (va a ser el indice de un for seguramente)
    #   c - Comparar hora (segundos) del registro:
    #       - Si dentro del umbral agregar registro a Fichero_D_PDA01_2025-05-29
    #       - Si fuera del umbral
    #           + guardar diferencia temporal
    #           + comparar con diferencia temporal del siguiente registro en el Fichero_C
    #               ~ Si disminuye la dif. temp. se elimina el registro actual del Fichero_C (fichero observado) y repetir g
    #               ~ Si aumenta la dif. temp. se elimina el registro actual del Fichero_B (fichero referencia) y repetir g
    #               Agregar estos registros a un fichero a parte especificado que no se ha encotrado su registro correspondiente
    current_app.logger.info("+++++++++++++++ CREANDO FICHERO D: UNIFICANDO FICHEROS B Y C +++++++++++++++++++")
    time_threshold = '15s'
    #df_D_dict, unify_stops_info = unify_stops_files(df_B_dict, df_C_dict, time_threshold)
    current_app.logger.info("+++++++++++++++ ESCRIBIENDO FICHERO D +++++++++++++++++++")
    # Convertir de dict a df
    #frames = []
    #for pda, dates in df_D_dict.items():
    #    for date, df in dates.items():
    #        if not df.empty:
    #            frames.append(df.assign(cod_pda=pda, solo_fecha=date))

    #df_D = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    df_B_sorted = df_B.sort_values(['solo_hora'])
    df_C_sorted = df_C.sort_values(['solo_hora'])

    df_B_sorted['solo_hora'] = pd.to_datetime(df_B_sorted['solo_hora'])
    df_C_sorted['solo_hora'] = pd.to_datetime(df_C_sorted['solo_hora'])

    df_B_sorted['cod_pda'] = df_B_sorted['cod_pda'].astype(str)
    df_C_sorted['cod_pda'] = df_C_sorted['cod_pda'].astype(str)

    df_B_sorted['solo_fecha'] = pd.to_datetime(df_B_sorted['solo_fecha'])
    df_C_sorted['solo_fecha'] = pd.to_datetime(df_C_sorted['solo_fecha'])

    df_B_sorted['formatted_fecha_hora'] = pd.to_datetime(df_B_sorted['formatted_fecha_hora'])
    df_C_sorted['formatted_fecha_hora'] = pd.to_datetime(df_C_sorted['formatted_fecha_hora'])

    df_D = pd.merge_asof(df_B_sorted, df_C_sorted, on='solo_hora', by=['cod_pda', 'solo_fecha'], tolerance=pd.Timedelta(time_threshold), direction='nearest')
    df_D = df_D.sort_values(['cod_pda', 'solo_fecha', 'solo_hora'])
    #df_D['longitud'] = df_D['longitud'].replace("", np.nan)
    #df_D = df_D.dropna(subset=['longitud'])
    #df_D['dif_temp'] = (df_D['formatted_fecha_hora_x'] - df_D['formatted_fecha_hora_y']).abs()
    #df_D['esParada'] = True
    #df_D = df_D['cod_pda', 'codired_x', 'Cod Actividad']
    path = os.path.join(save_path, 'Fichero_D.csv')
    df_D.to_csv(path, sep=';', index=False)



    # TODO: la lista de abajo (en principio se ejecutará en orden)
    # 6 - Crear Fichero_F = unificar ficheros A y D (PDA;fecha_hora;fecha;hora;longitud;latitud;segundosTranscurridos;esParada)
    #   a - Se crea una columna (booleana) para especificar si es parada (fichero D) o no (fichero A)
    #   b - Se intercalan los registros en función de la hora
    #       - Si las horas coinciden (que no debería) no quedamos con la parada (fichero D)

    return_info = {
        "Duplicados": duplicates_info,
        "PDAs_encontradas": found_pdas,
        "PDAs_utilizables": shared_pdas,
        #"Union_ficheros_paradas": unify_stops_info
    }

    return jsonify(return_info)














def sinconize_BC_dicts(df_B_dict, df_C_dict):
    current_app.logger.info("+++++++++++++++ SINCORNIZANDO FICHEROS FUNCION +++++++++++++++++++")
    # Sincronizar pdas
    shared_pdas = df_B_dict.keys() & df_C_dict.keys()
    current_app.logger.info(f"Nº pdas comunes: {len(shared_pdas)}")

    # Eliminar las pdas no comunes
    for dict, name in zip([df_B_dict, df_C_dict], ['Fichero_A', 'Fichero_B', 'Fichero_C']):
        for pda in list(dict.keys()):
            #current_app.logger.info(f"Analizando {pda} de {name} con {len(dict[pda].keys())} fechas")
            if pda not in shared_pdas:
                #current_app.logger.info(f"Eliminando {pda} de {name} ya que no se encuentra en otros ficheros")
                del dict[pda]
    
    # Eliminar las fechas no comunes
    for pda in shared_pdas:
        shared_dates = df_B_dict[pda].keys() & df_C_dict[pda].keys()
        for dict, name in zip([df_B_dict, df_C_dict], ['Fichero_A', 'Fichero_B', 'Fichero_C']):
            for date in list(dict[pda].keys()):
                if date not in shared_dates:
                    #current_app.logger.info(f"Eliminando {date} de {pda} de {name} ya que no se encuentra en otros ficheros")
                    del dict[pda][date]
    
    return df_B_dict, df_C_dict


def convert_numpy(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(v) for v in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    else:
        return obj


def calculate_base_statistics(df_B, df_C):
    # Longitud de dataframes
    B_length = len(df_B)
    C_length = len(df_C)
    total_length = B_length + C_length

    length_statistics = {
        "Registros totales": total_length,
        "Registros B": B_length,
        "Registros C": C_length
    }

    # Estadisticas de codigos de unidad
    codireds_B = df_B['codired'].sort_values().unique()
    codireds_B_length = len(codireds_B)
    codireds_C = df_C['codired'].sort_values().unique()
    codireds_C_length = len(codireds_C)

    shared_codireds = set(codireds_B.tolist()) & set(codireds_C.tolist())
    shared_codireds = sorted(shared_codireds)
    shared_codireds_length = len(shared_codireds)

    codired_statistics = {
        "Num codireds encontrados en fichero B": codireds_B_length,
        "Codireds en fichero B": codireds_B,
        "Num codireds encontrados en fichero C": codireds_C_length,
        "Codireds en fichero C": codireds_C,
        "Num codireds compartidos": shared_codireds_length,
        "Codireds compartidos": shared_codireds
    }

    # Estadisticas de PDAs
    pdas_B = df_B['cod_pda'].sort_values().unique()
    pdas_C = df_C['cod_pda'].sort_values().unique()

    shared_pdas = set(pdas_B.tolist()) & set(pdas_C.tolist())
    shared_pdas = sorted(shared_pdas)

    pda_statistics = {
        "Num PDAs encontradas en el fichero B": len(pdas_B),
        "PDAs en fichero B": pdas_B,
        "Num PDAs encontradas en el fichero C": len(pdas_C),
        "PDAs en fichero C": pdas_C,
        "Num PDAs compartida": len(shared_pdas),
        "PDAs compartidas": shared_pdas
    }

    # Estadisticas de Fechas
    dates_B = df_B['solo_fecha'].sort_values().unique()
    dates_B_length = len(dates_B)
    dates_C = df_C['solo_fecha'].sort_values().unique()
    dates_C_length = len(dates_C)

    shared_dates = set(dates_B.tolist()) & set(dates_C.tolist())
    shared_dates = sorted(shared_dates)

    dates_statistics = {
        "Num fechas en fichero B": dates_B_length,
        "Primera fecha en fichero B": dates_B[0],
        "Ultima fecha en fichero B": dates_B[-1],
        "Num fechas en fichero C": dates_C_length,
        "Primera fecha en fichero C": dates_C[0],
        "Ultima fecha en fichero C": dates_C[-1],
        "Num fechas compartidas": len(shared_dates),
        "Primera fecha compartida": list(shared_dates)[0],
        "Ultima fecha compartida": list(shared_dates)[-1]
    }

    base_statistics = {
        "Conteo de registros": length_statistics,
        "Conteo codireds": codired_statistics,
        "Conteo PDAs": pda_statistics,
        "Conteo fechas": dates_statistics
    }

    return base_statistics


def unifyBCFiles(df_B, df_C, save_path):
    """
        Calls necesary functions for creating new files from unifying the files
        Args:
            df_B : dataframe with data from file B
            df_C : dataframe with data from file C
        Returns:
            JSON with all the erased data and its related information
    """
    
    # Obtener Estadísticas iniciales
    current_app.logger.info(f'======================== CALCULANDO ESTADISTICAS INICIALES')
    first_info = calculate_base_statistics(df_B, df_C)


    # Eliminar PDAs defectuosas
    current_app.logger.info(f'======================== ELIMINANDO PDAS DEFECTUOSAS')
    current_app.logger.info("--------------- Procesando Fichero B")
    df_B = df_B[df_B['cod_pda'].str.startswith('PDA')]
    current_app.logger.info("--------------- Procesando Fichero C")
    df_C = df_C[df_C['cod_pda'].str.startswith('PDA')]
    current_app.logger.info("--------------- Calculando estadisticas")
    pda_erase_info = calculate_base_statistics(df_B, df_C)


    # Eliminar duplicados
    current_app.logger.info(f'SEPARANDO FICHEROS POR PDAS Y POR FECHASELIMINANDO DUPLICADOS')
    current_app.logger.info("--------------- Procesando Fichero B")
    df_B, duplicates_B = count_and_drop_duplicates(df_B)
    current_app.logger.info(f"Duplicados: {duplicates_B}")
    current_app.logger.info("--------------- Procesando Fichero C")
    df_C, duplicates_C = count_and_drop_duplicates(df_C)
    current_app.logger.info(f"Duplicados: {duplicates_C}")
    current_app.logger.info("--------------- Calculando estadisticas")
    total_duplicates = duplicates_B + duplicates_C
    current_app.logger.info(f"Duplicados totales: {total_duplicates}")

    df_B_clean = len(df_B)
    df_C_clean = len(df_C)
    total_clean = df_B_clean + df_C_clean

    duplicates_info = {
        "Duplicados totales": total_duplicates,
        "Duplicados B": duplicates_B,
        "Duplicados C": duplicates_C,
        "Registros totales no duplicados": total_clean,
        "Registros B no duplicatos": df_B_clean,
        "Registros C no duplicados": df_C_clean
    }


    # Dividir por PDA -> "PDA01": {}, "PDA02": {}, ...
    # Dividir por fecha -> "PDA01": { "2025-05-29": {}, ...}, ...
    current_app.logger.info(f'======================== SEPARANDO FICHEROS POR PDAS Y POR FECHAS')
    current_app.logger.info("--------------- Procesando Fichero B")
    df_B_dict = create_dict(df_B)
    current_app.logger.info("--------------- Procesando Fichero C")
    df_C_dict = create_dict(df_C)


    # Obtener pdas y fechas comunes y descartar el resto
    current_app.logger.info(f'======================== SINCORNIZANDO FICHEROS')
    df_B_dict, df_C_dict = sinconize_BC_dicts(df_B_dict, df_C_dict)
    

    # Rehacer dataframes
    current_app.logger.info(f'======================== REHACIENDO DATAFRAMES')
    current_app.logger.info("--------------- Procesando Fichero B")
    B_frames = []
    for pda, dates in df_B_dict.items():
        for date, df in dates.items():
            B_frames.append(df)

    df_B = pd.concat(B_frames, ignore_index=True)

    current_app.logger.info("--------------- Procesando Fichero C")
    C_frames = []
    for pda, dates in df_C_dict.items():
        for date, df in dates.items():
            C_frames.append(df)
    df_C = pd.concat(C_frames, ignore_index=True)

    current_app.logger.info("--------------- Calculando estadisticas")
    clean_df_info = calculate_base_statistics(df_B, df_C)
    

    # Union por la izquierda (Fichero B) con un umbral de tiempo
    current_app.logger.info(f'======================== CREANDO FICHERO D: UNIFICANDO FICHEROS B Y C')
    time_threshold = '15s'
    
    # Ordenar por hora
    df_B_sorted = df_B.sort_values(['solo_hora'])
    df_C_sorted = df_C.sort_values(['solo_hora'])

    # Convertir hora a datatime
    df_B_sorted['solo_hora'] = pd.to_datetime(df_B_sorted['solo_hora'])
    df_C_sorted['solo_hora'] = pd.to_datetime(df_C_sorted['solo_hora'])

    # Convertir codigo pda a string
    df_B_sorted['cod_pda'] = df_B_sorted['cod_pda'].astype(str)
    df_C_sorted['cod_pda'] = df_C_sorted['cod_pda'].astype(str)

    # Convertir fecha a datetime
    df_B_sorted['solo_fecha'] = pd.to_datetime(df_B_sorted['solo_fecha'])
    df_C_sorted['solo_fecha'] = pd.to_datetime(df_C_sorted['solo_fecha'])

    # Convertir fecha formateada a datetime
    df_B_sorted['formatted_fecha_hora'] = pd.to_datetime(df_B_sorted['formatted_fecha_hora'])
    df_C_sorted['formatted_fecha_hora'] = pd.to_datetime(df_C_sorted['formatted_fecha_hora'])

    # Realizar la union
    df_D = pd.merge_asof(df_B_sorted, df_C_sorted, on='solo_hora', by=['cod_pda', 'solo_fecha'], tolerance=pd.Timedelta(time_threshold), direction='nearest')

    # Ordenar por PDA, fecha y hora
    df_D = df_D.sort_values(['cod_pda', 'solo_fecha', 'solo_hora'])

    # Rellenar registros sin correspondencia con nan
    df_D['longitud'] = df_D['longitud'].replace("", np.nan)

    # Contar registros sin correspondencia
    unmerged_rows = df_D['longitud'].isna().sum()

    # Eliminar registros sin correspondencia
    df_D = df_D.dropna(subset=['longitud'])

    # Calcular diferencia temporal entre registros correspondientes
    df_D['dif_temp'] = (df_D['formatted_fecha_hora_x'] - df_D['formatted_fecha_hora_y']).abs()

    # Definir un nuevo campo para definir que son paradas
    df_D['esParada'] = True

    # Elinimar y renombrar columnas repetidas
    repeated_columns = ['codired_y', 'formatted_fecha_hora_y', 'fecha_hora_y']
    df_D.drop(repeated_columns, axis=1, inplace=True)
    df_D.rename(columns={
                "codired_x": "codired",
                "formatted_fecha_hora_x": "formatted_fecha_hora",
                "fecha_hora_x": "fecha_hora"
            }, inplace=True)
    

    current_app.logger.info(f'======================== ESCRIBIENDO FICHERO D')
    path = os.path.join(save_path, 'Fichero_D.csv')
    df_D.to_csv(path, sep=';', index=False)

    # Registros usados de cada df
    C_not_used = len(df_C)-len(df_D)
    total_not_used = unmerged_rows + C_not_used
    dates_D = df_D['solo_fecha'].sort_values().unique()
    dates_D_length = len(dates_D)
    not_used_day_mean = total_not_used/dates_D_length
    B_not_used_day_mean = unmerged_rows/dates_D_length
    C_not_used_day_mean = C_not_used/dates_D_length

    unused_info = {
        "Totales no usados en la union": total_not_used,
        "B_no_usados en la union": unmerged_rows,
        "C_no_usados en la union": len(df_C)-len(df_D),
        "Media diaria de registros sin correspondencia total": not_used_day_mean,
        "Media diaria de registros sin correspondencia fichero B": B_not_used_day_mean,
        "Media diaria de registros sin correspondencia fichero C": C_not_used_day_mean,
    }


    # Estructurar informacion final
    return_info = {
        "Informacion inicial": first_info,
        "Duplicados": duplicates_info,
        "Información de sincronizacion": clean_df_info,
        "Registros_no_usados": unused_info,
        "Registros_finales": len(df_D)
    }
    current_app.logger.info(f'Informacion devuelta por la union: {str(return_info)}')

    return jsonify(convert_numpy(return_info))


def unifyADFiles(df_A, df_D, save_path):
    """
        Calls necesary functions for creating new files from unifying the files
        Args:
            df_A : dataframe with data from file A
            df_D : dataframe with data from file D (files B and C)
        Returns:
            JSON with all the erased data and its related information
    """

    # Obtener Estadísticas iniciales
    current_app.logger.info(f'======================== CALCULANDO ESTADISTICAS INICIALES')
    first_info = calculate_base_statistics(df_A, df_D)


    # Eliminar PDAs defectuosas
    current_app.logger.info(f'======================== ELIMINANDO PDAS DEFECTUOSAS')
    current_app.logger.info("--------------- Procesando Fichero A")
    df_A = df_A[df_A['cod_pda'].str.startswith('PDA')]
    current_app.logger.info("--------------- Procesando Fichero D")
    df_D = df_D[df_D['cod_pda'].str.startswith('PDA')]
    current_app.logger.info("--------------- Calculando estadisticas")
    pda_erase_info = calculate_base_statistics(df_A, df_D)


    # Eliminar duplicados
    current_app.logger.info(f'SEPARANDO FICHEROS POR PDAS Y POR FECHASELIMINANDO DUPLICADOS')
    current_app.logger.info("--------------- Procesando Fichero A")
    df_A, duplicates_A = count_and_drop_duplicates(df_A)
    current_app.logger.info(f"Duplicados: {duplicates_A}")
    current_app.logger.info("--------------- Procesando Fichero D")
    df_D, duplicates_D = count_and_drop_duplicates(df_D)
    current_app.logger.info(f"Duplicados: {duplicates_D}")
    current_app.logger.info("--------------- Calculando estadisticas")
    total_duplicates = duplicates_A + duplicates_D
    current_app.logger.info(f"Duplicados totales: {total_duplicates}")

    df_A_clean = len(df_A)
    df_D_clean = len(df_D)
    total_clean = df_A_clean + df_D_clean

    duplicates_info = {
        "Duplicados totales": total_duplicates,
        "Duplicados A": duplicates_A,
        "Duplicados D": duplicates_D,
        "Registros totales no duplicados": total_clean,
        "Registros A no duplicatos": df_A_clean,
        "Registros D no duplicados": df_D_clean
    }


    # Dividir por PDA -> "PDA01": {}, "PDA02": {}, ...
    # Dividir por fecha -> "PDA01": { "2025-05-29": {}, ...}, ...
    current_app.logger.info(f'======================== SEPARANDO FICHEROS POR PDAS Y POR FECHAS')
    current_app.logger.info("--------------- Procesando Fichero A")
    df_A_dict = create_dict(df_A)
    current_app.logger.info("--------------- Procesando Fichero D")
    df_D_dict = create_dict(df_D)


    # Obtener pdas y fechas comunes y descartar el resto
    current_app.logger.info(f'======================== SINCORNIZANDO FICHEROS')
    df_A_dict, df_D_dict = sinconize_BC_dicts(df_A_dict, df_D_dict)
    

    # Rehacer dataframes
    current_app.logger.info(f'======================== REHACIENDO DATAFRAMES')
    current_app.logger.info("--------------- Procesando Fichero A")
    A_frames = []
    for pda, dates in df_A_dict.items():
        for date, df in dates.items():
            A_frames.append(df)

    df_A = pd.concat(A_frames, ignore_index=True)

    current_app.logger.info("--------------- Procesando Fichero D")
    D_frames = []
    for pda, dates in df_D_dict.items():
        for date, df in dates.items():
            D_frames.append(df)
    df_D = pd.concat(D_frames, ignore_index=True)

    current_app.logger.info("--------------- Calculando estadisticas")
    clean_df_info = calculate_base_statistics(df_A, df_D)
    

    # Union por la izquierda (Fichero B) con un umbral de tiempo
    current_app.logger.info(f'======================== CREANDO FICHERO E: UNIFICANDO FICHEROS A Y D')
    time_threshold = '15s'
    
    # Ordenar por hora
    df_A_sorted = df_A.sort_values(['solo_hora'])
    df_D_sorted = df_D.sort_values(['solo_hora'])

    # Convertir hora a datatime
    df_A_sorted['solo_hora'] = pd.to_datetime(df_A_sorted['solo_hora'])
    df_D_sorted['solo_hora'] = pd.to_datetime(df_D_sorted['solo_hora'])
    df_A_sorted['solo_hora'] = df_A_sorted['solo_hora'].dt.strftime('%H:%M:%S')
    df_D_sorted['solo_hora'] = df_D_sorted['solo_hora'].dt.strftime('%H:%M:%S')

    # Convertir codigo pda a string
    df_A_sorted['cod_pda'] = df_A_sorted['cod_pda'].astype(str)
    df_D_sorted['cod_pda'] = df_D_sorted['cod_pda'].astype(str)

    # Convertir fecha a datetime
    df_A_sorted['solo_fecha'] = pd.to_datetime(df_A_sorted['solo_fecha'])
    df_D_sorted['solo_fecha'] = pd.to_datetime(df_D_sorted['solo_fecha'])

    # Convertir fecha formateada a datetime
    df_A_sorted['formatted_fecha_hora'] = pd.to_datetime(df_A_sorted['formatted_fecha_hora'])
    df_D_sorted['formatted_fecha_hora'] = pd.to_datetime(df_D_sorted['formatted_fecha_hora'])

    # Realizar la union
    df_E = df_A_sorted.merge(df_D_sorted, how='outer')

    # Ordenar por PDA, fecha y hora
    df_E = df_E.sort_values(['cod_pda', 'solo_fecha', 'solo_hora'])

    # Eliminar y renombrar columnas necesarias
    df_E.drop('fecha_hora', axis=1, inplace=True)
    df_E.rename(columns={
                "formatted_fecha_hora": "fecha_hora"
            }, inplace=True)
    
    # Rellenar datos necesarios
    df_E['esParada'] = df_E['esParada'].fillna(False)

    current_app.logger.info(f'======================== ESCRIBIENDO FICHERO E')
    path = os.path.join(save_path, 'Fichero_E.csv')
    df_E.to_csv(path, sep=';', index=False)



    # Estructurar informacion final
    return_info = {
        "Informacion inicial": first_info,
        "Duplicados": duplicates_info,
        "Información de sincronizacion": clean_df_info,
        #"Registros_no_usados": unused_info,
        "Registros_finales": len(df_E)
    }
    current_app.logger.info(f'Informacion devuelta por la union: {str(return_info)}')

    return jsonify(convert_numpy(return_info))
