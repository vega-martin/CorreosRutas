import os
import time
import shutil

def ejecutar_limpieza_carpeta(directorio_objetivo):
    """
    Borra archivos en el directorio dado que tengan más de 24 horas de antigüedad.
    """
    if not directorio_objetivo or not os.path.exists(directorio_objetivo):
        print(f"El directorio {directorio_objetivo} no existe o no está configurado.")
        return

    ahora = time.time()
    limite_segundos = 10  # 24 horas

    # Listamos todo lo que hay en 'uploads'
    for nombre_item in os.listdir(directorio_objetivo):
        ruta_completa = os.path.join(directorio_objetivo, nombre_item)
        
        try:
            # 1. Obtenemos el tiempo de modificación
            t_mod = os.path.getmtime(ruta_completa)
            es_viejo = (ahora - t_mod) > limite_segundos

            if es_viejo:
                # CASO A: Es una CARPETA
                if os.path.isdir(ruta_completa):
                    # shutil.rmtree borra la carpeta y TODO lo que hay dentro
                    shutil.rmtree(ruta_completa)
                    print(f"Carpeta eliminada: {nombre_item}")
                
                # CASO B: Es un ARCHIVO suelto
                elif os.path.isfile(ruta_completa):
                    os.remove(ruta_completa)
                    print(f"Archivo eliminado: {nombre_item}")

        except Exception as e:
            print(f"Error al intentar borrar {nombre_item}: {e}")