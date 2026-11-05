"""Script de captura diaria de tasas de cambio de elTOQUE.

Consulta la API de elTOQUE, extrae las cotizaciones de USD, EUR y MLC,
y las guarda en el historial append-only de tasas de cambio.

Se ejecuta desde GitHub Actions (workflow `tasas-cambio.yml`) o manualmente.

Variables de entorno requeridas:
- ELTOQUE_API_TOKEN: clave API pública de elTOQUE (rol anon).

No modifica el historial existente ni elimina cotizaciones previas.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from .eltoque import (
    consultar_tasas,
    extraer_cotizaciones,
    ElToqueAuthError,
    ElToqueConnectionError,
    ElToqueError,
)
from . import almacenamiento


def main() -> int:
    """Ejecuta una captura de tasas de elTOQUE y guarda el historial.

    Returns:
        0 si la captura se completó correctamente (o sin novedad).
        1 si hubo un error de autenticación o conexión.
    """
    id_actualizacion, fecha_inicio, fecha_fin = almacenamiento.crear_actualizacion(
        ["eltoque"]
    )

    try:
        datos_api = consultar_tasas()
    except ElToqueAuthError as exc:
        almacenamiento.crear_incidencia_conexion(
            id_actualizacion=id_actualizacion,
            fuente="eltoque",
            fecha_captura=fecha_inicio,
            descripcion=str(exc),
            detalle_tecnico="Error de autenticación con la API de elTOQUE.",
            ruta=almacenamiento.RUTA_HISTORIAL,
        )
        fecha_fin = almacenamiento._ahora_iso()
        almacenamiento.registrar_actualizacion(
            id_actualizacion,
            fecha_inicio,
            fecha_fin,
            ["eltoque"],
            [
                {
                    "fuente": "eltoque",
                    "estado": "error",
                    "cotizaciones_nuevas": 0,
                    "incidencias": 1,
                }
            ],
            ruta=almacenamiento.RUTA_HISTORIAL,
        )
        print(f"Error de autenticación: {exc}", file=sys.stderr)
        return 1
    except ElToqueConnectionError as exc:
        almacenamiento.crear_incidencia_conexion(
            id_actualizacion=id_actualizacion,
            fuente="eltoque",
            fecha_captura=fecha_inicio,
            descripcion=str(exc),
            detalle_tecnico="Error de conexión con la API de elTOQUE.",
            url_fuente="https://tasas.eltoque.com/v1/trmi",
            ruta=almacenamiento.RUTA_HISTORIAL,
        )
        fecha_fin = almacenamiento._ahora_iso()
        almacenamiento.registrar_actualizacion(
            id_actualizacion,
            fecha_inicio,
            fecha_fin,
            ["eltoque"],
            [
                {
                    "fuente": "eltoque",
                    "estado": "error",
                    "cotizaciones_nuevas": 0,
                    "incidencias": 1,
                }
            ],
            ruta=almacenamiento.RUTA_HISTORIAL,
        )
        print(f"Error de conexión: {exc}", file=sys.stderr)
        return 1
    except ElToqueError as exc:
        almacenamiento.crear_incidencia_validacion(
            id_actualizacion=id_actualizacion,
            fuente="eltoque",
            fecha_captura=fecha_inicio,
            descripcion=str(exc),
            categoria="mercado_informal",
            url_fuente="https://tasas.eltoque.com/v1/trmi",
            ruta=almacenamiento.RUTA_HISTORIAL,
        )
        fecha_fin = almacenamiento._ahora_iso()
        almacenamiento.registrar_actualizacion(
            id_actualizacion,
            fecha_inicio,
            fecha_fin,
            ["eltoque"],
            [
                {
                    "fuente": "eltoque",
                    "estado": "error",
                    "cotizaciones_nuevas": 0,
                    "incidencias": 1,
                }
            ],
            ruta=almacenamiento.RUTA_HISTORIAL,
        )
        print(f"Error de la API: {exc}", file=sys.stderr)
        return 1

    cotizaciones = extraer_cotizaciones(datos_api)

    resultado = almacenamiento.registrar_cotizaciones(
        cotizaciones, id_actualizacion, ruta=almacenamiento.RUTA_HISTORIAL
    )

    fecha_fin = almacenamiento._ahora_iso()
    resumen_por_fuente = [
        {
            "fuente": "eltoque",
            "estado": "ok" if resultado["cotizaciones_agregadas"] > 0 else "sin_novedad",
            "cotizaciones_nuevas": resultado["cotizaciones_agregadas"],
            "incidencias": 0,
        }
    ]
    almacenamiento.registrar_actualizacion(
        id_actualizacion,
        fecha_inicio,
        fecha_fin,
        ["eltoque"],
        resumen_por_fuente,
        ruta=almacenamiento.RUTA_HISTORIAL,
    )

    print(
        f"Captura completada: {resultado['cotizaciones_agregadas']} cotización(es) nueva(s), "
        f"{resultado['sin_novedad']} sin novedad, "
        f"{resultado['duplicados_omitidos']} duplicado(s) omitido(s)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
