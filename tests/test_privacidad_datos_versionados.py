"""Comprobación automática de datos de contacto en JSON versionados.

Esta es la protección de E2: si un archivo JSON rastreado por Git contiene
teléfonos, enlaces de WhatsApp, correos, instrucciones de contacto o un
``publisher`` con datos personales, la prueba falla. Se ejecuta junto con el
resto de la suite:

    pytest tests/test_privacidad_datos_versionados.py

No instala ningún hook de Git. Para que bloquee un commit, hay que ejecutar
las pruebas antes de commitear o conectarlas a un hook/CI. Usa solo la
biblioteca estándar y datos ficticios en las pruebas unitarias.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "src")

from data.privacidad import (
    campos_personales,
    contiene_datos_contacto,
    revisar_archivo_json,
)


def _archivos_json_revisables() -> list[Path]:
    """Lista los JSON versionados y los nuevos que no están ignorados.

    Incluye archivos todavía sin seguimiento para que la comprobación también
    detecte un JSON problemático antes de que se agregue a Git.
    """
    resultado = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "*.json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [
        Path(linea) for linea in resultado.stdout.splitlines() if linea.strip()
    ]


def test_json_versionados_sin_datos_de_contacto():
    """Ningún JSON versionado o versionable debe tener datos de contacto."""
    archivos = _archivos_json_revisables()
    assert archivos, "No se encontraron archivos JSON para revisar"

    problemas = {}
    for ruta in archivos:
        resumen = revisar_archivo_json(ruta)
        if resumen["campos"]:
            problemas[str(ruta)] = resumen["campos"]

    assert not problemas, f"Archivos con datos de contacto: {problemas}"


def test_detector_rechaza_json_con_telefono(tmp_path: Path):
    ruta = tmp_path / "sucio.json"
    ruta.write_text(
        json.dumps(
            {
                "datos": [
                    {
                        "id_fuente": "ficticio-001",
                        "titulo": "Casa en Playa",
                        "descripcion": "Casa amplia. Teléfono: 55500000",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    resumen = revisar_archivo_json(ruta)

    assert resumen["anuncios"] == 1
    assert resumen["campos"].get("descripcion") == 1


def test_detector_rechaza_json_con_whatsapp_y_correo(tmp_path: Path):
    ruta = tmp_path / "sucio.json"
    ruta.write_text(
        json.dumps(
            {
                "datos": [
                    {
                        "id_fuente": "ficticio-002",
                        "titulo": "Casa 55500000",
                        "descripcion": "WhatsApp: https://wa.me/5355500000",
                        "direccion_texto": "Escribir a correo@ejemplo.com",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    resumen = revisar_archivo_json(ruta)

    assert set(resumen["campos"]) == {
        "titulo",
        "descripcion",
        "direccion_texto",
    }


def test_detector_rechaza_publisher_con_datos_personales(tmp_path: Path):
    ruta = tmp_path / "sucio.json"
    ruta.write_text(
        json.dumps(
            {
                "datos": [
                    {
                        "id_fuente": "ficticio-003",
                        "titulo": "Casa en Playa",
                        "publisher": {
                            "accountType": "private",
                            "name": "Persona de Prueba",
                            "phone": "55500000",
                            "avatarUrl": "https://example.com/avatar",
                            "slug": "persona-de-prueba",
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    resumen = revisar_archivo_json(ruta)

    assert set(resumen["campos"]) == {
        "publisher.name",
        "publisher.phone",
        "publisher.avatarUrl",
        "publisher.slug",
    }


def test_detector_acepta_json_limpio(tmp_path: Path):
    ruta = tmp_path / "limpio.json"
    ruta.write_text(
        json.dumps(
            {
                "datos": [
                    {
                        "id_fuente": "ficticio-004",
                        "titulo": "Casa en Playa",
                        "descripcion": (
                            "Casa de 3 habitaciones, 2 baños y 120 m2. "
                            "Incluye landline phone y garaje."
                        ),
                        "direccion_texto": "Calle 3ra, Playa",
                        "publisher": {"accountType": "private"},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    resumen = revisar_archivo_json(ruta)

    assert resumen["anuncios"] == 1
    assert resumen["campos"] == {}


def test_detector_acepta_json_sin_anuncios(tmp_path: Path):
    """Un JSON que no es de anuncios (por ejemplo, tasas) no da falsos positivos."""
    ruta = tmp_path / "tasas.json"
    ruta.write_text(
        json.dumps(
            {
                "historial": [
                    {"fecha": "2026-11-01", "valor": 395.5},
                    {"fecha": "2026-11-02", "valor": 400.0},
                ]
            }
        ),
        encoding="utf-8",
    )

    resumen = revisar_archivo_json(ruta)

    assert resumen["campos"] == {}


def test_campos_personales_no_confunde_comodidades():
    dato = {
        "titulo": "Casa en Playa",
        "descripcion": "Incluye landline phone y cell phone chargers.",
        "publisher": {"accountType": "private", "isVerified": True},
    }

    assert campos_personales(dato) == []
    assert contiene_datos_contacto(dato["descripcion"]) is False
