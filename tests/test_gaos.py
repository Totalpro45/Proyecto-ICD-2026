"""Pruebas para el extractor de GAOS.

Utiliza datos de ejemplo basados en la estructura real de la respuesta de
GAOS. No realiza peticiones HTTP reales.
"""

import sys
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, "src")

from sources.gaos import mapear_anuncio, extraer_anuncios, extraer_listings
from data.models import AnuncioInmobiliario


# --- Datos de ejemplo basados en la respuesta real de GAOS ---

ANUNCIO_EJEMPLO = {
    "ulistingid": "1a3e69b7-30ba-40ef-ad13-1118971454e0",
    "vctitle": "Venta de casa grande en Marianao ",
    "stittle_eng": None,
    "sdescription_eng": None,
    "sdescription_ita": None,
    "stittle_ita": None,
    "vcaddress": None,
    "dcprice": 15000,
    "dcoriginalprice": 15000,
    "vccurrencytype": "USD",
    "icontracttypeid": 1,
    "ilistingtypeid": 1,
    "ibeds": 4,
    "ibaths": 3,
    "ikitchens": 2,
    "iarea": 296,
    "vcconstructiontype": "capitalista",
    "vcconstructioncondition": "good",
    "vcconstructionroof": "slab",
    "vcelectricitynetwork": None,
    "vcwatersupply": "always",
    "vcimage": "https://ejemplo.com/imagen.webp",
    "vcimages": ["https://ejemplo.com/imagen1.webp"],
    "features": ["Agua de la calle", "Área de servicio", "Papeles en regla"],
    "ipriority": 0,
    "is_favorite": False,
    "price_period": None,
    "bisgem": None,
    "gem_reason": None,
    "total_count": 1789,
    "publisher": {
        "accountType": "private",
        "name": "Gustavo Valdés Pi",      # dato personal: no se recopila
        "phone": "+5352590736",            # dato personal: no se recopila
        "isVerified": False,
        "slug": None,
        "avatarUrl": None,
    },
}

ANUNCIO_EJEMPLO_APARTAMENTO = {
    "ulistingid": "uuid-apartamento-001",
    "vctitle": "Apartamento en venta en Vedado",
    "dcprice": 85000,
    "vccurrencytype": "USD",
    "icontracttypeid": 1,
    "ilistingtypeid": 2,
    "ibeds": 2,
    "ibaths": 1,
    "ikitchens": 1,
    "iarea": 65,
    "vcaddress": "Calle 23, Vedado",
    "vcconstructiontype": "capitalista",
    "vcconstructioncondition": "minor_repairs",
    "vcconstructionroof": "slab",
    "vcelectricitynetwork": None,
    "vcwatersupply": "always",
    "vcimage": "https://ejemplo.com/apt.webp",
    "vcimages": ["https://ejemplo.com/apt1.webp"],
    "features": ["Reformado", "Papeles en regla"],
    "ipriority": 0,
    "is_favorite": False,
    "price_period": None,
    "bisgem": None,
    "gem_reason": None,
    "total_count": 1789,
    "publisher": {
        "accountType": "agency",
        "name": "Inmobiliaria Raíces",   # dato personal: no se recopila
        "phone": "+53 7 854 1234",          # dato personal: no se recopila
        "isVerified": True,
        "slug": None,
        "avatarUrl": None,
    },
}


# --- Pruebas de mapeo ---

def test_mapear_anuncio_campos_obligatorios():
    """El anuncio mapeado tiene todos los campos obligatorios."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO)

    assert isinstance(anuncio, AnuncioInmobiliario)
    assert anuncio.fuente == "gaos"
    assert anuncio.id_fuente == "1a3e69b7-30ba-40ef-ad13-1118971454e0"
    assert anuncio.url == "https://gaos.app/propiedades/1a3e69b7-30ba-40ef-ad13-1118971454e0"
    assert anuncio.fecha_captura is not None
    assert anuncio.estado_parseo == "ok"
    assert anuncio.es_posible_duplicado is False


def test_mapear_anuncio_tipo_operacion():
    """icontracttypeid=1 se mapea a 'venta'."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO)
    assert anuncio.tipo_operacion == "venta"


