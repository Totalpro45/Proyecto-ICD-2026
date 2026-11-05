"""Funciones de normalización de datos para el proyecto inmobiliario.

Por ahora incluye la normalización de monedas, tipos de inmueble y tipos de
operación, tal como se define en `docs/decisiones.md`.
"""

# Monedas admitidas por el esquema común, en su forma canónica.
MONEDAS_ADMITIDAS = {"USD", "MLC", "CUP", "EUR", "OTRA"}

# Tipos de inmueble admitidos y sus variantes habituales.
TIPOS_INMUEBLE_ADMITIDOS = {
    "casa": "casa",
    "apartamento": "apartamento",
    "apto": "apartamento",
    "apto.": "apartamento",
    "habitacion": "habitacion",
    "habitación": "habitacion",
    "solar": "solar",
    "otro": "otro",
}

# Tipos de operación admitidos y sus variantes habituales.
TIPOS_OPERACION_ADMITIDOS = {
    "venta": "venta",
    "alquiler": "alquiler",
    "otro": "otro",
}


def normalizar_moneda(valor):
    """Normaliza una moneda a su código canónico.

    Acepta mayúsculas, minúsculas, espacios sobrantes y variantes habituales
    de escritura. Si no se puede identificar, devuelve None.

    No modifica ni convierte el valor numérico del precio.
    """
    if valor is None:
        return None

    if not isinstance(valor, str):
        return None

    normalizado = valor.strip().upper()

    if normalizado in MONEDAS_ADMITIDAS:
        return normalizado

    return None


def normalizar_tipo_inmueble(valor):
    """Normaliza el tipo de inmueble a su valor canónico en minúsculas.

    Acepta variantes habituales como `apto`, `apto.` y `habitación`.
    Si no se puede identificar, devuelve None.
    """
    if valor is None:
        return None

    if not isinstance(valor, str):
        return None

    normalizado = valor.strip().lower()

    return TIPOS_INMUEBLE_ADMITIDOS.get(normalizado)


def normalizar_tipo_operacion(valor):
    """Normaliza el tipo de operación a su valor canónico en minúsculas.

    Acepta variantes habituales de escritura.
    Si no se puede identificar, devuelve None.
    """
    if valor is None:
        return None

    if not isinstance(valor, str):
        return None

    normalizado = valor.strip().lower()

    return TIPOS_OPERACION_ADMITIDOS.get(normalizado)


def normalizar_municipio(valor):
    """Normaliza un nombre de municipio a formato de título.

    Elimina espacios al principio y al final, y aplica formato de título
    (por ejemplo, `PLAYA` → `Playa`, `playa nueva` → `Playa Nueva`).
    No corrige errores ortográficos ni adivina municipios.
    Devuelve None si el valor es None, está vacío o no es texto.
    """
    if valor is None:
        return None

    if not isinstance(valor, str):
        return None

    limpio = valor.strip()

    if not limpio:
        return None

    return limpio.title()


# Tipos de área admitidos y sus variantes habituales.
TIPOS_AREA_ADMITIDOS = {
    "construida": "construida",
    "área construida": "construida",
    "area construida": "construida",
    "construcción": "construida",
    "construccion": "construida",
    "total": "total",
    "área total": "total",
    "area total": "total",
    "superficie total": "total",
    "parcela": "parcela",
    "área de parcela": "parcela",
    "area de parcela": "parcela",
    "terreno": "parcela",
}


def normalizar_tipo_area(valor):
    """Normaliza el tipo de área a su valor canónico en minúsculas.

    Reconoce `construida`, `total` y `parcela`, junto con variantes
    habituales como `área construida`, `construcción`, `superficie total`
    o `terreno`.
    Si no se puede identificar, devuelve None.
    """
    if valor is None:
        return None

    if not isinstance(valor, str):
        return None

    normalizado = valor.strip().lower()

    return TIPOS_AREA_ADMITIDOS.get(normalizado)


# Estados de conservación admitidos y sus variantes habituales.
ESTADOS_CONSERVACION_ADMITIDOS = {
    "bueno": "bueno",
    "buen estado": "bueno",
    "regular": "regular",
    "estado regular": "regular",
    "malo": "malo",
    "mal estado": "malo",
    "a_reparar": "a_reparar",
    "necesita reparación": "a_reparar",
    "necesita reparacion": "a_reparar",
    "para reparar": "a_reparar",
    "desconocido": "desconocido",
}


def normalizar_estado_conservacion(valor):
    """Normaliza el estado de conservación a su valor canónico en minúsculas.

    Reconoce `bueno`, `regular`, `malo`, `a_reparar` y `desconocido`,
    junto con variantes como `buen estado`, `estado regular`, `mal estado`,
    `necesita reparación` y `para reparar`.
    Si no se puede identificar, devuelve None.
    """
    if valor is None:
        return None

    if not isinstance(valor, str):
        return None

    normalizado = valor.strip().lower()

    return ESTADOS_CONSERVACION_ADMITIDOS.get(normalizado)


