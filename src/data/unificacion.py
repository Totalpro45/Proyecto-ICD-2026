"""Unificación de capturas de anuncios de GAOS y Revolico.

Combina los anuncios procesados de ambas fuentes en un solo archivo JSON,
conservando la procedencia de cada registro sin modificar las capturas
originales.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from data.almacenamiento_anuncios import (
    generar_id_captura,
    obtener_fecha_captura,
    _escribir_json_atomico,
)
from sources.revolico import _clasificar_tipo_inmueble, REVOLICO_URL


def unificar_capturas(
    ruta_gaos: Path | str,
    ruta_revolico: Path | str,
    ruta_salida: Path | str | None = None,
) -> tuple[str, Path]:
    """Une los anuncios procesados de GAOS y Revolico en un solo archivo JSON.

    Conserva la procedencia de cada anuncio mediante el campo ``fuente``
    en cada registro y los metadatos de captura de origen en el envoltorio.
    No modifica los archivos de entrada.

    Args:
        ruta_gaos: ruta al archivo procesado de GAOS.
        ruta_revolico: ruta al archivo procesado de Revolico.
        ruta_salida: ruta donde guardar el archivo unificado (opcional).
            Si no se indica, se crea en ``data/processed/anuncios/``.

    Returns:
        Tupla con el ``id_captura`` generado y la ruta del archivo guardado.
    """
    ruta_gaos = Path(ruta_gaos)
    ruta_revolico = Path(ruta_revolico)

    with open(ruta_gaos, encoding="utf-8") as f:
        datos_gaos = json.load(f)
    with open(ruta_revolico, encoding="utf-8") as f:
        datos_revolico = json.load(f)

    anuncios_gaos = datos_gaos.get("datos", [])
    anuncios_revolico = datos_revolico.get("datos", [])

    # Añadir fuente a cada anuncio de GAOS (conservar valores originales)
    for anuncio in anuncios_gaos:
        anuncio["fuente"] = "gaos"

    # Añadir fuente y reclasificar tipo_inmueble para Revolico usando el título
    for anuncio in anuncios_revolico:
        anuncio["fuente"] = "revolico"
        anuncio["tipo_inmueble"] = _clasificar_tipo_inmueble(
            anuncio.get("titulo")
        )

    todos_anuncios = anuncios_gaos + anuncios_revolico

    id_captura = generar_id_captura()
    fecha_captura = obtener_fecha_captura()

    envoltorio = {
        "id_captura": id_captura,
        "fecha_captura": fecha_captura,
        "fuente": "multifuente",
        "url_fuente": None,
        "capturas_origen": [
            {
                "fuente": "gaos",
                "id_captura": datos_gaos.get("id_captura"),
                "fecha_captura": datos_gaos.get("fecha_captura"),
                "archivo": ruta_gaos.name,
                "cantidad": len(anuncios_gaos),
            },
            {
                "fuente": "revolico",
                "id_captura": datos_revolico.get("id_captura"),
                "fecha_captura": datos_revolico.get("fecha_captura"),
                "archivo": ruta_revolico.name,
                "cantidad": len(anuncios_revolico),
                "url_fuente_correcta": REVOLICO_URL,
                "nota": "En la captura histórica los metadatos decían GAOS; aquí se corrige a Revolico.",
            },
        ],
        "cantidad": len(todos_anuncios),
        "datos": todos_anuncios,
    }

    if ruta_salida is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        ruta_salida = (
            Path("data/processed/anuncios")
            / f"unificado_procesado_{id_captura[:8]}_{timestamp}.json"
        )

    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    _escribir_json_atomico(ruta_salida, envoltorio)

    return id_captura, ruta_salida
