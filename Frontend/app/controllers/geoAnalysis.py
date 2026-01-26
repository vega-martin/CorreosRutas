import geopandas as gpd
import pandas as pd
from shapely import wkt
import json
import os
from pyproj import Geod
import numpy as np

kd_tree_dic = {}

class Node:
    """Tree node representing a spatial point and its partitioning metadata.

    This class is typically used in spatial data structures such as
    k-d trees. Each node stores geographic coordinates, a reference
    to the original feature, and the dimension used to split the
    space at this node.

    Attributes:
        longitud (float): Longitude coordinate of the point.
        latitud (float): Latitude coordinate of the point.
        feature_original (Any): Reference to the original data
            structure or feature associated with this node.
        splitting_dimension (int): Dimension index used to split
            the space (e.g., 0 for longitude, 1 for latitude).
        left_node (Node | None): Left child node in the tree.
        right_node (Node | None): Right child node in the tree.
    """

    def __init__(
        self,
        longitud,
        latitud,
        feature_original,
        splitting_dimension,
        left_node=None,
        right_node=None
    ):
        """Initialize a Node instance.

        Args:
            longitud (float): Longitude coordinate of the point.
            latitud (float): Latitude coordinate of the point.
            feature_original (Any): Original feature or data object
                associated with this node.
            splitting_dimension (int): Dimension index used to split
                the space at this node.
            left_node (Node | None, optional): Left child node.
                Defaults to None.
            right_node (Node | None, optional): Right child node.
                Defaults to None.
        """
        self.longitud = longitud
        self.latitud = latitud
        self.feature_original = feature_original
        self.splitting_dimension = splitting_dimension
        self.left_node = left_node
        self.right_node = right_node



# --- GLOBAL SUPPORT FUNCTIONS ---
g = Geod(ellps='WGS84')


def geodesic_distance_meters(lat1, lon1, lat2, lon2):
    """Compute the geodesic distance between two points in meters.

    The distance is calculated on the WGS84 ellipsoid using
    `pyproj.Geod.inv`, which accounts for the Earth's curvature.

    Args:
        lat1 (float): Latitude of the first point.
        lon1 (float): Longitude of the first point.
        lat2 (float): Latitude of the second point.
        lon2 (float): Longitude of the second point.

    Returns:
        float: Geodesic distance between the two points, in meters.
    """
    _, _, distance = g.inv(lon1, lat1, lon2, lat2)
    return distance


# ------------------------------------

def convertToDataframe(geojson_data):
    """Convert GeoJSON feature data into a Pandas DataFrame.

    This function extracts point coordinates and selected properties
    from a GeoJSON FeatureCollection and returns them as a structured
    Pandas DataFrame. Only features with valid 2D point coordinates
    are processed.

    GeoJSON coordinates are expected in the format:
    `[longitude, latitude]`.

    Args:
        geojson_data (dict): GeoJSON object containing a
            `FeatureCollection` with point geometries.

    Returns:
        pandas.DataFrame: DataFrame with the following columns:
            - longitud (float): Longitude coordinate.
            - latitud (float): Latitude coordinate.
            - feature_original (dict): Subset of properties extracted
              from the original GeoJSON feature, including country,
              postcode, street, and number.
    """
    data_list = []
    for feature in geojson_data.get('features', []):
        coords = feature.get('geometry', {}).get('coordinates', [])
        if len(coords) == 2:
            data = feature.get('properties', {})
            data_list.append({
                # GeoJSON coordinates are in [longitude, latitude] order
                'longitud': coords[0],
                'latitud': coords[1],
                'feature_original': {
                    'country': data.get('country', ""),
                    'postcode': data.get('postcode', ""),
                    'street': data.get('street', ""),
                    'number': data.get('number', ""),
                }
            })

    df = pd.DataFrame(data_list)
    return df


