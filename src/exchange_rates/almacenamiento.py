"""Almacenamiento del historial de tasas de cambio.

Gestiona el archivo único JSON append-only en
``data/raw/exchange_rates/historial_tasas.json`` tal como se define en
``docs/sistema_tasas_cambio.md``.

Funciones principales:
- Cargar y guardar el historial sin sobrescribir registros previos.
- Añadir cotizaciones nuevas detectando duplicados (por clave y valor).
- Registrar actualizaciones e incidencias por separado.
- Conservar el archivo anterior como copia de seguridad antes de escribir.

No implementa captura automática ni integración con anuncios inmobiliarios;
solo almacena lo que se le proporcione.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ruta del historial (append-only, excluida de Git por .gitignore).
RUTA_HISTORIAL = Path("data/raw/exchange_rates/historial_tasas.json")

# Versión del esquema documentada en docs/sistema_tasas_cambio.md.
VERSION_ESQUEMA = "1.0"


def _ahora_iso() -> str:
    """Devuelve la fecha y hora actual en ISO 8601 con zona horaria UTC."""
    return datetime.now(timezone.utc).isoformat()


def _nuevo_uuid() -> str:
    """Genera un UUID único (versión 4)."""
    return str(uuid.uuid4())


def _clave_cotizacion(cotizacion: dict) -> tuple:
    """Calcula la clave de consulta de una cotización.

    Según docs/sistema_tasas_cambio.md §9.1:
    (fuente, categoria, moneda_origen, moneda_destino, tipo_tasa, segmento)
    """
    return (
        cotizacion.get("fuente"),
        cotizacion.get("categoria"),
        cotizacion.get("moneda_origen"),
        cotizacion.get("moneda_destino"),
        cotizacion.get("tipo_tasa"),
        cotizacion.get("segmento"),
    )


def cargar_historial(ruta: Path = RUTA_HISTORIAL) -> dict:
    """Carga el historial de tasas desde un archivo JSON.

    Si el archivo no existe, devuelve una estructura vacía con los bloques
    requeridos. Si el archivo existe pero está dañado, se conserva como
    respaldo y se devuelve una estructura vacía para no perder datos.
    """
    if not ruta.exists():
        return {
            "version_esquema": VERSION_ESQUEMA,
            "ultima_actualizacion": None,
            "cotizaciones": [],
            "actualizaciones": [],
            "incidencias": [],
        }

    try:
        with ruta.open("r", encoding="utf-8") as f:
            datos = json.load(f)
        if not isinstance(datos, dict):
            raise ValueError("La raíz del JSON no es un objeto")
        # Validar bloques mínimos
        for clave in ("cotizaciones", "actualizaciones", "incidencias"):
            if clave not in datos:
                datos[clave] = []
        if "version_esquema" not in datos:
            datos["version_esquema"] = VERSION_ESQUEMA
        if "ultima_actualizacion" not in datos:
            datos["ultima_actualizacion"] = None
        return datos
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        # No se puede leer: conservar el archivo dañado como respaldo y
        # devolver una estructura vacía para no perder datos nuevos.
        respaldo = ruta.with_suffix(ruta.suffix + ".corrupto")
        try:
            shutil.copy2(ruta, respaldo)
        except OSError:
            pass
        return {
            "version_esquema": VERSION_ESQUEMA,
            "ultima_actualizacion": None,
            "cotizaciones": [],
            "actualizaciones": [],
            "incidencias": [],
        }


def guardar_historial(
    datos: dict,
    ruta: Path = RUTA_HISTORIAL,
    ultima_actualizacion: Optional[str] = None,
) -> None:
    """Guarda el historial en el archivo JSON.

    Antes de escribir, conserva una copia del archivo anterior como
    respaldo (docs/sistema_tasas_cambio.md §10 regla 9).

    Args:
        datos: Historial a guardar.
        ruta: Ruta del archivo JSON.
        ultima_actualizacion: ISO 8601 de la última actualización. Si se
            proporciona, se usa en lugar de generar una nueva hora. Esto
            garantiza que ultima_actualizacion y fecha_fin de la
            actualización sean coherentes.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)

    # Copia de seguridad antes de sobrescribir.
    if ruta.exists():
        respaldo = ruta.with_suffix(ruta.suffix + ".bak")
        try:
            shutil.copy2(ruta, respaldo)
        except OSError:
            pass

    if ultima_actualizacion is not None:
        datos["ultima_actualizacion"] = ultima_actualizacion
    else:
        datos["ultima_actualizacion"] = _ahora_iso()

    with ruta.open("w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _es_duplicado_exacto(cotizacion: dict, existente: dict) -> bool:
    """Comprueba si dos cotizaciones son la misma observación.

    Según docs/sistema_tasas_cambio.md §12, se comparan:
    fuente, categoria, tipo_tasa, segmento, moneda_origen, moneda_destino,
    fecha_publicacion, fecha_vigencia y valor_texto_original.
    """
    campos = (
        "fuente", "categoria", "tipo_tasa", "segmento",
        "moneda_origen", "moneda_destino",
        "fecha_publicacion", "fecha_vigencia", "valor_texto_original",
    )
    return all(
        cotizacion.get(c) == existente.get(c) for c in campos
    )


def _es_duplicado_por_valor(cotizacion: dict, existente: dict) -> bool:
    """Comprueba si dos cotizaciones sin fecha son el mismo valor.

    Cuando no hay fecha_publicacion ni fecha_vigencia, no se puede
    distinguir "no hay tasa nueva" de "la fuente repitió el mismo valor".
    En ese caso, si el valor_texto_original coincide, se considera la
    misma observación.
    """
    return cotizacion.get("valor_texto_original") == existente.get(
        "valor_texto_original"
    )


def registrar_cotizaciones(
    cotizaciones: list[dict],
    id_actualizacion: str,
    ruta: Path = RUTA_HISTORIAL,
) -> dict:
    """Añade cotizaciones al historial append-only.

    Detecta duplicados y no los duplica:
    - Si todos los campos clave coinciden con una cotización ya guardada,
      no se añade.
    - Si no hay fechas y el valor coincide con la última de la misma clave,
      no se añade (sin_novedad).
    - Si el valor cambia, se añade como nueva cotización.

    Args:
        cotizaciones: Lista de diccionarios con los datos de las cotizaciones
            extraídas de la fuente.
        id_actualizacion: UUID de la actualización a la que pertenecen.
        ruta: Ruta del archivo JSON de historial.

    Returns:
        Diccionario con el resumen de la operación:
        - "cotizaciones_agregadas": número de cotizaciones nuevas guardadas.
        - "sin_novedad": número de consultas sin cotización nueva.
        - "duplicados_omitidos": número de duplicados detectados.
    """
    historial = cargar_historial(ruta)
    cotizaciones_existentes = historial.get("cotizaciones", [])

    agregadas = 0
    sin_novedad = 0
    duplicados_omitidos = 0

    for cot in cotizaciones:
        clave = _clave_cotizacion(cot)

        # Buscar si ya existe una cotización con la misma clave.
        existente_misma_clave = None
        for existente in cotizaciones_existentes:
            if _clave_cotizacion(existente) == clave:
                existente_misma_clave = existente
                break

        if existente_misma_clave is not None:
            # Ya existe una observación con esta clave.
            fp_cot = cot.get("fecha_publicacion")
            fv_cot = cot.get("fecha_vigencia")
            fp_ext = existente_misma_clave.get("fecha_publicacion")
            fv_ext = existente_misma_clave.get("fecha_vigencia")

            if _es_duplicado_exacto(cot, existente_misma_clave):
                # Es exactamente la misma observación: no se añade.
                if fp_cot is None and fv_cot is None and fp_ext is None and fv_ext is None:
                    # Sin fechas: la fuente repitió el mismo valor.
                    sin_novedad += 1
                else:
                    # Con fechas: es la misma observación capturada dos veces.
                    duplicados_omitidos += 1
                continue

            # Hay una cotización previa con la misma clave pero diferente.
            # Si no hay fechas, comparar con el último valor guardado.
            if fp_cot is None and fv_cot is None and fp_ext is None and fv_ext is None:
                # Sin fechas: comparar con el último valor guardado.
                if _es_duplicado_por_valor(cot, existente_misma_clave):
                    # Mismo valor: no es una observación nueva.
                    sin_novedad += 1
                    continue
                # Valor diferente: es una observación nueva.
            # Si hay fechas y el valor es diferente, es una nueva observación.

        # Nueva cotización: añadir al historial.
        nueva_cotizacion = {
            "id": _nuevo_uuid(),
            "id_actualizacion": id_actualizacion,
            "fuente": cot.get("fuente"),
            "categoria": cot.get("categoria"),
            "tipo_tasa": cot.get("tipo_tasa", "no_especificado"),
            "segmento": cot.get("segmento"),
            "moneda_origen": cot.get("moneda_origen"),
            "moneda_destino": cot.get("moneda_destino"),
            "valor": cot.get("valor"),
            "valor_texto_original": cot.get("valor_texto_original"),
            "fecha_publicacion": cot.get("fecha_publicacion"),
            "fecha_vigencia": cot.get("fecha_vigencia"),
            "fecha_captura": cot.get("fecha_captura") or _ahora_iso(),
            "url_fuente": cot.get("url_fuente"),
            "estado": cot.get("estado", "valida"),
            "motivo_sospecha": cot.get("motivo_sospecha"),
            "reemplaza_a": cot.get("reemplaza_a"),
        }

        cotizaciones_existentes.append(nueva_cotizacion)
        historial["cotizaciones"] = cotizaciones_existentes
        agregadas += 1

    guardar_historial(historial, ruta)

    return {
        "cotizaciones_agregadas": agregadas,
        "sin_novedad": sin_novedad,
        "duplicados_omitidos": duplicados_omitidos,
    }


def registrar_actualizacion(
    id_actualizacion: str,
    fecha_inicio: str,
    fecha_fin: str,
    fuentes_consultadas: list[str],
    resultado_por_fuente: list[dict],
    ruta: Path = RUTA_HISTORIAL,
) -> None:
    """Registra una ejecución del proceso en el historial.

    Args:
        id_actualizacion: UUID de la actualización.
        fecha_inicio: ISO 8601 de inicio.
        fecha_fin: ISO 8601 de fin.
        fuentes_consultadas: Lista de fuentes consultadas.
        resultado_por_fuente: Resumen por cada fuente consultada.
        ruta: Ruta del archivo JSON de historial.
    """
    historial = cargar_historial(ruta)

    actualizacion = {
        "id": id_actualizacion,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "fuentes_consultadas": fuentes_consultadas,
        "resultado_por_fuente": resultado_por_fuente,
    }

    historial.setdefault("actualizaciones", []).append(actualizacion)
    guardar_historial(historial, ruta, ultima_actualizacion=fecha_fin)


def registrar_incidencia(
    id_actualizacion: str,
    fuente: str,
    fecha_captura: str,
    tipo: str,
    descripcion: str,
    categoria: Optional[str] = None,
    estado: str = "abierta",
    url_fuente: Optional[str] = None,
    detalle_tecnico: Optional[str] = None,
    ruta: Path = RUTA_HISTORIAL,
) -> None:
    """Registra una incidencia (fallo o anomalía) en el historial.

    Las incidencias nunca son tasas y se guardan por separado.

    Args:
        id_actualizacion: UUID de la actualización en la que ocurrió.
        fuente: Fuente afectada (ej. "eltoque").
        fecha_captura: ISO 8601 de cuándo se detectó.
        tipo: Tipo de fallo (conexion, estructura, extraccion, validacion,
            parcial, otro).
        descripcion: Explicación breve.
        categoria: Tipo de mercado afectado (oficial, mercado_informal).
        estado: "abierta" o "resuelta".
        url_fuente: Dirección afectada, si aplica.
        detalle_tecnico: Texto técnico del error, si ayuda a revisarlo.
        ruta: Ruta del archivo JSON de historial.
    """
    historial = cargar_historial(ruta)

    incidencia = {
        "id": _nuevo_uuid(),
        "id_actualizacion": id_actualizacion,
        "fuente": fuente,
        "categoria": categoria,
        "fecha_captura": fecha_captura,
        "tipo": tipo,
        "descripcion": descripcion,
        "estado": estado,
        "url_fuente": url_fuente,
        "detalle_tecnico": detalle_tecnico,
    }

    historial.setdefault("incidencias", []).append(incidencia)
    guardar_historial(historial, ruta)


def crear_actualizacion(
    fuentes_consultadas: list[str],
) -> tuple[str, str, str]:
    """Crea los identificadores y fechas para una nueva actualización.

    Returns:
        Tupla (id_actualizacion, fecha_inicio, fecha_fin).
    """
    id_actualizacion = _nuevo_uuid()
    fecha_inicio = _ahora_iso()
    # fecha_fin se rellena al finalizar la actualización.
    return id_actualizacion, fecha_inicio, fecha_inicio


def crear_incidencia_conexion(
    id_actualizacion: str,
    fuente: str,
    fecha_captura: str,
    descripcion: str,
    detalle_tecnico: Optional[str] = None,
    url_fuente: Optional[str] = None,
    ruta: Path = RUTA_HISTORIAL,
) -> None:
    """Registra una incidencia de tipo conexión (no se pudo acceder)."""
    registrar_incidencia(
        id_actualizacion=id_actualizacion,
        fuente=fuente,
        categoria="mercado_informal",
        fecha_captura=fecha_captura,
        tipo="conexion",
        descripcion=descripcion,
        url_fuente=url_fuente,
        detalle_tecnico=detalle_tecnico,
        ruta=ruta,
    )


def crear_incidencia_estructura(
    id_actualizacion: str,
    fuente: str,
    fecha_captura: str,
    descripcion: str,
    detalle_tecnico: Optional[str] = None,
    url_fuente: Optional[str] = None,
    ruta: Path = RUTA_HISTORIAL,
) -> None:
    """Registra una incidencia de tipo estructura (cambio de formato)."""
    registrar_incidencia(
        id_actualizacion=id_actualizacion,
        fuente=fuente,
        categoria="mercado_informal",
        fecha_captura=fecha_captura,
        tipo="estructura",
        descripcion=descripcion,
        url_fuente=url_fuente,
        detalle_tecnico=detalle_tecnico,
        ruta=ruta,
    )


def crear_incidencia_validacion(
    id_actualizacion: str,
    fuente: str,
    fecha_captura: str,
    descripcion: str,
    categoria: Optional[str] = None,
    url_fuente: Optional[str] = None,
    detalle_tecnico: Optional[str] = None,
    ruta: Path = RUTA_HISTORIAL,
) -> None:
    """Registra una incidencia de tipo validación (dato no válido)."""
    registrar_incidencia(
        id_actualizacion=id_actualizacion,
        fuente=fuente,
        categoria=categoria,
        fecha_captura=fecha_captura,
        tipo="validacion",
        descripcion=descripcion,
        url_fuente=url_fuente,
        detalle_tecnico=detalle_tecnico,
        ruta=ruta,
    )