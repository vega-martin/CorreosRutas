
def parse_coord(value):
    if value is None:
        return None

    s = str(value).strip()

    # Caso ideal: ya es un float válido
    try:
        return float(s)
    except ValueError:
        pass

    # Caso decimal con coma
    try:
        return float(s.replace(',', '.'))
    except ValueError:
        pass

    # Caso mal formateado (sin separador decimal correcto)
    # Ej: "4012345" o "40.123.45"
    s_clean = s.replace('.', '').replace(',', '')

    if len(s_clean) < 3:
        raise ValueError(f"Coordenada inválida: {value}")

    s_fixed = s_clean[:2] + '.' + s_clean[2:]
    return float(s_fixed)