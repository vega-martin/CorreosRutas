import geopandas as gpd
import pandas as pd
from shapely import wkt
import json
import os
from pyproj import Geod
import numpy as np

kd_tree_dic = {}

# Clase nodo para almacenar los datos
class Node:
    def __init__(self,longitud,latitud,feature_original,splitting_dimension, left_node=None, right_node=None):
        self.longitud = longitud
        self.latitud = latitud
        self.feature_original = feature_original
        self.splitting_dimension = splitting_dimension
        self.left_node = left_node
        self.right_node = right_node


# --- FUNCIONES DE SOPORTE GLOBALES ---
g = Geod(ellps='WGS84')

def geodesic_distance_meters(lat1, lon1, lat2, lon2):
    """Calcula la distancia geodésica entre dos puntos en metros usando pyproj.Geod."""
    _, _, distance = g.inv(lon1, lat1, lon2, lat2)
    return distance

# ------------------------------------

def convertToDataframe(geojson_data):
    """
    Convierte los datos GeoJSON en un DataFrame de Pandas, extrayendo 
    las coordenadas y la información relevante de la feature original.
    """
    
    data_list = []
    for feature in geojson_data.get('features', []):
        coords = feature.get('geometry', {}).get('coordinates', [])
        if len(coords) == 2:
            data = feature.get('properties',{})
            data_list.append({
                # Las coordenadas GeoJSON están en formato [longitud, latitud]
                'longitud': coords[0],
                'latitud': coords[1],
                'feature_original': {
                    'country': data.get('country',""),
                    'postcode': data.get('postcode',""),
                    'street': data.get('street',""),
                    'number': data.get('number',""),
                }
            })
    
    df = pd.DataFrame(data_list)
    return df

def create_kd_tree_optimized(coord_array, metadata_array, indices=None, depth=0):
    """
    Generar el árbol binario multidimensional de los datos de geojson
    """
    if indices is None:
        indices = np.arange(len(coord_array))
        
    if len(indices) == 0:
        return None 
    
    k = 2 
    current_dim = depth % k

    median_pos = len(indices) // 2
    
    # (0=lat, 1=lon)
    partition_indices = np.argpartition(coord_array[indices, current_dim], median_pos)
    median_idx_in_subset = partition_indices[median_pos]
    
    median_absolute_index = indices[median_idx_in_subset]
    
    is_left = coord_array[indices, current_dim] < coord_array[median_absolute_index, current_dim]
    
    is_left[median_idx_in_subset] = False
    
    # Indices for the left and right subtrees
    left_indices = indices[is_left]
    right_indices = indices[~is_left]
    
    right_indices = right_indices[right_indices != median_absolute_index]
    
    # Create Node and Recurse
    node = Node(
        latitud=coord_array[median_absolute_index][0],
        longitud=coord_array[median_absolute_index][1],
        feature_original=metadata_array[median_absolute_index],
        splitting_dimension=current_dim,
        
        left_node=create_kd_tree_optimized(coord_array, metadata_array, left_indices, depth + 1),
        right_node=create_kd_tree_optimized(coord_array, metadata_array, right_indices, depth + 1)
    )

    return node

# --- FUNCIÓN DE BÚSQUEDA RECURSIVA ---

def _nearest_neighbor_recursive(current_node, target_point, best_dist_m, nearest_node):
    """Lógica recursiva del K-D Tree con poda heurística y pyproj.Geod."""
    
    if current_node is None:
        return best_dist_m, nearest_node

    target_lat, target_lon = target_point
    
    current_dist_m = geodesic_distance_meters(target_lat, target_lon, current_node.latitud, current_node.longitud)
    
    if current_dist_m < best_dist_m:
        best_dist_m = current_dist_m
        nearest_node = current_node

    dim = current_node.splitting_dimension
    
    # target_point tiene formato (lat, lon), dim=0 es lat, dim=1 es lon
    target_val = target_point[dim] 
    node_val = current_node.latitud if dim == 0 else current_node.longitud
    
    if target_val < node_val:
        search_first, search_second = current_node.left_node, current_node.right_node
    else:
        search_first, search_second = current_node.right_node, current_node.left_node

    # 3. Búsqueda en el subárbol "cercano"
    best_dist_m, nearest_node = _nearest_neighbor_recursive(
        search_first, target_point, best_dist_m, nearest_node
    )
    
    # Poda
    dist_to_plane_sq = (target_val - node_val)**2
    
    # Heurística para convertir D_best (metros) a grados cuadrados para la comparación
    meters_per_degree = 111320 
    best_dist_degrees_sq = (best_dist_m / meters_per_degree)**2
    
    if dist_to_plane_sq < best_dist_degrees_sq:
        # Búsqueda en el subárbol "lejano" (solo si es necesario)
        best_dist_m, nearest_node = _nearest_neighbor_recursive(
            search_second, target_point, best_dist_m, nearest_node
        )
        
    return best_dist_m, nearest_node


