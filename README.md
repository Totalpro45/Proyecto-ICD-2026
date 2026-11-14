# ¿Es asequible el precio de la vivienda para el cubano promedio?

**Proyecto académico — ICD 2026**
**Caso de estudio:** La Habana, Cuba
**Estado:** en desarrollo

Trabajo de la asignatura **Introducción a la Ciencia de Datos**, primer año de Ciencias de Datos. No es una
aplicación comercial ni un servicio web: es un proyecto de análisis de datos con
fines exclusivamente académicos.

## Objetivo

Analizar si el precio de la vivienda en La Habana es asequible para el cubano
promedio. Para ello se estudian anuncios de venta de casas y apartamentos y,
cuando los datos disponibles lo permiten, se comparan sus precios con distintos
referentes de ingreso.

El análisis previsto incluye:

- la distribución de precios por tipo de inmueble;
- las características de las viviendas (área, habitaciones, estado, etc.);
- la relación entre los precios anunciados y los ingresos disponibles.

Los precios que se analizan son **precios anunciados**, no precios de
transacción. Esa diferencia se explicará en todos los resultados.

## Fuentes de anuncios

Se han identificado los siguientes portales como posibles fuentes de anuncios:

- **GAOS** — extracción implementada (`src/sources/gaos.py`).
- **Revolico** — extracción implementada (`src/sources/revolico.py`).
- **Mambbu** — fuente candidata; su extracción está **pendiente de autorización** según sus términos de uso (ver `docs/decisiones.md` §8.3 y §10).
- **CasasOasis** — **excluida** de la extracción automatizada mientras no haya autorización expresa.

Cada portal se transforma a un **esquema de datos común** que permite
consolidar y comparar la información (ver `docs/decisiones.md`).

La extracción de GAOS y Revolico ya está implementada. Antes de poner en marcha
Mambbu se revisan las condiciones de uso de cada portal y, cuando corresponda, se
solicita autorización. No se intenta eludir mecanismos de protección anti
automatización.

## Tasas de cambio

Los anuncios inmobiliarios cubanos se publican en distintas monedas (CUP, USD,
MLC y EUR). Para compararlos y agregarlos hace falta una referencia común.

En Cuba coexisten dos referencias cambiarias que **no son equivalentes**:

- la **tasa oficial**, publicada por el Banco Central de Cuba (BCC);
- la **tasa del mercado informal**, documentada por elTOQUE.

El proyecto las conserva por separado, cada una con su procedencia y su fecha.
No se mezclan, no se promedian y no se presentan como si fueran la misma cosa.

El sistema de tasas de cambio está implementado (`src/exchange_rates/`). Existe
un historial de cotizaciones, y el repositorio incorpora una automatización
diaria mediante GitHub Actions para actualizar el historial de elTOQUE.

Las tasas no son el objeto de estudio: son un insumo para expresar los precios
inmobiliarios en una unidad comparable y para interpretar el contexto cambiario
en el que se anuncian.

## Uso de los datos

Los datos se utilizarán **exclusivamente con fines académicos y de análisis
estadístico**, en el marco de la asignatura Introduccion a la Ciencia de Datos.

- No hay uso comercial.
- No se redistribuirán los datos de elTOQUE ni se publicarán volcados de su API.
- No se recopilan datos personales de los anunciantes.
- En el informe se citará la fuente y la fecha de cada dato utilizado.

Este proyecto no está afiliado a elTOQUE ni al Banco Central de Cuba.

## Tecnologías y herramientas

- **Python** — lenguaje principal.
- `requests` y `BeautifulSoup` / `lxml` — descarga y parseo de HTML.
- `pandas` — limpieza, consolidación y análisis.
- `matplotlib` — visualización.
- **Jupyter** — exploración y análisis exploratorio.
- **JSON** — formato previsto para el historial de tasas.
- **Git y GitHub** — control de versiones y documentación.

`spaCy` figura como dependencia opcional y solo se usará si el análisis de texto
lo justifica.

## Estado actual

