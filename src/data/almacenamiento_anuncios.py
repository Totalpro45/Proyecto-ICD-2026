"""Almacenamiento de anuncios inmobiliarios (GAOS y Revolico).

Conserva los datos crudos de la API y los anuncios ya mapeados al esquema
común, separados en carpetas distintas:

- data/raw/anuncios/<fuente>/crudo/     <- datos crudos de la API
- data/processed/anuncios/<fuente>/     <- anuncios ya mapeados

Cada ejecución que termina correctamente guarda un par de archivos con el
mismo id_captura y fecha_captura, de modo que crudos y procesados pueden
relacionarse por esos metadatos. El nombre combina un sufijo del id_captura y
una marca de tiempo. No se comprueba si el archivo ya existe: ``os.replace``
puede sustituir uno existente, así que no se garantiza que no se sobrescriba.

La escritura es atómica por archivo: se escribe en un temporal del mismo
directorio y se publica con ``os.replace``. El par no se publica como una
transacción única. Si falla la escritura del segundo archivo, se intenta
eliminar el primero ya publicado, pero el rollback no está garantizado. Una
interrupción abrupta del proceso entre ambas publicaciones puede dejar solo el
crudo. ``leer_captura()`` comprueba que existan los dos archivos y que sus
identificadores coincidan, pero no es infalible ante colisiones de nombres.

Si falla una escritura, se intenta eliminar su temporal; antes de cada
escritura se intentan borrar los ``*.tmp`` de las carpetas de destino. Los
errores de borrado se ignoran, de modo que un temporal puede permanecer. Esa
limpieza afecta a todos los ``*.tmp`` de las carpetas indicadas, sin filtrar
por fuente.

No modifica el sistema de tasas de cambio.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from data.models import AnuncioInmobiliario
from data.privacidad import sanitizar_anuncio_procesado, sanitizar_crudo

# Clave de vendedor en crudo GAOS: publisher.accountType.
# Los valores conocidos se reutilizan de la lógica de mapear_anuncio en
# sources.gaos.py. Valores no reconocidos (p. ej. "realtor") quedan como None.
ACCOUNT_TYPE_MAP = {
    "private": "particular",
    "agency": "agencia",
}

# Rutas por defecto (se pueden sobrescribir pasando rutas alternativas a
# las funciones).
RUTA_CRUDO_DEFECTO = Path("data/raw/anuncios/gaos/crudo")
RUTA_PROCESADO_DEFECTO = Path("data/processed/anuncios/gaos")

# Sufijo de los archivos temporales de escritura.
EXTENSION_TEMPORAL = ".tmp"

# Nombre del campo de precio en los datos crudos, según la estructura de cada
# fuente. GAOS usa ``dcprice`` y Revolico ``precio``.
CAMPOS_PRECIO_CRUDO = {
    "gaos": "dcprice",
    "revolico": "precio",
}


def generar_id_captura() -> str:
    """Devuelve un identificador único para una captura."""
    import uuid

    return uuid.uuid4().hex


def obtener_fecha_captura() -> str:
    """Devuelve la fecha y hora actual en formato ISO 8601 con zona horaria."""
    return datetime.now(timezone.utc).isoformat()


def _ruta_crudo(ruta: Path | None = None) -> Path:
    """Devuelve la ruta del directorio de crudos."""
    return Path(ruta) if ruta is not None else RUTA_CRUDO_DEFECTO


def _ruta_procesado(ruta: Path | None = None) -> Path:
    """Devuelve la ruta del directorio de procesados."""
    return Path(ruta) if ruta is not None else RUTA_PROCESADO_DEFECTO


def _nombre_archivo(tipo: str, id_captura: str, timestamp: str, prefijo: str = "gaos") -> str:
    """Construye el nombre de archivo de una captura.

    Formato: <prefijo>_<tipo>_<sufijo_id>_<YYYYMMDD>_<HHMMSS>.json
    """
    sufijo = id_captura[:8]
    return f"{prefijo}_{tipo}_{sufijo}_{timestamp}.json"


def _escribir_json_atomico(ruta_final: Path, datos) -> None:
    """Escribe un JSON de forma atómica.

    Escribe en un archivo temporal del mismo directorio, vacía el búfer y
    publica con ``os.replace``. Si falla la escritura, intenta eliminar el
    temporal; los errores de borrado se ignoran, así que puede permanecer.
    """
    ruta_final = Path(ruta_final)
    ruta_final.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta_final.with_name(ruta_final.name + EXTENSION_TEMPORAL)

    try:
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporal, ruta_final)
    except Exception:
        try:
            temporal.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _limpiar_temporales(ruta: Path) -> int:
    """Intenta eliminar los archivos temporales (*.tmp) de una carpeta.

    Se invoca al inicio de cada escritura para recuperar temporales dejados
    por ejecuciones fallidas previas. Los errores de borrado se ignoran, de
    modo que algún temporal puede permanecer.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        return 0

    eliminados = 0
    for archivo in ruta.glob(f"*{EXTENSION_TEMPORAL}"):
        try:
            archivo.unlink(missing_ok=True)
            eliminados += 1
        except OSError:
            pass
    return eliminados


