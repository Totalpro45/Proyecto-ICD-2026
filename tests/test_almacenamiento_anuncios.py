"""Pruebas para el módulo de almacenamiento de anuncios inmobiliarios.

Comprueba:
- Que se pueden guardar y leer cotizaciones crudas y procesadas.
- Que crudos y procesados comparten el mismo id_captura.
- Que no se sobrescriben capturas previas.
- Que se pueden listar las capturas disponibles.
- Que leer una captura inexistente devuelve None.
- Que leer rechaza capturas incompletas y capturas cuyos identificadores
  internos no coinciden.
- Que el mapeo de crudos a procesados se hace internamente (sin una
  segunda extracción) mediante el mapeador existente.
- Que fallar al escribir un archivo deja los archivos temporales limpios y
  deshace lo ya publicado.
- Que se limpian temporales huérfanos de fallos previos.

Usa datos de prueba ficticios; no realiza peticiones HTTP ni toca archivos
reales del repositorio (usa carpetas temporales).
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from unittest.mock import patch

sys.path.insert(0, "src")

import data.almacenamiento_anuncios as almacenamiento
from data.almacenamiento_anuncios import (
    generar_id_captura,
    guardar_captura,
    leer_captura,
    listar_capturas,
    guardar_captura_completa,
)
from data.mapper import crear_anuncio
from data.models import AnuncioInmobiliario

from sources import gaos
from sources.revolico import mapear_anuncio_revolico

# --- Datos de ejemplo para Revolico ---

CRUDOS_REVOLICO_EJEMPLO = [
    {
        "id_fuente": "12345678",
        "url": "https://www.revolico.com/item/test-12345678",
        "precio": 150000,
        "moneda": "USD",
        "titulo": "Casa en venta en La Habana",
        "descripcion": None,
    },
    {
        "id_fuente": "87654321",
        "url": "https://www.revolico.com/item/test-87654321",
        "precio": 50000,
        "moneda": "USD",
        "titulo": "Apartamento en La Habana",
        "descripcion": None,
    },
]

URL_REVOLICO = "https://www.revolico.com/search?category=inmobiliaria&province=la-habana&subcategory=inmobiliaria-casas"


# --- Datos de ejemplo para pruebas ---

CRUDOS_EJEMPLO = [
    {
        "ulistingid": "abc-123",
        "vctitle": "Casa en venta",
        "precio": 150000,
        "vccurrencytype": "USD",
        "moneda": "USD",
    },
    {
        "ulistingid": "abc-456",
        "vctitle": "Apartamento en venta",
        "precio": 85000,
        "vccurrencytype": "USD",
    },
]


class _AnuncioFake:
    """Objeto simulado similar a AnuncioInmobiliario para pruebas."""

    def __init__(self, id_fuente: str, titulo: str, precio: float, moneda: str):
        self.id_fuente = id_fuente
        self.url = f"https://gaos.app/propiedades/{id_fuente}"
        self.fecha_captura = "2026-11-06T10:00:00Z"
        self.fecha_publicacion = None
        self.fecha_actualizacion = None
        self.provincia = "La Habana"
        self.municipio = None
        self.reparto = None
        self.direccion_texto = "Calle 23, Vedado"
        self.tipo_operacion = "venta"
        self.tipo_inmueble = "casa"
        self.area_m2 = 100.0
        self.tipo_area = None
        self.habitaciones = 3
        self.banos = 2
        self.planta = None
        self.estado_conservacion = "bueno"
        self.amueblado = None
        self.precio = precio
        self.moneda = moneda
        self.precio_usd = None
        self.tasa_conversion_usd = None
        self.tasa_fecha = None
        self.tasa_fuente = None
        self.precio_m2_usd = None
        self.tasa_id = None
        self.titulo = titulo
        self.descripcion = None
        self.vendedor_tipo = "particular"
        self.estado_parseo = "ok"
        self.notas_calidad = None
        self.es_posible_duplicado = False
        self.duplicado_grupo = None


ANUNCIOS_EJEMPLO = [
    _AnuncioFake("abc-123", "Casa en venta", 150000, "USD"),
    _AnuncioFake("abc-456", "Apartamento en venta", 85000, "USD"),
]


# --- Datos para pruebas de ampliación controlada ---

CRUDOS_LOTE_EJEMPLO = [
    {
        "ulistingid": "nuevo-001",
        "vctitle": "Anuncio nuevo 1",
        "dcprice": 100000,
        "vccurrencytype": "USD",
        "vcaddress": "Calle 1, Vedado",
    },
    {
        "ulistingid": "repetido-001",
        "vctitle": "Anuncio repetido previo",
        "dcprice": 50000,
        "vccurrencytype": "USD",
    },
    {
        "ulistingid": "dup-interno-001",
        "vctitle": "Duplicado interno 1",
        "dcprice": 30000,
        "vccurrencytype": "USD",
    },
    {
        "ulistingid": "dup-interno-001",
        "vctitle": "Duplicado interno 1 (repetido)",
        "dcprice": 30000,
        "vccurrencytype": "USD",
    },
    {
        "vctitle": "Anuncio sin ID",
        "dcprice": 20000,
        "vccurrencytype": "USD",
    },
]


CAPTURA_PREVIA_EJEMPLO = {
    "id_captura": "captura-previa-abc123",
    "tiene_crudo": True,
    "tiene_procesado": True,
}

LECTURA_PREVIA_EJEMPLO = {
    "crudo": {
        "id_captura": "captura-previa-abc123",
        "datos": [
            {
                "ulistingid": "repetido-001",
                "vctitle": "Anuncio repetido previo",
                "dcprice": 50000,
                "vccurrencytype": "USD",
            },
        ],
    },
    "procesado": {},
}


# --- Utilidades para pruebas ---


def _avanzar_al_siguiente_segundo() -> None:
    """Espera hasta que el reloj cambie de segundo.

    Permite generar capturas con marcas de tiempo distintas sin depender
    de un sleep corto que podría no cruzar el límite de segundo.
    """
    segundo_actual = datetime.now(timezone.utc).replace(microsecond=0)
    while datetime.now(timezone.utc).replace(microsecond=0) == segundo_actual:
        time.sleep(0.02)


# --- Pruebas de guardar_captura ---


def test_guardar_captura_crea_ambos_archivos():
    """Cada ejecución crea dos archivos: uno con los crudos y otro con las
    cotizaciones mapeadas, ambos con el mismo id_captura."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        id_captura = guardar_captura(CRUDOS_EJEMPLO, ANUNCIOS_EJEMPLO, ruta_crudo, ruta_procesado)

        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1

        assert id_captura[:8] in archivos_crudo[0].name
        assert id_captura[:8] in archivos_procesado[0].name

        # No deben quedar archivos temporales tras una escritura exitosa
        assert list(ruta_crudo.glob("*.tmp")) == []
        assert list(ruta_procesado.glob("*.tmp")) == []