El proyecto está **en desarrollo**. Cuenta con el código fuente, el sistema de
pruebas funcionando y datos capturados de las fuentes implementadas.

| Etapa | Estado |
|---|---|
| Estructura del repositorio | Hecha |
| Esquema de datos común | Documentado e implementado (`src/data/models.py`) |
| Plan de análisis | Documentado |
| Normalización y clasificación | Implementado (`src/data/normalization.py`, `src/data/mapper.py`) |
| Almacenamiento de capturas | Implementado (`src/data/almacenamiento_anuncios.py`) |
| Unificación de capturas | Implementado (`src/data/unificacion.py`) |
| Extracción de anuncios | Implementado para GAOS y Revolico (`src/sources/gaos.py`, `src/sources/revolico.py`) |
| Extracción de Mambbu | Pendiente (sujeta a autorización; ver `docs/decisiones.md` §8.3 y §10) |
| CasasOasis | Excluida mientras no haya autorización expresa |
| Sistema de tasas de cambio | Implementado (`src/exchange_rates/`) |
| Automatización de elTOQUE | Implementada y ejecutada mediante GitHub Actions |
| Identificación de municipios | Implementada (basada en texto, auditoría pendiente) |
| Datos salariales (Resolución 14) | Integrados (`data/reference/salarios/`); análisis pendiente en el notebook |
| Análisis exploratorio de precios | Ejecutado (figuras en `outputs/figuras/`); no es un análisis definitivo de todo el mercado |
| Comparación salarial | Pendiente de implementar |
| Análisis municipal | Pendiente de consolidar |
| Análisis de características | Pendiente |
| Precio por metro cuadrado | Pendiente de validar por las limitaciones de los datos de área |
| Notebook de análisis definitivo | Pendiente |

## Datos salariales

Para la comparación de precios con ingresos, se han integrado los datos de la
Resolución 14 de la Gaceta Oficial Ordinaria No. 60 (2026), disponibles en
`data/reference/salarios/`:

- `escala_general.csv` — escala salarial única del sector presupuestado.
- `cargos_sectoriales.csv` — cargos de distintas fuentes sectoriales.
- `pagos_adicionales.csv` — bonificaciones y coeficientes de ajuste.

Estos datos se utilizarán para comparar los precios inmobiliarios con
distintas referencias salariales. El análisis salarial todavía está pendiente
de implementación en el notebook de análisis.

## Identificación municipal

Se ha implementado una función (`src/data/normalization.py`) para identificar
los municipios de La Habana a partir de títulos y direcciones de los
anuncios, mediante normalización y búsqueda de texto (sin distinción de
mayúsculas ni tildes). No se utiliza spaCy y no se ha considerado necesario
para esta primera solución.

La identificación todavía requiere auditoría: no todos los anuncios tienen
municipio asignado, y los resultados no están completamente validados.

## Estructura del repositorio

```text
.
├── docs/                  Documentación del proyecto
│   ├── decisiones.md
│   ├── especificacion_analisis.md
│   └── sistema_tasas_cambio.md
├── src/                   Código fuente
│   ├── data/              Modelo, normalización, mapeo, almacenamiento y unificación
│   │   ├── almacenamiento_anuncios.py
│   │   ├── models.py
│   │   ├── mapper.py
│   │   ├── normalization.py
│   │   └── unificacion.py
│   ├── sources/           Extractores de fuentes inmobiliarias
│   │   ├── gaos.py        (extracción de GAOS implementada)
│   │   └── revolico.py    (extracción de Revolico implementada)
│   ├── exchange_rates/    Sistema de tasas de cambio (implementado)
│   └── analysis/          Directorio vacío (análisis pendiente en notebook)
├── tests/                 Pruebas del proyecto
├── outputs/               Resultados locales de análisis (gráficos y tablas de texto)
├── data/                  Datos locales (no se versionan)
│   └── reference/         Datos de referencia (salariales, etc.)
├── requirements.txt
└── README.md
```

Las carpetas `data/raw/`, `data/processed/` y `outputs/` contienen datos y
resultados locales que **no deben publicarse en Git**. Solo se versionan el código
y la documentación.

