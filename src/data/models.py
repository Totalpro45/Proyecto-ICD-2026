"""Modelo de datos común para anuncios inmobiliarios.

Define la clase `AnuncioInmobiliario` con el esquema acordado en
`docs/decisiones.md`. Todos los campos opcionales aceptan `None`; no se
inventan valores predeterminados para características desconocidas.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AnuncioInmobiliario:
    """Un anuncio inmobiliario normalizado al esquema común del proyecto.

    Conserva siempre los valores originales de precio y moneda. Los campos de
    conversión (`precio_usd`, `tasa_*`, `tasa_id`) solo se rellenan cuando existe
    una tasa de cambio documentada y justificable.
    """

    # --- Trazabilidad y fuente ---
    fuente: str
    id_fuente: str
    url: str
    fecha_captura: str
    fecha_publicacion: Optional[str] = None
    fecha_actualizacion: Optional[str] = None

    # --- Ubicación ---
    provincia: Optional[str] = None
    municipio: Optional[str] = None
    reparto: Optional[str] = None
    direccion_texto: Optional[str] = None

    # --- Características del inmueble ---
    tipo_operacion: Optional[str] = None
    tipo_inmueble: Optional[str] = None
    area_m2: Optional[float] = None
    tipo_area: Optional[str] = None
    habitaciones: Optional[int] = None
    banos: Optional[int] = None
    planta: Optional[str] = None
    estado_conservacion: Optional[str] = None
    amueblado: Optional[bool] = None

    # --- Precio y moneda (valores originales) ---
    precio: Optional[float] = None
    moneda: Optional[str] = None

    # --- Conversión a USD (solo si existe tasa documentada) ---
    precio_usd: Optional[float] = None
    tasa_conversion_usd: Optional[float] = None
    tasa_fecha: Optional[str] = None
    tasa_fuente: Optional[str] = None
    precio_m2_usd: Optional[float] = None
    tasa_id: Optional[str] = None

    # --- Texto descriptivo ---
    titulo: Optional[str] = None
    descripcion: Optional[str] = None

    # --- Vendedor (sin datos personales) ---
    vendedor_tipo: Optional[str] = None

    # --- Calidad de los datos ---
    estado_parseo: str = "ok"
    notas_calidad: Optional[str] = None
    es_posible_duplicado: bool = False
    duplicado_grupo: Optional[str] = None