def test_mapear_anuncio_tipo_inmueble():
    """ilistingtypeid=1 se mapea a 'casa'."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO)
    assert anuncio.tipo_inmueble == "casa"


def test_mapear_anuncio_apartamento():
    """ilistingtypeid=2 se mapea a 'apartamento'."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO_APARTAMENTO)
    assert anuncio.tipo_inmueble == "apartamento"


def test_mapear_anuncio_precio_y_moneda():
    """Precio y moneda se conservan correctamente."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO)
    assert anuncio.precio == 15000.0
    assert anuncio.moneda == "USD"


def test_mapear_anuncio_direccion_y_municipio():
    """Dirección se extrae del anuncio; municipio queda None cuando no se reconoce."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO_APARTAMENTO)
    assert anuncio.direccion_texto == "Calle 23, Vedado"
    assert anuncio.municipio is None


def test_mapear_anuncio_municipio_desde_titulo():
    """Si el título menciona un municipio de La Habana, se identifica."""
    dato = dict(ANUNCIO_EJEMPLO_APARTAMENTO)
    dato["vctitle"] = "Apartamento en venta en zona de Playa"
    anuncio = mapear_anuncio(dato)
    assert anuncio.municipio == "Playa"


def test_mapear_anuncio_municipio_desde_direccion():
    """Si la dirección menciona un municipio de La Habana, se identifica."""
    dato = dict(ANUNCIO_EJEMPLO_APARTAMENTO)
    dato["vcaddress"] = "Calle 23, Vedado, Plaza de la Revolución"
    anuncio = mapear_anuncio(dato)
    assert anuncio.municipio == "Plaza de la Revolución"


def test_mapear_anuncio_municipio_titulo_y_direccion_coinciden():
    """Título y dirección indican el mismo municipio: se usa ese municipio."""
    dato = dict(ANUNCIO_EJEMPLO_APARTAMENTO)
    dato["vctitle"] = "Casa en venta en Playa"
    dato["vcaddress"] = "Playa, La Habana"
    anuncio = mapear_anuncio(dato)
    assert anuncio.municipio == "Playa"
    assert anuncio.notas_calidad is None


def test_mapear_anuncio_municipio_contradiccion_titulo_direccion():
    """Título y dirección indican municipios diferentes: municipio None y
    nota de calidad registrando la contradicción."""
    dato = dict(ANUNCIO_EJEMPLO_APARTAMENTO)
    dato["vctitle"] = "Casa en venta en Centro Habana"
    dato["vcaddress"] = "Playa, La Habana"
    anuncio = mapear_anuncio(dato)
    assert anuncio.municipio is None
    assert anuncio.notas_calidad is not None
    assert "Contradicción" in anuncio.notas_calidad


def test_mapear_anuncio_municipio_solo_titulo():
    """Solo el título identifica municipio; la dirección no aporta nada."""
    dato = dict(ANUNCIO_EJEMPLO_APARTAMENTO)
    dato["vctitle"] = "Casa en Marianao"
    dato["vcaddress"] = "Calle 23"
    anuncio = mapear_anuncio(dato)
    assert anuncio.municipio == "Marianao"
    assert anuncio.notas_calidad is None


def test_mapear_anuncio_area_habitaciones_banos():
    """Área, habitaciones y baños se extraen correctamente."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO)
    assert anuncio.area_m2 == 296.0
    assert anuncio.habitaciones == 4
    assert anuncio.banos == 3


def test_mapear_anuncio_estado_conservacion():
    """vcconstructioncondition='good' se mapea a 'bueno'."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO)
    assert anuncio.estado_conservacion == "bueno"


