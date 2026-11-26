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

import pytest

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

# Registro ficticio con la forma de los registros antiguos sin procedencia.
COTIZACION_SIN_PROCEDENCIA = {
    "id": "00000000-0000-4000-8000-000000000001",
    "id_actualizacion": "00000000-0000-4000-8000-000000000010",
    "fuente": None,
    "categoria": None,
    "tipo_tasa": "no_especificado",
    "segmento": None,
    "moneda_origen": "USD",
    "moneda_destino": "CUP",
    "valor": 900.0,
    "valor_texto_original": "900.0",
    "fecha_publicacion": "2026-11-04T10:00:00",
    "fecha_vigencia": None,
    "fecha_captura": "2026-11-04T15:00:00+00:00",
    "url_fuente": None,
    "estado": "valida",
    "motivo_sospecha": None,
    "reemplaza_a": None,
}


def _ruta_temporal() -> Path:
    """Devuelve una ruta temporal para las pruebas de almacenamiento."""
    return Path(tempfile.mkdtemp()) / "historial_tasas.json"


def _historial_de_prueba(marca: str) -> dict:
    """Crea un historial ficticio identificable por una marca."""
    return {
        "version_esquema": "1.0",
        "cotizaciones": [],
        "actualizaciones": [{"id": marca}],
        "incidencias": [],
    }


def _archivos_temporales(ruta: Path) -> list[Path]:
    """Lista los archivos temporales que quedan junto al historial."""
    return [p for p in ruta.parent.iterdir() if p.suffix == ".tmp"]


def _guardar_cotizaciones(ruta: Path, cotizaciones: list[dict]) -> None:
    """Guarda un historial ficticio con las cotizaciones indicadas."""
    almacenamiento.guardar_historial(
        {
            "version_esquema": "1.0",
            "ultima_actualizacion": "2026-11-05T08:00:00Z",
            "cotizaciones": cotizaciones,
            "actualizaciones": [],
            "incidencias": [],
        },
        ruta,
    )


def _cotizacion_sin_fechas(valor: float, fecha_captura: str) -> dict:
    """Crea una cotización ficticia sin fechas de publicación ni vigencia."""
    return dict(
        COTIZACION_SIN_FECHAS,
        valor=valor,
        valor_texto_original=str(valor),
        fecha_captura=fecha_captura,
    )


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


def test_guardar_historial_crea_json_valido_y_respaldo_anterior():
    """Un guardado correcto actualiza el JSON y conserva el anterior en .bak."""
    ruta = _ruta_temporal()
    respaldo = ruta.with_suffix(ruta.suffix + ".bak")

    almacenamiento.guardar_historial(_historial_de_prueba("primera"), ruta)
    bytes_primera = ruta.read_bytes()
    assert not respaldo.exists()

    almacenamiento.guardar_historial(_historial_de_prueba("segunda"), ruta)

    actual = json.loads(ruta.read_text(encoding="utf-8"))
    anterior = json.loads(respaldo.read_text(encoding="utf-8"))
    assert actual["actualizaciones"] == [{"id": "segunda"}]
    assert anterior["actualizaciones"] == [{"id": "primera"}]
    assert respaldo.read_bytes() == bytes_primera
    assert not _archivos_temporales(ruta)


def test_error_de_serializacion_no_destruye_historial_ni_respaldo():
    """Un error al serializar no toca el historial ni el respaldo válido."""
    ruta = _ruta_temporal()
    respaldo = ruta.with_suffix(ruta.suffix + ".bak")
    almacenamiento.guardar_historial(_historial_de_prueba("primera"), ruta)
    almacenamiento.guardar_historial(_historial_de_prueba("segunda"), ruta)
    bytes_actual = ruta.read_bytes()
    bytes_respaldo = respaldo.read_bytes()

    datos_invalidos = _historial_de_prueba("tercera")
    datos_invalidos["incidencias"] = [{1, 2}]

    with pytest.raises(TypeError):
        almacenamiento.guardar_historial(datos_invalidos, ruta)

    assert ruta.read_bytes() == bytes_actual
    assert respaldo.read_bytes() == bytes_respaldo
    assert not _archivos_temporales(ruta)