# Valores de amueblado admitidos y sus variantes habituales.
AMEUBLADO_ADMITIDO = {
    "sí": True,
    "si": True,
    "true": True,
    "1": True,
    "amueblado": True,
    "amueblada": True,
    "no": False,
    "false": False,
    "0": False,
    "sin amueblar": False,
}


def normalizar_amueblado(valor):
    """Normaliza el estado de amueblado a un valor booleano.

    Reconoce valores afirmativos (`sí`, `si`, `true`, `1`, `amueblado`,
    `amueblada`) y negativos (`no`, `false`, `0`, `sin amueblar`).
    Los booleanos reales se conservan tal cual.
    Si no se puede identificar, devuelve None.
    """
    if isinstance(valor, bool):
        return valor

    if valor is None:
        return None

    if not isinstance(valor, str):
        return None

    normalizado = valor.strip().lower()

    if not normalizado:
        return None

    return AMEUBLADO_ADMITIDO.get(normalizado)


from datetime import date, datetime


def normalizar_fecha(valor):
    """Normaliza una fecha a formato ISO `YYYY-MM-DD`.

    Acepta cadenas en formato `YYYY-MM-DD` o `YYYY-MM-DDTHH:MM:SS` (con o
    sin zona horaria), así como objetos `date` y `datetime` de Python.
    No inventa fechas ni utiliza la fecha actual como sustituto.
    Devuelve None si el valor está vacío, es None o no puede interpretarse.
    """
    if valor is None:
        return None

    if isinstance(valor, datetime):
        return valor.date().isoformat()

    if isinstance(valor, date):
        return valor.isoformat()

    if not isinstance(valor, str):
        return None

    normalizado = valor.strip()

    if not normalizado:
        return None

    # Formato YYYY-MM-DD
    try:
        return date.fromisoformat(normalizado).isoformat()
    except ValueError:
        pass

    # Formato YYYY-MM-DDTHH:MM:SS (con o sin zona horaria)
    try:
        return datetime.fromisoformat(normalizado).date().isoformat()
    except ValueError:
        pass

    return None


import re


def normalizar_precio(valor):
    """Extrae el importe numérico y la moneda normalizada de un valor de entrada.

    Maneja formatos como `150000 USD`, `150 000 USD`, `150.000 USD` y
    `150,000 USD`, siempre que la interpretación sea inequívoca.

    No convierte monedas ni calcula `precio_usd`.

    Args:
        valor: Cadena con importe y moneda, o None.

    Returns:
        Tupla (importe, moneda) donde importe es float o None, y moneda es str
        o None. Si el formato es ambiguo o no se puede interpretar con
        seguridad, devuelve (None, None).
    """
    if valor is None:
        return None, None

    if not isinstance(valor, str):
        return None, None

    texto = valor.strip()

    if not texto:
        return None, None

    # Patrón: parte numérica (dígitos, espacios, puntos, comas) seguida
    # opcionalmente de un código de moneda.
    match = re.match(r'^([\d\s.,]+)\s*([A-Za-z]+)?\s*$', texto)
    if not match:
        return None, None

    parte_numerica = match.group(1).strip()
    moneda_raw = match.group(2)

    # Normalizar moneda si está presente
    if moneda_raw is not None:
        moneda = normalizar_moneda(moneda_raw)
        if moneda is None:
            # Moneda desconocida: no se puede interpretar con seguridad.
            return None, None
    else:
        moneda = None

    # Procesar parte numérica
    limpio = parte_numerica.replace(' ', '')

    if not limpio or not any(c.isdigit() for c in limpio):
        return None, None

    tiene_punto = '.' in limpio
    tiene_coma = ',' in limpio

    if tiene_punto and tiene_coma:
        # Ambos separadores: sin más contexto es ambiguo.
        return None, None

    if tiene_punto:
        # Solo punto: si va seguido de 1 o 2 dígitos es decimal.
        # Si va seguido de 3 o más dígitos es ambiguo (miles o decimales).
        ultimo_punto = limpio.rfind('.')
        despues = limpio[ultimo_punto + 1:]
        if len(despues) in (1, 2) and despues.isdigit():
            limpio = limpio.replace('.', '.')
        else:
            return None, None
    elif tiene_coma:
        # Solo coma: si va seguido de 1 o 2 dígitos es decimal.
        # Si va seguido de 3 o más dígitos es ambiguo.
        ultimo_coma = limpio.rfind(',')
        despues = limpio[ultimo_coma + 1:]
        if len(despues) in (1, 2) and despues.isdigit():
            limpio = limpio.replace(',', '.')
        else:
            return None, None

    try:
        importe = float(limpio)
    except ValueError:
        return None, None

    return importe, moneda
