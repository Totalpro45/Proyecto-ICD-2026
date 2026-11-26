"""Pruebas para la unificación de capturas de GAOS y Revolico.

Usa capturas sintéticas creadas dentro de las propias pruebas, con la misma
estructura que los archivos procesados reales. No depende de capturas locales
ignoradas por Git ni de datos personales.
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "src")

from data.unificacion import unificar_capturas

FECHA_CAPTURA = "2026-11-01T00:00:00+00:00"

CAPTURA_GAOS = {
    "id_captura": "gaos-prueba-0001",
    "fecha_captura": FECHA_CAPTURA,
    "fuente": "gaos",
    "url_fuente": "https://gaos.app/propiedades",
    "cantidad": 3,
    "datos": [
        {
            "id_fuente": "gaos-1",
            "url": "https://gaos.app/propiedades/gaos-1",
            "fecha_captura": FECHA_CAPTURA,
            "provincia": None,
            "municipio": None,
            "reparto": None,
            "direccion_texto": None,
            "tipo_operacion": "venta",
            "tipo_inmueble": "casa",
            "area_m2": 120.0,
            "tipo_area": None,
            "habitaciones": 3,
            "banos": 2,
            "planta": None,
            "estado_conservacion": None,
            "amueblado": None,
            "precio": 50000.0,
            "moneda": "USD",
            "titulo": "Casa en Marianao",
            "descripcion": None,
        },
        {
            "id_fuente": "gaos-2",
            "url": "https://gaos.app/propiedades/gaos-2",
            "fecha_captura": FECHA_CAPTURA,
            "provincia": "La Habana",
            "municipio": "Plaza de la Revolución",
            "reparto": None,
            "direccion_texto": None,
            "tipo_operacion": "venta",
            "tipo_inmueble": "apartamento",
            "area_m2": 80.0,
            "tipo_area": None,
            "habitaciones": 2,
            "banos": 1,
            "planta": None,
            "estado_conservacion": None,
            "amueblado": None,
            "precio": 40000.0,
            "moneda": "EUR",
            "titulo": "Apartamento en el Vedado",
            "descripcion": None,
        },
        {
            "id_fuente": "gaos-3",
            "url": "https://gaos.app/propiedades/gaos-3",
            "fecha_captura": FECHA_CAPTURA,
            "provincia": "La Habana",
            "municipio": "Centro Habana",
            "reparto": None,
            "direccion_texto": None,
            "tipo_operacion": "venta",
            "tipo_inmueble": "casa",
            "area_m2": 150.0,
            "tipo_area": None,
            "habitaciones": 4,
            "banos": 2,
            "planta": None,
            "estado_conservacion": None,
            "amueblado": None,
            "precio": 30000.0,
            "moneda": "USD",
            "titulo": "Casa en Centro Habana",
            "descripcion": None,
        },
    ],
}

CAPTURA_REVOLICO = {
    "id_captura": "revolico-prueba-0001",
    "fecha_captura": FECHA_CAPTURA,
    "fuente": "revolico",
    "url_fuente": "https://www.revolico.com/search",
    "cantidad": 4,
    "datos": [
        {
            "id_fuente": "rev-1",
            "url": "https://www.revolico.com/item/casa-prueba-1",
            "fecha_captura": FECHA_CAPTURA,
            "provincia": "La Habana",
            "municipio": None,
            "reparto": None,
            "direccion_texto": None,
            "tipo_operacion": "venta",
            "tipo_inmueble": "casa",
            "area_m2": None,
            "tipo_area": None,
            "habitaciones": None,
            "banos": None,
            "planta": None,
            "estado_conservacion": None,
            "amueblado": None,
            "precio": 600000.0,
            "moneda": "USD",
            "titulo": "Casa en venta en La Habana",
            "descripcion": None,
        },
        {
            "id_fuente": "rev-2",
            "url": "https://www.revolico.com/item/apartamento-prueba-2",
            "fecha_captura": FECHA_CAPTURA,
            "provincia": "La Habana",
            "municipio": None,
            "reparto": None,
            "direccion_texto": None,
            "tipo_operacion": "venta",
            "tipo_inmueble": "casa",
            "area_m2": None,
            "tipo_area": None,
            "habitaciones": None,
            "banos": None,
            "planta": None,
            "estado_conservacion": None,
            "amueblado": None,
            "precio": 25000.0,
            "moneda": "USD",
            "titulo": "Apartamento en Playa",
            "descripcion": None,
        },
        {
            "id_fuente": "rev-3",
            "url": "https://www.revolico.com/item/venta-prueba-3",
            "fecha_captura": FECHA_CAPTURA,
            "provincia": "La Habana",
            "municipio": None,
            "reparto": None,
            "direccion_texto": None,
            "tipo_operacion": "venta",
            "tipo_inmueble": "casa",
            "area_m2": None,
            "tipo_area": None,
            "habitaciones": None,
            "banos": None,
            "planta": None,
            "estado_conservacion": None,
            "amueblado": None,
            "precio": None,
            "moneda": None,
            "titulo": "Venta",
            "descripcion": None,
        },
        {
            "id_fuente": "rev-4",
            "url": "https://www.revolico.com/item/esmalte-prueba-4",
            "fecha_captura": FECHA_CAPTURA,
            "provincia": "La Habana",
            "municipio": None,
            "reparto": None,
            "direccion_texto": None,
            "tipo_operacion": "venta",
            "tipo_inmueble": "casa",
            "area_m2": None,
            "tipo_area": None,
            "habitaciones": None,
            "banos": None,
            "planta": None,
            "estado_conservacion": None,
            "amueblado": None,
            "precio": 1.0,
            "moneda": "USD",
            "titulo": "Esmalte sintético blanco",
            "descripcion": None,
        },
    ],
}


def _crear_capturas_de_prueba(directorio):
    """Escribe las capturas sintéticas y devuelve sus rutas."""
    directorio = Path(directorio)
    ruta_gaos = directorio / "gaos_procesado_prueba.json"
    ruta_revolico = directorio / "revolico_procesado_prueba.json"

    with open(ruta_gaos, "w", encoding="utf-8") as f:
        json.dump(CAPTURA_GAOS, f, ensure_ascii=False)
    with open(ruta_revolico, "w", encoding="utf-8") as f:
        json.dump(CAPTURA_REVOLICO, f, ensure_ascii=False)

    return ruta_gaos, ruta_revolico


def _hash_archivo(ruta):
    """Devuelve el hash SHA-256 de un archivo para detectar modificaciones."""
    with open(ruta, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_unificar_capturas_incorpora_todos_los_registros():
    """unificar_capturas combina los 3 anuncios de GAOS y los 4 de Revolico."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_gaos, ruta_revolico = _crear_capturas_de_prueba(tmpdir)
        salida = Path(tmpdir) / "unificado.json"
        id_captura, ruta = unificar_capturas(ruta_gaos, ruta_revolico, salida)

        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)

        assert isinstance(id_captura, str) and id_captura
        assert datos["cantidad"] == 7
        assert len(datos["datos"]) == 7