def test_error_de_escritura_no_destruye_historial_ni_respaldo():
    """Un fallo al escribir el temporal conserva el original y el respaldo."""
    ruta = _ruta_temporal()
    respaldo = ruta.with_suffix(ruta.suffix + ".bak")
    almacenamiento.guardar_historial(_historial_de_prueba("primera"), ruta)
    almacenamiento.guardar_historial(_historial_de_prueba("segunda"), ruta)
    bytes_actual = ruta.read_bytes()
    bytes_respaldo = respaldo.read_bytes()

    with patch(
        "exchange_rates.almacenamiento.os.fsync",
        side_effect=OSError("fallo de escritura simulado"),
    ):
        with pytest.raises(OSError):
            almacenamiento.guardar_historial(
                _historial_de_prueba("tercera"), ruta
            )

    assert ruta.read_bytes() == bytes_actual
    assert respaldo.read_bytes() == bytes_respaldo
    assert not _archivos_temporales(ruta)


def test_error_de_sustitucion_no_destruye_historial_ni_respaldo():
    """Un fallo en os.replace deja intactos el historial y el respaldo."""
    ruta = _ruta_temporal()
    respaldo = ruta.with_suffix(ruta.suffix + ".bak")
    almacenamiento.guardar_historial(_historial_de_prueba("primera"), ruta)
    almacenamiento.guardar_historial(_historial_de_prueba("segunda"), ruta)
    bytes_actual = ruta.read_bytes()
    bytes_respaldo = respaldo.read_bytes()

    with patch(
        "exchange_rates.almacenamiento.os.replace",
        side_effect=OSError("fallo de sustitución simulado"),
    ):
        with pytest.raises(OSError):
            almacenamiento.guardar_historial(
                _historial_de_prueba("tercera"), ruta
            )

    assert ruta.read_bytes() == bytes_actual
    assert respaldo.read_bytes() == bytes_respaldo
    assert json.loads(ruta.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "segunda"}
    ]
    assert json.loads(respaldo.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "primera"}
    ]
    assert not _archivos_temporales(ruta)


def _preparar_historial_con_respaldo(tmp_path: Path) -> tuple[Path, Path]:
    """Crea en ``tmp_path`` un historial con una versión anterior respaldada."""
    ruta = tmp_path / "historial_tasas.json"
    respaldo = ruta.with_suffix(ruta.suffix + ".bak")
    almacenamiento.guardar_historial(_historial_de_prueba("primera"), ruta)
    almacenamiento.guardar_historial(_historial_de_prueba("segunda"), ruta)
    return ruta, respaldo


def test_respaldo_copia_exacta_del_historial_anterior(tmp_path):
    """El respaldo contiene exactamente la versión anterior del historial."""
    ruta, respaldo = _preparar_historial_con_respaldo(tmp_path)
    assert respaldo.exists()

    # Una nueva versión sustituye el historial y actualiza el respaldo.
    almacenamiento.guardar_historial(_historial_de_prueba("tercera"), ruta)

    assert json.loads(ruta.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "tercera"}
    ]
    assert json.loads(respaldo.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "segunda"}
    ]
    assert not _archivos_temporales(ruta)


def test_fallo_al_crear_temporal_de_respaldo_conserva_archivos(tmp_path):
    """Si no se puede crear el temporal del respaldo, no se guarda nada."""
    ruta, respaldo = _preparar_historial_con_respaldo(tmp_path)
    bytes_actual = ruta.read_bytes()
    bytes_respaldo = respaldo.read_bytes()

    with patch(
        "exchange_rates.almacenamiento.tempfile.mkstemp",
        side_effect=OSError("fallo simulado al crear el temporal del respaldo"),
    ):
        with pytest.raises(OSError):
            almacenamiento.guardar_historial(
                _historial_de_prueba("tercera"), ruta
            )

    assert ruta.read_bytes() == bytes_actual
    assert respaldo.read_bytes() == bytes_respaldo
    assert json.loads(ruta.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "segunda"}
    ]
    assert json.loads(respaldo.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "primera"}
    ]
    assert not _archivos_temporales(ruta)


