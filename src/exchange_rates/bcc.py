"""Cliente para consultar la API oficial de tasas de cambio del BCC.

Utiliza el endpoint público del Banco Central de Cuba para obtener
las tasas de cambio oficiales, segmento III («Tasa Población y FGNE»).

No implementa captura diaria ni conversiones de precios de anuncios;
solo consulta y devuelve las cotizaciones tal como las publica el BCC.

Cada cotización devuelta incluye los metadatos de procedencia:
`fuente = "bcc"`, `categoria = "oficial"` y `segmento = "III"`.

La API del BCC no requiere autenticación.
"""

from __future__ import annotations

from typing import Optional

import requests

# Endpoint oficial de tasas activas del BCC.
BCC_API_URL = "https://api.bc.gob.cu/v1/tasas-de-cambio/activas"

# URL de la fuente, usada en el campo url_fuente de cada cotización.
BCC_URL_FUENTE = BCC_API_URL

# Identificadores de procedencia para las cotizaciones del BCC.
BCC_FUENTE = "bcc"
BCC_CATEGORIA = "oficial"
BCC_SEGMENTO = "III"

# Tipo de tasa utilizado: el BCC publica tres tasas por moneda
# (tasaOficial, tasaPublica, tasaEspecial). Este extractor usa exclusivamente
# tasaEspecial, que corresponde al Segmento III.
BCC_TIPO_TASA = "tasa_especial"

# Campo de la respuesta del BCC que contiene el valor del Segmento III.
BCC_CAMPO_VALOR = "tasaEspecial"

# Monedas que el proyecto rastrea y que están disponibles en la API del BCC.
# La API publica 13 monedas; MLC no está entre ellas.
MONEDAS_OBJETIVO = {"AUD", "CAD", "CHF", "CNY", "DKK", "EUR", "GBP", "JPY", "MXN", "NOK", "RUB", "SEK", "USD"}


class BccError(Exception):
    """Error genérico al consultar la API del BCC."""


class BccConnectionError(BccError):
    """Error de conexión con la API del BCC."""


class BccStructureError(BccError):
    """La respuesta de la API del BCC no tiene la estructura esperada."""


def consultar_tasas() -> dict:
    """Consulta las tasas de cambio activas del BCC.

    Realiza una única petición GET al endpoint de tasas activas
    y devuelve el JSON tal como lo publica el BCC, sin modificar valores
    ni inventar tasas.

    Returns:
        Diccionario con la respuesta JSON del BCC. Contiene al menos
        la clave "tasas" (lista de registros con tasas por moneda) y los
        campos de fecha de la cotización.

    Raises:
        BccConnectionError: si no se puede conectar o la respuesta no
            es JSON válido.
        BccStructureError: si la respuesta no tiene la estructura esperada
            (falta la clave "tasas" o no es una lista).
        BccError: para cualquier otro error de la API (HTTP >= 400).
    """
    try:
        respuesta = requests.get(BCC_API_URL, timeout=30)
    except requests.RequestException as exc:
        raise BccConnectionError(
            f"No se pudo conectar con la API del BCC: {exc}"
        ) from exc

    if respuesta.status_code >= 400:
        raise BccError(
            f"La API del BCC respondió con error HTTP {respuesta.status_code}."
        )

    try:
        datos = respuesta.json()
    except ValueError as exc:
        raise BccConnectionError(
            "La respuesta del BCC no es JSON válido."
        ) from exc

    if not isinstance(datos, dict):
        raise BccStructureError(
            "La respuesta del BCC no es un objeto JSON."
        )

    tasas = datos.get("tasas")
    if not isinstance(tasas, list):
        raise BccStructureError(
            "La clave 'tasas' de la respuesta del BCC no es una lista."
        )

    return datos


def extraer_cotizaciones(datos_api: dict) -> list[dict]:
    """Extrae las cotizaciones del Segmento III desde la respuesta del BCC.

    Solo se conservan las monedas que el proyecto rastrea y que están
    disponibles en la API del BCC. Se utiliza exclusivamente el campo
    `tasaEspecial` (Segmento III). No se extraen `tasaOficial` ni
    `tasaPublica`, y no se genera cotización para MLC (no publicada
    por el BCC).

    Cada cotización incluye los metadatos de procedencia:
    `fuente = "bcc"`, `categoria = "oficial"`, `segmento = "III"`.

    Args:
        datos_api: Diccionario devuelto por consultar_tasas().

    Returns:
        Lista de diccionarios con claves:
        - moneda_origen: código de moneda (ej. "USD")
        - moneda_destino: siempre "CUP"
        - valor: número (CUP por 1 unidad de moneda_origen, desde tasaEspecial)
        - valor_texto_original: representación textual del valor original
        - fecha_publicacion: fecha de la cotización según el BCC (fechaDia, ISO 8601)
        - fuente: siempre "bcc"
        - categoria: siempre "oficial"
        - segmento: siempre "III"
        - url_fuente: endpoint del BCC consultado
        - tipo_tasa: siempre "tasa_especial"
    """
    if not isinstance(datos_api, dict):
        return []

    tasas_raw = datos_api.get("tasas", [])
    if not isinstance(tasas_raw, list):
        return []

    cotizaciones = []
    for entrada in tasas_raw:
        if not isinstance(entrada, dict):
            continue

        codigo_moneda = entrada.get("codigoMoneda")
        if not isinstance(codigo_moneda, str):
            continue

        codigo_normalizado = codigo_moneda.strip().upper()
        if codigo_normalizado not in MONEDAS_OBJETIVO:
            continue

        valor_raw = entrada.get(BCC_CAMPO_VALOR)
        if valor_raw is None:
            # Valor ausente: no se inventa, se omite.
            continue

        try:
            valor = float(valor_raw)
        except (TypeError, ValueError):
            # Valor no numérico: no se puede interpretar con seguridad.
            continue

        if valor <= 0:
            # Valor inválido: no se conserva.
            continue

        fecha_publicacion = entrada.get("fechaDia")
        if fecha_publicacion is not None:
            fecha_publicacion = str(fecha_publicacion)

        cotizaciones.append(
            {
                "moneda_origen": codigo_normalizado,
                "moneda_destino": "CUP",
                "valor": valor,
                "valor_texto_original": str(valor_raw),
                "fecha_publicacion": fecha_publicacion,
                "fuente": BCC_FUENTE,
                "categoria": BCC_CATEGORIA,
                "segmento": BCC_SEGMENTO,
                "url_fuente": BCC_URL_FUENTE,
                "tipo_tasa": BCC_TIPO_TASA,
            }
        )

    return cotizaciones