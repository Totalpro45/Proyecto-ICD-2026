"""Extractor de anuncios inmobiliarios de GAOS.

Utiliza el Edge Function de Supabase publicado por GAOS para obtener
anuncios de viviendas en venta y alquiler. La `apikey` es la clave pública
(rol `anon`) de Supabase, expuesta en el frontend del portal y diseñada
para ser usada desde cualquier cliente.

No recopila datos personales de vendedores (nombres, teléfonos, WhatsApp).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import requests

from data.models import AnuncioInmobiliario
from data.normalization import (
    normalizar_amueblado,
    normalizar_estado_conservacion,
    normalizar_moneda,
    normalizar_tipo_area,
    normalizar_tipo_inmueble,
    normalizar_tipo_operacion,
)

# Clave pública de Supabase (rol anon) expuesta en el frontend de GAOS.
# Es un JWT con rol "anon", diseñada para usarse desde el navegador o cualquier
# cliente que llame a las Edge Functions del proyecto Supabase de GAOS.
GAOS_API_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh1aHdrdWVlc2ZibHNjbmJzbXNqIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzI3Njc0NjYsImV4cCI6MjA4ODM0MzQ2Nn0."
    "Q-60HzIGH4AdfrVJAidKEDfDdFpuzc_d29fbLO_6Bfc"
)

GAOS_API_URL = (
    "https://huhwkueesfblscnbsmsj.supabase.co"
    "/functions/v1/get_listings_list_viewport"
)

# Mapeo de icontracttypeid → tipo_operación
CONTRACT_TYPE_MAP = {
    1: "venta",
    2: "alquiler",
}

# Mapeo de ilistingtypeid → tipo_inmueble
# Nota: 1 y 2 están confirmados. El 5 aparece en las peticiones del frontend
# pero su significado no está documentado; se deja sin mapear.
LISTING_TYPE_MAP = {
    1: "casa",
    2: "apartamento",
}

# Valores de vcconstructioncondition conocidos y su equivalencia al esquema.
# Solo se incluyen mapeos cuya equivalencia esté clara.
ESTADO_CONSERVACION_MAP = {
    "good": "bueno",
    "excellent": "bueno",
    "minor_repairs": "regular",
    "major_repairs": "a_reparar",
    "needs_repair": "a_reparar",
    "poor": "malo",
    "ruined": "malo",
}


def _cabeceras() -> dict[str, str]:
    """Cabeceras de solicitud para el Edge Function de GAOS."""
    return {
        "User-Agent": "python-requests",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "apikey": GAOS_API_KEY,
        "Authorization": f"Bearer {GAOS_API_KEY}",
        "Origin": "https://gaos.app",
        "Referer": "https://gaos.app/",
    }


def _cargar_pagina(page: int, limit: int = 20) -> tuple[list[dict], Optional[int]]:
    """Carga una página de anuncios desde GAOS.

    Returns:
        Tupla (lista_de_anuncios_crudos, total_count) o ([], None) si hay error.
    """
    payload = {
        "ne_lat": None,
        "ne_lng": None,
        "sw_lat": None,
        "sw_lng": None,
        "page": page,
        "limit": limit,
        "contractTypeID": 1,
        "listingTypeIDs": [1, 2, 5],
        "provinceID": 3,
    }
    try:
        r = requests.post(
            GAOS_API_URL, json=payload, headers=_cabeceras(), timeout=30
        )
        if r.status_code != 200:
            return [], None
        datos = r.json()
        if not isinstance(datos, list):
            return [], None
        total = None
        if datos:
            total = datos[0].get("total_count")
        return datos, total
    except Exception:
        return [], None


def extraer_listings(limite_paginas: Optional[int] = None) -> list[dict]:
    """Extrae anuncios crudos de GAOS con paginación.

    Args:
        limite_paginas: Número máximo de páginas a consultar. Si es None,
            se consultan todas las páginas disponibles.

    Returns:
        Lista de diccionarios con los datos crudos de GAOS.
    """
    todos: list[dict] = []
    page = 1
    total_count: Optional[int] = None

    while True:
        anuncios, total = _cargar_pagina(page)
        if total is not None:
            total_count = total
        if not anuncios:
            break
        todos.extend(anuncios)
        page += 1
        if limite_paginas is not None and page > limite_paginas:
            break
        if total_count is not None and len(todos) >= total_count:
            break

    return todos


def mapear_anuncio(dato: dict) -> AnuncioInmobiliario:
    """Mapea un anuncio crudo de GAOS al esquema común `AnuncioInmobiliario`.

    No recopila datos personales de vendedores (nombres, teléfonos, WhatsApp).
    Los campos cuyo significado no esté confirmado se dejan como `None`.
    """
    # --- Trazabilidad y fuente ---
    ahora = datetime.now(timezone.utc).isoformat()
    id_fuente = dato.get("ulistingid") or ""

    # --- Tipo de operación ---
    tipo_operacion = normalizar_tipo_operacion(
        CONTRACT_TYPE_MAP.get(dato.get("icontracttypeid"))
    )

    # --- Tipo de inmueble ---
    tipo_inmueble = normalizar_tipo_inmueble(
        LISTING_TYPE_MAP.get(dato.get("ilistingtypeid"))
    )

    # --- Estado de conservación ---
    valor_estado = dato.get("vcconstructioncondition")
    if valor_estado is not None:
        estado_mapeado = ESTADO_CONSERVACION_MAP.get(valor_estado)
        if estado_mapeado is not None:
            estado_conservacion = normalizar_estado_conservacion(
                estado_mapeado
            )
        else:
            estado_conservacion = normalizar_estado_conservacion(valor_estado)
    else:
        estado_conservacion = None

    # --- Moneda ---
    moneda = normalizar_moneda(dato.get("vccurrencytype"))

    # --- Municipio / dirección ---
    # GAOS no tiene un campo separado de municipio; se guarda la dirección
    # completa en direccion_texto y se deja municipio como None.
    direccion_texto = dato.get("vcaddress")
    municipio = None

    # --- Área ---
    area_valor = dato.get("iarea")
    area_m2 = None
    if isinstance(area_valor, (int, float)) and area_valor > 0:
        area_m2 = float(area_valor)

    # --- Habitaciones y baños ---
    habitaciones = None
    hab_valor = dato.get("ibeds")
    if isinstance(hab_valor, (int, float)) and hab_valor > 0:
        habitaciones = int(hab_valor)

    banos = None
    ban_valor = dato.get("ibaths")
    if isinstance(ban_valor, (int, float)) and ban_valor > 0:
        banos = int(ban_valor)

    # --- Precio ---
    precio_valor = dato.get("dcprice")
    precio = None
    if isinstance(precio_valor, (int, float)) and precio_valor > 0:
        precio = float(precio_valor)

    # --- Vendedor ---
    vendedor_tipo = None
    publisher = dato.get("publisher")
    if isinstance(publisher, dict):
        account_type = publisher.get("accountType")
        if account_type == "private":
            vendedor_tipo = "particular"
        elif account_type == "agency":
            vendedor_tipo = "agencia"

    return AnuncioInmobiliario(
        # --- Trazabilidad y fuente ---
        fuente="gaos",
        id_fuente=id_fuente,
        url=f"https://gaos.app/propiedades/{id_fuente}",
        fecha_captura=ahora,
        fecha_publicacion=None,
        fecha_actualizacion=None,
        # --- Ubicación ---
        provincia="La Habana",
        municipio=municipio,
        reparto=None,
        direccion_texto=direccion_texto,
        # --- Características del inmueble ---
        tipo_operacion=tipo_operacion,
        tipo_inmueble=tipo_inmueble,
        area_m2=area_m2,
        tipo_area=None,
        habitaciones=habitaciones,
        banos=banos,
        planta=None,
        estado_conservacion=estado_conservacion,
        amueblado=None,
        # --- Precio y moneda (valores originales) ---
        precio=precio,
        moneda=moneda,
        # --- Conversión a USD (sin tasa todavía) ---
        precio_usd=None,
        tasa_conversion_usd=None,
        tasa_fecha=None,
        tasa_fuente=None,
        precio_m2_usd=None,
        tasa_id=None,
        # --- Texto descriptivo ---
        titulo=dato.get("vctitle"),
        descripcion=dato.get("sdescription_eng") or dato.get("sdescription_ita"),
        # --- Vendedor (sin datos personales) ---
        vendedor_tipo=vendedor_tipo,
        # --- Calidad de los datos ---
        estado_parseo="ok",
        notas_calidad=None,
        es_posible_duplicado=False,
        duplicado_grupo=None,
    )


def extraer_anuncios(
    limite_paginas: Optional[int] = None,
) -> list[AnuncioInmobiliario]:
    """Extrae y mapea anuncios de GAOS al esquema común.

    Args:
        limite_paginas: Número máximo de páginas a consultar.

    Returns:
        Lista de objetos `AnuncioInmobiliario` listos para guardar.
    """
    crudos = extraer_listings(limite_paginas=limite_paginas)
    return [mapear_anuncio(d) for d in crudos]