def test_fallo_parcial_en_copia_de_respaldo_conserva_archivos(tmp_path):
    """Si copy2 falla tras escribir parte del temporal, nada se sustituye."""
    ruta, respaldo = _preparar_historial_con_respaldo(tmp_path)
    bytes_actual = ruta.read_bytes()
    bytes_respaldo = respaldo.read_bytes()

    def copia_parcial(origen, destino, **kwargs):
        Path(destino).write_bytes(Path(origen).read_bytes()[:10])
        raise OSError("fallo simulado a mitad de la copia")

    with patch(
        "exchange_rates.almacenamiento.shutil.copy2", copia_parcial
    ):
        with pytest.raises(OSError):
            almacenamiento.guardar_historial(
                _historial_de_prueba("tercera"), ruta
            )

    assert ruta.read_bytes() == bytes_actual
    assert respaldo.read_bytes() == bytes_respaldo
    assert json.loads(respaldo.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "primera"}
    ]
    assert not _archivos_temporales(ruta)


def test_fallo_al_sustituir_respaldo_conserva_archivos(tmp_path):
    """Si falla el os.replace del respaldo, el guardado se aborta."""
    ruta, respaldo = _preparar_historial_con_respaldo(tmp_path)
    bytes_actual = ruta.read_bytes()
    bytes_respaldo = respaldo.read_bytes()

    replace_real = os.replace

    def replace_falla_respaldo(origen, destino):
        if Path(destino) == respaldo:
            raise OSError("fallo simulado al sustituir el respaldo")
        return replace_real(origen, destino)

    with patch(
        "exchange_rates.almacenamiento.os.replace",
        side_effect=replace_falla_respaldo,
    ):
        with pytest.raises(OSError):
            almacenamiento.guardar_historial(
                _historial_de_prueba("tercera"), ruta
            )

    assert ruta.read_bytes() == bytes_actual
    assert respaldo.read_bytes() == bytes_respaldo
    assert json.loads(ruta.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "segunda"}
    ]
    assert json.loads(respaldo.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "primera"}
    ]
    assert not _archivos_temporales(ruta)


def test_fallo_al_sustituir_historial_deja_respaldo_valido(tmp_path):
    """Si falla la sustitución final, el respaldo guarda el historial vigente."""
    ruta, respaldo = _preparar_historial_con_respaldo(tmp_path)
    bytes_actual = ruta.read_bytes()

    replace_real = os.replace

    def replace_falla_historial(origen, destino):
        if Path(destino) == ruta:
            raise OSError("fallo simulado al sustituir el historial")
        return replace_real(origen, destino)

    with patch(
        "exchange_rates.almacenamiento.os.replace",
        side_effect=replace_falla_historial,
    ):
        with pytest.raises(OSError):
            almacenamiento.guardar_historial(
                _historial_de_prueba("tercera"), ruta
            )

    assert ruta.read_bytes() == bytes_actual
    assert respaldo.read_bytes() == bytes_actual
    assert json.loads(respaldo.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "segunda"}
    ]
    assert not _archivos_temporales(ruta)


def test_primera_escritura_sin_historial_ni_respaldo(tmp_path):
    """La primera escritura funciona sin exigir un respaldo previo."""
    ruta = tmp_path / "historial_tasas.json"
    respaldo = ruta.with_suffix(ruta.suffix + ".bak")

    almacenamiento.guardar_historial(_historial_de_prueba("primera"), ruta)

    assert json.loads(ruta.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "primera"}
    ]
    assert not respaldo.exists()
    assert not _archivos_temporales(ruta)


