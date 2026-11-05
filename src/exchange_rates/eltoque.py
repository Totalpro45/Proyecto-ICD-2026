"""Cliente para consultar la API de tasas de cambio de elTOQUE.

Utiliza el Edge Function de Supabase publicado por elTOQUE para obtener
cotizaciones del mercado informal de divisas en Cuba (TRMI).

Autenticación mediante clave API (rol `anon`) enviada como Bearer token.
La clave se lee de la variable de entorno ELTOQUE_API_TOKEN y nunca se
almacena en código ni se sube a GitHub.

No implementa captura diaria ni conversiones de precios de anuncios;
solo consulta y devuelve las cotizaciones tal como las publica elTOQUE.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

# URL base de la API de elTOQUE. Se puede sobrescribir con variable de entorno.
ELTOQUE_API_BASE_URL = os.environ.get(
    "ELTOQUE_API_BASE_URL", "https://tasas.eltoque.com"
)

# Endpoint de cotizaciones del mercado informal.
ELTOQUE_TRMI_ENDPOINT = f"{ELTOQUE_API_BASE_URL.rstrip('/')}/v1/trmi"

# Monedas que el proyecto rastrea. ElTOQUE las publica denominadas en CUP.
# Nota: elTOQUE puede publicar el euro con el código "ECU" en lugar de "EUR".
# Esta equivalencia no ha sido confirmada oficialmente por elTOQUE, por lo que
# no se realiza mapeo automático de ECU a EUR. Cada código se conserva tal cual
# se publica, y cualquier análisis posterior deberá verificar la equivalencia.
MONEDAS_OBJETIVO = {"USD", "EUR", "MLC"}


class ElToqueError(Exception):
    """Error genérico al consultar la API de elTOQUE."""


class ElToqueAuthError(ElToqueError):
    """Error de autenticación con la API de elTOQUE (clave inválida o ausente)."""


class ElToqueConnectionError(ElToqueError):
    """Error de conexión con la API de elTOQUE."""


def _obtener_api_token() -> str:
    """Lee la clave API de elTOQUE desde la variable de entorno.

    Devuelve la cadena de la clave o lanza ElToqueAuthError si no está
    configurada.
    """
    token = os.environ.get("ELTOQUE_API_TOKEN", "").strip()
    if not token:
        raise ElToqueAuthError(
            "Falta la variable de entorno ELTOQUE_API_TOKEN. "
            "Configúrala en un archivo .env (no subir a GitHub) o en el entorno."
        )
    return token


def _cabeceras(token: str) -> dict[str, str]:
    """Cabeceras de solicitud para la API de elTOQUE."""
    return {
        "User-Agent": "proyecto-icd-2026/1.0",
        "Accept": "application/json",
        "apikey": token,
        "Authorization": f"Bearer {token}",
    }


def _rango_horas_previas(horas: int = 23) -> tuple[str, str]:
    """Genera el par (date_from, date_to) para consultar las últimas horas.

    El endpoint /v1/trmi requiere un rango de tiempo menor a 24 horas y
    devuelve la cotización más reciente publicada dentro de ese rango.
    Se usa una ventana de 23 horas para respetar el límite del servidor
    y absorber posible desfase horario UTC/Cuba.

    Formato de wire: YYYY-MM-DD HH:MM:SS (URL-encoded por requests).
    """
    ahora = datetime.now(timezone.utc)
    desde = ahora - timedelta(hours=horas)

    fmt = "%Y-%m-%d %H:%M:%S"
    return desde.strftime(fmt), ahora.strftime(fmt)


def consultar_tasas() -> dict:
    """Consulta las cotizaciones del mercado informal de elTOQUE.

    Realiza una única petición GET a /v1/trmi con una ventana de 23 horas
    y devuelve el JSON tal como lo publica elTOQUE, sin modificar valores
    ni inventar tasas.

    Returns:
        Diccionario con la respuesta JSON de elTOQUE. Contiene al menos
        la clave "tasas" (mapeo de código de moneda a valor en CUP) y los
        campos de fecha/hora de la cotización.

    Raises:
        ElToqueAuthError: si falta o es inválida la clave API (HTTP 401).
        ElToqueConnectionError: si no se puede conectar o la respuesta no
            es JSON válido.
        ElToqueError: para cualquier otro error de la API.
    """
    token = _obtener_api_token()
    date_from, date_to = _rango_horas_previas()

    params = {"date_from": date_from, "date_to": date_to}

    try:
        respuesta = requests.get(
            ELTOQUE_TRMI_ENDPOINT,
            params=params,
            headers=_cabeceras(token),
            timeout=30,
        )
    except requests.RequestException as exc:
        raise ElToqueConnectionError(
            f"No se pudo conectar con la API de elTOQUE: {exc}"
        ) from exc

    if respuesta.status_code == 401:
        raise ElToqueAuthError(
            "Autenticación fallida con la API de elTOQUE (HTTP 401). "
            "Verifica que ELTOQUE_API_TOKEN sea correcta y esté activa."
        )

    if respuesta.status_code >= 400:
        raise ElToqueError(
            f"La API de elTOQUE respondió con error HTTP {respuesta.status_code}."
        )

    try:
        datos = respuesta.json()
    except ValueError as exc:
        raise ElToqueConnectionError(
            "La respuesta de elTOQUE no es JSON válido."
        ) from exc

    return datos


def extraer_cotizaciones(datos_api: dict) -> list[dict]:
    """Extrae las cotizaciones de interés desde la respuesta de elTOQUE.

    Solo se conservan las monedas que el proyecto rastrea (USD, EUR, MLC).
    Los valores se conservan tal como los publica elTOQUE (CUP por 1 unidad
    de moneda de origen), sin redondear ni convertir.

    Args:
        datos_api: Diccionario devuelto por consultar_tasas().

    Returns:
        Lista de diccionarios con claves:
        - moneda_origen: código de moneda (ej. "USD")
        - moneda_destino: siempre "CUP"
        - valor: número (CUP por 1 unidad de moneda_origen)
        - valor_texto_original: representación textual del valor original
        - fecha_publicacion: fecha/hora de la cotización según elTOQUE (ISO 8601)
        - valor_bruto: valor numérico tal como lo publica elTOQUE
    """
    tasas_raw = datos_api.get("tasas", {})
    if not isinstance(tasas_raw, dict):
        return []

    fecha_publicacion = _construir_fecha_publicacion(datos_api)

    cotizaciones = []
    for codigo_moneda, valor_raw in tasas_raw.items():
        moneda_normalizada = _normalizar_moneda_eltoque(codigo_moneda)
        if moneda_normalizada not in MONEDAS_OBJETIVO:
            continue

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

        cotizaciones.append(
            {
                "moneda_origen": moneda_normalizada,
                "moneda_destino": "CUP",
                "valor": valor,
                "valor_texto_original": str(valor_raw),
                "fecha_publicacion": fecha_publicacion,
                "valor_bruto": valor_raw,
            }
        )

    return cotizaciones


def _normalizar_moneda_eltoque(codigo: str) -> Optional[str]:
    """Normaliza un código de moneda de elTOQUE al formato canónico del proyecto.

    Los códigos se conservan tal cual los publica elTOQUE sin realizar
    conversiones ni asumir equivalencias. En particular, no se asume que
    "ECU" signifique euro; esa equivalencia no ha sido confirmada
    oficialmente por elTOQUE y cualquier interpretación queda pendiente de
    verificación.

    Args:
        codigo: Código de moneda tal como lo publica elTOQUE.

    Returns:
        El código normalizado (mayúsculas, sin espacios) si pertenece a las
        monedas objetivo, o None si no es una cadena o no pertenece.
    """
    if not isinstance(codigo, str):
        return None

    normalizado = codigo.strip().upper()

    if normalizado in MONEDAS_OBJETIVO:
        return normalizado

    return None


def _construir_fecha_publicacion(datos_api: dict) -> Optional[str]:
    """Construye la fecha de publicación desde los campos de elTOQUE.

    elTOQUE devuelve la fecha y hora por separado (date, hour, minutes,
    seconds). Se combinan en un único string ISO 8601. Si falta algún
    campo, se devuelve None (no se inventa fecha).
    """
    if not isinstance(datos_api, dict):
        return None

    fecha = datos_api.get("date")
    hora = datos_api.get("hour")
    minutos = datos_api.get("minutes")
    segundos = datos_api.get("seconds")

    if fecha is None or hora is None:
        return None

    try:
        partes = [str(fecha), str(hora).zfill(2)]
        if minutos is not None:
            partes.append(str(minutos).zfill(2))
        if segundos is not None:
            partes.append(str(segundos).zfill(2))

        fecha_hora = "T".join(partes[:2])
        if len(partes) > 2:
            fecha_hora += ":" + partes[2]
        if len(partes) > 3:
            fecha_hora += ":" + partes[3]

        # Validar que sea una fecha ISO 8601 interpretable.
        datetime.fromisoformat(fecha_hora)
        return fecha_hora
    except (ValueError, TypeError):
        return None
