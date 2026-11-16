"""Sistema de tasas de cambio del proyecto ICD 2026.

Este paquete contiene los extractores de tasas de cambio de las fuentes
configuradas (elTOQUE, BCC, etc.) y las utilidades para consultarlas.

No contiene lógica de negocio de conversión de precios; solo obtiene y
devuelve cotizaciones crudas con su procedencia y fecha.
"""

from .bcc import (
    BccConnectionError,
    BccError,
    BccStructureError,
    extraer_cotizaciones as extraer_cotizaciones_bcc,
    consultar_tasas as consultar_tasas_bcc,
)
from .eltoque import (
    ElToqueAuthError,
    ElToqueConnectionError,
    ElToqueError,
    consultar_tasas as consultar_tasas_eltoque,
    extraer_cotizaciones as extraer_cotizaciones_eltoque,
)

__all__ = [
    "BccConnectionError",
    "BccError",
    "BccStructureError",
    "consultar_tasas_bcc",
    "extraer_cotizaciones_bcc",
    "ElToqueAuthError",
    "ElToqueConnectionError",
    "ElToqueError",
    "consultar_tasas_eltoque",
    "extraer_cotizaciones_eltoque",
]