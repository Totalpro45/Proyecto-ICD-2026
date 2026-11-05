"""Pruebas para el módulo de almacenamiento de tasas de cambio.

Comprueba:
- Carga y guardado del historial JSON append-only.
- Detección de duplicados exactos (no se añaden dos veces).
- Detección de sin_novedad (mismo valor sin fechas).
- Registro de cotizaciones nuevas cuando el valor cambia.
- Registro de actualizaciones e incidencias.
- Manejo de archivo dañado y copia de seguridad.
- No se modifican los datos originales; los campos se conservan tal cual.

Usa un archivo temporal para no modificar el historial real.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "src")

from exchange_rates import almacenamiento


# --- Datos de ejemplo para pruebas ---

COTIZACION_USD = {
    "fuente": "eltoque",
    "categoria": "mercado_informal",
    "tipo_tasa": "no_especificado",
    "segmento": None,
    "moneda_origen": "USD",
    "moneda_destino": "CUP",
    "valor": 890.0,
    "valor_texto_original": "890.0",
    "fecha_publicacion": "2026-11-05T07:25:00",
    "fecha_vigencia": None,
    "fecha_captura": "2026-11-05T08:00:00Z",
    "url_fuente": "https://tasas.eltoque.com/v1/trmi",
    "estado": "valida",
    "motivo_sospecha": None,
    "reemplaza_a": None,
}

COTIZACION_USD_DIFERENTE_VALOR = {
    "fuente": "eltoque",
    "categoria": "mercado_informal",
    "tipo_tasa": "no_especificado",
    "segmento": None,
    "moneda_origen": "USD",
    "moneda_destino": "CUP",
    "valor": 920.0,
    "valor_texto_original": "920.0",
    "fecha_publicacion": "2026-11-05T07:25:00",
    "fecha_vigencia": None,
    "fecha_captura": "2026-11-05T08:00:00Z",
    "url_fuente": "https://tasas.eltoque.com/v1/trmi",
    "estado": "valida",
    "motivo_sospecha": None,
    "reemplaza_a": None,
}

COTIZACION_MLC = {
    "fuente": "eltoque",
    "categoria": "mercado_informal",
    "tipo_tasa": "no_especificado",
    "segmento": None,
    "moneda_origen": "MLC",
    "moneda_destino": "CUP",
    "valor": 740.74,
    "valor_texto_original": "740.74",
    "fecha_publicacion": "2026-11-05T07:25:00",
    "fecha_vigencia": None,
    "fecha_captura": "2026-11-05T08:00:00Z",
    "url_fuente": "https://tasas.eltoque.com/v1/trmi",
    "estado": "valida",
    "motivo_sospecha": None,
    "reemplaza_a": None,
}

COTIZACION_SIN_FECHAS = {
    "fuente": "eltoque",
    "categoria": "mercado_informal",
    "tipo_tasa": "no_especificado",
    "segmento": None,
    "moneda_origen": "USD",
    "moneda_destino": "CUP",
    "valor": 890.0,
    "valor_texto_original": "890.0",
    "fecha_publicacion": None,
    "fecha_vigencia": None,
    "fecha_captura": "2026-11-05T08:00:00Z",
    "url_fuente": "https://tasas.eltoque.com/v1/trmi",
    "estado": "valida",
    "motivo_sospecha": None,
    "reemplaza_a": None,
}


def _ruta_temporal() -> Path:
    """Devuelve una ruta temporal para las pruebas de almacenamiento."""
    return Path(tempfile.mkdtemp()) / "historial_tasas.json"


# --- Pruebas de carga y guardado ---

def test_cargar_historial_no_existe_devuelve_estructura_vacia():
    """Si el archivo no existe, se devuelve una estructura vacía."""
    ruta = _ruta_temporal()
    historial = almacenamiento.cargar_historial(ruta)

    assert historial["version_esquema"] == "1.0"
    assert historial["cotizaciones"] == []
    assert historial["actualizaciones"] == []
    assert historial["incidencias"] == []
    assert historial["ultima_actualizacion"] is None


def test_guardar_y_cargar_historial():
    """Se puede guardar y cargar un historial sin perder datos."""
    ruta = _ruta_temporal()

    datos_iniciales = {
        "version_esquema": "1.0",
        "ultima_actualizacion": "2026-11-05T08:00:00Z",
        "cotizaciones": [],
        "actualizaciones": [],
        "incidencias": [],
    }
    almacenamiento.guardar_historial(datos_iniciales, ruta)

    assert ruta.exists()
    historial_cargado = almacenamiento.cargar_historial(ruta)
    assert historial_cargado["version_esquema"] == "1.0"
    assert historial_cargado["cotizaciones"] == []


def test_cargar_historial_dañado_devuelve_vacio_y_respaldos():
    """Si el archivo JSON está dañado, se devuelve estructura vacía y se crea respaldo."""
    ruta = _ruta_temporal()
    ruta.write_text("{json malformed", encoding="utf-8")

    historial = almacenamiento.cargar_historial(ruta)

    assert historial["cotizaciones"] == []
    assert historial["actualizaciones"] == []
    assert historial["incidencias"] == []

    # Debe existir un archivo de respaldo con el contenido dañado
    respaldo = ruta.with_suffix(ruta.suffix + ".corrupto")
    assert respaldo.exists()


# --- Pruebas de registrar cotizaciones ---

def test_registrar_cotizaciones_nuevas():
    """Las cotizaciones nuevas se añaden al historial con UUIDs únicos."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()
    ahora = almacenamiento._ahora_iso()

    resultado = almacenamiento.registrar_cotizaciones(
        [COTIZACION_USD, COTIZACION_MLC],
        id_actualizacion,
        ruta,
    )

    assert resultado["cotizaciones_agregadas"] == 2
    assert resultado["sin_novedad"] == 0
    assert resultado["duplicados_omitidos"] == 0

    historial = almacenamiento.cargar_historial(ruta)
    assert len(historial["cotizaciones"]) == 2

    # Cada cotización debe tener un UUID único
    ids = [c["id"] for c in historial["cotizaciones"]]
    assert len(ids) == len(set(ids))

    # Verificar que los campos se conservan
    usd = historial["cotizaciones"][0]
    assert usd["moneda_origen"] == "USD"
    assert usd["moneda_destino"] == "CUP"
    assert usd["valor"] == 890.0
    assert usd["valor_texto_original"] == "890.0"
    assert usd["fecha_publicacion"] == "2026-11-05T07:25:00"
    assert usd["fuente"] == "eltoque"
    assert usd["categoria"] == "mercado_informal"
    assert usd["estado"] == "valida"
    assert usd["id_actualizacion"] == id_actualizacion