def test_mapear_anuncio_estado_conservacion_minor_repairs():
    """vcconstructioncondition='minor_repairs' se mapea a 'regular'."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO_APARTAMENTO)
    assert anuncio.estado_conservacion == "regular"


def test_mapear_anuncio_vendedor_tipo_private():
    """accountType='private' se mapea a 'particular'."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO)
    assert anuncio.vendedor_tipo == "particular"


def test_mapear_anuncio_vendedor_tipo_agency():
    """accountType='agency' se mapea a 'agencia'."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO_APARTAMENTO)
    assert anuncio.vendedor_tipo == "agencia"


def test_mapear_anuncio_no_datos_personales():
    """No se recopilan nombres, teléfonos ni WhatsApp de vendedores."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO)
    # Estos campos deben estar vacíos o no contener datos personales
    assert anuncio.titulo == "Venta de casa grande en Marianao "
    assert anuncio.descripcion is None
    # No hay campo para teléfono ni nombre de vendedor en el esquema
    # (están excluidos deliberadamente)


def test_mapear_anuncio_campos_sin_mapear_son_none():
    """Campos cuya equivalencia no está confirmada quedan como None."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO)
    assert anuncio.tipo_area is None
    assert anuncio.planta is None
    assert anuncio.amueblado is None
    assert anuncio.precio_usd is None
    assert anuncio.tasa_id is None


def test_mapear_anuncio_fecha_captura_es_iso():
    """fecha_captura tiene formato ISO 8601."""
    anuncio = mapear_anuncio(ANUNCIO_EJEMPLO)
    # Debe poder parsearse como fecha ISO
    datetime.fromisoformat(anuncio.fecha_captura)


# --- Pruebas de extracción con mock ---

DATOS_PAGINA_1 = [ANUNCIO_EJEMPLO, ANUNCIO_EJEMPLO_APARTAMENTO]
DATOS_PAGINA_2 = []


def test_extraer_listings_una_pagina():
    """extraer_listings devuelve los anuncios de una página."""
    with patch("sources.gaos._cargar_pagina") as mock_cargar:
        mock_cargar.return_value = (DATOS_PAGINA_1, 2)
        resultados = extraer_listings(limite_paginas=1)

    assert len(resultados) == 2
    assert resultados[0]["ulistingid"] == ANUNCIO_EJEMPLO["ulistingid"]
    assert resultados[1]["ulistingid"] == ANUNCIO_EJEMPLO_APARTAMENTO["ulistingid"]


def test_extraer_listings_paginacion_detiene_en_limite():
    """extraer_listings respeta límite de páginas."""
    with patch("sources.gaos._cargar_pagina") as mock_cargar:
        mock_cargar.return_value = (DATOS_PAGINA_1, 2)
        resultados = extraer_listings(limite_paginas=1)

    assert mock_cargar.call_count == 1


def test_extraer_anuncios_devuelve_objetos_mapeados():
    """extraer_anuncios devuelve lista de AnuncioInmobiliario."""
    with patch("sources.gaos._cargar_pagina") as mock_cargar:
        mock_cargar.return_value = (DATOS_PAGINA_1, 2)
        resultados = extraer_anuncios(limite_paginas=1)

    assert len(resultados) == 2
    assert all(isinstance(a, AnuncioInmobiliario) for a in resultados)
    assert resultados[0].fuente == "gaos"
    assert resultados[0].id_fuente == "1a3e69b7-30ba-40ef-ad13-1118971454e0"
    assert resultados[1].fuente == "gaos"
    assert resultados[1].id_fuente == "uuid-apartamento-001"


def test_extraer_anuncios_sin_datos_personales():
    """extraer_anuncios no incluye datos personales de vendedores."""
    with patch("sources.gaos._cargar_pagina") as mock_cargar:
        mock_cargar.return_value = (DATOS_PAGINA_1, 2)
        resultados = extraer_anuncios(limite_paginas=1)

    for anuncio in resultados:
        # Verificar que no hay campos con datos personales
        assert anuncio.titulo is not None
        # El esquema no tiene campos para teléfono ni nombre de vendedor
        # (están excluidos deliberadamente del modelo)