def test_temporal_se_crea_en_el_mismo_directorio():
    """El temporal se escribe junto al historial para permitir os.replace."""
    ruta = _ruta_temporal()
    almacenamiento.guardar_historial(_historial_de_prueba("primera"), ruta)

    with patch(
        "exchange_rates.almacenamiento.os.replace", wraps=os.replace
    ) as reemplazo:
        almacenamiento.guardar_historial(
            _historial_de_prueba("segunda"), ruta
        )

    origen = Path(reemplazo.call_args.args[0])
    destino = Path(reemplazo.call_args.args[1])
    assert origen.parent == ruta.parent
    assert destino == ruta
    assert not origen.exists()


def test_guardar_historial_primera_vez_sin_archivo_original():
    """La primera escritura funciona aunque no exista el historial."""
    ruta = _ruta_temporal()
    respaldo = ruta.with_suffix(ruta.suffix + ".bak")

    almacenamiento.guardar_historial(_historial_de_prueba("primera"), ruta)

    assert ruta.exists()
    assert not respaldo.exists()
    assert json.loads(ruta.read_text(encoding="utf-8"))["actualizaciones"] == [
        {"id": "primera"}
    ]
    assert not _archivos_temporales(ruta)


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


# --- Pruebas de deduplicación con la última cotización ---

def test_deduplicacion_omite_si_coincide_con_la_ultima_cotizacion():
    """Una cotización igual a la última registrada no se añade."""
    ruta = _ruta_temporal()
    _guardar_cotizaciones(
        ruta,
        [
            _cotizacion_sin_fechas(890.0, "2026-11-05T08:00:00Z"),
            _cotizacion_sin_fechas(920.0, "2026-11-06T08:00:00Z"),
        ],
    )

    resultado = almacenamiento.registrar_cotizaciones(
        [_cotizacion_sin_fechas(920.0, "2026-11-07T08:00:00Z")],
        almacenamiento._nuevo_uuid(),
        ruta,
    )

    assert resultado["cotizaciones_agregadas"] == 0
    assert resultado["sin_novedad"] == 1
    assert resultado["duplicados_omitidos"] == 0
    assert len(almacenamiento.listar_cotizaciones(ruta)) == 2


def test_deduplicacion_añade_si_difiere_de_la_ultima_cotizacion():
    """Una cotización distinta de la última registrada sí se añade."""
    ruta = _ruta_temporal()
    _guardar_cotizaciones(
        ruta,
        [
            _cotizacion_sin_fechas(890.0, "2026-11-05T08:00:00Z"),
            _cotizacion_sin_fechas(920.0, "2026-11-06T08:00:00Z"),
        ],
    )

    resultado = almacenamiento.registrar_cotizaciones(
        [_cotizacion_sin_fechas(930.0, "2026-11-07T08:00:00Z")],
        almacenamiento._nuevo_uuid(),
        ruta,
    )

    assert resultado["cotizaciones_agregadas"] == 1
    assert resultado["sin_novedad"] == 0
    assert len(almacenamiento.listar_cotizaciones(ruta)) == 3


def test_deduplicacion_no_compara_con_una_cotizacion_antigua():
    """Un valor antiguo repetido se añade si la última cotización es distinta."""
    ruta = _ruta_temporal()
    _guardar_cotizaciones(
        ruta,
        [
            _cotizacion_sin_fechas(890.0, "2026-11-05T08:00:00Z"),
            _cotizacion_sin_fechas(920.0, "2026-11-06T08:00:00Z"),
        ],
    )

    resultado = almacenamiento.registrar_cotizaciones(
        [_cotizacion_sin_fechas(890.0, "2026-11-07T08:00:00Z")],
        almacenamiento._nuevo_uuid(),
        ruta,
    )

    assert resultado["cotizaciones_agregadas"] == 1
    assert resultado["sin_novedad"] == 0
    assert [c["valor"] for c in almacenamiento.listar_cotizaciones(ruta)] == [
        890.0,
        920.0,
        890.0,
    ]


