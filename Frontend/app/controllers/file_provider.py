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
    fecIni = data_req.get("ini")
    fecFin = data_req.get("fin")
    fecha_inicio_dt = date.fromisoformat(fecIni)
    fecha_fin_dt = date.fromisoformat(fecFin)
    diferencia_dias = (fecha_fin_dt - fecha_inicio_dt).days + 1

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

    # Normalización numérica
    for dato in data:
        dato['longitud'] = str(dato['longitud']).replace('.', ',')
        dato['latitud'] = str(dato['latitud']).replace('.', ',')
        dato['distance'] = str(dato['distance']).replace('.', ',')
        dato['nearest_latitud'] = str(dato['nearest_latitud']).replace('.', ',')
        dato['nearest_longitud'] = str(dato['nearest_longitud']).replace('.', ',')
        dato['distancia'] = str(dato['distancia']).replace(' m', '').replace('.', ',')
        tiempo = float(str(dato['tiempo']).replace(' sec', ''))
        dato['tiempo'] = str(tiempo).replace('.', ',')
        tiempoMedio = tiempo/diferencia_dias
        dato['tiempo_medio'] = str(tiempoMedio).replace('.', ',')
        dato['velocidad'] = str(dato['velocidad']).replace(' km/h', '').replace('.', ',')

    # Renombrar columnas




    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys(), delimiter=';')
    writer.writeheader()
    writer.writerows(data)

    csv_text = '\ufeff' + output.getvalue()

    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=tabla.csv"}
    )
