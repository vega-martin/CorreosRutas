from flask import jsonify, current_app
from datetime import time
import pandas as pd
import numpy as np
import os

TIME_THRESHOLD = '15s'
START_TIME = time(7, 30)
END_TIME = time(22, 0)


def count_and_drop_duplicates(df):
    df_length = len(df)
    df = df.drop_duplicates(ignore_index=True)
    duplicates_count = df_length - len(df)
    return df, duplicates_count


def align_two_dfs_on_zone_date(df1, df2):
    keys = ['cod_pda', 'solo_fecha']

    common = df1[keys].merge(df2[keys]).drop_duplicates()

    df1_filt = df1.merge(common, on=keys, how='inner')
    df2_filt = df2.merge(common, on=keys, how='inner')

    return df1_filt, df2_filt


def align_one_df_on_zone_date(df1, df2):
    keys = ['cod_pda', 'solo_fecha']

    # Claves comunes
    common = df1[keys].merge(df2[keys]).drop_duplicates()

    # Filtrar df2
    df_filt = df2.merge(common, on=keys, how='inner')

    # Registros eliminados
    df_removed = df2.merge(common, on=keys, how='left', indicator=True)
    df_removed = df_removed[df_removed['_merge'] == 'left_only']
    
    total_removed = len(df_removed)

    # Conjuntos para comprobar existencia individual
    set_pda   = set(df1['cod_pda'])
    set_fecha = set(df1['solo_fecha'])
    set_pairs = set(map(tuple, df1[keys].drop_duplicates().to_numpy()))

    def clasificar(row):
        cod_ok   = row['cod_pda'] in set_pda
        fecha_ok = row['solo_fecha'] in set_fecha

        # Todos los removed tienen pair_ok == False
        if not cod_ok and fecha_ok:
            return "solo_cod_pda_no_existe"
        elif cod_ok and not fecha_ok:
            return "solo_fecha_no_existe"
        elif not cod_ok and not fecha_ok:
            return "cod_pda_y_fecha_no_existen"
        else:
            return "solo_combinacion_no_existe"

    df_removed["motivo"] = df_removed.apply(clasificar, axis=1)

    # Diccionario de conteos
    #conteo = df_removed["motivo"].value_counts().to_dict()
    conteo = {
    "solo_cod_pda_no_existe": (df_removed["motivo"] == "solo_cod_pda_no_existe").sum(),
    "solo_fecha_no_existe": (df_removed["motivo"] == "solo_fecha_no_existe").sum(),
    "cod_pda_y_fecha_no_existen": (df_removed["motivo"] == "cod_pda_y_fecha_no_existen").sum(),
    "solo_combinacion_no_existe": (df_removed["motivo"] == "solo_combinacion_no_existe").sum()
}

    # Añadir total al diccionario
    conteo["total_eliminados"] = total_removed

    current_app.logger.info(f"Diccionario {conteo}")

    return df_filt, conteo