## Requisitos e instalación

- Python 3.12 o 3.13 **recomendado** (la 3.14 es muy reciente y algunas
  dependencias pueden no tener binarios precompilados).
- En Windows, usar el lanzador `py` (`python`/`pip` pueden no estar en el PATH).

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m pip install pytest
```

## Uso

El proyecto cuenta con pruebas automatizadas (`pytest`). Para ejecutarlas:

```powershell
py -m pytest tests/ -q
```

El extractor de GAOS (`src/sources/gaos.py`) permite obtener anuncios de
viviendas en venta de La Habana mediante el Edge Function público de Supabase
utilizado por el portal. Requiere la `apikey` pública de Supabase (rol `anon`)
que se configura en el propio módulo.

El extractor de Revolico (`src/sources/revolico.py`) permite obtener anuncios
de viviendas en venta de La Habana desde el portal de Revolico. No recopila
datos personales de vendedores (nombres, teléfonos, WhatsApp).

El módulo de almacenamiento (`src/data/almacenamiento_anuncios.py`) guarda
capturas crudas y procesadas por fuente, con metadatos de `fuente` y
`url_fuente`. La función de unificación (`src/data/unificacion.py`) combina
capturas de GAOS y Revolico en un único archivo JSON, manteniendo la
procedencia de cada anuncio mediante el campo `fuente` en cada registro.

## Automatización de tasas de cambio (GitHub Actions)

El proyecto incluye un workflow de GitHub Actions (`tasas-cambio.yml`) que
consulta la API de elTOQUE una vez al día y guarda las cotizaciones en el
historial de tasas de cambio (`data/raw/exchange_rates/historial_tasas.json`).

La credencial de elTOQUE se administra mediante los secretos del repositorio;
quien clone el proyecto no necesita obtener una clave propia para ejecutar las
pruebas ni trabajar con los análisis.

El workflow:

1. Descarga el repositorio e instala Python y las dependencias.
2. Ejecuta `src/exchange_rates/capturar.py`, que consulta la API de elTOQUE
   y guarda las cotizaciones nuevas en el historial.
3. Si hay cambios, los commitea y sube a la rama principal.
4. Si no hay novedad (misma cotización que la anterior), no crea commit.

Este archivo de historial es el único de `data/` que se versiona; el resto de
los datos locales no se suben a GitHub.

## Documentación

- [`docs/decisiones.md`](docs/decisiones.md): esquema de datos común, políticas y
  decisiones del proyecto, incluidas las pruebas de acceso a Revolico, GAOS y
  Mambbu, y el diseño del almacenamiento y unificación de capturas.
- [`docs/especificacion_analisis.md`](docs/especificacion_analisis.md): plan de
  análisis, variables, cálculos y limitaciones, incluido el análisis exploratorio
  de precios de GAOS y Revolico.
- [`docs/sistema_tasas_cambio.md`](docs/sistema_tasas_cambio.md): diseño del
  registro de tasas de cambio.

## Alcance y limitaciones

- Es un trabajo de primer año: prioriza la claridad y la trazabilidad sobre la
  complejidad técnica.
- La muestra actual procede de GAOS y Revolico y no representa necesariamente
  todo el mercado inmobiliario de La Habana.
- Los precios son precios anunciados, no precios finales de compraventa.
- Existen valores ausentes en las características de los inmuebles.
- La identificación de municipios se basa en texto y todavía requiere auditoría.
- Los datos de área son incompletos y sus unidades deben verificarse antes de
  calcular precios por metro cuadrado.
- Las tasas oficiales e informales representan referencias distintas.
- La equivalencia entre precios y meses de salario no representa el tiempo real
  necesario para comprar una vivienda.
- Revolico y GAOS presentan restricciones de acceso (HTTP 403 y 429
  respectivamente desde `requests`). Mambbu prohíbe la extracción automatizada
  en sus términos de uso. CasasOasis queda excluida mientras no haya
  autorización expresa. Consulte `docs/decisiones.md` §8 y §10 para detalles.
