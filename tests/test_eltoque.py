"""Pruebas para el extractor de elTOQUE.

Utiliza datos de ejemplo basados en la estructura real de la respuesta de
la API de elTOQUE. No realiza peticiones HTTP reales (usa mocks).
"""

import sys
from unittest.mock import patch

sys.path.insert(0, "src")

from exchange_rates import eltoque


# --- Datos de ejemplo basados en la respuesta real de elTOQUE ---

DATOS_API_EJEMPLO = {
    "tasas": {
        "USD": 890.0,
        "MLC": 740.74,
        "ECU": 970.0,  # elTOQUE usa ECU para el euro en algunas respuestas
        "CAD": 553.29,
        "BTC": 490.0,
    },
    "date": "2026-11-01",
    "hour": 7,
    "minutes": 25,
    "seconds": 7,
}

DATOS_API_SIN_TASAS = {
    "tasas": {},
    "date": "2026-11-01",
    "hour": 7,
    "minutes": 25,
    "seconds": 7,
}

DATOS_API_SIN_FECHA = {
    "tasas": {
        "USD": 890.0,
        "EUR": 970.0,
    },
}

DATOS_API_VALOR_NULO = {
    "tasas": {
        "USD": None,
        "EUR": 970.0,
        "MLC": 740.74,
    },
    "date": "2026-11-01",
    "hour": 7,
    "minutes": 25,
    "seconds": 7,
}

DATOS_API_VALOR_INVALIDO = {
    "tasas": {
        "USD": "no_es_numero",
        "EUR": 970.0,
    },
    "date": "2026-11-01",
    "hour": 7,
    "minutes": 25,
    "seconds": 7,
}

DATOS_API_VALOR_CERO = {
    "tasas": {
        "USD": 0,
        "EUR": 970.0,
    },
    "date": "2026-11-01",
    "hour": 7,
    "minutes": 25,
    "seconds": 7,
}


# --- Pruebas de consultar_tasas con mock ---

def test_consultar_tasas_exito():
    """consultar_tasas devuelve el JSON de elTOQUE cuando la petición tiene éxito."""
    with patch("exchange_rates.eltoque.requests.get") as mock_get, patch.dict(
        "os.environ", {"ELTOQUE_API_TOKEN": "token_valido"}
    ):
        mock_respuesta = mock_get.return_value
        mock_respuesta.status_code = 200
        mock_respuesta.json.return_value = DATOS_API_EJEMPLO

        resultado = eltoque.consultar_tasas()

        assert isinstance(resultado, dict)
        assert resultado["tasas"]["USD"] == 890.0
        assert resultado["tasas"]["ECU"] == 970.0  # elTOQUE usa ECU para el euro
        assert resultado["tasas"]["MLC"] == 740.74

        # Verificar que se enviaron los parámetros de fecha y la cabecera de auth
        args, kwargs = mock_get.call_args
        assert "date_from" in kwargs["params"]
        assert "date_to" in kwargs["params"]
        assert kwargs["headers"]["Authorization"].startswith("Bearer ")
        assert kwargs["headers"]["apikey"] == "token_valido"


def test_consultar_tasas_sin_token_devuelve_error():
    """Sin ELTOQUE_API_TOKEN se lanza ElToqueAuthError."""
    with patch.dict("os.environ", {}, clear=True):
        try:
            eltoque.consultar_tasas()
            assert False, "Debería haber lanzado ElToqueAuthError"
        except eltoque.ElToqueAuthError:
            pass


def test_consultar_tasas_http_401_devuelve_error():
    """HTTP 401 se traduce en ElToqueAuthError."""
    with patch("exchange_rates.eltoque.requests.get") as mock_get, patch.dict(
        "os.environ", {"ELTOQUE_API_TOKEN": "token_invalido"}
    ):
        mock_respuesta = mock_get.return_value
        mock_respuesta.status_code = 401

        try:
            eltoque.consultar_tasas()
            assert False, "Debería haber lanzado ElToqueAuthError"
        except eltoque.ElToqueAuthError:
            pass


def test_consultar_tasas_error_conexion_devuelve_error():
    """Error de conexión se traduce en ElToqueConnectionError."""
    import requests

    with patch("exchange_rates.eltoque.requests.get") as mock_get, patch.dict(
        "os.environ", {"ELTOQUE_API_TOKEN": "token_valido"}
    ):
        mock_get.side_effect = requests.RequestException("no hay red")

        try:
            eltoque.consultar_tasas()
            assert False, "Debería haber lanzado ElToqueConnectionError"
        except eltoque.ElToqueConnectionError:
            pass


def test_consultar_tasas_json_invalido_devuelve_error():
    """Respuesta que no es JSON válido se traduce en ElToqueConnectionError."""
    with patch("exchange_rates.eltoque.requests.get") as mock_get, patch.dict(
        "os.environ", {"ELTOQUE_API_TOKEN": "token_valido"}
    ):
        mock_respuesta = mock_get.return_value
        mock_respuesta.status_code = 200
        mock_respuesta.json.side_effect = ValueError("no es json")

        try:
            eltoque.consultar_tasas()
            assert False, "Debería haber lanzado ElToqueConnectionError"
        except eltoque.ElToqueConnectionError:
            pass


# --- Pruebas de extraer_cotizaciones ---

