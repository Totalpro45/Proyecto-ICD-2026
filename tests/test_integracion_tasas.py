"""Pruebas de integración del sistema de tasas de cambio (elTOQUE + BCC).

Comprueba que:
- Ambas fuentes se procesan en una misma ejecución.
- Cada fuente utiliza sus metadatos correctos (fuente, categoria, segmento).
- Ambas registran sus resultados en el historial mediante el almacenamiento existente.
- Un fallo en una fuente no impide que la otra se procese y guarde sus datos.
- El código de salida es 0 cuando ambas tienen éxito y distinto de cero cuando alguna falla.

No realiza peticiones HTTP reales (usa mocks).
"""

import sys
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch

sys.path.insert(0, "src")

from exchange_rates import capturar


# --- Datos de ejemplo para pruebas de integración ---

DATOS_ELTOQUE_EJEMPLO = {
    "tasas": {
        "USD": 890.0,
        "EUR": 970.0,
        "MLC": 740.74,
    },
    "date": "2026-11-01",
    "hour": 7,
    "minutes": 25,
    "seconds": 7,
}

DATOS_BCC_EJEMPLO = {
    "tasas": [
        {
            "codigoMoneda": "USD",
            "fechaDia": "2026-11-15T00:00:00.000Z",
            "nombreMoneda": "DOLAR NORTEAMERICANO",
            "tasaEspecial": 832,
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


# --- Pruebas de integración completa ---

def test_ejecucion_consulta_ambas_fuentes_y_guarda_historial():
    """python -m src.exchange_rates.capturar consulta tanto elTOQUE como BCC
    y guarda cotizaciones de ambas en el historial."""
    ruta = Path(mkdtemp()) / "historial_tasas.json"

    with (
        patch("exchange_rates.capturar.consultar_tasas_eltoque") as mock_eltoque,
        patch("exchange_rates.capturar.consultar_tasas_bcc") as mock_bcc,
        patch("exchange_rates.capturar.almacenamiento.RUTA_HISTORIAL", ruta),
    ):
        mock_eltoque.return_value = DATOS_ELTOQUE_EJEMPLO
        mock_bcc.return_value = DATOS_BCC_EJEMPLO

        codigo_salida = capturar.main()

        # Ambas fuentes fueron consultadas
        assert mock_eltoque.call_count == 1
        assert mock_bcc.call_count == 1

        # Código de salida 0: ambas tuvieron éxito
        assert codigo_salida == 0

        # Ambas guardaron cotizaciones en el historial
        historial = capturar.almacenamiento.cargar_historial(ruta)
        cotizaciones = historial["cotizaciones"]
        assert len(cotizaciones) == 5  # 3 de elTOQUE + 2 de BCC

        # Verificar metadatos de elTOQUE
        eltoque_cots = [c for c in cotizaciones if c["fuente"] == "eltoque"]
        assert len(eltoque_cots) == 3
        for c in eltoque_cots:
            assert c["categoria"] == "mercado_informal"
            assert c["segmento"] is None

        # Verificar metadatos de BCC
        bcc_cots = [c for c in cotizaciones if c["fuente"] == "bcc"]
        assert len(bcc_cots) == 2
        for c in bcc_cots:
            assert c["categoria"] == "oficial"
            assert c["segmento"] == "III"

        # Verificar que la actualización registró ambas fuentes
        actualizaciones = historial["actualizaciones"]
        assert len(actualizaciones) == 1
        assert actualizaciones[0]["fuentes_consultadas"] == ["eltoque", "bcc"]
        resultados = actualizaciones[0]["resultado_por_fuente"]
        assert {r["fuente"] for r in resultados} == {"eltoque", "bcc"}
        assert all(r["estado"] == "ok" for r in resultados)


# --- Pruebas de fallo parcial ---

def test_uno_fuente_falla_la_otra_conserva_datos_y_codigo_no_cero():
    """Si elTOQUE falla, BCC sigue procesándose y guarda sus datos.
    El código de salida es distinto de cero."""
    ruta = Path(mkdtemp()) / "historial_tasas.json"

    from exchange_rates.eltoque import ElToqueConnectionError

    with (
        patch("exchange_rates.capturar.consultar_tasas_eltoque") as mock_eltoque,
        patch("exchange_rates.capturar.consultar_tasas_bcc") as mock_bcc,
        patch("exchange_rates.capturar.almacenamiento.RUTA_HISTORIAL", ruta),
    ):
        mock_eltoque.side_effect = ElToqueConnectionError("sin red")
        mock_bcc.return_value = DATOS_BCC_EJEMPLO

        codigo_salida = capturar.main()

        # Ambas fuentes fueron intentadas
        assert mock_eltoque.call_count == 1
        assert mock_bcc.call_count == 1

        # Código de salida distinto de cero porque elTOQUE falló
        assert codigo_salida != 0

        # BCC guardó sus datos aunque elTOQUE falló
        historial = capturar.almacenamiento.cargar_historial(ruta)
        cotizaciones = historial["cotizaciones"]
        bcc_cots = [c for c in cotizaciones if c["fuente"] == "bcc"]
        assert len(bcc_cots) == 2

        # No hay cotizaciones de elTOQUE (falló)
        eltoque_cots = [c for c in cotizaciones if c["fuente"] == "eltoque"]
        assert len(eltoque_cots) == 0

        # Se registró una incidencia para elTOQUE
        incidencias = historial["incidencias"]
        eltoque_incidencias = [i for i in incidencias if i["fuente"] == "eltoque"]
        assert len(eltoque_incidencias) == 1

        # La actualización registró el fallo parcial
        actualizaciones = historial["actualizaciones"]
        assert len(actualizaciones) == 1
        resultados = actualizaciones[0]["resultado_por_fuente"]
        por_fuente = {r["fuente"]: r for r in resultados}
        assert por_fuente["eltoque"]["estado"] == "error"
        assert por_fuente["bcc"]["estado"] == "ok"


def test_ambas_fuentes_fallan_codigo_no_cero():
    """Si ambas fuentes fallan, el código de salida es 1 y no hay cotizaciones."""
    ruta = Path(mkdtemp()) / "historial_tasas.json"

    from exchange_rates.eltoque import ElToqueConnectionError
    from exchange_rates.bcc import BccConnectionError

    with (
        patch("exchange_rates.capturar.consultar_tasas_eltoque") as mock_eltoque,
        patch("exchange_rates.capturar.consultar_tasas_bcc") as mock_bcc,
        patch("exchange_rates.capturar.almacenamiento.RUTA_HISTORIAL", ruta),
    ):
        mock_eltoque.side_effect = ElToqueConnectionError("sin red eltoque")
        mock_bcc.side_effect = BccConnectionError("sin red bcc")

        codigo_salida = capturar.main()

        assert codigo_salida == 1

        historial = capturar.almacenamiento.cargar_historial(ruta)
        assert len(historial["cotizaciones"]) == 0
        assert len(historial["incidencias"]) == 2  # una por cada fuente

        actualizaciones = historial["actualizaciones"]
        assert len(actualizaciones) == 1
        resultados = actualizaciones[0]["resultado_por_fuente"]
        assert all(r["estado"] == "error" for r in resultados)
        assert all(r["cotizaciones_nuevas"] == 0 for r in resultados)
        assert all(r["incidencias"] == 1 for r in resultados)


# --- Pruebas de metadatos correctos por fuente ---

def test_eltoque_metadatos_correctos_en_historial():
    """Las cotizaciones de elTOQUE tienen fuente y categoria correctas."""
    ruta = Path(mkdtemp()) / "historial_tasas.json"

    with (
        patch("exchange_rates.capturar.consultar_tasas_eltoque") as mock_eltoque,
        patch("exchange_rates.capturar.consultar_tasas_bcc") as mock_bcc,
        patch("exchange_rates.capturar.almacenamiento.RUTA_HISTORIAL", ruta),
    ):
        mock_eltoque.return_value = DATOS_ELTOQUE_EJEMPLO
        mock_bcc.return_value = DATOS_BCC_EJEMPLO

        capturar.main()

        historial = capturar.almacenamiento.cargar_historial(ruta)
        for c in historial["cotizaciones"]:
            if c["fuente"] == "eltoque":
                assert c["categoria"] == "mercado_informal"
                assert c["segmento"] is None
                assert c["url_fuente"] == "https://tasas.eltoque.com/v1/trmi"
            elif c["fuente"] == "bcc":
                assert c["categoria"] == "oficial"
                assert c["segmento"] == "III"
                assert c["url_fuente"] == (
                    "https://api.bc.gob.cu/v1/tasas-de-cambio/activas"
                )


# --- Prueba de duplicados distinguen fuentes ---

def test_duplicados_distinguen_fuentes():
    """Una cotización de elTOQUE y otra de BCC con la misma moneda no son duplicados."""
    ruta = Path(mkdtemp()) / "historial_tasas.json"

    from exchange_rates import almacenamiento

    id_actualizacion = almacenamiento._nuevo_uuid()

    # Primera cotización de elTOQUE
    cot_eltoque = {
        "fuente": "eltoque",
        "categoria": "mercado_informal",
        "tipo_tasa": "no_especificado",
        "segmento": None,
        "moneda_origen": "USD",
        "moneda_destino": "CUP",
        "valor": 890.0,
        "valor_texto_original": "890.0",
        "fecha_publicacion": "2026-11-01T07:25:00",
        "fecha_vigencia": None,
        "fecha_captura": "2026-11-01T08:00:00Z",
        "url_fuente": "https://tasas.eltoque.com/v1/trmi",
        "estado": "valida",
        "motivo_sospecha": None,
        "reemplaza_a": None,
    }

    # Cotización de BCC con la misma moneda (USD)
    cot_bcc = {
        "fuente": "bcc",
        "categoria": "oficial",
        "tipo_tasa": "tasa_especial",
        "segmento": "III",
        "moneda_origen": "USD",
        "moneda_destino": "CUP",
        "valor": 832,
        "valor_texto_original": "832",
        "fecha_publicacion": "2026-11-15T00:00:00.000Z",
        "fecha_vigencia": None,
        "fecha_captura": "2026-11-15T08:00:00Z",
        "url_fuente": "https://api.bc.gob.cu/v1/tasas-de-cambio/activas",
        "estado": "valida",
        "motivo_sospecha": None,
        "reemplaza_a": None,
    }

    resultado1 = almacenamiento.registrar_cotizaciones(
        [cot_eltoque], id_actualizacion, ruta
    )
    resultado2 = almacenamiento.registrar_cotizaciones(
        [cot_bcc], id_actualizacion, ruta
    )

    # Ambas se agregan porque la clave de duplicado incluye fuente y categoria
    assert resultado1["cotizaciones_agregadas"] == 1
    assert resultado2["cotizaciones_agregadas"] == 1

    historial = almacenamiento.cargar_historial(ruta)
    assert len(historial["cotizaciones"]) == 2