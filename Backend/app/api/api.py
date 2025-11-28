from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request, jsonify, Response, send_file
from app.util.fileMgmt import ensure_folder, rename_file_columns, extractDataframes, format_date, get_statistics_A, extractBCDataframes
from app.services.unifyFiles import unifyBCFiles, unifyADFiles
from app.services.dataCleaning import removeOutliers
from app.util.createPDFs import crear_pdf
import json
from io import BytesIO
from datetime import timedelta, datetime
import uuid
import os

api_bp = Blueprint('api', __name__, template_folder='templates')



@api_bp.route('/upload_file', methods=['POST'])
def upload_file():
    # Descargar fichero en local
    current_app.logger.info('Se va a iniciar la descarga en local en el backend')
    base_upload = current_app.config.get("UPLOAD_FOLDER")

    id = request.form.get('id')
    type = request.form.get('type')
    f = request.files.get('file')

    data_filename = f"Fichero_{type}.csv"
    id_path = ensure_folder(id)
    save_path_temp = os.path.join(base_upload, id_path)
    save_path = os.path.join(save_path_temp, data_filename)
    f.save(save_path)

    rename_file_columns(save_path, type)
    format_date(save_path, type)

    if not os.path.exists(save_path):
        current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
        return jsonify({'error': f'El archivo no se guardó correctamente'}), 400
    
    current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
    
    return jsonify({'error': f'Archivo guardado correctamente'}), 200


@api_bp.route('/upload_A_file', methods=['POST'])
def upload_A_file():
    # Descargar fichero en local
    current_app.logger.info('Se va a iniciar la descarga en local en el backend')
    base_upload = current_app.config.get("UPLOAD_FOLDER")

    id = request.form.get('id')
    type = request.form.get('type')
    f = request.files.get('file')

    data_filename = f"Fichero_{type}.csv"
    id_path = ensure_folder(id)
    save_path_temp = os.path.join(base_upload, id_path)
    save_path = os.path.join(save_path_temp, data_filename)
    f.save(save_path)

    rename_file_columns(save_path, type)
    format_date(save_path, type)

    if not os.path.exists(save_path):
        current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
        return jsonify({'error': f'El archivo no se guardó correctamente'}), 400
    
    current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
    
    statistics_response = get_statistics_A(save_path)

    if isinstance(statistics_response, Response):
        statistics = statistics_response.get_json()

    final_response = {
        "logs": f'Archivo guardado correctamente.\n{statistics.get('info', '')}'
    }

    return jsonify(final_response), 200