def _precio_numerico(valor) -> bool:
    """Devuelve True si el valor es un precio numérico interpretable.

    Se aceptan int/float (salvo bool), None (dato desconocido que se conserva
    como nulo) y cadenas convertibles a float. No se confunde None con cero.
    La ausencia del campo se comprueba en ``_crudos_validos``.
    """
    if isinstance(valor, bool):
        return False
    if valor is None:
        return True
    if isinstance(valor, (int, float)):
        return True
    if isinstance(valor, str):
        try:
            float(valor)
            return True
        except ValueError:
            return False
    return False


def _campo_precio_crudo(fuente: str) -> str:
    """Devuelve el campo de precio que usan los crudos de una fuente.

    Si la fuente no está registrada se asume ``precio``, que es el nombre
    usado por el esquema común y por los mapeadores personalizados.
    """
    return CAMPOS_PRECIO_CRUDO.get(fuente, "precio")


def _crudos_validos(crudos: list[dict], fuente: str = "gaos") -> bool:
    """Verifica que todos los crudos declaren un precio interpretable.

    El campo depende de la estructura de la fuente: GAOS usa ``dcprice`` y
    Revolico ``precio``. Se rechaza el crudo si falta el campo esperado o si
    su valor no es numérico. Un ``None`` explícito se conserva como precio
    desconocido, tal como permite el esquema común.
    """
    campo = _campo_precio_crudo(fuente)
    for dato in crudos:
        if campo not in dato:
            return False
        if not _precio_numerico(dato.get(campo)):
            return False
    return True


