"""Script de captura diaria de tasas de cambio de elTOQUE y BCC.

Consulta la API de elTOQUE (mercado informal) y la API del BCC
(tasa oficial, Segmento III), extrae las cotizaciones y las guarda en
el historial append-only de tasas de cambio.

Cada fuente se procesa de forma independiente: si una falla, se registra
la incidencia correspondiente sin impedir que la otra fuente se procese.

Se ejecuta desde GitHub Actions (workflow `tasas-cambio.yml`) o manualmente.

Variables de entorno requeridas:
- ELTOQUE_API_TOKEN: clave API pública de elTOQUE (rol anon).

No modifica el historial existente ni elimina cotizaciones previas.
"""

from __future__ import annotations

import sys

from . import almacenamiento
from .bcc import (
    BccConnectionError,
    BccError,
    BccStructureError,
    consultar_tasas as consultar_tasas_bcc,
    extraer_cotizaciones as extraer_cotizaciones_bcc,
)
from .eltoque import (
    ElToqueAuthError,
    ElToqueConnectionError,
    ElToqueError,
    consultar_tasas as consultar_tasas_eltoque,
    extraer_cotizaciones as extraer_cotizaciones_eltoque,
)


def _capturar_fuente_eltoque(
    id_actualizacion: str,
    fecha_inicio: str,
    resultados_por_fuente: list,
) -> bool:
    """Ejecuta la captura de elTOQUE y registra sus resultados.

    Devuelve True si la captura de elTOQUE tuvo éxito (o sin novedad),
    False si hubo un error.
    """
    try:
        datos_api = consultar_tasas_eltoque()
    except ElToqueAuthError as exc:
        almacenamiento.crear_incidencia_conexion(
            id_actualizacion=id_actualizacion,
            fuente="eltoque",
            fecha_captura=fecha_inicio,
            descripcion=str(exc),
            detalle_tecnico="Error de autenticación con la API de elTOQUE.",
            ruta=almacenamiento.RUTA_HISTORIAL,
        )
        resultados_por_fuente.append(
            {
                "fuente": "eltoque",
                "estado": "error",
                "cotizaciones_nuevas": 0,
                "incidencias": 1,
            }
        )
        print(f"Error de autenticación (eltoque): {exc}", file=sys.stderr)
        return False
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
        resultados_por_fuente.append(
            {
                "fuente": "eltoque",
                "estado": "error",
                "cotizaciones_nuevas": 0,
                "incidencias": 1,
            }
        )
        print(f"Error de conexión (eltoque): {exc}", file=sys.stderr)
        return False
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
        resultados_por_fuente.append(
            {
                "fuente": "eltoque",
                "estado": "error",
                "cotizaciones_nuevas": 0,
                "incidencias": 1,
            }
        )
        print(f"Error de la API (eltoque): {exc}", file=sys.stderr)
        return False

    cotizaciones = extraer_cotizaciones_eltoque(datos_api)

    resultado = almacenamiento.registrar_cotizaciones(
        cotizaciones, id_actualizacion, ruta=almacenamiento.RUTA_HISTORIAL
    )

    resultados_por_fuente.append(
        {
            "fuente": "eltoque",
            "estado": "ok" if resultado["cotizaciones_agregadas"] > 0 else "sin_novedad",
            "cotizaciones_nuevas": resultado["cotizaciones_agregadas"],
            "incidencias": 0,
        }
    )
    print(
        f"elTOQUE: {resultado['cotizaciones_agregadas']} cotización(es) nueva(s), "
        f"{resultado['sin_novedad']} sin novedad, "
        f"{resultado['duplicados_omitidos']} duplicado(s) omitido(s)."
    )
    return True