def test_guardar_captura_no_sobrescribe():
    """Ejecutar dos veces con el mismo id_captura debe crear archivos distintos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        id_captura_1 = guardar_captura(CRUDOS_EJEMPLO, ANUNCIOS_EJEMPLO, ruta_crudo, ruta_procesado)
        id_captura_2 = guardar_captura(CRUDOS_EJEMPLO, ANUNCIOS_EJEMPLO, ruta_crudo, ruta_procesado)

        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))

        assert len(archivos_crudo) == 2
        assert len(archivos_procesado) == 2
        assert id_captura_1 != id_captura_2


def test_guardar_captura_devuelve_ambos_tipos():
    """Leer una captura debe devolver tanto crudos como procesados."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        id_captura = guardar_captura(CRUDOS_EJEMPLO, ANUNCIOS_EJEMPLO, ruta_crudo, ruta_procesado)

        resultado = leer_captura(id_captura, ruta_crudo, ruta_procesado)

        assert resultado is not None
        assert "crudo" in resultado
        assert "procesado" in resultado
        assert len(resultado["crudo"]["datos"]) == 2
        assert len(resultado["procesado"]["datos"]) == 2


def test_leer_captura_inexistente_devuelve_none():
    """Leer una captura que no existe debe devolver None."""
    resultado = leer_captura("id_inexistente")
    assert resultado is None


def test_leer_captura_rechaza_captura_incompleta():
    """Leer una captura con solo uno de los dos archivos debe devolver None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        id_captura = guardar_captura(CRUDOS_EJEMPLO[:1], ANUNCIOS_EJEMPLO[:1], ruta_crudo, ruta_procesado)

        # Solo crudo
        list(ruta_procesado.glob("gaos_procesado_*.json"))[0].unlink()
        assert leer_captura(id_captura, ruta_crudo, ruta_procesado) is None


def test_leer_captura_rechaza_id_interno_no_coincide():
    """Si el id_captura interno de un archivo no coincide, leer debe devolver None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        id_captura = guardar_captura(CRUDOS_EJEMPLO[:1], ANUNCIOS_EJEMPLO[:1], ruta_crudo, ruta_procesado)

        archivo_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))[0]
        datos = json.loads(archivo_crudo.read_text(encoding="utf-8"))
        datos["id_captura"] = "id_captura_diferente"
        archivo_crudo.write_text(json.dumps(datos), encoding="utf-8")

        assert leer_captura(id_captura, ruta_crudo, ruta_procesado) is None


def test_guardar_captura_fallo_escritura_hace_rollback_y_sin_temporales():
    """Si falla la publicación del segundo archivo, se deshace el primero y
    no quedan temporales."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        original = almacenamiento._escribir_json_atomico
        llamadas = {"n": 0}

        def falso(ruta, datos):
            llamadas["n"] += 1
            if llamadas["n"] == 2:
                raise OSError("disco lleno simulado")
            return original(ruta, datos)

        almacenamiento._escribir_json_atomico = falso
        try:
            with pytest.raises(OSError):
                guardar_captura(CRUDOS_EJEMPLO, ANUNCIOS_EJEMPLO, ruta_crudo, ruta_procesado)
        finally:
            almacenamiento._escribir_json_atomico = original

        # No quedó nada publicado ni temporales huérfanos
        assert list(ruta_crudo.glob("gaos_crudo_*.json")) == []
        assert list(ruta_procesado.glob("gaos_procesado_*.json")) == []
        assert list(ruta_crudo.glob("*.tmp")) == []
        assert list(ruta_procesado.glob("*.tmp")) == []


def test_guardar_captura_limpia_temporales_huerfanos():
    """Al guardar se eliminan temporales huérfanos de fallos previos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"
        ruta_crudo.mkdir(parents=True)
        ruta_procesado.mkdir(parents=True)

        orfano = ruta_crudo / "gaos_crudo_abcd1234_20260101_000000.json.tmp"
        orfano.write_text("basura", encoding="utf-8")
        assert orfano.exists()

        guardar_captura(CRUDOS_EJEMPLO, ANUNCIOS_EJEMPLO, ruta_crudo, ruta_procesado)

        assert not orfano.exists()
        assert list(ruta_crudo.glob("gaos_crudo_*.json")) == [list(ruta_crudo.glob("gaos_crudo_*.json"))[0]]


# --- Pruebas de listar_capturas ---


def test_listar_capturas_devuelve_ordenadas():
    """listar_capturas debe devolver las capturas ordenadas de más reciente a más antigua."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        guardar_captura(CRUDOS_EJEMPLO[:1], ANUNCIOS_EJEMPLO[:1], ruta_crudo, ruta_procesado)

        _avanzar_al_siguiente_segundo()

        guardar_captura(CRUDOS_EJEMPLO, ANUNCIOS_EJEMPLO, ruta_crudo, ruta_procesado)

        capturas = listar_capturas(ruta_crudo, ruta_procesado)

        assert len(capturas) == 2
        assert capturas[0]["fecha_captura"] > capturas[1]["fecha_captura"]


def test_listar_capturas_extrae_fecha_del_nombre():
    """La fecha listada es la marca de tiempo del nombre de archivo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        id_captura = guardar_captura(CRUDOS_EJEMPLO[:1], ANUNCIOS_EJEMPLO[:1], ruta_crudo, ruta_procesado)

        capturas = listar_capturas(ruta_crudo, ruta_procesado)

        assert len(capturas) == 1
        assert capturas[0]["id_captura"] == id_captura[:8]
        assert "_" in capturas[0]["fecha_captura"]  # YYYYMMDD_HHMMSS


