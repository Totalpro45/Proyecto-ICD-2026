"""Pruebas para el extractor de tasas de cambio del BCC.

Utiliza datos de ejemplo basados en la estructura real de la respuesta de
la API del BCC. No realiza peticiones HTTP reales (usa mocks).
"""

import sys
from unittest.mock import patch

sys.path.insert(0, "src")

from exchange_rates import bcc


# --- Datos de ejemplo basados en la respuesta real de la API del BCC ---

DATOS_API_EJEMPLO = {
    "tasas": [
        {
            "_id": "6af93c504f2c1bb5dd9c2ea9",
            "codigoMoneda": "USD",
            "fechaDia": "2026-11-15T00:00:00.000Z",
            "nombreMoneda": "DOLAR NORTEAMERICANO",
            "tasaEspecial": 832,
            "tasaOficial": 24,
            "tasaPublica": 120,
            "estado": "ACTIVA",
        },
        {
            "_id": "6af93c504f2c1bb5dd9c2ea2",
            "codigoMoneda": "EUR",
            "fechaDia": "2026-11-15T00:00:00.000Z",
            "nombreMoneda": "EURO",
            "tasaEspecial": 920.2752,
            "tasaOficial": 26.5464,
            "tasaPublica": 132.732,
            "estado": "ACTIVA",
        },
        {
            "_id": "6af93c504f2c1bb5dd9c2e9e",
            "codigoMoneda": "CAD",
            "fechaDia": "2026-11-15T00:00:00.000Z",
            "nombreMoneda": "DOLAR CANADIENSE",
            "tasaEspecial": 583.30704,
            "tasaOficial": 16.82616,
            "tasaPublica": 84.13082,
            "estado": "ACTIVA",
        },
    ],
    "fechaDia": "2026-11-15T00:00:00.000Z",
    "fechaHoy": "2026-11-15T00:00:00.000Z",
}

DATOS_API_TASAS_VACIAS = {
    "tasas": [],
    "fechaDia": "2026-11-15T00:00:00.000Z",
    "fechaHoy": "2026-11-15T00:00:00.000Z",
}

DATOS_API_SIN_TASAS = {
    "fechaDia": "2026-11-15T00:00:00.000Z",
    "fechaHoy": "2026-11-15T00:00:00.000Z",
}

DATOS_API_TASAS_NO_LISTA = {
    "tasas": "no es una lista",
    "fechaDia": "2026-11-15T00:00:00.000Z",
    "fechaHoy": "2026-11-15T00:00:00.000Z",
}

DATOS_API_VALOR_NULO = {
    "tasas": [
        {
            "codigoMoneda": "USD",
            "fechaDia": "2026-11-15T00:00:00.000Z",
            "nombreMoneda": "DOLAR NORTEAMERICANO",
            "tasaEspecial": None,
            "tasaOficial": 24,
            "tasaPublica": 120,
            "estado": "ACTIVA",
        },
        {
            "codigoMoneda": "EUR",
            "fechaDia": "2026-11-15T00:00:00.000Z",
            "nombreMoneda": "EURO",
            "tasaEspecial": 920.2752,
            "tasaOficial": 26.5464,
            "tasaPublica": 132.732,
            "estado": "ACTIVA",
        },
    ],
    "fechaDia": "2026-11-15T00:00:00.000Z",
    "fechaHoy": "2026-11-15T00:00:00.000Z",
}

DATOS_API_VALOR_NO_NUMERICO = {
    "tasas": [
        {
            "codigoMoneda": "USD",
            "fechaDia": "2026-11-15T00:00:00.000Z",
            "nombreMoneda": "DOLAR NORTEAMERICANO",
            "tasaEspecial": "no_es_numero",
            "tasaOficial": 24,
            "tasaPublica": 120,
            "estado": "ACTIVA",
        },
        {
            "codigoMoneda": "EUR",
            "fechaDia": "2026-11-15T00:00:00.000Z",
            "nombreMoneda": "EURO",
            "tasaEspecial": 920.2752,
            "tasaOficial": 26.5464,
            "tasaPublica": 132.732,
            "estado": "ACTIVA",
        },
    ],
    "fechaDia": "2026-11-15T00:00:00.000Z",
    "fechaHoy": "2026-11-15T00:00:00.000Z",
}

