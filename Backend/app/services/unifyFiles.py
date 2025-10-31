from flask import jsonify, current_app
from app.util.fileMgmt import standardize_date, split_date
import pandas as pd

def count_and_drop_duplicates(df):
    df_length = len(df)
    df = df.drop_duplicates()
    duplicates_count = df_length - len(df)
    return duplicates_count

def unifyAllFiles(pathA, pathB, pathC):
    """
        Calls necesary functions for creating new files from unifying the files
        Args:
            pathA : file A path
            pathB : file B path
            pathC : file c path
        Returns:
            JSON with all the erased data and its related information
    """
    try:
        df_A = pd.read_csv(pathA, delimiter=',', low_memory=False)
        df_B = pd.read_csv(pathB, delimiter=',', low_memory=False)
        df_C = pd.read_csv(pathC, delimiter=',', low_memory=False)
    except Exception:
        current_app.logger.error(f"Error al leer archivo CSV")
        return jsonify({'error' : 'Not able to ope files'})
    
    # 1 - Poner fecha_hora en el mismo formato en los 3 ficheros

    df_A['fecha_hora'] = df_A['fecha_hora'].apply(standardize_date).dt.strftime('%Y-%m-%d %H:%M:%S')
    df_B['fecha_hora'] = df_B['fecha_hora'].apply(standardize_date).dt.strftime('%Y-%m-%d %H:%M:%S')
    df_C['fecha_hora'] = df_C['fecha_hora'].apply(standardize_date).dt.strftime('%Y-%m-%d %H:%M:%S')

    # 2 - Crear 2 columnas a partir de fecha_hora (la original se puede dejar): fecha, hora

    df_A[['solo_fecha', 'solo_hora']] = df_A['fecha_hora'].apply(split_date)
    df_B[['solo_fecha', 'solo_hora']] = df_B['fecha_hora'].apply(split_date)
    df_C[['solo_fecha', 'solo_hora']] = df_C['fecha_hora'].apply(split_date)

    # 3 - Eliminar duplicados

    duplicates_A = count_and_drop_duplicates(df_A)
    duplicates_B = count_and_drop_duplicates(df_B)
    duplicates_C = count_and_drop_duplicates(df_C)
    total_duplicates = duplicates_A + duplicates_B + duplicates_C
    duplicates_info = {
        "Duplicados_totales": total_duplicates,
        "Duplicados_A": duplicates_A,
        "Duplicados_B": duplicates_B,
        "Duplicados_B": duplicates_C
    }

    # TODO: la lista de abajo (en principio se ejecutará en orden)
    # 4 - Ordenar y dividir por PDA -> Fichero_A_PDA01, Fichero_B_PDA01, Fichero_C_PDA01
    # 5 - Ordenar y dividir por fecha -> Fichero_A_PDA01_2025-05-29 se junta con Fichero_B_PDA01_2025-05-29 y Fichero_C_PDA01_2025-05-29
    # 6 - Ordenar por hora
    # 7 - Crear Fichero_D = unificar ficheros B y C (PDA;fecha_hora;fecha;hora;longitud;latitud;segundosTranscurridos)
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
    # 8 - Crear Fichero_F = unificar ficheros A y D (PDA;fecha_hora;fecha;hora;longitud;latitud;segundosTranscurridos;esParada)
    #   a - Se crea una columna (booleana) para especificar si es parada (fichero D) o no (fichero A)
    #   b - Se intercalan los registros en función de la hora
    #       - Si las horas coinciden (que no debería) no quedamos con la parada (fichero D)
    return jsonify({"Duplicados": duplicates_info})