@api_bp.route('/unifyFilesBC', methods=['POST'])
def unifyFilesBC():
    #cod = request.form.get('codired')
    id = request.form.get('id')
    files_paths = {}
    base_upload = current_app.config.get("UPLOAD_FOLDER")
    id_path = os.path.join(base_upload, str(id))

    for file_type in ('B', 'C'):
        for root, _, files in os.walk(id_path):
            for file in files:
                if file.endswith('.csv') and f'Fichero_{file_type}' in file:
                    wout_extension = os.path.splitext(file)[0]
                    parts = wout_extension.split('_')
                    if len(parts) == 2:
                        type = parts[1]
                        files_paths[type] = os.path.join(root, file)
    
    current_app.logger.info(f"Se han encontrado {len(files_paths)} archivos en la carperta de la sesion {id}")
    df_B, df_C, read_info = extractBCDataframes(files_paths['B'], files_paths['C'])
    if ((len(df_B) == 0) or (len(df_C) == 0)):
        return jsonify({"Registros totales: 0"})
    erased_info = unifyBCFiles(df_B, df_C, id_path)
    
    if isinstance(read_info, Response):
        read_info = read_info.get_json()

    if isinstance(erased_info, Response):
        erased_info = erased_info.get_json()


    final_info = f"""
    Información de lectura de los datos:
    - Registros totales: {erased_info["Informacion inicial"]["Conteo de registros"]["Registros totales"]}.
    \t - Pertenecientes al fichero B: {erased_info["Informacion inicial"]["Conteo de registros"]["Registros B"]}.
    \t - Pertenecientes al fichero C: {erased_info["Informacion inicial"]["Conteo de registros"]["Registros C"]}.
    - Códigos de unidad:
    \t - Pertenecientes al fichero B: {erased_info["Informacion inicial"]["Conteo codireds"]["Num codireds encontrados en fichero B"]}.
    \t - Lista: {erased_info["Informacion inicial"]["Conteo codireds"]["Codireds en fichero B"]}.
    \t - Pertenecientes al fichero C: {erased_info["Informacion inicial"]["Conteo codireds"]["Num codireds encontrados en fichero C"]}.
    \t - Lista: {erased_info["Informacion inicial"]["Conteo codireds"]["Codireds en fichero C"]}.
    \t - Compartidos: {erased_info["Informacion inicial"]["Conteo codireds"]["Num codireds compartidos"]}.
    \t - Lista: {erased_info["Informacion inicial"]["Conteo codireds"]["Codireds compartidos"]}.
    - PDAs:
    \t - Pertenecientes al fichero B: {erased_info["Informacion inicial"]["Conteo PDAs"]["Num PDAs encontradas en el fichero B"]}.
    \t - Lista: {erased_info["Informacion inicial"]["Conteo PDAs"]["PDAs en fichero B"]}.
    \t - Pertenecientes al fichero C: {erased_info["Informacion inicial"]["Conteo PDAs"]["Num PDAs encontradas en el fichero C"]}.
    \t - Lista: {erased_info["Informacion inicial"]["Conteo PDAs"]["PDAs en fichero C"]}.
    \t - Compartidos: {erased_info["Informacion inicial"]["Conteo PDAs"]["Num PDAs compartida"]}.
    \t - Lista: {erased_info["Informacion inicial"]["Conteo PDAs"]["PDAs compartidas"]}.
    - Fechas:
    \t - Pertenecientes al fichero B: {erased_info["Informacion inicial"]["Conteo fechas"]["Num fechas en fichero B"]}.
    \t - Primera fecha: {erased_info["Informacion inicial"]["Conteo fechas"]["Primera fecha en fichero B"]}.
    \t - Última fecha: {erased_info["Informacion inicial"]["Conteo fechas"]["Ultima fecha en fichero B"]}.
    \t - Pertenecientes al fichero C: {erased_info["Informacion inicial"]["Conteo fechas"]["Num fechas en fichero C"]}.
    \t - Primera fecha: {erased_info["Informacion inicial"]["Conteo fechas"]["Primera fecha en fichero C"]}.
    \t - Última fecha: {erased_info["Informacion inicial"]["Conteo fechas"]["Ultima fecha en fichero C"]}.
    \t - Compartidas: {erased_info["Informacion inicial"]["Conteo fechas"]["Num fechas compartidas"]}.
    \t - Primera fecha: {erased_info["Informacion inicial"]["Conteo fechas"]["Primera fecha compartida"]}.
    \t - Última fecha: {erased_info["Informacion inicial"]["Conteo fechas"]["Ultima fecha compartida"]}.
    
    
    Información de la unión de los datos:
    - Información duplicada:
    \t - Duplicados totales: {erased_info["Duplicados"]["Duplicados totales"]}.
    \t\t - Pertenecientes al conjunto B: {erased_info["Duplicados"]["Duplicados B"]}.
    \t\t - Pertenecientes al conjunto C: {erased_info["Duplicados"]["Duplicados C"]}.
    \t\t - Datos totales no duplicados: {erased_info["Duplicados"]["Registros totales no duplicados"]}.
    \t\t - Datos no duplicados del conjunto B: {erased_info["Duplicados"]["Registros B no duplicados"]}.
    \t\t - Datos no duplicados del conjunto C: {erased_info["Duplicados"]["Registros C no duplicados"]}.
    \t - Informacion de sincronización (eliminar PDAs y fechas no compartidas):
    \t\t - Registros totales: {erased_info["Información de sincronizacion"]["Conteo de registros"]["Registros totales"]}.
    \t\t\t - Pertenecientes al fichero B: {erased_info["Información de sincronizacion"]["Conteo de registros"]["Registros B"]}.
    \t\t\t - Pertenecientes al fichero C: {erased_info["Información de sincronizacion"]["Conteo de registros"]["Registros C"]}.
    \t\t - Códigos de unidad:
    \t\t\t - Pertenecientes al fichero B: {erased_info["Información de sincronizacion"]["Conteo codireds"]["Num codireds encontrados en fichero B"]}.
    \t\t\t - Lista: {erased_info["Información de sincronizacion"]["Conteo codireds"]["Codireds en fichero B"]}.
    \t\t\t - Pertenecientes al fichero C: {erased_info["Información de sincronizacion"]["Conteo codireds"]["Num codireds encontrados en fichero C"]}.
    \t\t\t - Lista: {erased_info["Información de sincronizacion"]["Conteo codireds"]["Codireds en fichero C"]}.
    \t\t\t - Compartidos: {erased_info["Información de sincronizacion"]["Conteo codireds"]["Num codireds compartidos"]}.
    \t\t\t - Lista: {erased_info["Información de sincronizacion"]["Conteo codireds"]["Codireds compartidos"]}.
    \t\t- PDAs:
    \t\t\t - Pertenecientes al fichero B: {erased_info["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs encontradas en el fichero B"]}.
    \t\t\t - Lista: {erased_info["Información de sincronizacion"]["Conteo PDAs"]["PDAs en fichero B"]}.
    \t\t\t - Pertenecientes al fichero C: {erased_info["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs encontradas en el fichero C"]}.
    \t\t\t - Lista: {erased_info["Información de sincronizacion"]["Conteo PDAs"]["PDAs en fichero C"]}.
    \t\t\t - Compartidos: {erased_info["Información de sincronizacion"]["Conteo PDAs"]["Num PDAs compartida"]}.
    \t\t\t - Lista: {erased_info["Información de sincronizacion"]["Conteo PDAs"]["PDAs compartidas"]}.
    \t\t - Fechas:
    \t\t\t - Pertenecientes al fichero B: {erased_info["Información de sincronizacion"]["Conteo fechas"]["Num fechas en fichero B"]}.
    \t\t\t - Primera fecha: {erased_info["Información de sincronizacion"]["Conteo fechas"]["Primera fecha en fichero B"]}.
    \t\t\t - Última fecha: {erased_info["Información de sincronizacion"]["Conteo fechas"]["Ultima fecha en fichero B"]}.
    \t\t\t - Pertenecientes al fichero C: {erased_info["Información de sincronizacion"]["Conteo fechas"]["Num fechas en fichero C"]}.
    \t\t\t - Primera fecha: {erased_info["Información de sincronizacion"]["Conteo fechas"]["Primera fecha en fichero C"]}.
    \t\t\t - Última fecha: {erased_info["Información de sincronizacion"]["Conteo fechas"]["Ultima fecha en fichero C"]}.
    \t\t\t - Compartidas: {erased_info["Información de sincronizacion"]["Conteo fechas"]["Num fechas compartidas"]}.
    \t\t\t - Primera fecha: {erased_info["Información de sincronizacion"]["Conteo fechas"]["Primera fecha compartida"]}.
    \t\t\t - Última fecha: {erased_info["Información de sincronizacion"]["Conteo fechas"]["Ultima fecha compartida"]}.
    \t - Informacion de correspondencia de registros en la unión:
    \t\t - Registros totales no usados en la union: {erased_info["Registros_no_usados"]["Totales no usados en la union"]}.
    \t\t - Registros del conjunto B no usados en la union: {erased_info["Registros_no_usados"]["B_no_usados en la union"]}.
    \t\t - Registros del conjunto C no usados en la union: {erased_info["Registros_no_usados"]["C_no_usados en la union"]}.
    
    
    - Registros finales: {erased_info["Registros_finales"]}.
    """


    final_response = {"logs": final_info}
    json_path = os.path.join(id_path, "D_statistics.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(erased_info, f, ensure_ascii=False, indent=4)

    return jsonify(final_response)


@api_bp.route('/unifyAllFiles', methods=['POST'])
def unifyAllFiles():
    id = request.form.get('id')
    files_paths = {}
    base_upload = current_app.config.get("UPLOAD_FOLDER")
    id_path = os.path.join(base_upload, str(id))

    for root, _, files in os.walk(id_path):
        for file in files:
            if file.endswith('.csv') and 'Fichero_' in file:
                wout_extension = os.path.splitext(file)[0]
                parts = wout_extension.split('_')
                if len(parts) == 2:
                    type = parts[1]
                    files_paths[type] = os.path.join(root, file)
    
    current_app.logger.info(f"Se han encontrado {len(files_paths)} archivos en la carperta de la sesion {id}")
    df_A, df_D, read_info = extractBCDataframes(files_paths['A'], files_paths['D'])
    if ((len(df_A) == 0) or (len(df_D) == 0)):
        return jsonify({"Registros totales: 0"})
    erased_info = unifyADFiles(df_A, df_D, id_path)

    
    outliers_info = removeOutliers(id_path)
    
    if isinstance(read_info, Response):
        read_info = read_info.get_json()

    if isinstance(erased_info, Response):
        erased_info = erased_info.get_json()

    final_response = {"logs": f'{erased_info}'}
    json_path = os.path.join(id_path, "E_statistics.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(erased_info, f, ensure_ascii=False, indent=4)

    current_app.logger.info("EMPEZANDO CREACION DE PDF CON ESTADISTICAS")
    file_path = os.path.join(id_path, 'estadisticas_union.pdf')
    crear_pdf(file_path, id_path)

    return jsonify(final_response)


@api_bp.route("/estan_unificados", methods = ['POST'])
def estan_unificados():
    id = request.form.get('id')
    base_upload = current_app.config.get("UPLOAD_FOLDER")
    id_path = os.path.join(base_upload, str(id))
    final_file = os.path.join(id_path, 'estadisticas_union.pdf')
    response = {'logs': os.path.exists(final_file)}
    return jsonify(response)



@api_bp.route("/descargar_estadisticas", methods=['POST'])
def descargar_estadisticas():
    # Ruta absoluta o relativa al PDF
    id = request.form.get('id')
    base_upload = current_app.config.get("UPLOAD_FOLDER")
    id_path = os.path.join(base_upload, str(id))
    pdf_path = os.path.join(id_path, 'estadisticas_union.pdf')

    # Comprobar si existe
    if not os.path.exists(pdf_path):
        return "El archivo no existe", 404

    # Devolver el PDF como descarga
    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="estadisticas.pdf"
    )