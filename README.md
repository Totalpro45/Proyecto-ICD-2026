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

## Por qué se usan tasas de cambio

Los anuncios inmobiliarios cubanos se publican en distintas monedas (CUP, USD,
MLC y EUR). Para compararlos y agregarlos hace falta una referencia común.

En Cuba coexisten dos referencias cambiarias que **no son equivalentes**:

- la **tasa oficial**, publicada por el Banco Central de Cuba (BCC);
- la **tasa del mercado informal**, documentada por elTOQUE.

El proyecto las conserva por separado, cada una con su procedencia y su fecha.
No se mezclan, no se promedian y no se presentan como si fueran la misma cosa.

La conversión de los precios a una moneda común dependerá de la disponibilidad
de tasas documentadas y justificables para la fecha correspondiente. Cuando no
exista una referencia adecuada, los anuncios se analizarán por separado según
su moneda original.

Las tasas no son el objeto de estudio: son un insumo para expresar los precios
inmobiliarios en una unidad comparable y para interpretar el contexto cambiario
en el que se anuncian.

## Qué se consultará en la API de elTOQUE

Se ha solicitado acceso a la API de elTOQUE para obtener, si se concede,
cotizaciones de baja frecuencia (frecuencia prevista: una vez al día) de:

- **USD** (dólar estadounidense);
- **EUR** (euro);
- **MLC** (moneda libremente convertible).

De cada cotización se conservará:

- el valor;
- la moneda de origen y la moneda de destino;
- la fecha de publicación que indique la fuente, si la declara;
- la fecha y hora de nuestra captura;
- la URL y la fuente consultada.

No se inventarán valores ni fechas. Si la fuente no publica un dato o este no
puede interpretarse, se registrará la incidencia y no se completará el hueco.

La integración con la API **todavía no está implementada**; el acceso se
encuentra en trámite.

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
| Diseño del sistema de tasas | Documentado e implementado (`src/exchange_rates/`) |
| Extracción de anuncios | Implementado para GAOS y Revolico (`src/sources/gaos.py`, `src/sources/revolico.py`) |
| Extracción de Mambbu | Pendiente (sujeta a autorización; ver `docs/decisiones.md` §8.3 y §10) |
| CasasOasis | Excluida mientras no haya autorización expresa |
| Almacenamiento de capturas | Implementado (`src/data/almacenamiento_anuncios.py`) |
| Unificación de capturas | Implementado (`src/data/unificacion.py`) |
| Limpieza y consolidación | Implementada (`src/data/normalization.py`, `src/data/mapper.py`) |
| Análisis y visualizaciones | Análisis exploratorio de precios ejecutado (figuras en `outputs/figuras/`); no es un análisis definitivo de todo el mercado |
| Salarios | Pendiente de incorporación al proyecto |

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
│   │   ├── modelos.py
│   │   ├── mapper.py
│   │   ├── normalización.py
│   │   └── unificacion.py
│   ├── sources/           Extractores de fuentes inmobiliarias
│   │   ├── gaos.py        (extracción de GAOS implementada)
│   │   └── revolico.py    (extracción de Revolico implementada)
│   ├── exchange_rates/    Sistema de tasas de cambio (implementado)
│   └── analysis/          Análisis y visualizaciones (no implementado como módulo)
├── tests/                 Pruebas del proyecto
├── outputs/               Resultados locales de análisis (gráficos y tablas de texto)
├── data/                  Datos locales (no se versionan)
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

El proyecto incluye un workflow de GitHub Actions que consulta la API de elTOQUE
una vez al día y guarda las cotizaciones en el historial de tasas de cambio.

### Configurar el secreto en GitHub

Antes de que el workflow funcione, debes agregar la clave API de elTOQUE como
secreto del repositorio:

1. Ve a **Settings** → **Secrets and variables** → **Actions** en GitHub.
2. Haz clic en **New repository secret**.
3. Nombre: `ELTOQUE_API_TOKEN`
4. Valor: la clave API que obtuviste en `https://tasas-token.eltoque.com/`
5. Haz clic en **Add secret**.

### Ejecutar el workflow manualmente

Desde la pestaña **Actions** de GitHub, selecciona el workflow
**"Captura diaria de tasas de cambio (elTOQUE)"** y haz clic en
**Run workflow**.

### Qué hace el workflow

1. Descarga el repositorio e instala Python y las dependencias.
2. Ejecuta `src/exchange_rates/capturar.py`, que consulta la API de elTOQUE
   y guarda las cotizaciones nuevas en
   `data/raw/exchange_rates/historial_tasas.json`.
3. Si hay cambios, los commitea y sube a la rama principal.
4. Si no hay novedad (misma cotización que la anterior), no crea commit.

El historial se guarda en `data/raw/exchange_rates/historial_tasas.json`.
Este archivo es el único de `data/` que se versiona; el resto de los datos
locales no se suben a GitHub.

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
- Los anuncios no representan todas las transacciones ni todo el mercado.
- Los resultados dependerán de la cobertura real de los datos y se reportará el
  tamaño de muestra de cada cálculo.
- Las conclusiones serán descriptivas; no se afirmarán relaciones causales.
- Revolico y GAOS presentan restricciones de acceso (HTTP 403 y 429
  respectivamente desde `requests`). Mambbu prohíbe la extracción automatizada
  en sus términos de uso. Consulte `docs/decisiones.md` §8 y §10 para detalles.
