from flask import jsonify, current_app
from app.services.unifyFiles import convert_numpy
from pyproj import Geod
import pandas as pd
import numpy as np
import os


def create_dict(df):
    df_dict = {}
    for pda, group_pda in df.groupby('cod_pda'):
        df_dict[pda] = {}
        for fecha, group_fecha in group_pda.groupby('solo_fecha'):
            #current_app.logger.info(f"Encontrado {pda}: {fecha}")
            df_dict[pda][fecha] = group_fecha
    return df_dict


def calculateDistance(df):
    geod = Geod(ellps="WGS84")

    lons = df['longitud'].str.replace(',', '.', regex=False).astype(float).values
    lats = df['latitud'].str.replace(',', '.', regex=False).astype(float).values

    lons2 = np.roll(lons, -1)
    lats2 = np.roll(lats, -1)

    _, _, dist = geod.inv(lons, lats, lons2, lats2) # Devuelve metros

    df['dist_anterior'] = dist
    df.iloc[-1, df.columns.get_loc('dist_anterior')] = 0
    return df


def calculateTime(df):
    df['solo_hora'] = pd.to_datetime(df['solo_hora'], format="%H:%M:%S")
    df['delta_t'] = (df['solo_hora'] - df['solo_hora'].shift(1)).dt.total_seconds()
    df['delta_t'] = df['delta_t'].fillna(0)
    return df


def calculateVel(df):
    df['velocidad'] = df['dist_anterior']/df['delta_t']
    df['velocidad'] = df['velocidad'].fillna(0)
    return df



def deleteOutliers(df):
    df_clean = df.copy()
    total_deleted = 0

    ref = pd.Series(dtype=float)
    vel = df_clean['velocidad']
    i = 0
    while not ref.equals(vel):
        current_app.logger.info(f'ITERACION {i} PARA QUITAR OUTLIERES')
        vel = df_clean['velocidad']

        ref = vel.copy()

        # ---- media de los 4 anteriores ----
        media_prev = vel.shift(1).rolling(window=12).mean()
        # ---- media de los 4 siguientes ----
        media_next = vel.shift(-1).rolling(window=12).mean()

        # Condiciones
        cond_actual = vel > 1.5 * media_prev
        cond_next = vel > 1.5 * media_next
        cond_med = vel > 3.5

        # marcar registros a eliminar
        to_delete = (cond_actual & cond_next) | cond_med

        deleted_now = to_delete.sum()
        current_app.logger.info(f'SE HAN DETECTADO {deleted_now} OUTLIERS EN ESTA ITELACION')

        total_deleted += deleted_now

        # ---- eliminar ----
        df_clean = df_clean[~to_delete].reset_index(drop=True)

        # ---- recalcular datos ----
        df_clean = calculateDistance(df_clean)
        df_clean = calculateTime(df_clean)
        df_clean = calculateVel(df_clean)
        i += 1

    return df_clean, total_deleted



def removeOutliers(file_path):
    try:
        path = os.path.join(file_path, 'Fichero_E.csv')
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception:
        return jsonify({})
    
    codireds = df['codired'].sort_values().unique()
    pdas = df['cod_pda'].sort_values().unique()
    dates = df['solo_fecha'].sort_values().unique()

    # Sacar estadísticas
    first_info = {
        "Registros totales": len(df),
        "Num codired": len(codireds),
        "Lista codired": codireds,
        "Num PDAs": len(pdas),
        "Lista PDAs": pdas,
        "Num fechas": len(dates),
        "Primera fecha": dates.tolist()[0],
        "Ultima fecha": dates.tolist()[-1]
    }
    num_routes = 0
    deleted_points = 0

    # Crear dict: { "PDA": {"fecha": df, "fecha": df, ...}, ...}
    df_dict = create_dict(df)

    for pda, dates in df_dict.items():
        for date, dataframe in dates.items():
            # Contar el num rutas
            num_routes += 1
            # Calcular distancia con el pto anterior
            dataframe = calculateDistance(dataframe)
            # Calcular tiempo con el pto anterior
            dataframe = calculateTime(dataframe)
            # Calclar velocidad
            dataframe = calculateVel(dataframe)

            # Eliminar olutiers
            dataframe, num_deleted_points = deleteOutliers(dataframe)

            # Contar registros eliminados
            deleted_points += num_deleted_points

            # Guardar modificaciones
            df_dict[pda][date] = dataframe

    # Reconstruir dataframe
    frames = []
    for pda, dates in df_dict.items():
        for date, dataframe in dates.items():
            frames.append(dataframe)

    df = pd.concat(frames, ignore_index=True)
    df['solo_hora'] = pd.to_datetime(df['solo_hora'])
    df['solo_hora'] = df['solo_hora'].dt.strftime('%H:%M:%S')

    # Escribir CSV
    path = os.path.join(file_path, 'Fichero_E_filtrado.csv')
    df.to_csv(path, sep=';', index=False)

    deleted_points_mean = deleted_points/num_routes

    after_info = {
        "Registros totales": len(df),
        "Registros eliminados": deleted_points,
        "Media de  puntos eliminados por ruta": deleted_points_mean
    }

    final_info = {
        "Informacion inicial": first_info,
        "Informacion tras eliminar outliers": after_info
    }

    current_app.logger.info(f'Informacion devuelta por la union: {str(final_info)}')

    return jsonify(convert_numpy(final_info))





        
