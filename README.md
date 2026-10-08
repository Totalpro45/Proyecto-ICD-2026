# Proyecto-ICD-2026

Trabajo de la asignatura **ICD 2026** (primer semestre de Ciencias de Datos).

**Título provisional:** ¿Es asequible el precio de la vivienda para el cubano promedio?
**Caso de estudio:** La Habana.

## Objetivo

Estudiar los anuncios inmobiliarios de La Habana para analizar:

- la distribución de los precios por municipio;
- el precio por metro cuadrado;
- las características de las viviendas (área, habitaciones, tipo de inmueble, etc.);
- la relación entre los precios de venta anunciados y los salarios disponibles.

## Fuentes de datos

Inicialmente se usarán cuatro portales de anuncios inmobiliarios cubanos:

- Revolico
- GAOS
- Mambbu
- CasasOasis

Cada portal se descargará y transformará a un **esquema de datos común** (ver
`docs/decisiones.md`) que permita consolidar y comparar la información.

## Tecnologías previstas

- Python
- `requests` + `BeautifulSoup` (descarga y parseo de HTML)
- `pandas` (limpieza y análisis)
- `matplotlib` (visualización)
- `spaCy` (opcional, solo si el análisis de texto lo justifica)

## Requisitos previos

- Python 3.12 o 3.13 **recomendado** (la 3.14 es muy reciente y algunas
  dependencias pueden no tener binarios precompilados).
- En Windows, usar el lanzador `py` (`python`/`pip` pueden no estar en el PATH).

## Instalación

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

## Uso

Aún no hay código ejecutable. El desarrollo se hará por etapas pequeñas.

## Estructura del proyecto (prevista)

```
.
├── data/
│   ├── raw/          # HTML/JSON tal como se descarga (no versionado)
│   └── processed/    # CSV limpios listos para análisis (no versionado)
├── notebooks/        # Exploración y EDA
├── src/              # Código reutilizable (scraper, parsing, cleaning)
├── outputs/
│   ├── figures/      # Gráficos generados
│   └── tables/       # Tablas generadas
└── docs/             # Decisiones, supuestos y documentación
```

## Estado

- [x] Estructura base del repositorio
- [ ] Definición del esquema de datos común
- [ ] Recolección (scraping) por fuente
- [ ] Limpieza y consolidación
- [ ] Análisis y visualizaciones
- [ ] Relación precios vs. salarios
