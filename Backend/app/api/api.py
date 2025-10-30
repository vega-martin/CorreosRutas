from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request, jsonify
from app.util.fileMgmt import ensure_folder, rename_file_columns
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

    if not os.path.exists(save_path):
        current_app.logger.error(f"Error: el archivo no se guardó en {save_path}")
        return jsonify({'error': f'El archivo no se guardó correctamente'}), 400
    
    current_app.logger.info(f"Archivo guardado correctamente en {save_path}")
    
    return jsonify({'error': f'Archivo guardado correctamente'}), 200


@api_bp.route('/unifyFiles', methods=['POST'])
def unifyFiles():
    # TODO: la lista de abajo (en principio se ejecutará en orden)
    # 1 - Poner fecha_hora en el mismo formato en los 3 ficheros
    # 2 - Crear 2 columnas a partir de fecha_hora (la original se puede dejar): fecha, hora
    # 3 - Eliminar duplicados
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
    
    return jsonify({'error': f'Archivos unificados correctamente'}), 200