"""Sistema de tasas de cambio del proyecto ICD 2026.

Este paquete contiene los extractores de tasas de cambio de las fuentes
configuradas (elTOQUE, BCC, etc.) y las utilidades para consultarlas.

No contiene lógica de negocio de conversión de precios; solo obtiene y
devuelve cotizaciones crudas con su procedencia y fecha.
"""

from .eltoque import (
    ElToqueAuthError,
    ElToqueConnectionError,
    ElToqueError,
    consultar_tasas,
    extraer_cotizaciones,
)

__all__ = [
    "ElToqueAuthError",
    "ElToqueConnectionError",
    "ElToqueError",
    "consultar_tasas",
    "extraer_cotizaciones",
]
