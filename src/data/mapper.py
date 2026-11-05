"""Mapeo de datos extraídos al modelo común de anuncios inmobiliarios.

Convierte un diccionario con datos de origen en una instancia de
`AnuncioInmobiliario`, aplicando las funciones de normalización cuando
corresponda.
"""

from data.models import AnuncioInmobiliario
from data.normalization import (
    normalizar_amueblado,
    normalizar_estado_conservacion,
    normalizar_moneda,
    normalizar_municipio,
    normalizar_tipo_area,
    normalizar_tipo_inmueble,
    normalizar_tipo_operacion,
)

# Campos obligatorios del modelo que deben estar presentes en el diccionario.
CAMPOS_OBLIGATORIOS = ("fuente", "id_fuente", "url", "fecha_captura")


def crear_anuncio(datos):
    """Crea un `AnuncioInmobiliario` a partir de un diccionario de datos.

    Copia los campos que existen en el modelo y aplica normalización a los
    campos que lo requieren. Los campos ausentes o no identificables quedan
    como `None`. No convierte precios ni consulta tasas de cambio.
    """
    if not isinstance(datos, dict):
        raise ValueError("datos debe ser un diccionario")

    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in datos or datos[campo] is None:
            raise ValueError(f"Campo obligatorio ausente: {campo}")

    return AnuncioInmobiliario(
        # --- Trazabilidad y fuente ---
        fuente=datos["fuente"],
        id_fuente=datos["id_fuente"],
        url=datos["url"],
        fecha_captura=datos["fecha_captura"],
        fecha_publicacion=datos.get("fecha_publicacion"),
        fecha_actualizacion=datos.get("fecha_actualizacion"),

        # --- Ubicación ---
        provincia=datos.get("provincia"),
        municipio=normalizar_municipio(datos.get("municipio")),
        reparto=datos.get("reparto"),
        direccion_texto=datos.get("direccion_texto"),

        # --- Características del inmueble ---
        tipo_operacion=normalizar_tipo_operacion(datos.get("tipo_operacion")),
        tipo_inmueble=normalizar_tipo_inmueble(datos.get("tipo_inmueble")),
        area_m2=datos.get("area_m2"),
        tipo_area=normalizar_tipo_area(datos.get("tipo_area")),
        habitaciones=datos.get("habitaciones"),
        banos=datos.get("banos"),
        planta=datos.get("planta"),
        estado_conservacion=normalizar_estado_conservacion(
            datos.get("estado_conservacion")
        ),
        amueblado=normalizar_amueblado(datos.get("amueblado")),

        # --- Precio y moneda (valores originales) ---
        precio=datos.get("precio"),
        moneda=normalizar_moneda(datos.get("moneda")),

        # --- Conversión a USD (sin conversion todavía) ---
        precio_usd=None,
        tasa_conversion_usd=None,
        tasa_fecha=None,
        tasa_fuente=None,
        precio_m2_usd=None,
        tasa_id=None,

        # --- Texto descriptivo ---
        titulo=datos.get("titulo"),
        descripcion=datos.get("descripcion"),

        # --- Vendedor (sin datos personales) ---
        vendedor_tipo=datos.get("vendedor_tipo"),

        # --- Calidad de los datos ---
        estado_parseo=datos.get("estado_parseo", "ok"),
        notas_calidad=datos.get("notas_calidad"),
        es_posible_duplicado=datos.get("es_posible_duplicado", False),
        duplicado_grupo=datos.get("duplicado_grupo"),
    )