def find_nearest_address(kd_tree_root, target_lat, target_lon):
    """Función para iniciar la búsqueda NNS y formatear el resultado."""
    
    # target_point se define como (latitud, longitud) para la indexación dim=0 y dim=1
    target_point = (target_lat, target_lon)
    
    best_dist_m, nearest_node = _nearest_neighbor_recursive(
        current_node=kd_tree_root,
        target_point=target_point,
        best_dist_m=float('inf'),
        nearest_node=None
    )
    
    if nearest_node:
        address_data = nearest_node.feature_original
        
        return {
            'distance_meters': best_dist_m,
            'nearest_latitud': nearest_node.latitud,
            'nearest_longitud': nearest_node.longitud,
            'street': address_data.get('street', 'N/A'),
            'number': address_data.get('number', 'N/A'),
            'post_code': address_data.get('postcode', 'N/A')
        }
    return None

def initialize_global_tree(file_geojson, cod):
    global kd_tree_dic
    if cod in kd_tree_dic: return

    if not os.path.exists(file_geojson):
        return

    try:
        with open(file_geojson, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
        
        df_geojson = convertToDataframe(geojson_data)
        if df_geojson.empty: return

        coord_array = df_geojson[['latitud', 'longitud']].to_numpy()
        metadata_array = df_geojson['feature_original'].to_numpy()

        KD_TREE_ROOT = create_kd_tree_optimized(coord_array, metadata_array)

        kd_tree_dic[cod] = KD_TREE_ROOT
    except Exception as e:
        return

# --- FUNCIÓN PRINCIPAL ---

def asociar_direcciones_a_puntos(datos_completos, file_geojson, cod):
    """
    Función principal que construye el K-D Tree y asocia la dirección 
    más cercana a cada punto de la lista de usuario.
    """

    global kd_tree_dic
    if cod not in kd_tree_dic:
        print("Iniciando árbol binario")
        initialize_global_tree(file_geojson, cod)
        if cod not in kd_tree_dic:
            return {"error": "Fallo al inicializar datos de portales"}

    KD_TREE_ROOT = kd_tree_dic[cod]

    for point in datos_completos:
        target_lat = point.get('latitud')
        target_lon = point.get('longitud')
        
        if target_lat is not None and target_lon is not None:
            
            # Buscar la dirección más cercana usando el K-D Tree y Geod
            nearest_info = find_nearest_address(KD_TREE_ROOT, target_lat, target_lon)
            
            if nearest_info:
                # Actualizar el diccionario del punto con la información de la dirección
                point['distance'] = nearest_info['distance_meters'] 
                point['street'] = nearest_info['street']
                point['number'] = nearest_info['number']
                point['post_code'] = nearest_info['post_code']
                point['nearest_latitud'] = nearest_info['nearest_latitud']
                point['nearest_longitud'] = nearest_info['nearest_longitud']
            else:
                # Caso si el K-D Tree no se construyó o no encontró nada (p. ej., datos fuera de rango)
                point['distance'] = 'N/A'
                point['street'] = 'No encontrado'
                point['number'] = 'N/A'
                point['post_code'] = 'N/A'
                point['nearest_latitud'] = 'N/A'
                point['nearest_longitud'] = 'N/A'
        
    return datos_completos