DATOS_API_VALOR_CERO = {
    "tasas": [
        {
            "codigoMoneda": "USD",
            "fechaDia": "2026-11-15T00:00:00.000Z",
            "nombreMoneda": "DOLAR NORTEAMERICANO",
            "tasaEspecial": 0,
            "tasaOficial": 24,
            "tasaPublica": 120,
            "estado": "ACTIVA",
        },
        {
            "codigoMoneda": "EUR",
            "fechaDia": "2026-11-15T00:00:00.000Z",
            "nombreMoneda": "EURO",
            "tasaEspecial": 920.2752,
            "tasaOficial": 26.5464,
            "tasaPublica": 132.732,
            "estado": "ACTIVA",
        },
    ],
    "fechaDia": "2026-11-15T00:00:00.000Z",
    "fechaHoy": "2026-11-15T00:00:00.000Z",
}

DATOS_API_SIN_CODIGO_MONEDA = {
    "tasas": [
        {
            "fechaDia": "2026-11-15T00:00:00.000Z",
            "nombreMoneda": "DOLAR NORTEAMERICANO",
            "tasaEspecial": 832,
            "tasaOficial": 24,
            "tasaPublica": 120,
            "estado": "ACTIVA",
        },
    ],
    "fechaDia": "2026-11-15T00:00:00.000Z",
    "fechaHoy": "2026-11-15T00:00:00.000Z",
}


# --- Pruebas de consultar_tasas con mock ---

def test_consultar_tasas_exito():
    """consultar_tasas devuelve el JSON del BCC cuando la petición tiene éxito."""
    with patch("exchange_rates.bcc.requests.get") as mock_get:
        mock_respuesta = mock_get.return_value
        mock_respuesta.status_code = 200
        mock_respuesta.json.return_value = DATOS_API_EJEMPLO

        resultado = bcc.consultar_tasas()

        assert isinstance(resultado, dict)
        assert "tasas" in resultado
        assert len(resultado["tasas"]) == 3
        assert resultado["tasas"][0]["codigoMoneda"] == "USD"

        # Verificar que se usó el endpoint correcto
        args, kwargs = mock_get.call_args
        assert "api.bc.gob.cu" in args[0]
        assert kwargs["timeout"] == 30