def guardar_captura(
    crudos: list[dict],
    anuncios: list[AnuncioInmobiliario],
    ruta_crudo: Path | None = None,
    ruta_procesado: Path | None = None,
    prefijo_archivo: str = "gaos",
    fuente: str = "gaos",
    url_fuente: str = "https://gaos.app/propiedades",
) -> str:
    """Guarda las cotizaciones crudas de la API y las cotizaciones ya mapeadas
    al esquema común.

    Ambos se guardan con el mismo id_captura y fecha_captura, para que
    puedan relacionarse después. El nombre de archivo combina un sufijo del
    id_captura y una marca de tiempo; no se comprueba previamente si ya
    existe, así que no se garantiza que no haya sobrescritura.

    La escritura es atómica por archivo. Si falla la publicación del segundo
    archivo, se intenta eliminar el primero ya publicado; es un rollback de
    mejor esfuerzo y no está garantizado ante una interrupción abrupta.

    Antes de escribir, se eliminan de los crudos y de los anuncios los
    teléfonos, enlaces de WhatsApp, correos e instrucciones de contacto.

    Args:
        crudos: lista de diccionarios tal como llegan de la API de GAOS.
        anuncios: lista de objetos AnuncioInmobiliario ya mapeados (uno por
            crudo, en el mismo orden).
        ruta_crudo: carpeta destino para los crudos (opcional).
        ruta_procesado: carpeta destino para los procesados (opcional).
        fuente: identificador de la fuente de datos (por defecto "gaos").
        url_fuente: URL de origen de los datos (por defecto "https://gaos.app/propiedades").

    Returns:
        El id_captura asignado a esta ejecución.

    Raises:
        OSError: si no se puede crear directorio ni escribir archivo.
    """
    id_captura = generar_id_captura()
    fecha_captura = obtener_fecha_captura()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Construir el registro de crudos tal como llegan de la API, sin datos
    # personales de contacto.
    datos_crudos = {
        "id_captura": id_captura,
        "fecha_captura": fecha_captura,
        "fuente": fuente,
        "url_fuente": url_fuente,
        "cantidad": len(crudos),
        "datos": [sanitizar_crudo(dato) for dato in crudos],
    }

    # Construir las cotizaciones ya mapeadas al esquema común.
    # Todos los campos del esquema común se leen del objeto AnuncioInmobiliario
    # ya mapeado, no de los datos crudos de GAOS (que usan claves distintas:
    # ulistingid, dcprice, vccurrencytype, iarea, ibeds, ibaths, vcaddress, etc.).
    anuncios_procesados = []
    for dato, anuncio in zip(crudos, anuncios):
        anuncios_procesados.append(
            {
                "id_fuente": anuncio.id_fuente,
                "url": anuncio.url,
                "fecha_captura": anuncio.fecha_captura,
                "fecha_publicacion": anuncio.fecha_publicacion,
                "fecha_actualizacion": anuncio.fecha_actualizacion,
                "provincia": anuncio.provincia,
                "municipio": anuncio.municipio,
                "reparto": anuncio.reparto,
                "direccion_texto": anuncio.direccion_texto,
                "tipo_operacion": anuncio.tipo_operacion,
                "tipo_inmueble": anuncio.tipo_inmueble,
                "area_m2": anuncio.area_m2,
                "tipo_area": anuncio.tipo_area,
                "habitaciones": anuncio.habitaciones,
                "banos": anuncio.banos,
                "planta": anuncio.planta,
                "estado_conservacion": anuncio.estado_conservacion,
                "amueblado": anuncio.amueblado,
                "precio": anuncio.precio,
                "moneda": anuncio.moneda,
                "precio_usd": anuncio.precio_usd,
                "tasa_conversion_usd": anuncio.tasa_conversion_usd,
                "tasa_fecha": anuncio.tasa_fecha,
                "tasa_fuente": anuncio.tasa_fuente,
                "precio_m2_usd": anuncio.precio_m2_usd,
                "tasa_id": anuncio.tasa_id,
                "titulo": anuncio.titulo,
                "descripcion": anuncio.descripcion,
                "vendedor_tipo": anuncio.vendedor_tipo,
                "estado_parseo": anuncio.estado_parseo,
                "notas_calidad": anuncio.notas_calidad,
                "es_posible_duplicado": anuncio.es_posible_duplicado,
                "duplicado_grupo": anuncio.duplicado_grupo,
            }
        )

    anuncios_procesados = [
        sanitizar_anuncio_procesado(anuncio) for anuncio in anuncios_procesados
    ]

    datos_procesados = {
        "id_captura": id_captura,
        "fecha_captura": fecha_captura,
        "fuente": fuente,
        "url_fuente": url_fuente,
        "cantidad": len(anuncios_procesados),
        "datos": anuncios_procesados,
    }

    sufijo = id_captura[:8]

    ruta_crudo_final = _ruta_crudo(ruta_crudo)
    ruta_procesado_final = _ruta_procesado(ruta_procesado)

    nombre_crudo = _nombre_archivo("crudo", id_captura, timestamp, prefijo_archivo)
    nombre_procesado = _nombre_archivo("procesado", id_captura, timestamp, prefijo_archivo)

    # Crear directorios si no existen
    ruta_crudo_final.mkdir(parents=True, exist_ok=True)
    ruta_procesado_final.mkdir(parents=True, exist_ok=True)

    # Recuperar temporales huérfanos de ejecuciones fallidas previas
    _limpiar_temporales(ruta_crudo_final)
    _limpiar_temporales(ruta_procesado_final)

    archivo_crudo = ruta_crudo_final / nombre_crudo
    archivo_procesado = ruta_procesado_final / nombre_procesado

    # Publicar ambos archivos; si falla el segundo, deshacer el primero
    publicados: list[Path] = []
    try:
        _escribir_json_atomico(archivo_crudo, datos_crudos)
        publicados.append(archivo_crudo)
        _escribir_json_atomico(archivo_procesado, datos_procesados)
        publicados.append(archivo_procesado)
    except Exception:
        for archivo in publicados:
            try:
                archivo.unlink(missing_ok=True)
            except OSError:
                pass
        raise

    return id_captura