# --- Pruebas de guardar_captura_completa ---


def test_guardar_captura_completa_mapea_internamente():
    """guardar_captura_completa debe aplicar el mapeador internamente,
    sin requerir que el llamador ya tenga los anuncios mapeados ni hacer una
    segunda extracción."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        id_captura = guardar_captura_completa(CRUDOS_EJEMPLO, ruta_crudo, ruta_procesado)

        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1

        assert id_captura[:8] in archivos_crudo[0].name
        assert id_captura[:8] in archivos_procesado[0].name

        resultado = leer_captura(id_captura, ruta_crudo, ruta_procesado)
        assert resultado is not None
        assert len(resultado["crudo"]["datos"]) == 2
        assert len(resultado["procesado"]["datos"]) == 2

        # El mapeador mapeó vctitle como título y no hubo conversión de moneda
        # (por tanto no hubo segunda petición ni tasa de cambio).
        procesado = resultado["procesado"]["datos"][0]
        assert procesado["titulo"] == "Casa en venta"
        assert procesado["precio_usd"] is None
        assert procesado["tasa_id"] is None


def test_guardar_captura_completa_usa_mismo_id_captura():
    """Ambos archivos deben compartir el mismo id_captura."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        id_captura = guardar_captura_completa(CRUDOS_EJEMPLO, ruta_crudo, ruta_procesado)

        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1

        assert id_captura[:8] in archivos_crudo[0].name
        assert id_captura[:8] in archivos_procesado[0].name


def test_guardar_captura_completa_devuelve_ambos_tipos():
    """guardar_captura_completa debe devolver tanto crudos como mapeados."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        id_captura = guardar_captura_completa(CRUDOS_EJEMPLO, ruta_crudo, ruta_procesado)

        resultado = leer_captura(id_captura, ruta_crudo, ruta_procesado)
        assert resultado is not None
        assert len(resultado["crudo"]["datos"]) == 2
        assert len(resultado["procesado"]["datos"]) == 2


def test_guardar_captura_completa_rechaza_datos_invalidos_no_guarda():
    """Si un valor de precio no es numérico, se rechaza y no se guarda nada."""
    datos_con_error = [
        {
            "ulistingid": "abc-123",
            "vctitle": "Casa en venta",
            "precio": "no es un número",
            "vccurrencytype": "USD",
            "moneda": "USD",
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        resultado = guardar_captura_completa(datos_con_error, ruta_crudo, ruta_procesado)

        assert resultado is None

        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))

        assert len(archivos_crudo) == 0
        assert len(archivos_procesado) == 0


def test_guardar_captura_completa_rechaza_precio_no_numerico_no_guarda():
    """Un precio como 'cien mil' no es numérico: no se guarda ningún archivo."""
    datos_con_error = [
        {
            "ulistingid": "abc-123",
            "vctitle": "Casa en venta",
            "precio": "cien mil",
            "vccurrencytype": "USD",
            "moneda": "USD",
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        resultado = guardar_captura_completa(datos_con_error, ruta_crudo, ruta_procesado)

        assert resultado is None

        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))

        assert len(archivos_crudo) == 0
        assert len(archivos_procesado) == 0


# --- Pruebas de integración: capturar_y_guardar (flujo extracción → almacenamiento) ---


def test_capturar_y_guardar_guarda_extraccion_exitosa():
    """extraer_listings devuelve datos -> se guardan crudos y procesados."""
    crudos_simulados = [
        {
            "ulistingid": "abc-123",
            "vctitle": "Casa en venta",
            "precio": 150000,
            "vccurrencytype": "USD",
            "moneda": "USD",
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        with patch("sources.gaos.extraer_listings", return_value=crudos_simulados):
            id_captura = gaos.capturar_y_guardar(
                ruta_crudo=ruta_crudo, ruta_procesado=ruta_procesado
            )

        assert id_captura is not None
        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))
        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1

        # Los archivos deben llevar el id_captura y contener los datos crudos.
        assert id_captura[:8] in archivos_crudo[0].name
        assert id_captura[:8] in archivos_procesado[0].name


def test_capturar_y_guardar_extraccion_vacia_no_guarda():
    """extraer_listings devuelve [] -> no se guarda ninguna captura."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        with patch("sources.gaos.extraer_listings", return_value=[]):
            id_captura = gaos.capturar_y_guardar(
                ruta_crudo=ruta_crudo, ruta_procesado=ruta_procesado
            )

    assert id_captura is None
    assert list(ruta_crudo.glob("gaos_crudo_*.json")) == []
    assert list(ruta_procesado.glob("gaos_procesado_*.json")) == []


