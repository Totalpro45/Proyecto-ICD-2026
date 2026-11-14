"""Extractor de anuncios inmobiliarios de Revolico.

Extrae anuncios de venta de casas en La Habana desde el portal de Revolico.
No recopila datos personales de vendedores (nombres, teléfonos, WhatsApp).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from data.almacenamiento_anuncios import (
    RUTA_CRUDO_DEFECTO,
    RUTA_PROCESADO_DEFECTO,
    guardar_captura_completa,
)
from data.models import AnuncioInmobiliario
from data.normalization import (
    identificar_municipio_en_titulo_revolico,
)

# URL pública de GAOS para anuncios de venta de casas en La Habana.
REVOLICO_URL = (
    "https://www.revolico.com/search"
    "?category=inmobiliaria"
    "&province=la-habana"
    "&subcategory=inmobiliaria-casas"
)

# Rutas por defecto para almacenamiento de capturas de Revolico.
RUTA_CRUDO_DEFECTO_REVOLICO = Path("data/raw/anuncios/revolico/crudo")
RUTA_PROCESADO_DEFECTO_REVOLICO = Path("data/processed/anuncios/revolico")


def _cabeceras() -> dict[str, str]:
    """Cabeceras de solicitud para la página de Revolico."""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
    }


def extraer_listings_revolico() -> list[dict]:
    """Extrae anuncios crudos de Revolico (primera página de venta de casas).

    Realiza una petición HTTP GET al portal de Revolico y devuelve una lista
    de diccionarios con los datos crudos de cada anuncio encontrado.

    Returns:
        Lista de diccionarios con los datos crudos de Revolico. Cada diccionario
        contiene:
            - id_fuente: identificador numérico extraído de la URL del anuncio.
            - url: URL completa del anuncio.
            - precio: importe numérico o None si no se pudo interpretar.
            - moneda: código de moneda (USD, EUR, etc.) o None si no se pudo
              interpretar.
            - titulo: título del anuncio (texto restante tras quitar precio y
              moneda).
            - descripcion: None (no se puede separar de forma fiable).

    Raises:
        OSError: Si la petición HTTP falla o devuelve un código de error.
    """
    r = requests.get(REVOLICO_URL, headers=_cabeceras(), timeout=30)
    if r.status_code != 200:
        raise OSError(
            f"Error al consultar Revolico: {r.status_code} {r.reason}"
        )

    soup = BeautifulSoup(r.text, "html.parser")

    anuncios: list[dict] = []
    for enlace in soup.find_all("a", href=True):
        href = enlace.get("href", "")
        if not href or "/item/" not in href or "publish" in href:
            continue

        # Extraer el ID numérico de la URL: /item/<slug>-<id>
        match_id = re.search(r"/item/.*-(\d+)", href)
        if not match_id:
            continue
        id_fuente = match_id.group(1)

        # Extraer precio y moneda del texto del enlace
        texto = enlace.get_text(strip=True)
        m_precio = re.search(r"([\d.,]+)\s*(USD|EUR|CUP|MLC)", texto)
        if m_precio:
            precio_str = m_precio.group(1)
            moneda = m_precio.group(2)

            # Eliminar separadores de miles y convertir a número
            try:
                precio = float(precio_str.replace(",", "").replace(".", ""))
            except ValueError:
                precio = None
                moneda = None
        else:
            precio = None
            moneda = None

        # El título es el texto restante después de quitar precio y moneda
        texto_sin_precio = re.sub(
            r"^[\d.,]+\s*(USD|EUR|CUP|MLC)\s*", "", texto
        ).strip()

        anuncios.append(
            {
                "id_fuente": id_fuente,
                "url": f"https://www.revolico.com{href}",
                "precio": precio,
                "moneda": moneda,
                "titulo": texto_sin_precio,
                "descripcion": None,
            }
        )

    return anuncios


def _clasificar_tipo_inmueble(titulo: str | None) -> str:
    """Clasifica el tipo de inmueble a partir del título del anuncio.

    La clasificación se basa exclusivamente en el texto del título y
    distingue cuatro categorías:

    - ``casa``: la palabra completa ``casa`` aparece en el título.
    - ``apartamento``: aparecen palabras completas como ``apartamento``,
      ``apto`` o ``apt``.
    - ``no_vivienda``: el título indica claramente un producto o servicio
      que no es una vivienda (esmalte sintético, tanques de agua, servicios
      de gestión inmobiliaria, etc.).
    - ``indeterminado``: el título no permite identificar con suficiente
      seguridad el tipo de inmueble.

    Se ignoran mayúsculas, minúsculas y acentos. Se utilizan límites de
    palabra para evitar falsos positivos (por ejemplo, no se confunde
    ``casa`` con ``casero`` ni ``apto`` con otras palabras).

    Args:
        titulo: Título del anuncio, o None si no hay título.

    Returns:
        Una de las cadenas ``casa``, ``apartamento``, ``no_vivienda`` o
        ``indeterminado``.
    """
    if not titulo:
        return "indeterminado"

    texto = titulo.lower()

    # Palabras completas que indican apartamento (se evalúan primero para
    # evitar que una palabra secundaria clasifique un inmueble como
    # no_vivienda).
    patrones_apartamento = [
        r"\bapartamento\b",
        r"\bapto\b",
        r"\bapt\b",
    ]

    for patron in patrones_apartamento:
        if re.search(patron, texto):
            return "apartamento"

    # Palabra completa que indica casa.
    if re.search(r"\bcasa\b", texto):
        return "casa"

    # Expresiones que indican claramente un producto o servicio no inmobiliario.
    # Se evalúan tras vivienda para evitar falsos positivos cuando el título
    # menciona una palabra secundaria (por ejemplo, "casa con tanque de agua"
    # sigue siendo una casa).
    patrones_no_vivienda = [
        r"\besmlate\b",
        r"\besmalte\b",
        r"\btanques\s+de\s+agua\b",
        r"\bgestionamos\b",
        r"\bll[aá]manos\b",
        r"\basesor[ií]a\s+inmobiliaria\b",
        r"\bcorredora\b",
    ]

    for patron in patrones_no_vivienda:
        if re.search(patron, texto):
            return "no_vivienda"

    return "indeterminado"


def mapear_anuncio_revolico(dato: dict, fecha_captura: str) -> AnuncioInmobiliario:
    """Mapea un anuncio crudo de Revolico al esquema común.

    Args:
        dato: Diccionario con datos crudos de Revolico (claves: id_fuente,
            url, precio, moneda, titulo, descripcion).
        fecha_captura: Fecha y hora de captura en formato ISO 8601.

    Returns:
        Un objeto AnuncioInmobiliario mapeado al esquema común.
    """
    return AnuncioInmobiliario(
        fuente="revolico",
        id_fuente=dato.get("id_fuente", ""),
        url=dato.get("url", ""),
        fecha_captura=fecha_captura,
        fecha_publicacion=None,
        fecha_actualizacion=None,
        provincia="La Habana",
        municipio=identificar_municipio_en_titulo_revolico(dato.get("titulo")),
        reparto=None,
        direccion_texto=None,
        tipo_operacion="venta",
        tipo_inmueble=_clasificar_tipo_inmueble(dato.get("titulo")),
        area_m2=None,
        tipo_area=None,
        habitaciones=None,
        banos=None,
        planta=None,
        estado_conservacion=None,
        amueblado=None,
        precio=dato.get("precio"),
        moneda=dato.get("moneda"),
        precio_usd=None,
        tasa_conversion_usd=None,
        tasa_fecha=None,
        tasa_fuente=None,
        precio_m2_usd=None,
        tasa_id=None,
        titulo=dato.get("titulo"),
        descripcion=dato.get("descripcion"),
        vendedor_tipo=None,
        estado_parseo="ok",
        notas_calidad=None,
        es_posible_duplicado=False,
        duplicado_grupo=None,
    )


def capturar_y_guardar_revolico(
    ruta_crudo: Path | None = None,
    ruta_procesado: Path | None = None,
) -> str | None:
    """Captura anuncios de Revolico y los guarda crudos y procesados.

    El flujo es:
    1. Consultar Revolico una sola vez (extraer_listings_revolico).
    2. Si la extracción falla o no devuelve datos, informar y no guardar nada.
    3. Pasar los datos crudos a guardar_captura_completa, que los mapea
       internamente y guarda ambos archivos con el mismo id_captura.
    4. Informar cuántos anuncios se obtuvieron y dónde se guardó la captura.

    Args:
        ruta_crudo: carpeta destino para los crudos (opcional).
        ruta_procesado: carpeta destino para los procesados (opcional).

    Returns:
        El id_captura asignado a esta ejecución, o None si no se guardó nada.
    """
    crudos = extraer_listings_revolico()

    if not crudos:
        print(
            "No se obtuvieron anuncios de Revolico. No se guardó ninguna captura."
        )
        return None

    return guardar_captura_completa(
        crudos,
        ruta_crudo=ruta_crudo or RUTA_CRUDO_DEFECTO_REVOLICO,
        ruta_procesado=ruta_procesado or RUTA_PROCESADO_DEFECTO_REVOLICO,
        mapear_func=mapear_anuncio_revolico,
        prefijo_archivo="revolico",
        fuente="revolico",
        url_fuente=REVOLICO_URL,
    )


if __name__ == "__main__":
    capturar_y_guardar_revolico()