def test_deduplicacion_con_fechas_compara_con_la_ultima_cotizacion():
    """Con fechas, tampoco se compara con la primera coincidencia."""
    ruta = _ruta_temporal()
    antigua = dict(COTIZACION_USD)
    reciente = dict(
        COTIZACION_USD,
        valor=920.0,
        valor_texto_original="920.0",
        fecha_captura="2026-11-06T08:00:00Z",
    )
    _guardar_cotizaciones(ruta, [antigua, reciente])

    # Es idéntica a la cotización antigua, pero distinta de la más reciente.
    nueva = dict(COTIZACION_USD, fecha_captura="2026-11-07T08:00:00Z")
    resultado = almacenamiento.registrar_cotizaciones(
        [nueva], almacenamiento._nuevo_uuid(), ruta
    )

    assert resultado["cotizaciones_agregadas"] == 1
    assert resultado["duplicados_omitidos"] == 0
    assert len(almacenamiento.listar_cotizaciones(ruta)) == 3


def test_deduplicacion_usa_fecha_captura_y_no_el_orden_de_la_lista():
    """La comparación usa la fecha de captura aunque el historial esté desordenado."""
    ruta = _ruta_temporal()
    reciente = _cotizacion_sin_fechas(920.0, "2026-11-06T08:00:00Z")
    antigua = _cotizacion_sin_fechas(890.0, "2026-11-05T08:00:00Z")
    # Se guarda primero la más reciente para que la posición no coincida con
    # el orden temporal.
    _guardar_cotizaciones(ruta, [reciente, antigua])

    resultado = almacenamiento.registrar_cotizaciones(
        [_cotizacion_sin_fechas(890.0, "2026-11-07T08:00:00Z")],
        almacenamiento._nuevo_uuid(),
        ruta,
    )

    assert resultado["cotizaciones_agregadas"] == 1
    assert resultado["sin_novedad"] == 0


def test_deduplicacion_respeta_los_campos_de_la_clave():
    """Cambiar cualquier campo de la clave genera una cotización separada."""
    ruta = _ruta_temporal()
    base = _cotizacion_sin_fechas(900.0, "2026-11-05T08:00:00Z")
    _guardar_cotizaciones(ruta, [base])

    variantes = [
        dict(
            base,
            fuente="bcc",
            categoria="oficial",
            fecha_captura="2026-11-06T08:00:00Z",
        ),
        dict(
            base,
            tipo_tasa="tasa_especial",
            fecha_captura="2026-11-06T08:00:01Z",
        ),
        dict(
            base,
            segmento="III",
            fecha_captura="2026-11-06T08:00:02Z",
        ),
        dict(
            base,
            moneda_origen="EUR",
            fecha_captura="2026-11-06T08:00:03Z",
        ),
        dict(
            base,
            moneda_destino="MLC",
            fecha_captura="2026-11-06T08:00:04Z",
        ),
    ]

    resultado = almacenamiento.registrar_cotizaciones(
        variantes, almacenamiento._nuevo_uuid(), ruta
    )

    assert resultado["cotizaciones_agregadas"] == 5
    guardadas = almacenamiento.listar_cotizaciones(ruta)
    assert len(guardadas) == 6
    assert len({almacenamiento._clave_cotizacion(c) for c in guardadas}) == 6


def test_deduplicacion_conserva_registros_sin_procedencia():
    """Un registro histórico sin fuente no se compara con uno nuevo válido."""
    ruta = _ruta_temporal()
    legado = dict(COTIZACION_SIN_PROCEDENCIA)
    _guardar_cotizaciones(ruta, [legado])

    resultado = almacenamiento.registrar_cotizaciones(
        [_cotizacion_sin_fechas(900.0, "2026-11-05T08:00:00Z")],
        almacenamiento._nuevo_uuid(),
        ruta,
    )

    assert resultado["cotizaciones_agregadas"] == 1
    todas = almacenamiento.listar_cotizaciones(ruta)
    assert len(todas) == 2
    assert todas[0] == legado
    assert todas[0]["fuente"] is None
    assert todas[0]["categoria"] is None

    filtradas = almacenamiento.listar_cotizaciones(ruta, fuente="eltoque")
    assert len(filtradas) == 1