def filter_by_time_range(df, start_time, end_time):
    df_copy = df.copy()
    df_copy['solo_hora'] = pd.to_datetime(df_copy['solo_hora']).dt.time
    mask = (df_copy['solo_hora'] >= start_time) & (df_copy['solo_hora'] <= end_time)
    return df[mask]


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
        "Lista fecha en fichero B": dates_B,
        "Num fechas en fichero C": dates_C_length,
        "Lista fecha en fichero C": dates_C,
        "Num fechas compartidas": len(shared_dates),
        "Lista fecha compartida": shared_dates
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

    # TODO: añadir a las estadisticas

    # Eliminar PDAs defectuosas
    current_app.logger.info(f'======================== ELIMINANDO PDAS DEFECTUOSAS')
    current_app.logger.info("--------------- Procesando Fichero B")
    df_B = df_B[df_B['cod_pda'].str.startswith('PDA')]
    current_app.logger.info("--------------- Procesando Fichero C")
    df_C = df_C[df_C['cod_pda'].str.startswith('PDA')]
    current_app.logger.info("--------------- Calculando estadisticas")
    pda_erase_info = calculate_base_statistics(df_B, df_C)

    # TODO: eliminar fechas defectuosas



    # Eliminar duplicados
    current_app.logger.info(f'SEPARANDO FICHEROS POR PDAS Y POR FECHAS ELIMINANDO DUPLICADOS')
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
        "Registros B no duplicados": df_B_clean,
        "Registros C no duplicados": df_C_clean
    }

    # Extraer PDAS y Fechas compartidas
    current_app.logger.info(f'======================== SINCORNIZANDO DATAFRAMES')
    df_B, df_C = align_two_dfs_on_zone_date(df_B, df_C)
    
    current_app.logger.info("--------------- Calculando estadisticas")
    
    clean_df_info = calculate_base_statistics(df_B, df_C)

    # Union por la izquierda (Fichero B) con un umbral de tiempo
    current_app.logger.info(f'======================== CREANDO FICHERO D: UNIFICANDO FICHEROS B Y C')
    
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
    df_D = pd.merge_asof(df_B_sorted, df_C_sorted, on='solo_hora', by=['cod_pda', 'solo_fecha'], tolerance=pd.Timedelta(TIME_THRESHOLD), direction='nearest')

    # Ordenar por PDA, fecha y hora
    df_D = df_D.sort_values(['cod_pda', 'solo_fecha', 'solo_hora'])

    # Rellenar registros sin correspondencia con nan
    df_D['longitud'] = df_D['longitud'].replace("", np.nan)

    # Contar registros sin correspondencia
    unmerged_rows = df_D['longitud'].isna().sum()

    # Eliminar registros sin correspondencia
    df_D = df_D.dropna(subset=['longitud'])

    # Calcular diferencia temporal entre registros correspondientes
    df_D['dif_temp'] = (df_D['formatted_fecha_hora_x'] - df_D['formatted_fecha_hora_y']).abs().dt.total_seconds()

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
    before_A_length = len(df_A)
    df_A = df_A[df_A['cod_pda'].str.startswith('PDA')]
    pda_A_length = before_A_length - len(df_A)
    current_app.logger.info("--------------- Procesando Fichero D")
    before_D_length = len(df_D)
    df_D = df_D[df_D['cod_pda'].str.startswith('PDA')]
    pda_D_length = before_D_length - len(df_D)

    # Eliminar fechas defectuosas
    current_app.logger.info(f'======================== ELIMINANDO FECHAS DEFECTUOSAS')
    current_app.logger.info("--------------- Procesando Fichero A")
    before_A_length = len(df_A)
    df_A = df_A.dropna(subset=['solo_fecha'])
    fechas_A_length = before_A_length - len(df_A)
    current_app.logger.info("--------------- Procesando Fichero D")
    before_D_length = len(df_D)
    df_D = df_D.dropna(subset=['solo_fecha'])
    fechas_D_length = before_D_length - len(df_D)

    # Eliminar horas defectuosas
    current_app.logger.info(f'======================== ELIMINANDO HORAS DEFECTUOSAS')
    current_app.logger.info("--------------- Procesando Fichero A")
    before_A_length = len(df_A)
    df_A = filter_by_time_range(df_A, START_TIME, END_TIME)
    horas_A_length = before_A_length - len(df_A)
    current_app.logger.info("--------------- Procesando Fichero D")
    before_D_length = len(df_D)
    df_D = filter_by_time_range(df_D, START_TIME, END_TIME)
    hora_D_length = before_D_length - len(df_D)

    current_app.logger.info("--------------- Calculando estadisticas")
    defective_info = {
        "PDAs A": pda_A_length,
        "PDAs D": pda_D_length,
        "Fechas A": fechas_A_length,
        "Fechas D": fechas_D_length,
        "Horas A": horas_A_length,
        "Horas D": hora_D_length
    }


    # Eliminar duplicados
    current_app.logger.info(f'SEPARANDO FICHEROS POR PDAS Y POR FECHAS ELIMINANDO DUPLICADOS')
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
        "Registros A no duplicados": df_A_clean,
        "Registros D no duplicados": df_D_clean
    }


    # Extraer PDAS y Fechas compartidas
    current_app.logger.info(f'======================== SINCORNIZANDO DATAFRAMES')
    df_D, aling_info = align_one_df_on_zone_date(df_A, df_D)

    current_app.logger.info("--------------- Calculando estadisticas")
    clean_df_info = calculate_base_statistics(df_A, df_D)
    

    # Union por la izquierda (Fichero B) con un umbral de tiempo
    current_app.logger.info(f'======================== CREANDO FICHERO E: UNIFICANDO FICHEROS A Y D')
    
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

    # Rellenar registros defectuosos con nan
    df_D['fecha_hora'] = df_D['fecha_hora'].replace("", np.nan)

    # Eliminar registros defectuosos
    df_D = df_D.dropna(subset=['fecha_hora'])

    current_app.logger.info(f'======================== ESCRIBIENDO FICHERO E')
    path = os.path.join(save_path, 'Fichero_E.csv')
    df_E.to_csv(path, sep=';', index=False)



    # Estructurar informacion final
    return_info = {
        "Informacion inicial": first_info,
        "Defectuoso": defective_info,
        "Duplicados": duplicates_info,
        "Motivo eliminar sincronizacion": aling_info,
        "Información de sincronizacion": clean_df_info,
        #"Registros_no_usados": unused_info,
        "Registros_finales": len(df_E)
    }
    current_app.logger.info(f'Informacion devuelta por la union: {str(return_info)}')

    return jsonify(convert_numpy(return_info))
