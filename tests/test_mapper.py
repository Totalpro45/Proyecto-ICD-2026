"""Pruebas para crear_anuncio.

Comprueba el mapeo de un diccionario de datos a `AnuncioInmobiliario`,
incluido un anuncio completo y otro con datos incompletos.
"""

import sys

sys.path.insert(0, "src")

from data.mapper import crear_anuncio


def test_crear_anuncio_completo():
    """Un anuncio con todos los campos se mapea correctamente."""
    datos = {
        "fuente": "mambbu",
        "id_fuente": "casa-miramar-001",
        "url": "https://mambbu.com/propiedades/casa-miramar-001",
        "fecha_captura": "2026-11-03T10:00:00Z",
        "fecha_publicacion": "2026-10-25",
        "provincia": "La Habana",
        "municipio": "PLAYA",
        "reparto": "Miramar",
        "direccion_texto": "Calle 20 # 123",
        "tipo_operacion": "VENTA",
        "tipo_inmueble": "casa",
        "area_m2": 150.5,
        "tipo_area": "construida",
        "habitaciones": 3,
        "banos": 2,
        "planta": "planta baja",
        "estado_conservacion": "buen estado",
        "amueblado": "sí",
        "precio": 120000,
        "moneda": "USD",
        "titulo": "Casa en Miramar",
        "descripcion": "Espaciosa casa de 3 habitaciones",
        "vendedor_tipo": "particular",
        "estado_parseo": "ok",
        "notas_calidad": None,
        "es_posible_duplicado": False,
        "duplicado_grupo": None,
    }

    anuncio = crear_anuncio(datos)

    assert anuncio.fuente == "mambbu"
    assert anuncio.id_fuente == "casa-miramar-001"
    assert anuncio.url == "https://mambbu.com/propiedades/casa-miramar-001"
    assert anuncio.fecha_captura == "2026-11-03T10:00:00Z"
    assert anuncio.fecha_publicacion == "2026-10-25"
    assert anuncio.provincia == "La Habana"
    assert anuncio.municipio == "Playa"
    assert anuncio.reparto == "Miramar"
    assert anuncio.direccion_texto == "Calle 20 # 123"
    assert anuncio.tipo_operacion == "venta"
    assert anuncio.tipo_inmueble == "casa"
    assert anuncio.area_m2 == 150.5
    assert anuncio.tipo_area == "construida"
    assert anuncio.habitaciones == 3
    assert anuncio.banos == 2
    assert anuncio.planta == "planta baja"
    assert anuncio.estado_conservacion == "bueno"
    assert anuncio.amueblado is True
    assert anuncio.precio == 120000
    assert anuncio.moneda == "USD"
    assert anuncio.titulo == "Casa en Miramar"
    assert anuncio.descripcion == "Espaciosa casa de 3 habitaciones"
    assert anuncio.vendedor_tipo == "particular"
    assert anuncio.estado_parseo == "ok"
    assert anuncio.notas_calidad is None
    assert anuncio.es_posible_duplicado is False
    assert anuncio.duplicado_grupo is None

    # Campos de conversión deben quedar vacíos (sin tasas todavía)
    assert anuncio.precio_usd is None
    assert anuncio.tasa_conversion_usd is None
    assert anuncio.tasa_fecha is None
    assert anuncio.tasa_fuente is None
    assert anuncio.precio_m2_usd is None
    assert anuncio.tasa_id is None


def test_crear_anuncio_incompleto():
    """Un anuncio con solo los campos obligatorios se crea con None en el resto."""
    datos = {
        "fuente": "revolico",
        "id_fuente": "12345",
        "url": "https://www.revolico.com/item/casa-12345",
        "fecha_captura": "2026-11-03T10:00:00Z",
    }

    anuncio = crear_anuncio(datos)

    assert anuncio.fuente == "revolico"
    assert anuncio.id_fuente == "12345"
    assert anuncio.url == "https://www.revolico.com/item/casa-12345"
    assert anuncio.fecha_captura == "2026-11-03T10:00:00Z"

    # Todos los campos opcionales deben ser None o sus valores por defecto
    assert anuncio.precio is None
    assert anuncio.moneda is None
    assert anuncio.area_m2 is None
    assert anuncio.tipo_area is None
    assert anuncio.tipo_inmueble is None
    assert anuncio.municipio is None
    assert anuncio.titulo is None
    assert anuncio.precio_usd is None
    assert anuncio.tasa_id is None
    assert anuncio.estado_parseo == "ok"
    assert anuncio.es_posible_duplicado is False


def test_crear_anuncio_normaliza_campos():
    """La función aplica normalización a los campos correspondientes."""
    datos = {
        "fuente": "gaos",
        "id_fuente": "uuid-123",
        "url": "https://gaos.app/properties/uuid-123",
        "fecha_captura": "2026-11-03T10:00:00Z",
        "municipio": "  Centro Habana  ",
        "tipo_operacion": "Alquiler",
        "tipo_inmueble": "APTO.",
        "tipo_area": "área total",
        "estado_conservacion": "necesita reparación",
        "amueblado": "sin amueblar",
        "moneda": "  cup  ",
    }

    anuncio = crear_anuncio(datos)

    assert anuncio.municipio == "Centro Habana"
    assert anuncio.tipo_operacion == "alquiler"
    assert anuncio.tipo_inmueble == "apartamento"
    assert anuncio.tipo_area == "total"
    assert anuncio.estado_conservacion == "a_reparar"
    assert anuncio.amueblado is False
    assert anuncio.moneda == "CUP"


def test_crear_anuncio_campo_obligatorio_ausente():
    """Falta un campo obligatorio → ValueError."""
    datos = {
        "fuente": "revolico",
        "id_fuente": "12345",
        # falta url y fecha_captura
    }

    try:
        crear_anuncio(datos)
        assert False, "debería haber lanzado ValueError"
    except ValueError as e:
        assert "url" in str(e) or "fecha_captura" in str(e)


def test_crear_anuncio_no_es_dict():
    """Entrada no diccionario → ValueError."""
    try:
        crear_anuncio("no soy un diccionario")
        assert False, "debería haber lanzado ValueError"
    except ValueError:
        pass