def create_kd_tree_optimized(coord_array, metadata_array, indices=None, depth=0):
    """Build an optimized k-d tree from spatial coordinate data.

    This function recursively constructs a balanced k-d tree (k=2)
    from a set of latitude/longitude coordinates. It uses NumPy's
    `argpartition` to select the median in linear time, avoiding
    full sorting at each recursion level.

    The tree alternates the splitting dimension at each depth:
    - 0: latitude
    - 1: longitude

    Args:
        coord_array (numpy.ndarray): Array of shape (N, 2) containing
            spatial coordinates in the form:
            `[latitud, longitud]`.
        metadata_array (Sequence[Any]): Array-like structure containing
            metadata associated with each coordinate. Each entry is
            attached to the corresponding tree node.
        indices (numpy.ndarray | None, optional): Indices of
            `coord_array` to consider at the current recursion level.
            If None, all points are used. Defaults to None.
        depth (int, optional): Current recursion depth, used to
            determine the splitting dimension. Defaults to 0.

    Returns:
        Node | None: Root node of the constructed k-d tree subtree,
        or None if no indices are provided.
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

# --- RECURSIVE SEARCH FUNCTION ---
def _nearest_neighbor_recursive(current_node, target_point, best_dist_m, nearest_node):
    """Recursively search a k-d tree for the nearest neighbor.

    This function implements the core recursive logic for a k-d tree
    nearest-neighbor query with heuristic pruning. Distances are
    computed using geodesic distance (WGS84) via `pyproj.Geod`.

    The algorithm first explores the subtree closest to the target
    point and only explores the opposite subtree if the distance to
    the splitting plane indicates a closer point may exist.

    Args:
        current_node (Node | None): Current node in the k-d tree.
        target_point (tuple[float, float]): Target point coordinates
            in the form `(latitud, longitud)`.
        best_dist_m (float): Current best distance found, in meters.
        nearest_node (Node | None): Node corresponding to the current
            nearest neighbor.

    Returns:
        tuple[float, Node | None]: A tuple containing:
            - Best (minimum) distance found, in meters.
            - Node corresponding to the nearest neighbor.
    """
    if current_node is None:
        return best_dist_m, nearest_node

    target_lat, target_lon = target_point
    
    current_dist_m = geodesic_distance_meters(
        target_lat,
        target_lon,
        current_node.latitud,
        current_node.longitud
    )
    
    if current_dist_m < best_dist_m:
        best_dist_m = current_dist_m
        nearest_node = current_node

    dim = current_node.splitting_dimension
    
    # target_point is (lat, lon): dim=0 -> latitude, dim=1 -> longitude
    target_val = target_point[dim]
    node_val = (
        current_node.latitud if dim == 0
        else current_node.longitud
    )
    
    if target_val < node_val:
        search_first, search_second = (
            current_node.left_node,
            current_node.right_node
        )
    else:
        search_first, search_second = (
            current_node.right_node,
            current_node.left_node
        )

    # Search the "near" subtree first
    best_dist_m, nearest_node = _nearest_neighbor_recursive(
        search_first,
        target_point,
        best_dist_m,
        nearest_node
    )
    
    # Pruning: distance from target to splitting plane
    dist_to_plane_sq = (target_val - node_val) ** 2
    
    # Heuristic conversion: meters to squared degrees
    meters_per_degree = 111_320
    best_dist_degrees_sq = (best_dist_m / meters_per_degree) ** 2
    
    if dist_to_plane_sq < best_dist_degrees_sq:
        # Search the "far" subtree only if necessary
        best_dist_m, nearest_node = _nearest_neighbor_recursive(
            search_second,
            target_point,
            best_dist_m,
            nearest_node
        )
        
    return best_dist_m, nearest_node


def find_nearest_address(kd_tree_root, target_lat, target_lon):
    """Find the nearest address to a target geographic coordinate.

    This function serves as a public wrapper around the internal
    k-d tree nearest-neighbor search. It initializes the recursive
    search, then formats the result into a user-friendly dictionary
    containing distance and address information.

    Args:
        kd_tree_root (Node | None): Root node of the k-d tree
            containing address points.
        target_lat (float): Latitude of the target location.
        target_lon (float): Longitude of the target location.

    Returns:
        dict | None: Dictionary with nearest address information if
        a neighbor is found, otherwise None. The dictionary contains:
            - distance_meters (float): Distance to the nearest address.
            - nearest_latitud (float): Latitude of the nearest point.
            - nearest_longitud (float): Longitude of the nearest point.
            - street (str): Street name of the nearest address.
            - number (str): Street number of the nearest address.
            - post_code (str): Postal code of the nearest address.
    """
    # target_point is defined as (latitude, longitude)
    # to match dim=0 (lat) and dim=1 (lon) indexing
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
    """Initialize and cache a global k-d tree from a GeoJSON file.

    This function loads a GeoJSON file, converts its contents into a
    structured DataFrame, builds an optimized k-d tree from the
    extracted coordinates, and stores the resulting tree in a global
    dictionary keyed by the provided code.

    If the tree for the given code already exists, or if the input
    file is missing or invalid, the function exits silently.

    Args:
        file_geojson (str): Path to the GeoJSON file containing
            point features with geographic coordinates.
        cod (Hashable): Key used to store and retrieve the k-d tree
            instance from the global cache.

    Side Effects:
        - Reads data from disk.
        - Modifies the global `kd_tree_dic` dictionary by adding a
          new k-d tree entry when successful.

    Returns:
        None
    """
    global kd_tree_dic
    if cod in kd_tree_dic:
        return

    if not os.path.exists(file_geojson):
        return

    try:
        with open(file_geojson, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
        
        df_geojson = convertToDataframe(geojson_data)
        if df_geojson.empty:
            return

        coord_array = df_geojson[['latitud', 'longitud']].to_numpy()
        metadata_array = df_geojson['feature_original'].to_numpy()

        KD_TREE_ROOT = create_kd_tree_optimized(coord_array, metadata_array)

        kd_tree_dic[cod] = KD_TREE_ROOT
    except Exception as e:
        return

# --- MAIN FUNCTION ---
def asociar_direcciones_a_puntos(complete_data, file_geojson, cod):
    """Associate the nearest address to each user-provided point.

    This function acts as the main orchestration layer of the workflow.
    It ensures that a k-d tree is initialized for the specified code,
    then iterates over a list of user points and enriches each point
    with the nearest address information obtained from the k-d tree.

    Address matching is performed using geodesic distance (WGS84)
    and a nearest-neighbor search on a k-d tree.

    Args:
        complete_data (list[dict]): List of user-provided points.
            Each dictionary is expected to contain at least:
            - 'latitud' (float)
            - 'longitud' (float)
        file_geojson (str): Path to the GeoJSON file containing
            address point data.
        cod (Hashable): Key used to identify and cache the k-d tree
            instance.

    Side Effects:
        - Initializes and caches a k-d tree in the global `kd_tree_dic`
          dictionary if it does not already exist.
        - Mutates each dictionary in `complete_data` by adding
          address-related fields.

    Returns:
        list[dict] | dict: The updated list of points enriched with
        nearest address data. If initialization fails, a dictionary
        with an error description is returned.
    """
    global kd_tree_dic
    if cod not in kd_tree_dic:
        print("Iniciando árbol binario")
        initialize_global_tree(file_geojson, cod)
        if cod not in kd_tree_dic:
            return {"error": "Failure to initialize portal data"}

    KD_TREE_ROOT = kd_tree_dic[cod]

    for point in complete_data:
        target_lat = point.get('latitud')
        target_lon = point.get('longitud')
        
        if target_lat is not None and target_lon is not None:
            
            # Find nearest address using the k-d tree and geodesic distance
            nearest_info = find_nearest_address(
                KD_TREE_ROOT,
                target_lat,
                target_lon
            )
            
            if nearest_info:
                # Update point with nearest address information
                point['distance'] = nearest_info['distance_meters']
                point['street'] = nearest_info['street']
                point['number'] = nearest_info['number']
                point['post_code'] = nearest_info['post_code']
                point['nearest_latitud'] = nearest_info['nearest_latitud']
                point['nearest_longitud'] = nearest_info['nearest_longitud']
            else:
                # Case where no nearest neighbor is found
                point['distance'] = 'N/A'
                point['street'] = 'No encontrado'
                point['number'] = 'N/A'
                point['post_code'] = 'N/A'
                point['nearest_latitud'] = 'N/A'
                point['nearest_longitud'] = 'N/A'
        
    return complete_data