def test_extraer_cotizaciones_monedas_objetivo():
    """Solo se extraen USD, EUR y MLC; ECU no se mapea a EUR automáticamente."""
    cotizaciones = eltoque.extraer_cotizaciones(DATOS_API_EJEMPLO)

    monedas = {c["moneda_origen"] for c in cotizaciones}
    assert "USD" in monedas
    assert "MLC" in monedas
    # ECU no está en MONEDAS_OBJETIVO, no debe aparecer como tal
    assert "ECU" not in monedas
    # CAD y BTC no están en MONEDAS_OBJETIVO, no deben aparecer
    assert "CAD" not in monedas
    assert "BTC" not in monedas


def test_extraer_cotizaciones_valores_conservados():
    """Los valores se conservan tal como los publica elTOQUE."""
    cotizaciones = eltoque.extraer_cotizaciones(DATOS_API_EJEMPLO)

    usd = next(c for c in cotizaciones if c["moneda_origen"] == "USD")
    assert usd["valor"] == 890.0
    assert usd["moneda_destino"] == "CUP"
    assert usd["valor_texto_original"] == "890.0"

    mlc = next(c for c in cotizaciones if c["moneda_origen"] == "MLC")
    assert mlc["valor"] == 740.74
    assert mlc["moneda_destino"] == "CUP"


def test_extraer_cotizaciones_ecu_no_se_mapea_a_eur():
    """ECU no se mapea a EUR automáticamente (equivalencia no confirmada)."""
    cotizaciones = eltoque.extraer_cotizaciones(DATOS_API_EJEMPLO)

    eur_entries = [c for c in cotizaciones if c["moneda_origen"] == "EUR"]
    # ECU no se mapea a EUR, por lo tanto no debe haber entradas EUR
    # provenientes de ECU. DATOS_API_EJEMPLO no tiene EUR directo.
    assert len(eur_entries) == 0

    # ECU también debe estar excluida porque no está en MONEDAS_OBJETIVO
    ecu_entries = [c for c in cotizaciones if c["moneda_origen"] == "ECU"]
    assert len(ecu_entries) == 0


def test_extraer_cotizaciones_valor_nulo_se_omite():
    """Valor nulo se omite, no se inventa."""
    cotizaciones = eltoque.extraer_cotizaciones(DATOS_API_VALOR_NULO)

    monedas = {c["moneda_origen"] for c in cotizaciones}
    assert "USD" not in monedas  # USD es None, se omite
    assert "EUR" in monedas
    assert "MLC" in monedas


def test_extraer_cotizaciones_valor_invalido_se_omite():
    """Valor no numérico se omite."""
    cotizaciones = eltoque.extraer_cotizaciones(DATOS_API_VALOR_INVALIDO)

    monedas = {c["moneda_origen"] for c in cotizaciones}
    assert "USD" not in monedas
    assert "EUR" in monedas


def test_extraer_cotizaciones_valor_cero_se_omite():
    """Valor cero se omite (no es válido)."""
    cotizaciones = eltoque.extraer_cotizaciones(DATOS_API_VALOR_CERO)

    monedas = {c["moneda_origen"] for c in cotizaciones}
    assert "USD" not in monedas  # USD es 0, se omite
    assert "EUR" in monedas


def test_extraer_cotizaciones_sin_tasas_devuelve_vacia():
    """Sin tasas en la respuesta se devuelve lista vacía."""
    cotizaciones = eltoque.extraer_cotizaciones(DATOS_API_SIN_TASAS)
    assert cotizaciones == []


def test_extraer_cotizaciones_fecha_publicacion():
    """La fecha de publicación se construye correctamente."""
    cotizaciones = eltoque.extraer_cotizaciones(DATOS_API_EJEMPLO)

    for c in cotizaciones:
        assert c["fecha_publicacion"] == "2026-11-01T07:25:07"


def test_extraer_cotizaciones_sin_fecha_devuelve_none():
    """Sin fecha en la respuesta, fecha_publicacion es None."""
    cotizaciones = eltoque.extraer_cotizaciones(DATOS_API_SIN_FECHA)

    for c in cotizaciones:
        assert c["fecha_publicacion"] is None


# --- Pruebas de _normalizar_moneda_eltoque ---

def test_normalizar_moneda_eltoque_usd():
    assert eltoque._normalizar_moneda_eltoque("USD") == "USD"


def test_normalizar_moneda_eltoque_ecu_no_se_mapea_a_eur():
    """ECU no se mapea automáticamente a EUR (equivalencia no confirmada)."""
    assert eltoque._normalizar_moneda_eltoque("ECU") is None


def test_normalizar_moneda_eltoque_mlc():
    assert eltoque._normalizar_moneda_eltoque("MLC") == "MLC"


def test_normalizar_moneda_eltoque_desconocido_devuelve_none():
    assert eltoque._normalizar_moneda_eltoque("CAD") is None
    assert eltoque._normalizar_moneda_eltoque("BTC") is None
    assert eltoque._normalizar_moneda_eltoque("ECU") is None


# --- Pruebas de _construir_fecha_publicacion ---

def test_construir_fecha_publicacion_completa():
    datos = {"date": "2026-11-01", "hour": 7, "minutes": 25, "seconds": 7}
    assert eltoque._construir_fecha_publicacion(datos) == "2026-11-01T07:25:07"


def test_construir_fecha_publicacion_sin_segundos():
    datos = {"date": "2026-11-01", "hour": 7, "minutes": 25}
    assert eltoque._construir_fecha_publicacion(datos) == "2026-11-01T07:25"


def test_construir_fecha_publicacion_sin_fecha_devuelve_none():
    datos = {"hour": 7, "minutes": 25}
    assert eltoque._construir_fecha_publicacion(datos) is None


def test_construir_fecha_publicacion_vacio_devuelve_none():
    assert eltoque._construir_fecha_publicacion({}) is None
    assert eltoque._construir_fecha_publicacion(None) is None