def test_capturar_y_guardar_excepcion_extraccion_no_guarda():
    """Si extraer_listings lanza una excepción, se informa, se retorna None
    y no se guarda ningún archivo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        with patch(
            "sources.gaos.extraer_listings",
            side_effect=ConnectionError("timeout simulado"),
        ):
            id_captura = gaos.capturar_y_guardar(
                ruta_crudo=ruta_crudo, ruta_procesado=ruta_procesado
            )

    assert id_captura is None
    assert list(ruta_crudo.glob("gaos_crudo_*.json")) == []
    assert list(ruta_procesado.glob("gaos_procesado_*.json")) == []


# --- Pruebas de regresión: campos del mapeador en el JSON procesado ---


CRUDOS_GAOS_EJEMPLO = [
    {
        "ulistingid": "gaos-001",
        "vctitle": "Apartamento en el Vedado",
        "vcaddress": "Calle 23, Vedado",
        "dcprice": 150000,
        "vccurrencytype": "USD",
        "dcoriginalprice": 150000,
        "ibeds": 2,
        "ibaths": 1,
        "ikitchens": 1,
        "iarea": 80,
        "icontracttypeid": 1,
        "ilistingtypeid": 2,
        "vcconstructioncondition": "good",
        "publisher": {"accountType": "private"},
    },
    {
        "ulistingid": "gaos-002",
        "vctitle": "Casa en Marianao",
        "vcaddress": None,
        "dcprice": None,
        "vccurrencytype": "USD",
        "dcoriginalprice": None,
        "ibeds": None,
        "ibaths": None,
        "ikitchens": None,
        "iarea": None,
        "icontracttypeid": None,
        "ilistingtypeid": None,
        "vcconstructioncondition": None,
        "publisher": None,
    },
    {
        "ulistingid": "gaos-003",
        "vctitle": "Casa con vendedor desconocido",
        "vcaddress": None,
        "dcprice": 100000,
        "vccurrencytype": "USD",
        "dcoriginalprice": 100000,
        "ibeds": 3,
        "ibaths": 2,
        "ikitchens": 1,
        "iarea": 120,
        "icontracttypeid": 1,
        "ilistingtypeid": 1,
        "vcconstructioncondition": "minor_repairs",
        "publisher": {"accountType": "realtor"},
    },
]


def _anuncios_mapeados_desde_gaos(fecha_captura: str) -> list[AnuncioInmobiliario]:
    """Mapea datos crudos de GAOS al esquema común usando el mapeador.

    Reutiliza los mismos diccionarios de mapeo que _datos_para_mapeo en
    data.almacenamiento_anuncios, importados de sources.gaos.
    """
    from data.almacenamiento_anuncios import ACCOUNT_TYPE_MAP

    anuncios = []
    for dato in CRUDOS_GAOS_EJEMPLO:
        publisher = dato.get("publisher")
        account_type = publisher.get("accountType") if isinstance(publisher, dict) else None

        anuncios.append(
            crear_anuncio(
                {
                    "fuente": "gaos",
                    "id_fuente": dato.get("ulistingid") or "",
                    "url": f"https://gaos.app/propiedades/{dato.get('ulistingid') or ''}",
                    "fecha_captura": fecha_captura,
                    "fecha_publicacion": None,
                    "fecha_actualizacion": None,
                    "provincia": "La Habana",
                    "municipio": None,
                    "reparto": None,
                    "direccion_texto": dato.get("vcaddress"),
                    "tipo_operacion": gaos.CONTRACT_TYPE_MAP.get(
                        dato.get("icontracttypeid")
                    ),
                    "tipo_inmueble": gaos.LISTING_TYPE_MAP.get(
                        dato.get("ilistingtypeid")
                    ),
                    "area_m2": dato.get("iarea"),
                    "tipo_area": None,
                    "habitaciones": dato.get("ibeds"),
                    "banos": dato.get("ibaths"),
                    "planta": None,
                    "estado_conservacion": gaos.ESTADO_CONSERVACION_MAP.get(
                        dato.get("vcconstructioncondition")
                    ),
                    "amueblado": None,
                    "precio": dato.get("dcprice"),
                    "moneda": dato.get("vccurrencytype"),
                    "precio_usd": None,
                    "tasa_conversion_usd": None,
                    "tasa_fecha": None,
                    "tasa_fuente": None,
                    "precio_m2_usd": None,
                    "tasa_id": None,
                    "titulo": dato.get("vctitle"),
                    "descripcion": None,
                    "vendedor_tipo": ACCOUNT_TYPE_MAP.get(account_type),
                    "estado_parseo": "ok",
                    "notas_calidad": None,
                    "es_posible_duplicado": False,
                    "duplicado_grupo": None,
                }
            )
        )
    return anuncios


def test_guardar_captura_guarda_campos_mapeados_desde_anuncio():
    """guardar_captura debe escribir en el JSON procesado los campos del
    objeto AnuncioInmobiliario ya mapeado, no intentar leer claves del
    esquema común directamente de los crudos de GAOS (que usan claves
    distintas: ulistingid, dcprice, vccurrencytype, etc.)."""
    from datetime import datetime, timezone

    fecha_captura = datetime.now(timezone.utc).isoformat()
    anuncios = _anuncios_mapeados_desde_gaos(fecha_captura)

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        id_captura = guardar_captura(CRUDOS_GAOS_EJEMPLO, anuncios, ruta_crudo, ruta_procesado)

        archivo_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))[0]
        with open(archivo_procesado, "r", encoding="utf-8") as f:
            datos_procesados = json.load(f)

    assert datos_procesados["id_captura"] == id_captura
    assert datos_procesados["cantidad"] == 3

    anuncios_proc = datos_procesados["datos"]

    # Anuncio 1: todos los campos disponibles deben estar presentes
    a1 = anuncios_proc[0]
    assert a1["id_fuente"] == "gaos-001"
    assert a1["url"] == "https://gaos.app/propiedades/gaos-001"
    assert a1["fecha_captura"] == fecha_captura
    assert a1["precio"] == 150000
    assert a1["moneda"] == "USD"
    assert a1["area_m2"] == 80
    assert a1["habitaciones"] == 2
    assert a1["banos"] == 1
    assert a1["direccion_texto"] == "Calle 23, Vedado"
    assert a1["tipo_operacion"] == "venta"
    assert a1["tipo_inmueble"] == "apartamento"
    assert a1["estado_conservacion"] == "bueno"
    assert a1["titulo"] == "Apartamento en el Vedado"
    assert a1["vendedor_tipo"] == "particular"
    assert a1["provincia"] == "La Habana"

    # Anuncio 2: campos ausentes en el crudo deben ser nulos en el procesado
    a2 = anuncios_proc[1]
    assert a2["id_fuente"] == "gaos-002"
    assert a2["precio"] is None
    assert a2["moneda"] == "USD"
    assert a2["area_m2"] is None
    assert a2["habitaciones"] is None
    assert a2["banos"] is None
    assert a2["direccion_texto"] is None
    assert a2["tipo_operacion"] is None
    assert a2["tipo_inmueble"] is None
    assert a2["estado_conservacion"] is None
    assert a2["titulo"] == "Casa en Marianao"
    assert a2["vendedor_tipo"] is None

    # Anuncio 3: gaos-003 con vendedor "realtor" (no mapeable → None) y condición mapeable
    a3 = anuncios_proc[2]
    assert a3["id_fuente"] == "gaos-003"
    assert a3["tipo_operacion"] == "venta"
    assert a3["tipo_inmueble"] == "casa"
    assert a3["estado_conservacion"] == "regular"
    assert a3["vendedor_tipo"] is None

    # Anuncio 3: gaos-003 con vendedor "realtor" (no mapeable) y condición mapeable
    a3 = anuncios_proc[2]
    assert a3["id_fuente"] == "gaos-003"
    assert a3["tipo_operacion"] == "venta"
    assert a3["tipo_inmueble"] == "casa"
    assert a3["estado_conservacion"] == "regular"
    assert a3["vendedor_tipo"] is None


def test_guardar_captura_completa_guarda_campos_mapeados():
    """guardar_captura_completa debe mapear internamente y guardar los
    campos del esquema común correctamente en el JSON procesado, sin leer
    claves del esquema común directamente de los crudos de GAOS."""
    from datetime import datetime, timezone

    fecha_captura = "2026-11-07T12:00:00Z"

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        # Sobrescribir obtener_fecha_captura para usar una fecha fija
        import data.almacenamiento_anuncios as almacenamiento

        original = almacenamiento.obtener_fecha_captura
        almacenamiento.obtener_fecha_captura = lambda: fecha_captura
        try:
            id_captura = guardar_captura_completa(CRUDOS_GAOS_EJEMPLO, ruta_crudo, ruta_procesado)
        finally:
            almacenamiento.obtener_fecha_captura = original

        assert id_captura is not None

        archivo_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))[0]
        with open(archivo_procesado, "r", encoding="utf-8") as f:
            datos_procesados = json.load(f)

    assert datos_procesados["cantidad"] == 3

    a1 = datos_procesados["datos"][0]
    assert a1["id_fuente"] == "gaos-001"
    assert a1["precio"] == 150000
    assert a1["moneda"] == "USD"
    assert a1["area_m2"] == 80
    assert a1["habitaciones"] == 2
    assert a1["banos"] == 1
    assert a1["direccion_texto"] == "Calle 23, Vedado"
    assert a1["tipo_operacion"] == "venta"
    assert a1["tipo_inmueble"] == "apartamento"
    assert a1["estado_conservacion"] == "bueno"
    assert a1["titulo"] == "Apartamento en el Vedado"
    assert a1["vendedor_tipo"] == "particular"

    a2 = datos_procesados["datos"][1]
    assert a2["id_fuente"] == "gaos-002"
    assert a2["precio"] is None
    assert a2["moneda"] == "USD"
    assert a2["area_m2"] is None
    assert a2["habitaciones"] is None
    assert a2["banos"] is None
    assert a2["direccion_texto"] is None
    assert a2["tipo_operacion"] is None
    assert a2["tipo_inmueble"] is None
    assert a2["estado_conservacion"] is None
    assert a2["titulo"] == "Casa en Marianao"
    assert a2["vendedor_tipo"] is None

    a3 = datos_procesados["datos"][2]
    assert a3["id_fuente"] == "gaos-003"
    assert a3["precio"] == 100000
    assert a3["moneda"] == "USD"
    assert a3["area_m2"] == 120
    assert a3["habitaciones"] == 3
    assert a3["banos"] == 2
    assert a3["direccion_texto"] is None
    assert a3["tipo_operacion"] == "venta"
    assert a3["tipo_inmueble"] == "casa"
    assert a3["estado_conservacion"] == "regular"
    assert a3["titulo"] == "Casa con vendedor desconocido"
    # "realtor" no está en ACCOUNT_TYPE_MAP, por tanto debe ser None
    assert a3["vendedor_tipo"] is None


# --- Pruebas de ampliación controlada ---


def test_ampliar_captura_controlada_guarda_lote_completo_y_estadisticas():
    """ampliar_captura_controlada guarda el lote completo (sin filtrar) e
    informa cuántos son nuevos, repetidos, duplicados internos y sin id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        with patch(
            "sources.gaos.listar_capturas",
            return_value=[CAPTURA_PREVIA_EJEMPLO],
        ), patch(
            "sources.gaos.leer_captura",
            return_value=LECTURA_PREVIA_EJEMPLO,
        ), patch(
            "sources.gaos.extraer_listings",
            return_value=CRUDOS_LOTE_EJEMPLO,
        ):
            resultado = gaos.ampliar_captura_controlada(
                limite_paginas=5,
                ruta_crudo=ruta_crudo,
                ruta_procesado=ruta_procesado,
            )

        assert resultado is not None
        assert resultado["consultados"] == 5
        assert resultado["nuevos"] == 2  # nuevo-001 y dup-interno-001 (primera vez)
        assert resultado["repetidos_previos"] == 1  # repetido-001
        assert resultado["duplicados_internos"] == 1  # dup-interno-001 (segunda vez)
        assert resultado["sin_id"] == 1  # anuncio sin ulistingid
        assert resultado["id_captura"] is not None

        # El lote completo se guardó (5 anuncios en crudo y 5 en procesado)
        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))
        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1
        assert resultado["id_captura"][:8] in archivos_crudo[0].name
        assert resultado["id_captura"][:8] in archivos_procesado[0].name