def test_deduplicacion_en_lote_no_duplica_la_misma_observacion():
    """Un lote con valores repetidos solo guarda cada observación una vez."""
    ruta = _ruta_temporal()
    cotizacion_920 = _cotizacion_sin_fechas(920.0, "2026-11-05T08:00:00Z")
    cotizacion_890 = _cotizacion_sin_fechas(890.0, "2026-11-05T08:00:01Z")

    resultado = almacenamiento.registrar_cotizaciones(
        [
            cotizacion_920,
            cotizacion_920,
            cotizacion_890,
            cotizacion_890,
        ],
        almacenamiento._nuevo_uuid(),
        ruta,
    )

    assert resultado["cotizaciones_agregadas"] == 2
    assert resultado["sin_novedad"] == 2
    assert [
        c["valor"] for c in almacenamiento.listar_cotizaciones(ruta)
    ] == [920.0, 890.0]


# --- Pruebas de procedencia y consultas ---

def _historial_con_legado_y_valida() -> Path:
    """Crea un historial temporal con un registro sin procedencia y otro válido."""
    ruta = _ruta_temporal()
    valida = dict(
        COTIZACION_USD,
        id="00000000-0000-4000-8000-000000000002",
    )
    historial = {
        "version_esquema": "1.0",
        "ultima_actualizacion": "2026-11-05T08:00:00Z",
        "cotizaciones": [
            dict(COTIZACION_SIN_PROCEDENCIA),
            valida,
        ],
        "actualizaciones": [],
        "incidencias": [],
    }
    almacenamiento.guardar_historial(historial, ruta)
    return ruta


def test_consulta_general_incluye_registros_sin_procedencia():
    """La consulta sin filtros devuelve también los registros históricos."""
    ruta = _historial_con_legado_y_valida()

    cotizaciones = almacenamiento.listar_cotizaciones(ruta)

    assert len(cotizaciones) == 2
    assert sum(1 for c in cotizaciones if c.get("fuente") is None) == 1
    assert sum(1 for c in cotizaciones if c.get("categoria") is None) == 1


def test_filtro_por_fuente_no_atribuye_registros_sin_procedencia():
    """Filtrar por fuente excluye los registros cuya fuente es nula."""
    ruta = _historial_con_legado_y_valida()

    eltoque = almacenamiento.listar_cotizaciones(ruta, fuente="eltoque")

    assert len(eltoque) == 1
    assert all(c["fuente"] == "eltoque" for c in eltoque)
    assert all(
        c["id"] != COTIZACION_SIN_PROCEDENCIA["id"] for c in eltoque
    )
    assert almacenamiento.listar_cotizaciones(ruta, fuente="bcc") == []


def test_filtro_por_categoria_no_atribuye_registros_sin_procedencia():
    """Filtrar por categoría excluye los registros cuya categoría es nula."""
    ruta = _historial_con_legado_y_valida()

    informal = almacenamiento.listar_cotizaciones(
        ruta, categoria="mercado_informal"
    )

    assert len(informal) == 1
    assert all(c["categoria"] == "mercado_informal" for c in informal)
    assert all(
        c["id"] != COTIZACION_SIN_PROCEDENCIA["id"] for c in informal
    )
    assert almacenamiento.listar_cotizaciones(ruta, categoria="oficial") == []


