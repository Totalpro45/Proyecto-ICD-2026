"""Pruebas para la unificación de capturas de GAOS y Revolico.

Utiliza datos reales de los archivos procesados existentes sin modificarlos.
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "src")

from data.unificacion import unificar_capturas

GAOS_FILE = Path(
    "data/processed/anuncios/gaos/gaos_procesado_41998da8_20261107_225122.json"
)
REVOLICO_FILE = Path(
    "data/processed/anuncios/revolico/revolico_procesado_87abc29d_20261108_170228.json"
)


def _hash_archivo(ruta):
    """Devuelve el hash SHA-256 de un archivo para detectar modificaciones."""
    with open(ruta, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_unificar_capturas_incorpora_207_registros():
    """unificar_capturas combina los 100 anuncios de GAOS y los 107 de Revolico."""
    with tempfile.TemporaryDirectory() as tmpdir:
        salida = Path(tmpdir) / "unificado.json"
        id_captura, ruta = unificar_capturas(GAOS_FILE, REVOLICO_FILE, salida)

        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)

        assert datos["cantidad"] == 207
        assert len(datos["datos"]) == 207


def test_unificar_capturas_conta_por_fuente():
    """Hay exactamente 100 anuncios de GAOS y 107 de Revolico."""
    with tempfile.TemporaryDirectory() as tmpdir:
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(GAOS_FILE, REVOLICO_FILE, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        fuentes = [a.get("fuente") for a in datos["datos"]]
        assert fuentes.count("gaos") == 100
        assert fuentes.count("revolico") == 107


def test_unificar_capturas_conserva_ids_origen():
    """Los identificadores de origen (id_fuente) se conservan en cada anuncio."""
    with tempfile.TemporaryDirectory() as tmpdir:
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(GAOS_FILE, REVOLICO_FILE, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        ids_gaos = {a.get("id_fuente") for a in datos["datos"] if a.get("fuente") == "gaos"}
        ids_rev = {a.get("id_fuente") for a in datos["datos"] if a.get("fuente") == "revolico"}
        assert len(ids_gaos) == 100
        assert len(ids_rev) == 107


def test_unificar_capturas_revolico_usa_nueva_clasificacion():
    """Los anuncios de Revolico usan la clasificación por título, no el valor hardcodeado 'casa'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(GAOS_FILE, REVOLICO_FILE, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        tipos = {
            a.get("tipo_inmueble")
            for a in datos["datos"]
            if a.get("fuente") == "revolico"
        }
        assert "apartamento" in tipos
        assert "casa" in tipos
        assert "indeterminado" in tipos
        assert "no_vivienda" in tipos


def test_unificar_capturas_no_vivienda_no_desaparecen():
    """Los anuncios clasificados como no_vivienda se conservan en el conjunto."""
    with tempfile.TemporaryDirectory() as tmpdir:
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(GAOS_FILE, REVOLICO_FILE, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        no_vivienda = [a for a in datos["datos"] if a.get("tipo_inmueble") == "no_vivienda"]
        assert len(no_vivienda) >= 1


def test_unificar_capturas_conserva_precios_monedas():
    """Los precios y monedas originales se mantienen sin conversión."""
    with tempfile.TemporaryDirectory() as tmpdir:
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(GAOS_FILE, REVOLICO_FILE, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        # Anuncio de Revolico con precio alto
        rev = [a for a in datos["datos"] if a.get("id_fuente") == "43381124"][0]
        assert rev.get("precio") == 600000.0
        assert rev.get("moneda") == "USD"

        # Anuncio de GAOS con moneda EUR
        euros = [a for a in datos["datos"] if a.get("moneda") == "EUR"]
        assert len(euros) > 0


def test_unificar_capturas_conserva_valores_nulos():
    """Los valores ausentes se conservan como None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(GAOS_FILE, REVOLICO_FILE, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        # GAOS tiene provincia nula en este archivo
        g = [a for a in datos["datos"] if a.get("fuente") == "gaos"][0]
        assert g.get("provincia") is None
        assert g.get("municipio") is None

        # Revolico tiene area_m2 nulo en todos
        r = [a for a in datos["datos"] if a.get("fuente") == "revolico"][0]
        assert r.get("area_m2") is None


def test_unificar_capturas_no_modifica_archivos_entrada():
    """Los archivos de entrada no se modifican durante la unificación."""
    hash_gaos_antes = _hash_archivo(GAOS_FILE)
    hash_rev_antes = _hash_archivo(REVOLICO_FILE)

    with tempfile.TemporaryDirectory() as tmpdir:
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(GAOS_FILE, REVOLICO_FILE, salida)

    hash_gaos_despues = _hash_archivo(GAOS_FILE)
    hash_rev_despues = _hash_archivo(REVOLICO_FILE)

    assert hash_gaos_antes == hash_gaos_despues
    assert hash_rev_antes == hash_rev_despues


def test_unificar_capturas_procedencia_inequivoca():
    """Cada anuncio tiene un campo fuente que identifica su origen."""
    with tempfile.TemporaryDirectory() as tmpdir:
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(GAOS_FILE, REVOLICO_FILE, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        for anuncio in datos["datos"]:
            assert anuncio.get("fuente") in ("gaos", "revolico")

        # El envoltorio tiene metadatos de ambas capturas de origen
        assert datos.get("fuente") == "multifuente"
        assert len(datos.get("capturas_origen", [])) == 2
        assert datos["capturas_origen"][0]["fuente"] == "gaos"
        assert datos["capturas_origen"][1]["fuente"] == "revolico"