def test_ampliar_captura_controlada_error_extraccion_no_guarda():
    """Si extraer_listings falla, no se guarda ninguna captura."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        with patch(
            "sources.gaos.listar_capturas",
            return_value=[CAPTURA_PREVIA_EJEMPLO],
        ), patch(
            "sources.gaos.leer_captura",
            return_value=LECTURA_PREVIA_EJEMPLO,
        ), patch(
            "sources.gaos.extraer_listings",
            side_effect=ConnectionError("fallo de red simulado"),
        ):
            resultado = gaos.ampliar_captura_controlada(
                limite_paginas=5,
                ruta_crudo=ruta_crudo,
                ruta_procesado=ruta_procesado,
            )

    assert resultado is None
    assert list(ruta_crudo.glob("gaos_crudo_*.json")) == []
    assert list(ruta_procesado.glob("gaos_procesado_*.json")) == []


def test_ampliar_captura_controlada_error_lectura_previas_no_guarda():
    """Si fallar la lectura de capturas previas, no se guarda ninguna captura."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        with patch(
            "sources.gaos.listar_capturas",
            side_effect=OSError("disco no disponible"),
        ), patch(
            "sources.gaos.extraer_listings",
            return_value=CRUDOS_LOTE_EJEMPLO,
        ):
            resultado = gaos.ampliar_captura_controlada(
                limite_paginas=5,
                ruta_crudo=ruta_crudo,
                ruta_procesado=ruta_procesado,
            )

    assert resultado is None
    assert list(ruta_crudo.glob("gaos_crudo_*.json")) == []
    assert list(ruta_procesado.glob("gaos_procesado_*.json")) == []