def test_unificar_capturas_conta_por_fuente():
    """Hay exactamente 3 anuncios de GAOS y 4 de Revolico."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_gaos, ruta_revolico = _crear_capturas_de_prueba(tmpdir)
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(ruta_gaos, ruta_revolico, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        fuentes = [a.get("fuente") for a in datos["datos"]]
        assert fuentes.count("gaos") == 3
        assert fuentes.count("revolico") == 4


def test_unificar_capturas_conserva_ids_origen():
    """Los identificadores de origen (id_fuente) se conservan en cada anuncio."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_gaos, ruta_revolico = _crear_capturas_de_prueba(tmpdir)
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(ruta_gaos, ruta_revolico, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        ids_gaos = {a.get("id_fuente") for a in datos["datos"] if a.get("fuente") == "gaos"}
        ids_rev = {a.get("id_fuente") for a in datos["datos"] if a.get("fuente") == "revolico"}
        assert len(ids_gaos) == 3
        assert len(ids_rev) == 4


def test_unificar_capturas_revolico_usa_nueva_clasificacion():
    """Los anuncios de Revolico usan la clasificación por título, no el valor hardcodeado 'casa'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_gaos, ruta_revolico = _crear_capturas_de_prueba(tmpdir)
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(ruta_gaos, ruta_revolico, salida)

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
        ruta_gaos, ruta_revolico = _crear_capturas_de_prueba(tmpdir)
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(ruta_gaos, ruta_revolico, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        no_vivienda = [a for a in datos["datos"] if a.get("tipo_inmueble") == "no_vivienda"]
        assert len(no_vivienda) >= 1


def test_unificar_capturas_conserva_precios_monedas():
    """Los precios y monedas originales se mantienen sin conversión."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_gaos, ruta_revolico = _crear_capturas_de_prueba(tmpdir)
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(ruta_gaos, ruta_revolico, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        # Anuncio de Revolico con precio alto
        rev = [a for a in datos["datos"] if a.get("id_fuente") == "rev-1"][0]
        assert rev.get("precio") == 600000.0
        assert rev.get("moneda") == "USD"

        # Anuncio de GAOS con moneda EUR
        euros = [a for a in datos["datos"] if a.get("moneda") == "EUR"]
        assert len(euros) > 0


def test_unificar_capturas_conserva_valores_nulos():
    """Los valores ausentes se conservan como None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_gaos, ruta_revolico = _crear_capturas_de_prueba(tmpdir)
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(ruta_gaos, ruta_revolico, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        # GAOS tiene provincia y municipio nulos en su primera captura
        g = [a for a in datos["datos"] if a.get("fuente") == "gaos"][0]
        assert g.get("provincia") is None
        assert g.get("municipio") is None

        # Revolico tiene area_m2 nulo en todos
        r = [a for a in datos["datos"] if a.get("fuente") == "revolico"][0]
        assert r.get("area_m2") is None


def test_unificar_capturas_no_modifica_archivos_entrada():
    """Los archivos de entrada no se modifican durante la unificación."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_gaos, ruta_revolico = _crear_capturas_de_prueba(tmpdir)
        hash_gaos_antes = _hash_archivo(ruta_gaos)
        hash_rev_antes = _hash_archivo(ruta_revolico)

        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(ruta_gaos, ruta_revolico, salida)

        hash_gaos_despues = _hash_archivo(ruta_gaos)
        hash_rev_despues = _hash_archivo(ruta_revolico)

    assert hash_gaos_antes == hash_gaos_despues
    assert hash_rev_antes == hash_rev_despues


def test_unificar_capturas_procedencia_inequivoca():
    """Cada anuncio tiene un campo fuente que identifica su origen."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_gaos, ruta_revolico = _crear_capturas_de_prueba(tmpdir)
        salida = Path(tmpdir) / "unificado.json"
        unificar_capturas(ruta_gaos, ruta_revolico, salida)

        with open(salida, encoding="utf-8") as f:
            datos = json.load(f)

        for anuncio in datos["datos"]:
            assert anuncio.get("fuente") in ("gaos", "revolico")

        # El envoltorio tiene metadatos de ambas capturas de origen
        assert datos.get("fuente") == "multifuente"
        assert len(datos.get("capturas_origen", [])) == 2
        assert datos["capturas_origen"][0]["fuente"] == "gaos"
        assert datos["capturas_origen"][1]["fuente"] == "revolico"
