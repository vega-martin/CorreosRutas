from flask import Blueprint, current_app,session, Response, request
import requests, os, json, io, csv
from datetime import date

file_provider_bp = Blueprint('file_provider', __name__, template_folder='templates')




# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@file_provider_bp.route('/get_stadistics')
def get_stadistics():
    # Preparar datos
    data = {
        "id": session.get("id"),
    }

    api_url = current_app.config.get("API_URL")
    
    # Llamar a la API
    api_response = requests.post(f"{api_url}/descargar_estadisticas", data=data)

    # Verificar éxito
    if api_response.status_code != 200:
        return f"Error en la API: {api_response.status_code}", 500

    # Reenviar el contenido del PDF al cliente
    return Response(
        api_response.content,           # contenido binario
        mimetype="application/pdf",     # tipo MIME correcto
        headers={"Content-Disposition": "attachment; filename=estadisticas.pdf"}
    )




@file_provider_bp.route('/get_generated_file', methods=["POST"])
def get_generated_file():
    data = request.get_json()
    file = data.get("file")

    uploaded = session.get('uploaded_files', {})
    api_url = current_app.config.get("API_URL")
    data = {"id": session.get("id")}

    if (file == "D"):
        r = requests.post(f"{api_url}/get_fichero_intermedio", data=data)
    else:
        r = requests.post(f"{api_url}/get_fichero_unificado", data=data)
    
    r.raise_for_status()

    return Response(
        r.content,
        status=r.status_code,
        mimetype=r.headers.get("Content-Type", "application/octet-stream"),
        headers={
            "Content-Disposition": r.headers.get("Content-Disposition")
        }
    )




@file_provider_bp.route("/get_table", methods=["POST"])
def get_table():
    data_req = request.get_json(silent=True)
    if not data_req:
        return "Invalid JSON body", 400

    table_type = data_req.get("type")
    cod = data_req.get("cod")

    if table_type == "original":
        json_path = os.path.join(
            current_app.config["UPLOAD_FOLDER"],
            session.get("id"),
            "table_data.json"
        )
    elif table_type == "cluster":
        json_path = os.path.join(
            current_app.config["UPLOAD_FOLDER"],
            session.get("id"),
            "table_data_filtered.json"
        )
    else:
        return "Invalid type", 400

    if not os.path.exists(json_path):
        return "JSON file not found", 404

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        return "Invalid JSON format", 400

    if len(data) == 0:
        return Response(
            '\ufeff',
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=tabla.csv"}
        )

    current_app.logger.info("DESCARGA DE TABLA HTML: conversion de tipos")

    # Normalización numérica
    for dato in data:
        dato['distance_portal'] = str(dato['distance_portal']).replace('.', ',')
        dato['latitud_portal'] = str(dato['latitud_portal']).replace('.', ',')
        dato['longitud_portal'] = str(dato['longitud_portal']).replace('.', ',')
        dato['time_accumulated'] = str(dato['time_accumulated']).replace('.', ',')
        dato['time_mean'] = str(dato['time_mean']).replace('.', ',')

    current_app.logger.info("DESCARGA DE TABLA HTML: rellenar tabla")

    mid_data = fill_data(cod, data)

    current_app.logger.info("DESCARGA DE TABLA HTML: renombrar cabecera")

    # Renombrar columnas
    if table_type == "original":
        new_keys = {
            "cod_pda": "num_inv",
            "street" : "calle",
            "number": "numero",
            "latitud_portal" : "latitud",
            "longitud_portal": "longitud",
            "distance_portal": "distancia_media_al_portal",
            "post_code" : "cod_postal",
            "pts_cluster" : "pts_primarios",
            "times_visited": "veces_visitado",
            "time_accumulated" : "tiempo_acumulado",
            "time_mean" : "tiempo_medio",
            "is_stop" : "es_parada",
            "even_odd_count" : "conteo_par/impar",
            "zigzag_count" : "conteo_zigzag",
            "type" : "tipo"
            }
    elif table_type == "cluster":
        new_keys = {
            "cod_pda": "num_inv",
            "street" : "calle",
            "number": "centroide",
            "latitud_portal" : "latitud",
            "longitud_portal": "longitud",
            "distance_portal": "distancia_media_al_portal",
            "post_code" : "cod_postal",
            "pts_cluster" : "pts_primarios",
            "times_visited": "veces_visitado",
            "time_accumulated" : "tiempo_acumulado",
            "time_mean" : "tiempo_medio",
            "is_stop" : "es_parada",
            "even_odd_count" : "conteo_par/impar",
            "zigzag_count" : "conteo_zigzag",
            "type" : "tipo"
            }
    else:
        return "Invalid type", 400
    final_data = [
            {new_keys.get(k, k): v for k, v in item.items()}
            for item in mid_data
        ]


    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=final_data[0].keys(), delimiter=';')
    writer.writeheader()
    writer.writerows(final_data)

    csv_text = '\ufeff' + output.getvalue()

    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=tabla.csv"}
    )


def fill_data(cod, og_data):
    static_dir = current_app.config.get("GEOJSON_FOLDER")
    geojson_path = os.path.join(static_dir, f'{cod}.geojson')

    with open(geojson_path, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
    
    geojson_data_list = []
    for feature in geojson_data.get('features', []):
        coords = feature.get('geometry', {}).get('coordinates', [])
        if len(coords) == 2:
            data = feature.get('properties', {})
            geojson_data_list.append({
                # GeoJSON coordinates are in [longitude, latitude] order
                "cod_pda": "-",
                "street": data.get('street', ""),
                "number": data.get('number', ""),
                "latitud_portal": str(coords[1]).replace('.', ','),
                "longitud_portal": str(coords[0]).replace('.', ','),
                "distance_portal": 0,
                "post_code": data.get('postcode', ""),
                "pts_cluster" : "-",
                "times_visited": 0,
                "time_accumulated" : 0,
                "time_mean" : 0,
                "is_stop" : "-",
                "even_odd_count" : 0,
                "zigzag_count" : 0,
                "type" : "-"
            })

    # Crear índice de lista2 por clave compuesta
    index_og_data = {
        (elem["street"], elem["number"]): elem
        for elem in og_data
    }

    # Reemplazar elementos en lista1 si hay coincidencia
    final_data = [
        index_og_data.get((elem["street"], elem["number"]), elem)
        for elem in geojson_data_list
    ]

    return final_data