def test_registrar_cotizaciones_duplicado_exacto_no_se_añade():
    """Si la cotización ya existe con los mismos campos, no se duplica."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()

    # Primera inserción
    almacenamiento.registrar_cotizaciones(
        [COTIZACION_USD], id_actualizacion, ruta
    )

    # Segunda inserción con el mismo dato
    resultado = almacenamiento.registrar_cotizaciones(
        [COTIZACION_USD], id_actualizacion, ruta
    )

    assert resultado["cotizaciones_agregadas"] == 0
    assert resultado["duplicados_omitidos"] == 1
    assert resultado["sin_novedad"] == 0

    historial = almacenamiento.cargar_historial(ruta)
    assert len(historial["cotizaciones"]) == 1


def test_registrar_cotizaciones_sin_novedad_mismo_valor_sin_fechas():
    """Sin fechas y mismo valor: se registra como sin_novedad, no se añade."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()

    # Primera inserción sin fechas
    almacenamiento.registrar_cotizaciones(
        [COTIZACION_SIN_FECHAS], id_actualizacion, ruta
    )

    # Segunda inserción con el mismo valor sin fechas
    resultado = almacenamiento.registrar_cotizaciones(
        [COTIZACION_SIN_FECHAS], id_actualizacion, ruta
    )

    assert resultado["cotizaciones_agregadas"] == 0
    assert resultado["sin_novedad"] == 1
    assert resultado["duplicados_omitidos"] == 0

    historial = almacenamiento.cargar_historial(ruta)
    assert len(historial["cotizaciones"]) == 1