def _buscar_archivo_captura(ruta: Path, patron: str) -> Path | None:
    """Devuelve el primer archivo que coincide con el patrón, o None."""
    for archivo in ruta.glob(patron):
        return archivo
    return None


def leer_captura(
    id_captura: str,
    ruta_crudo: Path | None = None,
    ruta_procesado: Path | None = None,
    prefijo_archivo: str = "gaos",
) -> dict | None:
    """Lee un par de archivos (crudo y procesado) por id_captura.

    Devuelve un diccionario con claves 'crudo' y 'procesado', o None si
    la captura es incompleta (falta alguno de los dos archivos) o si los
    identificadores internos de los archivos no coinciden con el
    id_captura solicitado.

    Args:
        id_captura: identificador de la captura.
        ruta_crudo: carpeta de crudos (opcional, usa la de GAOS por defecto).
        ruta_procesado: carpeta de procesados (opcional, usa la de GAOS por
            defecto).
        prefijo_archivo: prefijo del nombre de archivo ("gaos" por defecto;
            "revolico" para capturas de Revolico).
    """
    ruta_crudo = _ruta_crudo(ruta_crudo)
    ruta_procesado = _ruta_procesado(ruta_procesado)

    sufijo = id_captura[:8]

    archivo_crudo = _buscar_archivo_captura(
        ruta_crudo, f"{prefijo_archivo}_crudo_{sufijo}*.json"
    )
    archivo_procesado = _buscar_archivo_captura(
        ruta_procesado, f"{prefijo_archivo}_procesado_{sufijo}*.json"
    )

    # Captura incompleta: falta alguno de los dos archivos
    if archivo_crudo is None or archivo_procesado is None:
        return None

    with open(archivo_crudo, "r", encoding="utf-8") as f:
        crudo = json.load(f)
    with open(archivo_procesado, "r", encoding="utf-8") as f:
        procesado = json.load(f)

    id_crudo = crudo.get("id_captura")
    id_procesado = procesado.get("id_captura")

    # Los identificadores internos deben coincidir entre sí y con el solicitado
    if id_crudo != id_captura or id_procesado != id_captura or id_crudo != id_procesado:
        return None

    return {"crudo": crudo, "procesado": procesado}


def listar_capturas(
    ruta_crudo: Path | None = None,
    ruta_procesado: Path | None = None,
    prefijo_archivo: str = "gaos",
) -> list[dict]:
    """Lista todas las capturas disponibles, ordenadas de más reciente a más antigua.

    La fecha se extrae de la marca de tiempo del nombre de archivo
    (``gaos_<tipo>_<sufijo>_<YYYYMMDD_HHMMSS>.json``), no de una parte
    errónea del nombre.

    Args:
        ruta_crudo: carpeta de crudos (opcional, usa la de GAOS por defecto).
        ruta_procesado: carpeta de procesados (opcional, usa la de GAOS por
            defecto).
        prefijo_archivo: prefijo del nombre de archivo ("gaos" por defecto;
            "revolico" para capturas de Revolico).
    """
    ruta_crudo = _ruta_crudo(ruta_crudo)
    ruta_procesado = _ruta_procesado(ruta_procesado)

    capturas: dict[str, dict] = {}

    for archivo in ruta_crudo.glob(f"{prefijo_archivo}_crudo_*.json"):
        partes = archivo.stem.split("_")
        # gaos_crudo_<sufijo>_<YYYYMMDD>_<HHMMSS>  (el timestamp lleva "_")
        if (
            len(partes) >= 5
            and partes[0] == prefijo_archivo
            and partes[1] == "crudo"
        ):
            id_captura = partes[2]
            fecha_str = "_".join(partes[3:])
            capturas[id_captura] = {
                "id_captura": id_captura,
                "fecha_captura": fecha_str,
                "tiene_crudo": True,
                "tiene_procesado": False,
            }

    for archivo in ruta_procesado.glob(f"{prefijo_archivo}_procesado_*.json"):
        partes = archivo.stem.split("_")
        if (
            len(partes) >= 5
            and partes[0] == prefijo_archivo
            and partes[1] == "procesado"
        ):
            id_captura = partes[2]
            fecha_str = "_".join(partes[3:])
            if id_captura in capturas:
                capturas[id_captura]["tiene_procesado"] = True
            else:
                capturas[id_captura] = {
                    "id_captura": id_captura,
                    "fecha_captura": fecha_str,
                    "tiene_crudo": False,
                    "tiene_procesado": True,
                }

    return sorted(capturas.values(), key=lambda c: c["fecha_captura"], reverse=True)


