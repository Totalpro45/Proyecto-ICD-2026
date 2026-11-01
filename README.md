# ¿Es asequible el precio de la vivienda para el cubano promedio?

**Proyecto académico — ICD 2026**
**Caso de estudio:** La Habana, Cuba
**Estado:** en desarrollo

Trabajo de la asignatura **Introducción a la Ciencia de Datos**, primer año de Ciencias de Datos. No es una
aplicación comercial ni un servicio web: es un proyecto de análisis de datos con
fines exclusivamente académicos.

## Objetivo

Analizar si el precio de la vivienda en La Habana es asequible para el cubano
promedio. Para ello se estudiarán anuncios de venta de casas y apartamentos y,
cuando los datos disponibles lo permitan, se compararán sus precios con distintos
referentes de ingreso.

El análisis previsto incluye:

- la distribución de precios por municipio y tipo de inmueble;
- el precio por metro cuadrado;
- las características de las viviendas (área, habitaciones, estado, etc.);
- la relación entre los precios anunciados y los ingresos disponibles.

Los precios que se analizan son **precios anunciados**, no precios de
transacción. Esa diferencia se explicará en todos los resultados.

## Fuentes de anuncios (previstas)

Se han identificado los siguientes portales como posibles fuentes de anuncios:

- Revolico
- GAOS
- Mambbu

Cada portal se transformará a un **esquema de datos común** que permita
consolidar y comparar la información (ver `docs/decisiones.md`).

La extracción automatizada todavía no ha comenzado. Antes de ponerla en marcha
se revisarán las condiciones de uso de cada portal y, cuando corresponda, se
solicitará autorización. No se intentará eludir mecanismos de protección
anti automatización.

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

El proyecto está **en desarrollo**. Todavía no hay código ejecutable ni datos
recopilados.

| Etapa | Estado |
|---|---|
| Estructura del repositorio | Hecha |
| Esquema de datos común | Documentado (borrador) |
| Plan de análisis | Documentado |
| Diseño del sistema de tasas | Documentado, no implementado |
| Extracción de anuncios | No iniciada |
| Integración con la API de elTOQUE | Pendiente de acceso |
| Limpieza y consolidación | No iniciada |
| Análisis y visualizaciones | No iniciados |

## Estructura del repositorio

```text
.
├── docs/                  Documentación del proyecto
│   ├── decisiones.md
│   ├── especificacion_analisis.md
│   └── sistema_tasas_cambio.md
├── requirements.txt
└── README.md
```

Las carpetas `data/`, `src/`, `notebooks/` y `outputs/` se crearán cuando empiece
la implementación. Los datos locales no se versionan.

## Requisitos e instalación

- Python 3.12 o 3.13 **recomendado** (la 3.14 es muy reciente y algunas
  dependencias pueden no tener binarios precompilados).
- En Windows, usar el lanzador `py` (`python`/`pip` pueden no estar en el PATH).

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

## Uso

Aún no hay código ejecutable. El desarrollo se hará por etapas pequeñas y cada
etapa se documentará antes de continuar.

## Documentación

- [`docs/decisiones.md`](docs/decisiones.md): esquema de datos común, políticas y
  decisiones del proyecto.
- [`docs/especificacion_analisis.md`](docs/especificacion_analisis.md): plan de
  análisis, variables, cálculos y limitaciones.
- [`docs/sistema_tasas_cambio.md`](docs/sistema_tasas_cambio.md): diseño del
  registro de tasas de cambio.

## Alcance y limitaciones

- Los anuncios no representan todas las transacciones ni todo el mercado.
- Los resultados dependerán de la cobertura real de los datos y se reportará el
  tamaño de muestra de cada cálculo.
- Las conclusiones serán descriptivas; no se afirmarán relaciones causales.