def test_registrar_cotizaciones_valor_diferente_sin_fechas_se_añade():
    """Sin fechas pero valor diferente: se añade como nueva cotización."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()

    # Primera inserción sin fechas
    almacenamiento.registrar_cotizaciones(
        [COTIZACION_SIN_FECHAS], id_actualizacion, ruta
    )

    # Segunda inserción con valor diferente sin fechas
    cotizacion_valor_diferente = dict(COTIZACION_SIN_FECHAS)
    cotizacion_valor_diferente["valor"] = 920.0
    cotizacion_valor_diferente["valor_texto_original"] = "920.0"

    resultado = almacenamiento.registrar_cotizaciones(
        [cotizacion_valor_diferente], id_actualizacion, ruta
    )

    assert resultado["cotizaciones_agregadas"] == 1
    assert resultado["sin_novedad"] == 0
    assert resultado["duplicados_omitidos"] == 0

    historial = almacenamiento.cargar_historial(ruta)
    assert len(historial["cotizaciones"]) == 2


def test_registrar_cotizaciones_múltiples_monedas():
    """Se pueden guardar múltiples monedas en una misma actualización."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()

    resultado = almacenamiento.registrar_cotizaciones(
        [COTIZACION_USD, COTIZACION_MLC], id_actualizacion, ruta
    )

    assert resultado["cotizaciones_agregadas"] == 2

    historial = almacenamiento.cargar_historial(ruta)
    monedas = {c["moneda_origen"] for c in historial["cotizaciones"]}
    assert monedas == {"USD", "MLC"}


def test_registrar_cotizaciones_no_sobrescribe_historial_previo():
    """Las cotizaciones nuevas se añaden sin borrar las anteriores."""
    ruta = _ruta_temporal()
    id_act1 = almacenamiento._nuevo_uuid()
    id_act2 = almacenamiento._nuevo_uuid()

    # Primera actualización
    almacenamiento.registrar_cotizaciones(
        [COTIZACION_USD], id_act1, ruta
    )

    # Segunda actualización con otra moneda
    almacenamiento.registrar_cotizaciones(
        [COTIZACION_MLC], id_act2, ruta
    )

    historial = almacenamiento.cargar_historial(ruta)
    assert len(historial["cotizaciones"]) == 2
    ids_actualizacion = {c["id_actualizacion"] for c in historial["cotizaciones"]}
    assert ids_actualizacion == {id_act1, id_act2}


# --- Pruebas de registrar actualización ---

def test_registrar_actualizacion():
    """Se registra una actualización con sus metadatos."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()
    fecha_inicio = almacenamiento._ahora_iso()
    fecha_fin = almacenamiento._ahora_iso()

    almacenamiento.registrar_actualizacion(
        id_actualizacion,
        fecha_inicio,
        fecha_fin,
        ["eltoque"],
        [
            {
                "fuente": "eltoque",
                "estado": "ok",
                "cotizaciones_nuevas": 2,
                "incidencias": 0,
            }
        ],
        ruta,
    )

    historial = almacenamiento.cargar_historial(ruta)
    assert len(historial["actualizaciones"]) == 1
    act = historial["actualizaciones"][0]
    assert act["id"] == id_actualizacion
    assert act["fuentes_consultadas"] == ["eltoque"]
    assert act["resultado_por_fuente"][0]["estado"] == "ok"


# --- Pruebas de registrar incidencias ---

def test_registrar_incidencia_conexion():
    """Se registra una incidencia de tipo conexión."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()
    fecha_captura = almacenamiento._ahora_iso()

    almacenamiento.crear_incidencia_conexion(
        id_actualizacion,
        "eltoque",
        fecha_captura,
        "No se pudo conectar con la API",
        detalle_tecnico="timeout",
        url_fuente="https://tasas.eltoque.com/v1/trmi",
        ruta=ruta,
    )

    historial = almacenamiento.cargar_historial(ruta)
    assert len(historial["incidencias"]) == 1
    inc = historial["incidencias"][0]
    assert inc["tipo"] == "conexion"
    assert inc["fuente"] == "eltoque"
    assert inc["estado"] == "abierta"
    assert inc["detalle_tecnico"] == "timeout"
    assert inc["url_fuente"] == "https://tasas.eltoque.com/v1/trmi"


def test_registrar_incidencia_estructura():
    """Se registra una incidencia de tipo estructura."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()
    fecha_captura = almacenamiento._ahora_iso()

    almacenamiento.crear_incidencia_estructura(
        id_actualizacion,
        "eltoque",
        fecha_captura,
        "La estructura del JSON cambió",
        ruta=ruta,
    )

    historial = almacenamiento.cargar_historial(ruta)
    assert len(historial["incidencias"]) == 1
    inc = historial["incidencias"][0]
    assert inc["tipo"] == "estructura"
    assert inc["estado"] == "abierta"


def test_registrar_incidencia_validacion():
    """Se registra una incidencia de tipo validación."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()
    fecha_captura = almacenamiento._ahora_iso()

    almacenamiento.crear_incidencia_validacion(
        id_actualizacion,
        "eltoque",
        fecha_captura,
        "Valor nulo en moneda USD",
        categoria="mercado_informal",
        ruta=ruta,
    )

    historial = almacenamiento.cargar_historial(ruta)
    assert len(historial["incidencias"]) == 1
    inc = historial["incidencias"][0]
    assert inc["tipo"] == "validacion"
    assert inc["categoria"] == "mercado_informal"
    assert inc["estado"] == "abierta"