def guardar_captura_completa(
    crudos: list[dict],
    ruta_crudo: Path | None = None,
    ruta_procesado: Path | None = None,
    mapear_func=None,
    prefijo_archivo: str = "gaos",
    fuente: str = "gaos",
    url_fuente: str = "https://gaos.app/propiedades",
) -> str | None:
    """Guarda las cotizaciones crudas de la API y las mapea automáticamente
    al esquema común, guardando ambos archivos con el mismo id_captura.

    Esta función es el punto de entrada recomendado: recibe una única lista
    de datos crudos, aplica el mapeo internamente mediante el mapeador
    propio de GAOS (``sources.gaos.mapear_anuncio``) o mediante un mapeador
    personalizado, y guarda ambos archivos con el mismo id_captura, sin
    realizar una segunda petición HTTP.

    Los datos sin el campo de precio propio de su fuente o con un precio no
    numérico se rechazan: no se guarda nada y se devuelve None. El campo es
    ``dcprice`` para GAOS y ``precio`` para Revolico.

    Antes de escribir, se eliminan de los crudos y de los anuncios los
    teléfonos, enlaces de WhatsApp, correos e instrucciones de contacto.
    El resto de la descripción se conserva.

    Args:
        crudos: lista de diccionarios tal como llegan de la API de GAOS.
        ruta_crudo: carpeta destino para los crudos (opcional).
        ruta_procesado: carpeta destino para los procesados (opcional).
        mapear_func: función opcional para mapear cada crudo a un
            ``AnuncioInmobiliario``. Debe aceptar (dato, fecha_captura) y
            devolver un objeto ``AnuncioInmobiliario``. Si no se proporciona,
            se usa ``sources.gaos.mapear_anuncio``, que conoce las claves
            propias de GAOS (``vcaddress``, ``sdescription_eng``, etc.).

    Returns:
        El id_captura asignado a esta ejecución, o None si los datos no son
        válidos y no se guardó nada.

    Raises:
        OSError: si no se puede crear directorio ni escribir archivo.
        ValueError: si el mapeador personalizado no devuelve un
            ``AnuncioInmobiliario``.
    """
    # Rechazar datos inválidos antes de escribir algo
    if not _crudos_validos(crudos, fuente):
        return None

    id_captura = generar_id_captura()
    fecha_captura = obtener_fecha_captura()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Mapear los datos crudos a objetos AnuncioInmobiliario. El mapeador por
    # defecto es el de GAOS, que conoce sus claves originales; se importa aquí
    # de forma perezosa porque sources.gaos importa este mismo módulo.
    if mapear_func is None:
        from sources.gaos import mapear_anuncio

        mapear_func = mapear_anuncio

    anuncios = []
    for dato in crudos:
        anuncio = mapear_func(dato, fecha_captura)

        if not isinstance(anuncio, AnuncioInmobiliario):
            raise ValueError(
                f"El mapeador debe devolver un AnuncioInmobiliario, "
                f"pero devolvió {type(anuncio).__name__}"
            )
        anuncios.append(anuncio)

    # Construir el registro de crudos tal como llegan de la API, sin datos
    # personales de contacto.
    datos_crudos = {
        "id_captura": id_captura,
        "fecha_captura": fecha_captura,
        "fuente": fuente,
        "url_fuente": url_fuente,
        "cantidad": len(crudos),
        "datos": [sanitizar_crudo(dato) for dato in crudos],
    }

    # Construir las cotizaciones ya mapeadas al esquema común.
    anuncios_procesados = []
    for dato, anuncio in zip(crudos, anuncios):
        anuncios_procesados.append(
            {
                "id_fuente": anuncio.id_fuente,
                "url": anuncio.url,
                "fecha_captura": anuncio.fecha_captura,
                "fecha_publicacion": anuncio.fecha_publicacion,
                "fecha_actualizacion": anuncio.fecha_actualizacion,
                "provincia": anuncio.provincia,
                "municipio": anuncio.municipio,
                "reparto": anuncio.reparto,
                "direccion_texto": anuncio.direccion_texto,
                "tipo_operacion": anuncio.tipo_operacion,
                "tipo_inmueble": anuncio.tipo_inmueble,
                "area_m2": anuncio.area_m2,
                "tipo_area": anuncio.tipo_area,
                "habitaciones": anuncio.habitaciones,
                "banos": anuncio.banos,
                "planta": anuncio.planta,
                "estado_conservacion": anuncio.estado_conservacion,
                "amueblado": anuncio.amueblado,
                "precio": anuncio.precio,
                "moneda": anuncio.moneda,
                "precio_usd": anuncio.precio_usd,
                "tasa_conversion_usd": anuncio.tasa_conversion_usd,
                "tasa_fecha": anuncio.tasa_fecha,
                "tasa_fuente": anuncio.tasa_fuente,
                "precio_m2_usd": anuncio.precio_m2_usd,
                "tasa_id": anuncio.tasa_id,
                "titulo": anuncio.titulo,
                "descripcion": anuncio.descripcion,
                "vendedor_tipo": anuncio.vendedor_tipo,
                "estado_parseo": anuncio.estado_parseo,
                "notas_calidad": anuncio.notas_calidad,
                "es_posible_duplicado": anuncio.es_posible_duplicado,
                "duplicado_grupo": anuncio.duplicado_grupo,
            }
        )

    anuncios_procesados = [
        sanitizar_anuncio_procesado(anuncio) for anuncio in anuncios_procesados
    ]

    datos_procesados = {
        "id_captura": id_captura,
        "fecha_captura": fecha_captura,
        "fuente": fuente,
        "url_fuente": url_fuente,
        "cantidad": len(anuncios_procesados),
        "datos": anuncios_procesados,
    }

    sufijo = id_captura[:8]

    ruta_crudo_final = _ruta_crudo(ruta_crudo)
    ruta_procesado_final = _ruta_procesado(ruta_procesado)

    nombre_crudo = _nombre_archivo("crudo", id_captura, timestamp, prefijo_archivo)
    nombre_procesado = _nombre_archivo("procesado", id_captura, timestamp, prefijo_archivo)

    # Crear directorios si no existen
    ruta_crudo_final.mkdir(parents=True, exist_ok=True)
    ruta_procesado_final.mkdir(parents=True, exist_ok=True)

    # Recuperar temporales huérfanos de ejecuciones fallidas previas
    _limpiar_temporales(ruta_crudo_final)
    _limpiar_temporales(ruta_procesado_final)

    archivo_crudo = ruta_crudo_final / nombre_crudo
    archivo_procesado = ruta_procesado_final / nombre_procesado

    # Publicar ambos archivos; si falla el segundo, deshacer el primero
    publicados: list[Path] = []
    try:
        _escribir_json_atomico(archivo_crudo, datos_crudos)
        publicados.append(archivo_crudo)
        _escribir_json_atomico(archivo_procesado, datos_procesados)
        publicados.append(archivo_procesado)
    except Exception:
        for archivo in publicados:
            try:
                archivo.unlink(missing_ok=True)
            except OSError:
                pass
        raise

    return id_captura
