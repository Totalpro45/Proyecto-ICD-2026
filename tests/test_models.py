"""Pruebas para el modelo de datos inmobiliarios.

Comprueba el comportamiento actual de `AnuncioInmobiliario` sin implementar
reglas nuevas.
"""

import sys
import uuid

sys.path.insert(0, "src")

from data.models import AnuncioInmobiliario


def _nuevo_id():
    return str(uuid.uuid4())


def test_anuncio_con_campos_opcionales_ausentes():
    """Se puede crear un anuncio con todos los campos opcionales ausentes."""
    anuncio = AnuncioInmobiliario(
        fuente="revolico",
        id_fuente=_nuevo_id(),
        url="https://www.revolico.com/item/casa-123",
        fecha_captura="2026-11-03T10:00:00Z",
        estado_parseo="ok",
    )

    assert anuncio.fuente == "revolico"
    assert anuncio.id_fuente is not None
    assert anuncio.url == "https://www.revolico.com/item/casa-123"
    assert anuncio.fecha_captura == "2026-11-03T10:00:00Z"
    assert anuncio.estado_parseo == "ok"

    # Campos opcionales deben ser None
    assert anuncio.precio is None
    assert anuncio.moneda is None
    assert anuncio.area_m2 is None
    assert anuncio.tipo_area is None
    assert anuncio.tipo_inmueble is None
    assert anuncio.municipio is None
    assert anuncio.titulo is None
    assert anuncio.descripcion is None
    assert anuncio.precio_usd is None
    assert anuncio.tasa_id is None


def test_anuncio_con_precio_y_moneda_originales():
    """Se puede crear un anuncio con precio y moneda originales."""
    anuncio = AnuncioInmobiliario(
        fuente="mambbu",
        id_fuente=_nuevo_id(),
        url="https://mambbu.com/propiedades/casa-456",
        fecha_captura="2026-11-03T10:00:00Z",
        precio=85000,
        moneda="USD",
        estado_parseo="ok",
    )

    assert anuncio.precio == 85000
    assert anuncio.moneda == "USD"


def test_anuncio_con_superficie_y_tipo_area():
    """Se puede crear un anuncio con superficie y tipo de área."""
    anuncio = AnuncioInmobiliario(
        fuente="gaos",
        id_fuente=_nuevo_id(),
        url="https://gaos.app/properties/abc-123",
        fecha_captura="2026-11-03T10:00:00Z",
        area_m2=120.0,
        tipo_area="construida",
        estado_parseo="ok",
    )

    assert anuncio.area_m2 == 120.0
    assert anuncio.tipo_area == "construida"


def test_valores_ausentes_permanecen_como_none():
    """Los valores ausentes permanecen como None."""
    anuncio = AnuncioInmobiliario(
        fuente="revolico",
        id_fuente=_nuevo_id(),
        url="https://www.revolico.com/item/casa-789",
        fecha_captura="2026-11-03T10:00:00Z",
        estado_parseo="error",
    )

    assert anuncio.precio is None
    assert anuncio.moneda is None
    assert anuncio.area_m2 is None
    assert anuncio.tipo_area is None
    assert anuncio.tipo_inmueble is None
    assert anuncio.tipo_operacion is None
    assert anuncio.municipio is None
    assert anuncio.provincia is None
    assert anuncio.titulo is None
    assert anuncio.descripcion is None
    assert anuncio.vendedor_tipo is None
    assert anuncio.precio_usd is None
    assert anuncio.tasa_conversion_usd is None
    assert anuncio.tasa_fecha is None
    assert anuncio.tasa_fuente is None
    assert anuncio.precio_m2_usd is None
    assert anuncio.tasa_id is None


def test_valores_proporcionados_se_conservan_correctamente():
    """Los valores proporcionados se conservan correctamente."""
    anuncio = AnuncioInmobiliario(
        fuente="mambbu",
        id_fuente=_nuevo_id(),
        url="https://mambbu.com/propiedades/casa-001",
        fecha_captura="2026-11-03T10:00:00Z",
        fecha_publicacion="2026-10-25",
        provincia="La Habana",
        municipio="Playa",
        reparto="Miramar",
        direccion_texto="Calle 20 # 123, entre 5ta y 7ma",
        tipo_operacion="venta",
        tipo_inmueble="casa",
        area_m2=150.5,
        tipo_area="total",
        habitaciones=3,
        banos=2,
        planta="planta baja",
        estado_conservacion="bueno",
        amueblado=True,
        precio=120000,
        moneda="USD",
        precio_usd=120000.0,
        tasa_conversion_usd=1.0,
        tasa_fecha="2026-11-03T08:00:00Z",
        tasa_fuente="bcc",
        precio_m2_usd=797.34,
        tasa_id="00000000-0000-4000-8000-000000000001",
        titulo="Casa en venta en Miramar",
        descripcion="Espaciosa casa de 3 habitaciones",
        vendedor_tipo="particular",
        estado_parseo="ok",
        notas_calidad=None,
        es_posible_duplicado=False,
        duplicado_grupo=None,
    )

    assert anuncio.fecha_publicacion == "2026-10-25"
    assert anuncio.provincia == "La Habana"
    assert anuncio.municipio == "Playa"
    assert anuncio.reparto == "Miramar"
    assert anuncio.direccion_texto == "Calle 20 # 123, entre 5ta y 7ma"
    assert anuncio.tipo_operacion == "venta"
    assert anuncio.tipo_inmueble == "casa"
    assert anuncio.area_m2 == 150.5
    assert anuncio.tipo_area == "total"
    assert anuncio.habitaciones == 3
    assert anuncio.banos == 2
    assert anuncio.planta == "planta baja"
    assert anuncio.estado_conservacion == "bueno"
    assert anuncio.amueblado is True
    assert anuncio.precio == 120000
    assert anuncio.moneda == "USD"
    assert anuncio.precio_usd == 120000.0
    assert anuncio.tasa_conversion_usd == 1.0
    assert anuncio.tasa_fecha == "2026-11-03T08:00:00Z"
    assert anuncio.tasa_fuente == "bcc"
    assert anuncio.precio_m2_usd == 797.34
    assert anuncio.tasa_id == "00000000-0000-4000-8000-000000000001"
    assert anuncio.titulo == "Casa en venta en Miramar"
    assert anuncio.descripcion == "Espaciosa casa de 3 habitaciones"
    assert anuncio.vendedor_tipo == "particular"
    assert anuncio.estado_parseo == "ok"
    assert anuncio.notas_calidad is None
    assert anuncio.es_posible_duplicado is False
    assert anuncio.duplicado_grupo is None