# --- Pruebas de utilidades ---

def test_nuevo_uuid_es_unico():
    """Cada UUID generado es único."""
    ids = {almacenamiento._nuevo_uuid() for _ in range(100)}
    assert len(ids) == 100


def test_clave_cotizacion_incluye_campos_esenciales():
    """La clave incluye los campos definidos en la documentación."""
    clave = almacenamiento._clave_cotizacion(COTIZACION_USD)
    assert clave == (
        "eltoque", "mercado_informal", "USD", "CUP",
        "no_especificado", None,
    )


# --- Pruebas de coherencia de fechas ---

def test_fecha_captura_es_diferente_de_fecha_publicacion():
    """fecha_captura debe ser el momento de captura, no la fecha de publicación."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()

    # COTIZACION_USD tiene fecha_publicacion="2026-11-05T07:25:00"
    # pero fecha_captura="2026-11-05T08:00:00Z" (distinta)
    almacenamiento.registrar_cotizaciones(
        [COTIZACION_USD], id_actualizacion, ruta
    )

    historial = almacenamiento.cargar_historial(ruta)
    cotizacion = historial["cotizaciones"][0]

    # fecha_publicacion y fecha_captura no deben ser iguales
    assert cotizacion["fecha_publicacion"] != cotizacion["fecha_captura"]
    assert cotizacion["fecha_publicacion"] == "2026-11-05T07:25:00"
    assert cotizacion["fecha_captura"] == "2026-11-05T08:00:00Z"


def test_ultima_actualizacion_coincide_con_fecha_fin():
    """ultima_actualizacion debe ser igual a fecha_fin de la última actualización."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()
    fecha_inicio = almacenamiento._ahora_iso()
    fecha_fin = almacenamiento._ahora_iso()

    almacenamiento.registrar_cotizaciones(
        [COTIZACION_USD], id_actualizacion, ruta
    )

    almacenamiento.registrar_actualizacion(
        id_actualizacion,
        fecha_inicio,
        fecha_fin,
        ["eltoque"],
        [
            {
                "fuente": "eltoque",
                "estado": "ok",
                "cotizaciones_nuevas": 1,
                "incidencias": 0,
            }
        ],
        ruta,
    )

    historial = almacenamiento.cargar_historial(ruta)

    # ultima_actualizacion debe coincidir con fecha_fin
    assert historial["ultima_actualizacion"] == fecha_fin

    # La última actualización debe tener fecha_fin igual a ultima_actualizacion
    ultima_act = historial["actualizaciones"][-1]
    assert ultima_act["fecha_fin"] == historial["ultima_actualizacion"]


def test_fecha_publicacion_procede_de_api_no_de_captura():
    """fecha_publicacion debe ser la fecha que indica la fuente (elTOQUE),
    no la fecha en que nosotros capturamos los datos."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()

    # COTIZACION_USD tiene fecha_publicacion="2026-11-05T07:25:00"
    # y fecha_captura="2026-11-05T08:00:00Z"
    almacenamiento.registrar_cotizaciones(
        [COTIZACION_USD], id_actualizacion, ruta
    )

    historial = almacenamiento.cargar_historial(ruta)
    cotizacion = historial["cotizaciones"][0]

    # fecha_publicacion debe ser la de elTOQUE, no la de captura
    assert cotizacion["fecha_publicacion"] == "2026-11-05T07:25:00"
    assert cotizacion["fecha_publicacion"] != cotizacion["fecha_captura"]


def test_fecha_captura_no_es_fecha_publicacion():
    """fecha_captura no debe copiarse de fecha_publicacion."""
    ruta = _ruta_temporal()
    id_actualizacion = almacenamiento._nuevo_uuid()

    # Usar una cotización donde fecha_publicacion y fecha_captura son distintas
    almacenamiento.registrar_cotizaciones(
        [COTIZACION_USD], id_actualizacion, ruta
    )

    historial = almacenamiento.cargar_historial(ruta)
    cotizacion = historial["cotizaciones"][0]

    # fecha_captura debe ser el momento de captura, no la fecha de publicación
    assert cotizacion["fecha_captura"] != cotizacion["fecha_publicacion"]
    assert cotizacion["fecha_captura"] == "2026-11-05T08:00:00Z"