def test_ampliar_captura_controlada_sin_capturas_previas_todo_nuevo():
    """Si no hay capturas previas, todos los anuncios con id se consideran nuevos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "crudo"
        ruta_procesado = Path(tmpdir) / "procesado"

        with patch(
            "sources.gaos.listar_capturas",
            return_value=[],
        ), patch(
            "sources.gaos.extraer_listings",
            return_value=CRUDOS_LOTE_EJEMPLO,
        ):
            resultado = gaos.ampliar_captura_controlada(
                limite_paginas=5,
                ruta_crudo=ruta_crudo,
                ruta_procesado=ruta_procesado,
            )

    assert resultado is not None
    assert resultado["consultados"] == 5
    assert resultado["nuevos"] == 3  # nuevo-001, dup-interno-001 (primera vez), repetido-001
    assert resultado["repetidos_previos"] == 0
    assert resultado["duplicados_internos"] == 1
    assert resultado["sin_id"] == 1


# --- Pruebas de desacoplamiento: mapeador personalizado y rutas por fuente ---


def test_guardar_captura_completa_mapeador_personalizado_guarda_en_rutas_distintas():
    """guardar_captura_completa con mapeador personalizado guarda en las rutas
    especificadas y usa el mapeador proporcionado en lugar del de GAOS."""
    from data.models import AnuncioInmobiliario

    def mi_mapeador(dato, fecha_captura):
        return AnuncioInmobiliario(
            fuente="fuente_prueba",
            id_fuente=dato.get("id", ""),
            url=dato.get("url", ""),
            fecha_captura=fecha_captura,
            precio=dato.get("precio"),
            moneda=dato.get("moneda"),
            titulo=dato.get("titulo"),
        )

    crudos = [
        {"id": "test-001", "titulo": "Anuncio prueba 1", "precio": 100000, "moneda": "USD"},
        {"id": "test-002", "titulo": "Anuncio prueba 2", "precio": 200000, "moneda": "USD"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "mi_fuente" / "crudo"
        ruta_procesado = Path(tmpdir) / "mi_fuente" / "procesado"

        id_captura = guardar_captura_completa(
            crudos,
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
            mapear_func=mi_mapeador,
        )

        assert id_captura is not None

        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1
        assert id_captura[:8] in archivos_crudo[0].name
        assert id_captura[:8] in archivos_procesado[0].name

        # Verificar que el mapeador personalizado se usó
        with open(archivos_procesado[0], encoding="utf-8") as f:
            datos_procesados = json.load(f)

        assert datos_procesados["cantidad"] == 2
        assert datos_procesados["datos"][0]["id_fuente"] == "test-001"
        assert datos_procesados["datos"][0]["titulo"] == "Anuncio prueba 1"
        assert datos_procesados["datos"][0]["precio"] == 100000
        assert datos_procesados["datos"][0]["moneda"] == "USD"
        assert datos_procesados["datos"][0]["vendedor_tipo"] is None  # no mapeado


def test_guardar_captura_completa_sin_mapeador_usa_mapeador_de_gaos():
    """Regresión: llamar a guardar_captura_completa sin mapeador usa el
    mapeador interno de GAOS y guarda en las rutas indicadas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "gaos" / "crudo"
        ruta_procesado = Path(tmpdir) / "gaos" / "procesado"

        id_captura = guardar_captura_completa(
            CRUDOS_GAOS_EJEMPLO, ruta_crudo=ruta_crudo, ruta_procesado=ruta_procesado
        )

        assert id_captura is not None

        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1

        with open(archivos_procesado[0], encoding="utf-8") as f:
            datos_procesados = json.load(f)

        assert datos_procesados["cantidad"] == 3
        # El mapeador de GAOS mapea vctitle como título
        assert datos_procesados["datos"][0]["titulo"] == "Apartamento en el Vedado"
        assert datos_procesados["datos"][0]["precio"] == 150000
        assert datos_procesados["datos"][0]["moneda"] == "USD"


