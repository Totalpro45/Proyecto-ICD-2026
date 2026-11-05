"""Pruebas para extraer_datos_pagina de Revolico.

Comprueba JSON válido, ausencia del bloque y JSON inválido.
"""

import sys

sys.path.insert(0, "src")

from sources.revolico import extraer_datos_pagina, inspeccionar_estructura


def test_json_valido():
    """Bloque __NEXT_DATA__ con JSON válido devuelve el diccionario."""
    html = (
        '<html><head></head><body>'
        '<script id="__NEXT_DATA__" type="application/json">'
        '{"props":{"pageProps":{"foo":"bar"}},"page":"/"}'
        '</script>'
        '</body></html>'
    )

    resultado = extraer_datos_pagina(html)

    assert isinstance(resultado, dict)
    assert resultado["props"]["pageProps"]["foo"] == "bar"


def test_bloque_ausente_devuelve_none():
    """Sin bloque __NEXT_DATA__ devuelve None."""
    html = '<html><head></head><body><p>contenido sin datos</p></body></html>'

    assert extraer_datos_pagina(html) is None


def test_json_invalido_devuelve_none():
    """Bloque __NEXT_DATA__ con contenido no JSON devuelve None."""
    html = (
        '<html><head></head><body>'
        '<script id="__NEXT_DATA__" type="application/json">'
        '{no es json válido}'
        '</script>'
        '</body></html>'
    )

    assert extraer_datos_pagina(html) is None


def test_texto_vacio_devuelve_none():
    """HTML vacío o None devuelve None."""
    assert extraer_datos_pagina("") is None
    assert extraer_datos_pagina("   ") is None


def test_script_sin_contenido_devuelve_none():
    """Bloque __NEXT_DATA__ vacío devuelve None."""
    html = (
        '<html><head></head><body>'
        '<script id="__NEXT_DATA__" type="application/json"></script>'
        '</body></html>'
    )

    assert extraer_datos_pagina(html) is None


# --- Pruebas para inspeccionar_estructura ---


def test_inspeccionar_estructura_json_pequeno():
    """Inspección de un JSON pequeño devuelve claves y listas detectadas."""
    datos = {
        "page": "/search",
        "props": {
            "pageProps": {
                "resultados": [
                    {"id": 1, "titulo": "Casa en venta"},
                    {"id": 2, "titulo": "Apartamento en alquiler"},
                ],
                "filtros": {"precio_min": 50000},
            }
        },
    }

    resumen = inspeccionar_estructura(datos)

    assert "page" in resumen["claves_principales"]
    assert "props" in resumen["claves_principales"]
    assert resumen["tiene_props"] is True
    assert resumen["tiene_pageprops"] is True
    assert "resultados" in resumen["claves_pageprops"]
    assert "filtros" in resumen["claves_pageprops"]

    lista_resultados = [l for l in resumen["posibles_listas_anuncios"] if l["ruta"] == "props.pageProps.resultados"]
    assert len(lista_resultados) == 1
    assert lista_resultados[0]["cantidad"] == 2
    assert lista_resultados[0]["tipo_elementos"] == "dict"


def test_inspeccionar_estructura_sin_listas():
    """JSON sin listas indica que no se encontraron listas."""
    datos = {"page": "/", "props": {"pageProps": {"foo": "bar"}}}

    resumen = inspeccionar_estructura(datos)

    assert resumen["posibles_listas_anuncios"] == []
    assert any("no se puede confirmar" in o for o in resumen["observaciones"])


def test_inspeccionar_estructura_no_es_dict():
    """Entrada que no es diccionario devuelve error."""
    resumen = inspeccionar_estructura("no soy un diccionario")
    assert "error" in resumen
    assert resumen["error"] == "datos no es un diccionario"

    resumen = inspeccionar_estructura(None)
    assert "error" in resumen

    resumen = inspeccionar_estructura([1, 2, 3])
    assert "error" in resumen


def test_inspeccionar_estructura_listas_en_niveles_profundos():
    """Detecta listas anidadas en rutas profundas."""
    datos = {
        "props": {
            "pageProps": {
                "data": {
                    "items": [{"a": 1}, {"a": 2}, {"a": 3}],
                    "meta": {"total": 3},
                }
            }
        }
    }

    resumen = inspeccionar_estructura(datos)

    lista_items = [l for l in resumen["posibles_listas_anuncios"] if l["ruta"] == "props.pageProps.data.items"]
    assert len(lista_items) == 1
    assert lista_items[0]["cantidad"] == 3
    assert lista_items[0]["tipo_elementos"] == "dict"