def _capturar_fuente_bcc(
    id_actualizacion: str,
    fecha_inicio: str,
    resultados_por_fuente: list,
) -> bool:
    """Ejecuta la captura de BCC y registra sus resultados.

    Devuelve True si la captura de BCC tuvo éxito (o sin novedad),
    False si hubo un error.
    """
    try:
        datos_api = consultar_tasas_bcc()
    except BccConnectionError as exc:
        almacenamiento.crear_incidencia_conexion(
            id_actualizacion=id_actualizacion,
            fuente="bcc",
            fecha_captura=fecha_inicio,
            descripcion=str(exc),
            detalle_tecnico="Error de conexión con la API del BCC.",
            url_fuente="https://api.bc.gob.cu/v1/tasas-de-cambio/activas",
            ruta=almacenamiento.RUTA_HISTORIAL,
        )
        resultados_por_fuente.append(
            {
                "fuente": "bcc",
                "estado": "error",
                "cotizaciones_nuevas": 0,
                "incidencias": 1,
            }
        )
        print(f"Error de conexión (bcc): {exc}", file=sys.stderr)
        return False
    except BccStructureError as exc:
        almacenamiento.crear_incidencia_estructura(
            id_actualizacion=id_actualizacion,
            fuente="bcc",
            fecha_captura=fecha_inicio,
            descripcion=str(exc),
            detalle_tecnico="La respuesta de la API del BCC no tiene la estructura esperada.",
            url_fuente="https://api.bc.gob.cu/v1/tasas-de-cambio/activas",
            ruta=almacenamiento.RUTA_HISTORIAL,
        )
        resultados_por_fuente.append(
            {
                "fuente": "bcc",
                "estado": "error",
                "cotizaciones_nuevas": 0,
                "incidencias": 1,
            }
        )
        print(f"Error de estructura (bcc): {exc}", file=sys.stderr)
        return False
    except BccError as exc:
        almacenamiento.crear_incidencia_validacion(
            id_actualizacion=id_actualizacion,
            fuente="bcc",
            fecha_captura=fecha_inicio,
            descripcion=str(exc),
            categoria="oficial",
            url_fuente="https://api.bc.gob.cu/v1/tasas-de-cambio/activas",
            ruta=almacenamiento.RUTA_HISTORIAL,
        )
        resultados_por_fuente.append(
            {
                "fuente": "bcc",
                "estado": "error",
                "cotizaciones_nuevas": 0,
                "incidencias": 1,
            }
        )
        print(f"Error de la API (bcc): {exc}", file=sys.stderr)
        return False

    cotizaciones = extraer_cotizaciones_bcc(datos_api)

    resultado = almacenamiento.registrar_cotizaciones(
        cotizaciones, id_actualizacion, ruta=almacenamiento.RUTA_HISTORIAL
    )

    resultados_por_fuente.append(
        {
            "fuente": "bcc",
            "estado": "ok" if resultado["cotizaciones_agregadas"] > 0 else "sin_novedad",
            "cotizaciones_nuevas": resultado["cotizaciones_agregadas"],
            "incidencias": 0,
        }
    )
    print(
        f"BCC: {resultado['cotizaciones_agregadas']} cotización(es) nueva(s), "
        f"{resultado['sin_novedad']} sin novedad, "
        f"{resultado['duplicados_omitidos']} duplicado(s) omitido(s)."
    )
    return True


def main() -> int:
    """Ejecuta una captura de tasas de elTOQUE y BCC y guarda el historial.

    Cada fuente se procesa de forma independiente. Si una falla, la otra
    sigue ejecutándose y conserva sus datos.

    Returns:
        0 si ambas fuentes se procesaron correctamente (o sin novedad).
        1 si alguna fuente falló.
    """
    id_actualizacion, fecha_inicio, fecha_fin = almacenamiento.crear_actualizacion(
        ["eltoque", "bcc"]
    )

    resultados_por_fuente: list = []

    exito_eltoque = _capturar_fuente_eltoque(
        id_actualizacion, fecha_inicio, resultados_por_fuente
    )
    exito_bcc = _capturar_fuente_bcc(
        id_actualizacion, fecha_inicio, resultados_por_fuente
    )

    fecha_fin = almacenamiento._ahora_iso()
    almacenamiento.registrar_actualizacion(
        id_actualizacion,
        fecha_inicio,
        fecha_fin,
        ["eltoque", "bcc"],
        resultados_por_fuente,
        ruta=almacenamiento.RUTA_HISTORIAL,
    )

    hubo_exito_ambas = exito_eltoque and exito_bcc
    if hubo_exito_ambas:
        print("Captura completada para ambas fuentes.")
    else:
        fuentes_fallidas = []
        if not exito_eltoque:
            fuentes_fallidas.append("eltoque")
        if not exito_bcc:
            fuentes_fallidas.append("bcc")
        print(
            "Captura completada con fallos en: "
            + ", ".join(fuentes_fallidas),
            file=sys.stderr,
        )

    return 0 if hubo_exito_ambas else 1


if __name__ == "__main__":
    sys.exit(main())