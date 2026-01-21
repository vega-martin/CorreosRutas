import pandas as pd
import math
import json

# ========= PARÁMETROS =========
INPUT_CSV = "tabla (12).csv"   # nombre del archivo de entrada
OUTPUT_JSON = "clusters_salida.json"

MAX_PUNTOS_CLUSTER = 10        # máximo de puntos por cluster
MAX_DISTANCIA_METROS = 1000.0   # distancia máxima (m) entre primer y último punto del cluster

# ========= FUNCIONES AUXILIARES =========

def to_float_comma(x):
    """Convierte '40,123' -> 40.123. Devuelve None si no es válido."""
    if pd.isna(x):
        return None
    x = str(x).strip()
    if x in ("", "-", "None", "nan"):
        return None
    x = x.replace(",", ".")
    try:
        return float(x)
    except ValueError:
        return None


def to_int_safe(x):
    """Convierte a entero (acepta '123', '123,0', etc.)."""
    if pd.isna(x):
        return None
    x = str(x).strip()
    if x in ("", "-", "None", "nan"):
        return None
    try:
        return int(float(x.replace(",", ".")))
    except ValueError:
        return None


# Haversine en metros
R_TIERRA = 6371000.0  # metros

def haversine_m(lat1, lon1, lat2, lon2):
    """Distancia Haversine en metros entre dos puntos lat/lon."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R_TIERRA * c


def es_par(n):
    return n is not None and n % 2 == 0


def validar_tipo_por_calle(df):
    """Comprueba que cada calle solo tenga un tipo."""
    agrupado = df.groupby("street")["tipo"].nunique()
    calles_mal = agrupado[agrupado > 1]
    if not calles_mal.empty:
        raise ValueError(f"Hay calles con más de un tipo: {calles_mal.to_dict()}")


def clusterizar_secuencia_puntos(rows, max_puntos, max_dist):
    """
    rows: lista de dicts (misma calle, misma lógica de tipo/paridad, ya ordenados).
    max_puntos: máximo puntos por cluster.
    max_dist: distancia máxima entre el primer y el último (en metros).
    """
    clusters = []
    i = 0
    n = len(rows)
    while i < n:
        inicio = i
        cluster = [rows[i]]
        j = i + 1

        while j < n:
            if len(cluster) == max_puntos:
                break

            p_inicio = rows[inicio]
            p_nuevo = rows[j]

            d = haversine_m(
                p_inicio["latitud"], p_inicio["longitud"],
                p_nuevo["latitud"],  p_nuevo["longitud"]
            )

            if d is None or d > max_dist:
                break

            cluster.append(rows[j])
            j += 1

        clusters.append(cluster)
        i = j

    return clusters


def sumar_tiempo_cluster(cluster):
    """Suma el campo 'tiempo' de todos los puntos del cluster."""
    total = 0.0
    for r in cluster:
        v = str(r.get("tiempo", "")).strip()
        if v in ("", "-", "None", "nan"):
            continue
        v = v.replace(",", ".")
        try:
            total += float(v)
        except ValueError:
            continue
    return total


def seleccionar_punto_central_por_distancia(cluster):
    """
    Devuelve el punto del cluster cuya posición geográfica
    está más cerca del centroide (media de latitudes y longitudes).
    """
    if len(cluster) == 1:
        return cluster[0]

    # Centroide simple: media de latitudes y longitudes
    lats = [p["latitud"] for p in cluster if p.get("latitud") is not None]
    lons = [p["longitud"] for p in cluster if p.get("longitud") is not None]

    if not lats or not lons:
        # Si no tenemos coordenadas válidas, devolvemos el central por índice
        return cluster[len(cluster) // 2]

    centro_lat = sum(lats) / len(lats)
    centro_lon = sum(lons) / len(lons)

    mejor_punto = None
    mejor_dist = float("inf")

    for p in cluster:
        lat = p.get("latitud")
        lon = p.get("longitud")
        if lat is None or lon is None:
            continue

        d = haversine_m(centro_lat, centro_lon, lat, lon)
        if d is None:
            continue

        if d < mejor_dist:
            mejor_dist = d
            mejor_punto = p

    # Por seguridad, si algo fallara, devolvemos el del medio por índice
    return mejor_punto or cluster[len(cluster) // 2]


# ========= PROCESO PRINCIPAL =========

def cluster_por_diametro(datos, max_pts_cluster = 10, max_distancia_metros = 1000.0):
    # 1) Leer datos
    # df = pd.read_csv(INPUT_CSV, sep=";", dtype=str)
    df = pd.DataFrame(datos)

    # Normalizar nombres de columnas (por si hay espacios)
    df.columns = [c.strip() for c in df.columns]

    # 2) Convertir tipos necesarios
    df["latitud"] = df["latitud"].apply(to_float_comma)
    df["longitud"] = df["longitud"].apply(to_float_comma)
    df["number"] = df["number"].apply(to_int_safe)

    # 3) Validar tipo único por calle
    validar_tipo_por_calle(df)

    # 4) Ordenar por street y number
    df_sorted = df.sort_values(by=["street", "number"], ascending=[True, True])

    clusters_global = []

    # 5) Agrupar por calle
    for street, df_calle in df_sorted.groupby("street"):
        tipo = df_calle["tipo"].iloc[0]
        rows = df_calle.to_dict(orient="records")

        # Tratamos tipo "-" igual que "zigzag": no se separa par/impar
        if tipo == "zigzag" or tipo == "-":
            clusters = clusterizar_secuencia_puntos(
                rows, max_pts_cluster, max_distancia_metros
            )
            clusters_global.extend(clusters)

        elif tipo == "par/impar":
            # Separa en pares e impares por número
            pares = [r for r in rows if es_par(r["number"])]
            impares = [r for r in rows if (r["number"] is not None and not es_par(r["number"]))]

            if pares:
                clusters_p = clusterizar_secuencia_puntos(
                    pares, max_pts_cluster, max_distancia_metros
                )
                clusters_global.extend(clusters_p)

            if impares:
                clusters_i = clusterizar_secuencia_puntos(
                    impares, max_pts_cluster, max_distancia_metros
                )
                clusters_global.extend(clusters_i)

        else:
            raise ValueError(f"Tipo desconocido en calle {street}: {tipo}")

    # 6) Construir JSON de salida
    salida = []

    for cluster in clusters_global:
        centro = seleccionar_punto_central_por_distancia(cluster)
        tiempo_total = sumar_tiempo_cluster(cluster)

        obj = {}
        # Copiar todos los campos originales del centro
        for k, v in centro.items():
            obj[k] = v

        # Sobrescribimos 'tiempo' con la suma
        obj["tiempo"] = tiempo_total

        # Lista de IDs (o lo que quieras usar) de los puntos del cluster
        obj["puntos_cluster"] = [r.get("number") for r in cluster]

        salida.append(obj)

    # 7) Guardar a JSON
    # with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    #     json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"Clusters generados: {len(salida)}")
    # print(f"Archivo JSON guardado en: {OUTPUT_JSON}")

    # Devolver datos
    return salida

