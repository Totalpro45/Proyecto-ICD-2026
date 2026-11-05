"""Extracción de datos de páginas de Revolico.

Por ahora solo localiza el bloque `__NEXT_DATA__` de Next.js y devuelve su
contenido como diccionario. No realiza peticiones HTTP ni extrae anuncios.
"""

import json

from bs4 import BeautifulSoup


def extraer_datos_pagina(html):
    """Extrae el JSON del bloque `__NEXT_DATA__` de una página de Revolico.

    Args:
        html: Cadena con el HTML de la página.

    Returns:
        Diccionario con los datos de `__NEXT_DATA__`, o None si el bloque no
        existe o su contenido no es JSON válido.
    """
    if not isinstance(html, str) or not html.strip():
        return None

    soup = BeautifulSoup(html, "lxml")
    script = soup.find("script", id="__NEXT_DATA__")

    if script is None:
        return None

    contenido = script.string or script.get_text()
    if not contenido or not contenido.strip():
        return None

    try:
        return json.loads(contenido)
    except (json.JSONDecodeError, ValueError):
        return None


def inspeccionar_estructura(datos):
    """Inspecciona la estructura del diccionario `__NEXT_DATA__`.

    Devuelve un resumen con las claves principales, la estructura de `props`,
    `pageProps` si existe, y posibles listas de anuncios con sus rutas y
    cantidad de elementos. No extrae ni transforma anuncios.

    Args:
        datos: Diccionario con los datos de `__NEXT_DATA__`.

    Returns:
        Diccionario con el resumen de la estructura.
    """
    if not isinstance(datos, dict):
        return {"error": "datos no es un diccionario"}

    resumen = {
        "claves_principales": list(datos.keys()),
        "tiene_props": "props" in datos,
        "claves_props": [],
        "tiene_pageprops": False,
        "claves_pageprops": [],
        "posibles_listas_anuncios": [],
        "observaciones": [],
    }

    def _buscar_listas(obj, ruta_actual=""):
        if isinstance(obj, dict):
            for clave, valor in obj.items():
                nueva_ruta = f"{ruta_actual}.{clave}" if ruta_actual else clave
                if isinstance(valor, list):
                    resumen["posibles_listas_anuncios"].append(
                        {
                            "ruta": nueva_ruta,
                            "tipo": "list",
                            "cantidad": len(valor),
                            "tipo_elementos": type(valor[0]).__name__
                            if valor
                            else None,
                        }
                    )
                elif isinstance(valor, dict):
                    _buscar_listas(valor, nueva_ruta)

    # Inspeccionar props y pageProps
    if "props" in datos and isinstance(datos["props"], dict):
        resumen["claves_props"] = list(datos["props"].keys())

        if "pageProps" in datos["props"] and isinstance(
            datos["props"]["pageProps"], dict
        ):
            resumen["tiene_pageprops"] = True
            resumen["claves_pageprops"] = list(
                datos["props"]["pageProps"].keys()
            )

    _buscar_listas(datos)

    if not resumen["posibles_listas_anuncios"]:
        resumen["observaciones"].append(
            "No se encontraron listas en la estructura. Sin un JSON real de Revolico "
            "no se puede confirmar dónde están los anuncios."
        )
    else:
        resumen["observaciones"].append(
            "Las listas encontradas son candidatos a anuncios. Se requiere un JSON real "
            "de Revolico para confirmar cuál contiene los anuncios inmobiliarios."
        )

    return resumen
