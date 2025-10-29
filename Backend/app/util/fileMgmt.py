from flask import current_app, request, jsonify
import pandas as pd


def valid_extension(name):
    """Comprueba si la extensión es valida"""

    valid_ext = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in name and name.rsplit('.', 1)[1].lower() in valid_ext


def valid_file(path):
    try:
        df = pd.read_csv(path, delimiter=';', low_memory=False)
    except Exception as e:
        return jsonify({'error': f'Error al leer el archivo: {str(e)}'}), 500

    required_columns_map = {
        "A": {'fec_lectura_medicion', 'longitud_wgs84_gd', 'latitud_wgs84_gd', 'cod_inv_pda'},
        "B": {'Num Inv', 'Fec Actividad', 'Seg Transcurrido'},
        "C": {'COD_SECCION', 'INSTANTE', 'LONGITUD', 'LATITUD'}
    }

    # Determinar tipo de fichero
    for type in required_columns_map:
        required_columns = required_columns_map.get(type)
        if required_columns.issubset(df.columns):
            file_type = type
        
    if file_type == "A":
        

    if not required_columns:
        current_app.logger.error('Error: el fichero no cumple con los criterios')
        return jsonify({'error': f'El archivo no cumple con los criterios'}), 400
    
    if not required_columns.issubset(df.columns):
        return jsonify({'error': f'El fichero CSV debe contener las columnas: {", ".join(required_columns)}'}), 400
    
    current_app.logger.info('Archivo subido válido')

    return jsonify({'message': 'Archivo válido'}), 200