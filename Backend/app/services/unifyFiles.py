from flask import jsonify, current_app
from collections import defaultdict
import pandas as pd
import numpy as np
import os

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


def unify_stops_files(df_B_dict, df_C_dict, time_threshold):
    unify_dict = {}
    unify_info = {
        "Registros_fusionados": 0,
        "Registros_B_desechados": 0,
        "Registros_C_desechados": 0
    }
    for pda, dates in df_B_dict.items():
        for date, df_B in dates.items():
            df_C = df_C_dict[pda][date]

            df_B = df_B.copy()
            df_C = df_C.copy()

            df_B['solo_hora'] = pd.to_datetime(df_B['solo_hora'], format='%H:%M:%S')
            df_C['solo_hora'] = pd.to_datetime(df_C['solo_hora'], format='%H:%M:%S')

            # Cartesian join to compare every pair
            merged = df_B.merge(df_C, how='cross')

            # Compute absolute time difference in seconds
            merged['diff_sec'] = (merged['solo_hora_x'] - merged['solo_hora_y']).abs().dt.total_seconds()

            # Filter where difference < threshold seconds
            df_D = merged[merged['diff_sec'] < time_threshold].copy()

            # Compute mean time between the two solo_hora columns
            df_D['solo_hora'] = df_D[['solo_hora_x', 'solo_hora_y']].mean(axis=1)
            df_D['solo_hora'] = df_D['solo_hora'].dt.strftime('%H:%M:%S')

            df_D = df_D['cod_pda', 'codired', 'latitud', 'longitud', 'seg_transcurridos', 'solo_fecha', 'solo_hora', 'diff_sec']

            unify_info['Registros_fusionados'] += len(df_D)

            # -------------------------------
            # Find unmatched rows
            # -------------------------------

            matched_df_B_times = merged.loc[merged['diff_sec'] < time_threshold, 'solo_hora_x'].unique()
            matched_df_C_times = merged.loc[merged['diff_sec'] < time_threshold, 'solo_hora_y'].unique()

            unmatched_df_B = df_B[~df_B['solo_hora'].isin(matched_df_B_times)]
            unmatched_df_C = df_C[~df_C['solo_hora'].isin(matched_df_C_times)]

            unify_info['Registros_B_desechados'] += len(unmatched_df_B)
            unify_info['Registros_C_desechados'] += len(unmatched_df_C)

            if pda not in unify_dict:
                unify_dict[pda] = {}
            unify_dict[pda][date] = df_D
    return unify_dict, unify_info



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
        "Duplicados_B": duplicates_C
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
    df_D['longitud'] = df_D['longitud'].replace("", np.nan)
    df_D = df_D.dropna(subset=['longitud'])
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