def test_registrar_cotizaciones_conserva_registros_sin_procedencia():
    """Añadir cotizaciones nuevas no elimina ni atribuye el historial antiguo."""
    ruta = _ruta_temporal()
    almacenamiento.guardar_historial(
        {
            "version_esquema": "1.0",
            "ultima_actualizacion": "2026-11-05T08:00:00Z",
            "cotizaciones": [dict(COTIZACION_SIN_PROCEDENCIA)],
            "actualizaciones": [],
            "incidencias": [],
        },
        ruta,
    )

    resultado = almacenamiento.registrar_cotizaciones(
        [COTIZACION_USD], almacenamiento._nuevo_uuid(), ruta
    )

    assert resultado["cotizaciones_agregadas"] == 1
    todas = almacenamiento.listar_cotizaciones(ruta)
    assert len(todas) == 2
    assert todas[0] == COTIZACION_SIN_PROCEDENCIA
    assert todas[0]["fuente"] is None
    assert todas[0]["categoria"] is None

    filtradas = almacenamiento.listar_cotizaciones(ruta, fuente="eltoque")
    assert len(filtradas) == 1
    assert filtradas[0]["id_actualizacion"] != COTIZACION_SIN_PROCEDENCIA[
        "id_actualizacion"
    ]


@pytest.mark.parametrize("campo", ["fuente", "categoria"])
def test_registrar_cotizaciones_rechaza_procedencia_nula(campo):
    """Una cotización nueva sin fuente o sin categoría se rechaza."""
    ruta = _ruta_temporal()
    cotizacion = dict(COTIZACION_USD)
    cotizacion[campo] = None

    with pytest.raises(ValueError):
        almacenamiento.registrar_cotizaciones(
            [cotizacion], almacenamiento._nuevo_uuid(), ruta
        )

    assert not ruta.exists()


@pytest.mark.parametrize("campo", ["fuente", "categoria"])
def test_registrar_cotizaciones_rechaza_procedencia_ausente(campo):
    """Una cotización nueva sin el campo de procedencia se rechaza."""
    ruta = _ruta_temporal()
    cotizacion = dict(COTIZACION_USD)
    del cotizacion[campo]

    with pytest.raises(ValueError):
        almacenamiento.registrar_cotizaciones(
            [cotizacion], almacenamiento._nuevo_uuid(), ruta
        )

    assert not ruta.exists()


def test_registrar_cotizaciones_rechaza_combinacion_no_admitida():
    """La fuente y la categoría deben corresponder entre sí."""
    ruta = _ruta_temporal()
    cotizacion = dict(
        COTIZACION_USD,
        fuente="bcc",
        categoria="mercado_informal",
    )

    with pytest.raises(ValueError):
        almacenamiento.registrar_cotizaciones(
            [cotizacion], almacenamiento._nuevo_uuid(), ruta
        )

    assert not ruta.exists()


def test_lote_con_una_cotizacion_invalida_no_guarda_parciales():
    """Si una cotización del lote no es válida, no se escribe ninguna."""
    ruta = _ruta_temporal()
    invalida = dict(COTIZACION_MLC, fuente=None)

    with pytest.raises(ValueError):
        almacenamiento.registrar_cotizaciones(
            [COTIZACION_USD, invalida],
            almacenamiento._nuevo_uuid(),
            ruta,
        )

    assert not ruta.exists()


def test_registrar_cotizaciones_acepta_bcc_y_eltoque():
    """Las procedencias válidas del proyecto siguen aceptándose."""
    ruta = _ruta_temporal()
    cotizacion_bcc = dict(
        COTIZACION_USD,
        fuente="bcc",
        categoria="oficial",
        tipo_tasa="tasa_especial",
        segmento="III",
        valor=832.0,
        valor_texto_original="832",
        url_fuente="https://api.bc.gob.cu/v1/tasas-de-cambio/activas",
    )

    resultado = almacenamiento.registrar_cotizaciones(
        [COTIZACION_USD, cotizacion_bcc],
        almacenamiento._nuevo_uuid(),
        ruta,
    )

    assert resultado["cotizaciones_agregadas"] == 2
    guardadas = almacenamiento.listar_cotizaciones(ruta)
    procedencias = {(c["fuente"], c["categoria"]) for c in guardadas}
    assert procedencias == {
        ("eltoque", "mercado_informal"),
        ("bcc", "oficial"),
    }


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