def test_dos_fuentes_guardan_en_carpetas_distintas():
    """Dos fuentes distintas guardan en carpetas distintas sin mezclar datos."""
    from data.models import AnuncioInmobiliario

    def mi_mapeador(dato, fecha_captura):
        return AnuncioInmobiliario(
            fuente="fuente_b",
            id_fuente=dato.get("id", ""),
            url=dato.get("url", ""),
            fecha_captura=fecha_captura,
            precio=dato.get("precio"),
            moneda=dato.get("moneda"),
            titulo=dato.get("titulo"),
        )

    crudos_fuente_a = [
        {"id": "a-001", "titulo": "Anuncio A", "precio": 50000, "moneda": "USD"},
    ]
    crudos_fuente_b = [
        {"id": "b-001", "titulo": "Anuncio B", "precio": 75000, "moneda": "USD"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_a_crudo = Path(tmpdir) / "fuente_a" / "crudo"
        ruta_a_procesado = Path(tmpdir) / "fuente_a" / "procesado"
        ruta_b_crudo = Path(tmpdir) / "fuente_b" / "crudo"
        ruta_b_procesado = Path(tmpdir) / "fuente_b" / "procesado"

        id_captura_a = guardar_captura_completa(
            crudos_fuente_a, ruta_crudo=ruta_a_crudo, ruta_procesado=ruta_a_procesado
        )
        id_captura_b = guardar_captura_completa(
            crudos_fuente_b,
            ruta_crudo=ruta_b_crudo,
            ruta_procesado=ruta_b_procesado,
            mapear_func=mi_mapeador,
        )

        assert id_captura_a is not None
        assert id_captura_b is not None
        assert id_captura_a != id_captura_b

        archivos_a_crudo = list(ruta_a_crudo.glob("gaos_crudo_*.json"))
        archivos_a_procesado = list(ruta_a_procesado.glob("gaos_procesado_*.json"))
        archivos_b_crudo = list(ruta_b_crudo.glob("gaos_crudo_*.json"))
        archivos_b_procesado = list(ruta_b_procesado.glob("gaos_procesado_*.json"))

        assert len(archivos_a_crudo) == 1
        assert len(archivos_a_procesado) == 1
        assert len(archivos_b_crudo) == 1
        assert len(archivos_b_procesado) == 1

        # Verificar contenido de la fuente A (mapeador GAOS)
        with open(archivos_a_procesado[0], encoding="utf-8") as f:
            datos_a = json.load(f)
        assert datos_a["datos"][0]["titulo"] == "Anuncio A"

        # Verificar contenido de la fuente B (mapeador personalizado)
        with open(archivos_b_procesado[0], encoding="utf-8") as f:
            datos_b = json.load(f)
        assert datos_b["datos"][0]["titulo"] == "Anuncio B"


# --- Pruebas de soporte multfuente (GAOS y Revolico) ---


def _guardar_captura_revolico_ejemplo(ruta_crudo, ruta_procesado):
    """Guarda una captura de Revolico de ejemplo y devuelve su id_captura."""
    return guardar_captura_completa(
        CRUDOS_REVOLICO_EJEMPLO,
        ruta_crudo=ruta_crudo,
        ruta_procesado=ruta_procesado,
        mapear_func=mapear_anuncio_revolico,
        prefijo_archivo="revolico",
        fuente="revolico",
        url_fuente=URL_REVOLICO,
    )


def test_leer_captura_revolico_por_prefijo_y_rutas():
    """leer_captura con prefijo_archivo='revolico' localiza archivos de
    Revolico y devuelve crudo y procesado relacionados por id_captura."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "revolico" / "crudo"
        ruta_procesado = Path(tmpdir) / "revolico" / "procesado"

        id_captura = _guardar_captura_revolico_ejemplo(ruta_crudo, ruta_procesado)

        resultado = leer_captura(
            id_captura,
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
            prefijo_archivo="revolico",
        )

        assert resultado is not None
        assert resultado["crudo"]["id_captura"] == id_captura
        assert resultado["procesado"]["id_captura"] == id_captura
        assert resultado["crudo"]["fuente"] == "revolico"
        assert resultado["crudo"]["url_fuente"] == URL_REVOLICO
        assert resultado["procesado"]["fuente"] == "revolico"
        assert resultado["procesado"]["url_fuente"] == URL_REVOLICO
        assert len(resultado["crudo"]["datos"]) == 2
        assert len(resultado["procesado"]["datos"]) == 2


def test_listar_capturas_revolico_por_prefijo_y_rutas():
    """listar_capturas con prefijo_archivo='revolico' lista capturas de
    Revolico usando rutas de Revolico."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "revolico" / "crudo"
        ruta_procesado = Path(tmpdir) / "revolico" / "procesado"

        id_captura = _guardar_captura_revolico_ejemplo(ruta_crudo, ruta_procesado)

        capturas = listar_capturas(
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
            prefijo_archivo="revolico",
        )

        assert len(capturas) == 1
        assert capturas[0]["id_captura"] == id_captura[:8]
        assert capturas[0]["tiene_crudo"] is True
        assert capturas[0]["tiene_procesado"] is True


def test_leer_captura_gaos_sin_prefijo_sigue_funcionando():
    """Regresión: leer_captura sin prefijo_archivo usa 'gaos' por defecto
    y localiza archivos gaos_*."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "gaos" / "crudo"
        ruta_procesado = Path(tmpdir) / "gaos" / "procesado"

        id_captura = guardar_captura_completa(
            CRUDOS_EJEMPLO, ruta_crudo=ruta_crudo, ruta_procesado=ruta_procesado
        )

        resultado = leer_captura(id_captura, ruta_crudo, ruta_procesado)

        assert resultado is not None
        assert resultado["crudo"]["id_captura"] == id_captura
        assert resultado["procesado"]["id_captura"] == id_captura


def test_listar_capturas_gaos_sin_prefijo_sigue_funcionando():
    """Regresión: listar_capturas sin prefijo_archivo usa 'gaos' por defecto
    y lista archivos gaos_*."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "gaos" / "crudo"
        ruta_procesado = Path(tmpdir) / "gaos" / "procesado"

        id_captura = guardar_captura_completa(
            CRUDOS_EJEMPLO, ruta_crudo=ruta_crudo, ruta_procesado=ruta_procesado
        )

        capturas = listar_capturas(ruta_crudo, ruta_procesado)

        assert len(capturas) == 1
        assert capturas[0]["id_captura"] == id_captura[:8]
        assert capturas[0]["tiene_crudo"] is True
        assert capturas[0]["tiene_procesado"] is True


def test_listar_capturas_solo_crudo_muestra_captura():
    """listar_capturas muestra una captura aunque solo exista el archivo
    crudo (no exige que ambos existan)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "gaos" / "crudo"
        ruta_procesado = Path(tmpdir) / "gaos" / "procesado"

        id_captura = generar_id_captura()
        timestamp = "20261108_120000"
        nombre = f"gaos_crudo_{id_captura[:8]}_{timestamp}.json"

        datos = {
            "id_captura": id_captura,
            "fecha_captura": "2026-11-08T12:00:00Z",
            "fuente": "gaos",
            "url_fuente": "https://gaos.app/propiedades",
            "cantidad": 1,
            "datos": [{"id_fuente": "1", "titulo": "Test"}],
        }

        ruta_crudo.mkdir(parents=True, exist_ok=True)
        ruta_procesado.mkdir(parents=True, exist_ok=True)

        (ruta_crudo / nombre).write_text(json.dumps(datos), encoding="utf-8")

        capturas = listar_capturas(ruta_crudo, ruta_procesado)

        assert len(capturas) == 1
        assert capturas[0]["id_captura"] == id_captura[:8]
        assert capturas[0]["tiene_crudo"] is True
        assert capturas[0]["tiene_procesado"] is False


def test_listar_capturas_solo_procesado_muestra_captura():
    """listar_capturas muestra una captura aunque solo exista el archivo
    procesado (no exige que ambos existan)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "gaos" / "crudo"
        ruta_procesado = Path(tmpdir) / "gaos" / "procesado"

        id_captura = generar_id_captura()
        timestamp = "20261108_120000"
        nombre = f"gaos_procesado_{id_captura[:8]}_{timestamp}.json"

        datos = {
            "id_captura": id_captura,
            "fecha_captura": "2026-11-08T12:00:00Z",
            "fuente": "gaos",
            "url_fuente": "https://gaos.app/propiedades",
            "cantidad": 1,
            "datos": [{"id_fuente": "1", "titulo": "Test"}],
        }

        ruta_crudo.mkdir(parents=True, exist_ok=True)
        ruta_procesado.mkdir(parents=True, exist_ok=True)

        (ruta_procesado / nombre).write_text(json.dumps(datos), encoding="utf-8")

        capturas = listar_capturas(ruta_crudo, ruta_procesado)

        assert len(capturas) == 1
        assert capturas[0]["id_captura"] == id_captura[:8]
        assert capturas[0]["tiene_crudo"] is False
        assert capturas[0]["tiene_procesado"] is True


def test_leer_captura_rechaza_id_interno_no_coincide_con_prefijo_revolico():
    """leer_captura con prefijo 'revolico' rechaza si el id_captura interno
    de los archivos no coincide con el solicitado."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "revolico" / "crudo"
        ruta_procesado = Path(tmpdir) / "revolico" / "procesado"

        id_captura = _guardar_captura_revolico_ejemplo(ruta_crudo, ruta_procesado)

        # Intentar leer con un id_captura diferente al guardado
        resultado = leer_captura(
            "otro_id_captura_que_no_existe",
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
            prefijo_archivo="revolico",
        )

        assert resultado is None


# --- Pruebas de guardado multifuente (guardar_captura_completa) ---


def test_guardar_captura_completa_revolico_guarda_ambos_archivos_con_mismo_id():
    """guardar_captura_completa con prefijo 'revolico' crea crudo y procesado
    con el mismo id_captura y metadatos de Revolico."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "revolico" / "crudo"
        ruta_procesado = Path(tmpdir) / "revolico" / "procesado"

        id_captura = guardar_captura_completa(
            CRUDOS_REVOLICO_EJEMPLO,
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
            mapear_func=mapear_anuncio_revolico,
            prefijo_archivo="revolico",
            fuente="revolico",
            url_fuente=URL_REVOLICO,
        )

        assert id_captura is not None

        archivos_crudo = list(ruta_crudo.glob("revolico_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("revolico_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1

        # Mismo id_captura en los nombres de archivo
        assert id_captura[:8] in archivos_crudo[0].name
        assert id_captura[:8] in archivos_procesado[0].name

        # Leer ambos archivos y verificar metadatos
        with open(archivos_crudo[0], encoding="utf-8") as f:
            datos_crudos = json.load(f)
        with open(archivos_procesado[0], encoding="utf-8") as f:
            datos_procesados = json.load(f)

        assert datos_crudos["id_captura"] == id_captura
        assert datos_procesados["id_captura"] == id_captura
        assert datos_crudos["fuente"] == "revolico"
        assert datos_crudos["url_fuente"] == URL_REVOLICO
        assert datos_procesados["fuente"] == "revolico"
        assert datos_procesados["url_fuente"] == URL_REVOLICO


def test_guardar_captura_completa_gaos_predeterminados_sigue_funcionando():
    """Regresión: guardar_captura_completa sin parámetros de fuente usa los
    predeterminados de GAOS y guarda archivos gaos_* con metadatos de GAOS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "gaos" / "crudo"
        ruta_procesado = Path(tmpdir) / "gaos" / "procesado"

        id_captura = guardar_captura_completa(
            CRUDOS_EJEMPLO,
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
        )

        assert id_captura is not None

        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1

        # Mismo id_captura en los nombres de archivo
        assert id_captura[:8] in archivos_crudo[0].name
        assert id_captura[:8] in archivos_procesado[0].name

        # Leer ambos archivos y verificar metadatos predeterminados de GAOS
        with open(archivos_crudo[0], encoding="utf-8") as f:
            datos_crudos = json.load(f)
        with open(archivos_procesado[0], encoding="utf-8") as f:
            datos_procesados = json.load(f)

        assert datos_crudos["id_captura"] == id_captura
        assert datos_procesados["id_captura"] == id_captura
        assert datos_crudos["fuente"] == "gaos"
        assert datos_crudos["url_fuente"] == "https://gaos.app/propiedades"
        assert datos_procesados["fuente"] == "gaos"
        assert datos_procesados["url_fuente"] == "https://gaos.app/propiedades"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