def test_consultar_tasas_error_conexion_devuelve_error():
    """Error de conexión se traduce en BccConnectionError."""
    import requests

    with patch("exchange_rates.bcc.requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("no hay red")

        try:
            bcc.consultar_tasas()
            assert False, "Debería haber lanzado BccConnectionError"
        except bcc.BccConnectionError:
            pass


def test_consultar_tasas_http_error_devuelve_error():
    """HTTP >= 400 se traduce en BccError."""
    with patch("exchange_rates.bcc.requests.get") as mock_get:
        mock_respuesta = mock_get.return_value
        mock_respuesta.status_code = 500

        try:
            bcc.consultar_tasas()
            assert False, "Debería haber lanzado BccError"
        except bcc.BccError:
            pass


def test_consultar_tasas_json_invalido_devuelve_error():
    """Respuesta que no es JSON válido se traduce en BccConnectionError."""
    with patch("exchange_rates.bcc.requests.get") as mock_get:
        mock_respuesta = mock_get.return_value
        mock_respuesta.status_code = 200
        mock_respuesta.json.side_effect = ValueError("no es json")

        try:
            bcc.consultar_tasas()
            assert False, "Debería haber lanzado BccConnectionError"
        except bcc.BccConnectionError:
            pass


def test_consultar_tasas_respuesta_no_es_objeto_devuelve_error():
    """Respuesta JSON que no es un objeto se traduce en BccStructureError."""
    with patch("exchange_rates.bcc.requests.get") as mock_get:
        mock_respuesta = mock_get.return_value
        mock_respuesta.status_code = 200
        mock_respuesta.json.return_value = ["no", "es", "objeto"]

        try:
            bcc.consultar_tasas()
            assert False, "Debería haber lanzado BccStructureError"
        except bcc.BccStructureError:
            pass


def test_consultar_tasas_tasas_no_lista_devuelve_error():
    """Respuesta sin clave 'tasas' o con 'tasas' no lista se traduce en BccStructureError."""
    with patch("exchange_rates.bcc.requests.get") as mock_get:
        mock_respuesta = mock_get.return_value
        mock_respuesta.status_code = 200
        mock_respuesta.json.return_value = DATOS_API_SIN_TASAS

        try:
            bcc.consultar_tasas()
            assert False, "Debería haber lanzado BccStructureError"
        except bcc.BccStructureError:
            pass


# --- Pruebas de extraer_cotizaciones ---

def test_extraer_cotizaciones_monedas_disponibles():
    """Se extraen las monedas disponibles en la respuesta del BCC."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_EJEMPLO)

    monedas = {c["moneda_origen"] for c in cotizaciones}
    assert "USD" in monedas
    assert "EUR" in monedas
    assert "CAD" in monedas


def test_extraer_cotizaciones_usa_tasa_especial():
    """Se utiliza exclusivamente tasaEspecial, no tasaOficial ni tasaPublica."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_EJEMPLO)

    usd = next(c for c in cotizaciones if c["moneda_origen"] == "USD")
    assert usd["valor"] == 832  # tasaEspecial, no tasaOficial (24) ni tasaPublica (120)
    assert usd["valor_texto_original"] == "832"

    eur = next(c for c in cotizaciones if c["moneda_origen"] == "EUR")
    assert eur["valor"] == 920.2752  # tasaEspecial


def test_extraer_cotizaciones_segmento_iii():
    """Cada cotización tiene segmento='III'."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_EJEMPLO)

    for c in cotizaciones:
        assert c["segmento"] == "III"


def test_extraer_cotizaciones_fuente_y_categoria():
    """Cada cotización tiene fuente='bcc' y categoria='oficial'."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_EJEMPLO)

    for c in cotizaciones:
        assert c["fuente"] == "bcc"
        assert c["categoria"] == "oficial"
        assert c["url_fuente"] == "https://api.bc.gob.cu/v1/tasas-de-cambio/activas"
        assert c["tipo_tasa"] == "tasa_especial"


def test_extraer_cotizaciones_moneda_destino_cup():
    """La moneda destino es siempre CUP."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_EJEMPLO)

    for c in cotizaciones:
        assert c["moneda_destino"] == "CUP"


def test_extraer_coticiones_fecha_publicacion():
    """La fecha de publicación se toma de fechaDia."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_EJEMPLO)

    for c in cotizaciones:
        assert c["fecha_publicacion"] == "2026-11-15T00:00:00.000Z"


def test_extraer_cotizaciones_no_mlc():
    """No se genera cotización para MLC (no publicada por el BCC)."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_EJEMPLO)

    monedas = {c["moneda_origen"] for c in cotizaciones}
    assert "MLC" not in monedas


def test_extraer_cotizaciones_valor_nulo_se_omite():
    """Valor nulo en tasaEspecial se omite, no se inventa."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_VALOR_NULO)

    monedas = {c["moneda_origen"] for c in cotizaciones}
    assert "USD" not in monedas  # USD es None, se omite
    assert "EUR" in monedas


def test_extraer_cotizaciones_valor_no_numerico_se_omite():
    """Valor no numérico en tasaEspecial se omite."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_VALOR_NO_NUMERICO)

    monedas = {c["moneda_origen"] for c in cotizaciones}
    assert "USD" not in monedas
    assert "EUR" in monedas


def test_extraer_cotizaciones_valor_cero_se_omite():
    """Valor cero en tasaEspecial se omite."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_VALOR_CERO)

    monedas = {c["moneda_origen"] for c in cotizaciones}
    assert "USD" not in monedas  # USD es 0, se omite
    assert "EUR" in monedas


def test_extraer_cotizaciones_tasas_vacias_devuelve_vacia():
    """Sin tasas en la respuesta se devuelve lista vacía."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_TASAS_VACIAS)
    assert cotizaciones == []


def test_extraer_cotizaciones_sin_clave_tasas_devuelve_vacia():
    """Sin clave 'tasas' se devuelve lista vacía."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_SIN_TASAS)
    assert cotizaciones == []


def test_extraer_cotizaciones_sin_codigo_moneda_se_omite():
    """Entrada sin codigoMoneda se omite."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_SIN_CODIGO_MONEDA)
    assert cotizaciones == []


def test_extraer_cotizaciones_datos_api_no_dict_devuelve_vacia():
    """Si datos_api no es un dict, se devuelve lista vacía."""
    assert bcc.extraer_cotizaciones(None) == []
    assert bcc.extraer_cotizaciones([]) == []
    assert bcc.extraer_cotizaciones("no es dict") == []


def test_extraer_cotizaciones_tasas_no_lista_devuelve_vacia():
    """Si 'tasas' no es una lista, se devuelve lista vacía."""
    cotizaciones = bcc.extraer_cotizaciones(DATOS_API_TASAS_NO_LISTA)
    assert cotizaciones == []