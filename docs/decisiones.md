# Esquema de datos común y decisiones iniciales

**Proyecto:** ¿Es asequible el precio de la vivienda para el cubano promedio?
**Caso de estudio:** La Habana
**Fuentes iniciales:** Revolico, GAOS, Mambbu, CasasOasis
**Fuentes candidatas a extracción:** Revolico, GAOS y Mambbu (sujetas a verificar
condiciones de acceso y uso). **CasasOasis:** datos disponibles, pero su
integración aún no está implementada; se abordará después de la reestructuración
y corrección de errores del proyecto.
**Estado:** borrador; recoge decisiones de diseño y criterios, algunos ya
aplicados en componentes implementados (extractores de GAOS y Revolico,
almacenamiento y unificación de capturas de anuncios, y consulta y registro de
tasas de cambio). No describe por completo la implementación ni el estado final
del proyecto: quedan aspectos pendientes y limitaciones documentadas, como la
autorización de Mambbu, la integración de CasasOasis y las restricciones de
acceso de los portales.

Este documento define el **esquema de datos común** al que se transformarán los
anuncios de las fuentes, junto con las políticas de moneda, datos personales,
valores ausentes, duplicados, la información recabada en la inspección técnica
previa al scraping y las decisiones del sistema de tasas de cambio.

---

## 1. Esquema de datos común

Convenciones:

- `null` indica **dato ausente**; nunca se usa un valor inventado ni se
  presupone información que el anuncio no declara.
- Los tipos son orientativos para la futura implementación en `pandas`.
- "Obligatorio" significa que debe existir para toda fila válida; "opcional"
  depende de lo que exponga cada portal.

### 1.1 Trazabilidad y fuente

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `fuente` | categoría | sí | Portal de origen: `revolico`, `gaos`, `mambbu`, `casasoasis`. |
| `id_fuente` | texto | sí | Identificador del anuncio dentro del portal. |
| `url` | texto | sí | URL del anuncio. |
| `fecha_captura` | fecha-hora (ISO 8601) | sí | Momento en que se descargó el anuncio. Clave para la reproducibilidad. |
| `fecha_publicacion` | fecha | no | Fecha de publicación, solo si el portal la muestra de forma fiable. |
| `fecha_actualizacion` | fecha | no | Última actualización, solo si el portal la muestra. |

### 1.2 Ubicación

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `provincia` | categoría | no | Se espera `La Habana`; `null` si no es determinable. |
| `municipio` | categoría | no | Uno de los municipios de La Habana. `null` si no se puede determinar con certeza. |
| `reparto` | texto | no | Barrio o reparto, si aparece. |
| `direccion_texto` | texto | no | Dirección tal como aparece, sin forzar normalización. |

> La lista canónica de municipios todavía debe fijarse (ver sección 6).

### 1.3 Características del inmueble

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `tipo_operacion` | categoría | no | `venta`, `alquiler`, `otro`; `null` si no es claro. |
| `tipo_inmueble` | categoría | no | `apartamento`, `casa`, `habitacion`, `solar`, `otro`. |
| `area_m2` | decimal | no | Área declarada en metros cuadrados. No se recalcula ni se estima. |
| `habitaciones` | entero | no | Número de habitaciones declarado. |
| `banos` | entero | no | Número de baños declarado. |
| `planta` | texto | no | Planta o nivel, si aparece (puede ser no numérico, p. ej. "planta baja"). |
| `estado_conservacion` | texto | no | Estado declarado (p. ej. "bueno", "para remodelar"), tal cual. |
| `amueblado` | booleano | no | Solo si el anuncio lo indica explícitamente. |

### 1.4 Precio y moneda

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `precio` | decimal | sí (si el anuncio tiene precio) | Valor numérico **original**, tal como se anuncia. |
| `moneda` | categoría | sí (si hay `precio`) | `USD`, `MLC`, `CUP`, `EUR` u `otra`. Moneda original. |
| `precio_usd` | decimal | no | Precio normalizado a USD. Solo se rellena si existe una tasa documentada y justificable (ver sección 2). Si no, `null`. |
| `tasa_conversion_usd` | decimal | no | Tasa aplicada para obtener `precio_usd`. |
| `tasa_fecha` | fecha/hora | no | Fecha y hora de captura de la cotización aplicada (`fecha_captura`). No representa necesariamente su fecha de publicación ni de vigencia. |
| `tasa_fuente` | texto | no | Fuente de la tasa aplicada. |
| `precio_m2_usd` | decimal | no | Derivado: `precio_usd / area_m2`, solo si ambos existen y `area_m2 > 0`. |

> **Nota sobre el estado actual:** en el archivo unificado procesado
> (`data/processed/anuncios/unificado_procesado_83924fda_20261115_034632.json`),
> los campos `precio_usd`, `tasa_conversion_usd`, `tasa_fecha`, `tasa_fuente`
> y `tasa_id` permanecen vacíos (`null`) en todos los registros, ya que no se
> ha aplicado ninguna conversión a USD. Estos campos están definidos en el
> esquema para cuando exista una tasa de cambio documentada y justificable;
> hasta entonces, los precios se conservan únicamente en su moneda original.

**Validación del precio al guardar.** Antes de escribir una captura,
`guardar_captura_completa()` valida el lote completo con `_crudos_validos()`.
El campo de precio depende de la fuente (`CAMPOS_PRECIO_CRUDO`: `dcprice` para
GAOS y `precio` para Revolico); una fuente no registrada cae en `precio`. Se
rechaza el lote —no se guarda nada y la función devuelve `None`— si algún crudo
no incluye ese campo o si su valor no es numérico. Se aceptan enteros, decimales
y cadenas convertibles a `float`; se rechazan booleanos, cadenas vacías o no
numéricas, listas y diccionarios. Un `null` explícito se acepta como precio
desconocido, igual que en el esquema común. La validación no exige que el valor
sea positivo ni comprueba la moneda.

`guardar_captura()` es una función de nivel inferior que recibe anuncios ya
mapeados y **no** aplica esta validación. Los flujos de los extractores
(`capturar_y_guardar`, `capturar_y_guardar_revolico` y
`ampliar_captura_controlada`) usan `guardar_captura_completa()`.

#### 1.4.1 Trazabilidad de la conversión

Para que `precio_usd` pueda ser reproducible hasta la cotización concreta, el
esquema define **un solo campo adicional**, sin eliminar los existentes:

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `tasa_id` | texto | no | Referencia al `id` de la cotización aplicada (ver sección 11 y `docs/sistema_tasas_cambio.md`). Se guarda como texto libre: no se valida el formato UUID. `null` si no hubo conversión. |

**Estado de implementación:** el campo ya existe en el modelo
(`AnuncioInmobiliario.tasa_id`), en el mapeo y en los archivos procesados, y se
serializa con valor `null` por defecto. El modelo lo declara como texto opcional
(`Optional[str]`) y no valida que sea un UUID. Ningún flujo aplica todavía
conversiones a USD, así que ningún registro lo rellena: los extractores y el
mapeo lo inicializan en `null`. Su presencia no garantiza por sí sola la
trazabilidad mientras no exista una conversión que lo asigne.

**Justificación:** `tasa_conversion_usd`, `tasa_fecha` y `tasa_fuente` permiten
leer una conversión, pero no identifican de forma única la cotización usada. Con
`tasa_id` se pueden recuperar del historial la categoría, la modalidad, el
segmento y las fechas exactas, sin duplicar esos datos en cada anuncio. El
almacenamiento de anuncios no comprueba que el UUID exista en el historial de
tasas ni que corresponda a la conversión aplicada.

### 1.5 Texto descriptivo

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `titulo` | texto | no | Título del anuncio. |
| `descripcion` | texto | no | Cuerpo o descripción completa del anuncio. |

### 1.6 Vendedor (sin datos personales)

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `vendedor_tipo` | categoría | no | `particular`, `agencia` o `desconocido`, solo cuando sea razonablemente identificable. |

### 1.7 Calidad de los datos

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `estado_parseo` | categoría | sí | `ok`, `parcial` o `error`, según cuánto se pudo extraer. |
| `notas_calidad` | texto | no | Incidencias, ambigüedades o campos dudosos del anuncio. |
| `es_posible_duplicado` | booleano | sí | Marca si el anuncio podría estar duplicado (ver sección 5). Por defecto `False`. |
| `duplicado_grupo` | texto | no | Identificador del grupo de posibles duplicados. No implica eliminación. |

---

## 2. Política de moneda y normalización a USD

1. **Siempre** se conservan `precio` y `moneda` originales.
2. `precio_usd` se rellena **solo** cuando existe una tasa de conversión
   documentada, con fuente (`tasa_fuente`) y fecha (`tasa_fecha`).
3. **No se inventan tasas** ni se asume una única tasa para todos los anuncios
   en CUP. El mercado informal de divisas puede variar en el tiempo, por
   ubicación y por tipo de cambio, por lo que aplicar una sola tasa sería
   injustificable.
4. Si la moneda es ambigua, si no hay tasa fiable, o si la conversión no es
   defendible, `precio_usd` queda en `null`.
5. La elección de la fuente de tasas (p. ej. oficial vs. informal) es una
   decisión **pendiente** (sección 6). El sistema de registro y consulta de
   tasas se especifica en la sección 11.
6. Las tasas **oficiales** y las del **mercado informal** no se mezclan ni se
   tratan como equivalentes. Cada conversión conserva la categoría de la
   cotización utilizada, obtenida a través de `tasa_id`.
7. Cuando se convierta un precio, se guardará el `tasa_id` de la cotización
   aplicada, de modo que la conversión sea reproducible.

---

## 3. Datos ausentes frente a valores cero

- Un dato que no aparece se registra como `null` (o `NaN` en pandas), **no**
  como `0`.
- `0` se usa únicamente cuando el anuncio expresa explícitamente un valor de
  cero (p. ej. "0 habitaciones" no es habitual, pero "0 baños" podría darse en
  un solar).
- **No se imputan ni se inventan** metros cuadrados, habitaciones, baños,
  municipios ni ninguna otra característica. Si no está en el anuncio, es
  `null`.

---

## 4. Política de datos personales

- **No** se almacenan deliberadamente teléfonos, nombres completos, correos ni
  otros datos de contacto de los anunciantes. El saneamiento reconoce patrones
  concretos (teléfonos, enlaces y esquemas de WhatsApp, correos, instrucciones
  de contacto y presentaciones personales como «my name is …», «me llamo …» o
  «mi nombre es …»). **No es un detector exhaustivo**: pueden persistir nombres
  autodeclarados en formas no contempladas (por ejemplo, una firma suelta sin
  verbo de presentación) y otras formas de identificación como apodos, perfiles
  o direcciones exactas. El saneamiento reduce el riesgo, pero no garantiza que
  un archivo quede libre de cualquier dato personal. En particular, las
  presentaciones con iniciales (por ejemplo, «my name is J. …») pueden quedar
  parcialmente saneadas: se elimina la frase de presentación, pero el apellido
  puede permanecer, porque el punto de la inicial no se atraviesa para no
  borrar la primera palabra de la oración siguiente.
- Solo se conserva `vendedor_tipo` (`particular` / `agencia` / `desconocido`)
  cuando sea razonablemente identificable.
- Si aparece información de contacto, se descarta antes de guardar. El
  saneamiento cubre `titulo`, `descripcion`, `direccion_texto` y
  `notas_calidad` del anuncio procesado, los campos de texto conocidos del
  crudo y los subcampos personales de `publisher` (`name`, `phone`, `avatarUrl`,
  `slug`). Si un texto queda sin contenido útil, se guarda como `null`; si no
  contenía contacto, se conserva sin cambios. En las presentaciones personales
  se elimina la frase completa con el nombre y se conserva el resto del texto
  (por ejemplo, el precio o las características que vienen después). Los
  objetos originales no se modifican.
- Los datos crudos con información personal no se publican ni se versionan: la
  mayor parte de `data/` está excluida por `.gitignore` y las excepciones
  versionadas se limitan al historial de tasas, al unificado de anuncios
  saneado y a los tres CSV de referencia salarial (ver §9 y §11.2).

---

## 5. Política inicial de duplicados

Objetivo: **detectar y marcar** posibles duplicados, **sin eliminar**
información automáticamente.

Señales previstas (a validar en cada portal):

1. Mismo `fuente` + mismo `id_fuente`.
2. Misma `url` normalizada (sin parámetros de seguimiento).
3. Coincidencia de `titulo`, `precio`, `moneda`, `municipio` y `area_m2`
   (cuando estén presentes).
4. Similitud alta de texto (`titulo` + `descripcion`) mediante comparación de
   cadenas; más adelante, opcionalmente, con `spaCy`.

Reglas:

- Las coincidencias se marcan con `es_posible_duplicado = True` y se agrupan en
  `duplicado_grupo`.
- **No** se borra ninguna fila automáticamente.
- Duplicados entre fuentes distintas (el mismo inmueble en varios portales) se
  marcan, pero se conservan como registros separados.
- La decisión de consolidar o descartar se hace en una etapa posterior y
  revisable.

---

## 6. Decisiones pendientes

1. **Tasa de referencia definitiva** para los análisis (oficial, informal o
   ambas por separado). La recolección diaria y el historial ya están definidos
   (sección 11); lo que falta es la elección metodológica.
2. Fuente oficial del "salario promedio" para el análisis de asequibilidad.
3. Lista canónica de los municipios de La Habana y reglas de mapeo desde texto
   libre.
4. Criterio de `area_m2`: ¿área total, de construcción o de parcela? Puede
   variar entre portales.
5. Alcance del dataset: ¿solo venta o también alquiler? ¿qué período y qué
   tamaño de muestra?
6. Umbrales de similitud y reglas definitivas de detección de duplicados.
7. Uso efectivo de `spaCy` (si aporta valor sobre el texto de los anuncios).
8. Manejo de anuncios retirados o censurados y de la variación temporal.
9. Revisión de `robots.txt` y términos de uso de cada portal, y estrategia de
   rate limiting. **Nota:** `robots.txt` **no** equivale por sí solo a una
   autorización de scraping; hay que revisar además las condiciones de uso
   aplicables antes de automatizar el acceso.
10. Mecanismo exacto de paginación de GAOS y de "Cargar más" de Mambbu (ver
    sección 8.6).
11. **Criterios de sospecha** de una cotización: qué anomalías concretas
    justifican marcarla como `sospechosa` (sección 11).
12. **Hora exacta y zona horaria** de la actualización diaria de tasas.
13. **Triangulación** entre monedas: no se implementa por ahora.

---

## 7. Verificaciones por portal (antes de implementar el scraping)

Para cada fuente (Revolico, GAOS, Mambbu, CasasOasis) hay que confirmar:

- Qué campos expone realmente y cuáles faltan habitualmente.
- Si la moneda viene etiquetada de forma explícita o hay que inferirla.
- Cómo se presenta la ubicación (municipio estructurado vs. texto libre).
- Si hay `fecha_publicacion` / `fecha_actualizacion` fiables.
- Si el contenido se carga con JavaScript (afectaría a `BeautifulSoup`).
- Estructura de la paginación y del identificador del anuncio.
- Restricciones de acceso (`robots.txt`, términos de uso, bloqueos).
- Formato de las áreas y de las características del inmueble.

Los resultados de estas verificaciones se documentan en la **sección 8** y
ajustarán el esquema común si es necesario.

---

## 8. Resultados de la inspección técnica preliminar

Inspección realizada el **2026-10-08** (fecha del sistema). Método: lectura de
`robots.txt`, sitemaps, HTML servido de páginas de listado y algunas páginas
legales, mediante un número reducido de peticiones puntuales. **Sin crawling
masivo, sin eludir restricciones y sin recoger datos personales.**

Convención: **[V]** = observación directa; **[I]** = inferencia a partir de lo
observado, pendiente de confirmar.

### 8.1 Revolico

- [V] URL de listado:
  `https://www.revolico.com/search?category=inmobiliaria&province=la-habana&subcategory=inmobiliaria-casas`.
  URL de anuncio: `https://www.revolico.com/item/<slug>-<id>`.
- [V] Render SSR (Next.js) con `__NEXT_DATA__`; el HTML ya trae enlaces a
  anuncios y precios, favorable a `requests` + `BeautifulSoup`.
- [V] **Monedas mixtas** en los anuncios (USD, CUP, MLC).
- [V] Las **características del inmueble** (m², habitaciones, baños) aparecen a
  menudo en **texto libre**, no en campos estructurados.
- [V] No se observó fecha de publicación. [I] Los anuncios pueden incluir
  teléfonos en el texto (dato personal → descartar).
- [V] **Paginación:** `?page=2..6` al menos. **Identificador:** id numérico al
  final de la URL del anuncio.
- [V] `robots.txt`: `Allow: /` salvo rutas privadas (`/checkout/`, `/cdn-cgi/`,
  `/account`, `/auth`, `/favorites/`). Sin `Crawl-delay`.
- [V] Términos de uso públicos en
  `https://help.revolico.com/es/articles/7263759-condiciones-de-uso`; no
  constituyen un permiso explícito de scraping.
- [V] **Prueba de acceso (2026-11-04):** petición HTTP GET a la URL de listado
  de La Habana devuelve **HTTP 403**. No se obtuvo el HTML de la página ni se
  pudo inspeccionar el bloque `__NEXT_DATA__`. No se intentó eludir el bloqueo.

### 8.2 GAOS

- [V] URLs de listado: `/venta-viviendas/la-habana`, `/venta-casas/la-habana`,
  `/venta-apartamentos/la-habana`, etc. URL de anuncio:
  `https://gaos.app/properties/<uuid>`.
- [V] Render SSR (Next.js App Router) con datos embebidos (`self.__next_f`);
  backend `supabase`.
- [V] **Identificadores UUID** en las URLs de anuncio.
- [I] Campos en ficha: precio USD, ubicación/municipio, habitaciones, baños,
  área; fecha de publicación poco clara.
- [V] El listado de viviendas mostró 10 ítems. **La paginación sigue sin
  verificarse** (posible `?page=` o carga vía JavaScript).
- [V] `robots.txt`: permisivo salvo rutas privadas (`/login`, `/publish`,
  `/profile`, `/host`); bloquea bots de IA/SEO. Sitemap en
  `https://gaos.app/sitemap.xml`.
- [V] No se encontró página pública de Términos de Servicio; sí Política de
  Privacidad (`/es/privacidad`). Sin permiso explícito de scraping.
- [V] **Prueba de acceso (2026-11-04):** petición HTTP GET a la URL de listado
  de La Habana devuelve **HTTP 429**. Se recibe una página de "Vercel Security
  Checkpoint" sin contenido útil. No se intentó eludir el bloqueo.

### 8.3 Mambbu

- [V] URL de listado: `https://mambbu.com/propiedades` (filtros por operación,
  provincia, municipio y tipo). URL de anuncio:
  `https://mambbu.com/propiedades/<slug>`.
- [V] **Identificadores en las URLs** (slug).
- [V] Render SSR (Astro); el HTML trae enlaces, precios y JSON-LD.
- [V] Campos estructurados: precio USD, habitaciones, baños, área m², año.
- [V] Presenta **fechas relativas** ("Hace N días/semanas").
- [V] Aparecen nombres y WhatsApp de contacto (dato personal → descartar).
- [V] Total declarado: 189 propiedades; botón "Cargar más propiedades (18 de
  189)". `?page=2` devuelve la misma estructura inicial, por lo que el
  **mecanismo de "Cargar más" queda pendiente de investigar** (probable endpoint
  o carga JavaScript).
- [V] `robots.txt`: permisivo salvo rutas privadas (`/admin/`, `/agencia/`,
  `/agente/`, `/login`, `/registro`). Sitemap con fichas individuales y páginas
  por tipo/municipio.
- [V] Términos, Privacidad y Cookies publicados en `/terminos`, `/privacidad`
  y `/cookies`. La sección 8 de los términos de uso prohíbe **expresamente**
  copiar el portal ni extraer sus anuncios de forma automatizada sin
  autorización. No se encontró un mecanismo funcional de contacto para solicitar
  dicha autorización (los documentos indican `[COMPLETAR: email de contacto]`).
- [V] **Prueba de acceso (2026-11-04):** petición HTTP GET a la URL de listado
  de propiedades devuelve **HTTP 200**. El HTML (321 KB) contiene anuncios
  renderizados por Astro con campos como precio, moneda, habitaciones,
  metros cuadrados, municipio y provincia. Los anuncios están en el HTML,
  no en un bloque JSON-LD ni en `__NEXT_DATA__`. No se guardaron anuncios
  ni datos personales.

### 8.4 CasasOasis

- [V] `robots.txt` explícitamente contrario al scraping: bloquea
  `python-requests`, `python-urllib`, `curl`, `wget`, `Scrapy`,
  `Go-http-client`, `node-fetch` y `HTTrack`; menciona defensas **ScrapeShield**
  y **Cloudflare** e incluye una ruta **honeypot**; permite buscadores y
  crawlers de IA declarados.
- **Decisión de la inspección preliminar:** quedó **fuera de la extracción
  automatizada** mientras no existiera autorización expresa. No se accedió a su
  catálogo durante la inspección.
- **Situación actual:** sus datos están disponibles, pero su integración aún no
  está implementada; se realizará después de la reestructuración y corrección de
  errores del proyecto.

### 8.5 URLs consultadas

- **Revolico:** `robots.txt`; listado de La Habana
  (`/search?category=inmobiliaria&province=la-habana&subcategory=inmobiliaria-casas`);
  condiciones de uso en `help.revolico.com`.
  **Prueba de acceso:** HTTP 403 en la URL de listado (2026-11-04).
- **GAOS:** `robots.txt`; portada; `/venta-viviendas/la-habana`;
  `sitemap.xml`; `/es/privacidad`.
  **Prueba de acceso:** HTTP 429 en la URL de listado, `robots.txt` y
  `/es/privacidad` (2026-11-04); página de Vercel Security Checkpoint.
- **Mambbu:** `robots.txt`; `/propiedades`; `/propiedades?page=2`;
  `sitemap.xml`; `/sobre-mambbu`; `/terminos`; `/privacidad`; `/cookies`.
  **Prueba de acceso:** HTTP 200 en `/propiedades` (2026-11-04). Los términos
  de uso prohíben la extracción automatizada sin autorización.
- **CasasOasis:** `robots.txt` (y resultados de búsqueda; **sin** acceder a su
  catálogo).

### 8.6 Resumen de identificadores y paginación

| Fuente | Identificador | Paginación conocida | Estado |
|---|---|---|---|
| Revolico | id numérico en `/item/<slug>-<id>` | `?page=N` [V] | Extractor implementado (`src/sources/revolico.py`); acceso restringido (HTTP 403 el 2026-11-04) y sin autorización legal demostrada |
| GAOS | UUID en `/properties/<uuid>` | No verificada | Extractor implementado (`src/sources/gaos.py`); acceso restringido (HTTP 429 el 2026-11-04) y sin autorización legal demostrada |
| Mambbu | slug en `/propiedades/<slug>` | "Cargar más" [V] | HTTP 200 en acceso (2026-11-04), pero términos prohíben extracción automatizada sin autorización; implementación pendiente de autorización |
| CasasOasis | No inspeccionado | No aplica | Inspección: excluida. Actual: datos disponibles; integración pendiente |

> **Nota sobre la identificación de municipios:** la función de identificación
> de municipios a partir de texto libre (`src/data/normalization.py`) tiene
> cobertura limitada: no todos los anuncios tienen municipio asignado. Las 190
> pruebas de `tests/test_normalization.py` pasan actualmente; cubren
> normalización de moneda, tipo de inmueble, tipo de operación, área, estado de
> conservación, amueblado, fecha y precio, además de la identificación de
> municipios y localidades (incluidos casos ambiguos y referencias geográficas a
> «la playa»). Que pasen no valida todos los casos posibles ni el sistema
> completo: los resultados municipales siguen debiendo interpretarse con cautela
> y no se presentan como definitivos.

---

## 9. Política de privacidad para la extracción

1. **No** recopilar deliberadamente contactos personales: teléfonos, WhatsApp,
   correos, nombres completos ni cualquier otro dato identificativo.
2. Las fichas de los portales **sí contienen** datos personales. El saneamiento
   se aplica antes de guardar cada captura (`sanitizar_crudo()` y
   `sanitizar_anuncio_procesado()` en `src/data/privacidad.py`), no en el
   parser. Limpia los campos de texto conocidos del crudo (`titulo`,
   `descripcion`, `direccion_texto`, `notas_calidad`, `vctitle`, `vcaddress`,
   `sdescription_eng`, `sdescription_ita`, `stittle_eng`, `stittle_ita` y
   `gem_reason`), los cuatro campos de texto del anuncio procesado (`titulo`,
   `descripcion`, `direccion_texto`, `notas_calidad`), las entradas de texto de
   `features` y los subcampos `name`, `phone`, `avatarUrl` y `slug` de
   `publisher`. Solo se conserva `vendedor_tipo` cuando sea razonablemente
   identificable.
3. **Evitar conservar HTML sin filtrar** cuando incluya datos personales. Si se
   guarda el HTML crudo para auditoría, debe redactarse o someterse a una
   política de retención definida. Las capturas actuales se guardan como JSON,
   no como HTML.
4. **No publicar ni versionar** datos personales. La mayor parte de `data/` está
   excluida por `.gitignore`; las únicas excepciones versionadas son el historial
   de tasas, el archivo unificado de anuncios saneado y los tres CSV de
   referencia salarial. La prueba `tests/test_privacidad_datos_versionados.py`
   revisa los JSON rastreados por Git y los no ignorados (incluidos los que aún
   no tienen seguimiento) y falla si encuentra contacto en campos de texto, en
   los subcampos personales de `publisher` o en `features`. No es un hook de
   Git: la protección depende de ejecutar la suite o de conectarla a un
   hook/CI. Tampoco revisa archivos ignorados (por ejemplo, capturas locales en
   `data/raw/`) ni CSV, y solo detecta los patrones que reconoce el módulo; no
   se afirma que todas las capturas históricas o locales estén libres de datos
   personales.
5. No eludir CAPTCHA ni autenticación, y no realizar peticiones masivas;
   aplicar un `Crawl-delay` conservador y un `User-Agent` identificable.

---

## 10. Estado de las fuentes

- **Fuentes objetivo:** Revolico, GAOS y Mambbu. GAOS y Revolico cuentan con
  extractor implementado (`src/sources/gaos.py`, `src/sources/revolico.py`);
  Mambbu sigue pendiente de autorización. En los tres casos deben revisarse las
  condiciones de acceso y uso, y la existencia de un extractor **no** demuestra
  autorización legal.
- **CasasOasis:** datos disponibles; integración aún no implementada, prevista
  después de la reestructuración y corrección de errores del proyecto.
- **Resultado de pruebas de acceso (2026-11-04):**
  - **Revolico:** HTTP 403. No se obtuvo HTML ni se pudo inspeccionar
    `__NEXT_DATA__`.
  - **GAOS:** HTTP 429. Página de Vercel Security Checkpoint, sin contenido útil.
  - **Mambbu:** HTTP 200. Los anuncios aparecen en HTML generado por Astro, pero
    la sección 8 de sus términos de uso prohíbe expresamente la extracción
    automatizada de anuncios sin autorización. El `robots.txt` permite el acceso
    general, pero no sustituye la autorización exigida en los términos. No se
    encontró un mecanismo funcional para solicitar autorización.
- `robots.txt` **no equivale por sí solo a una autorización de scraping**:
  debe revisarse además las condiciones de uso aplicables de cada portal.
- No se deben evadir bloqueos, sistemas anti-bots ni restricciones de acceso.
- GAOS y Revolico están implementados, pero su acceso automatizado no está
  garantizado: las pruebas de acceso registradas muestran restricciones (HTTP 403
  y 429) y las condiciones de uso deben seguir revisándose. Mambbu continúa
  pendiente de autorización. No se presentan estas fuentes como plenamente
  autorizadas.

---

## 11. Sistema de tasas de cambio

Diseño detallado y justificación en **`docs/sistema_tasas_cambio.md`**. Aquí se
recogen las decisiones vinculantes y las que siguen pendientes.

Principio de diseño: **la solución más simple que conserve bien los datos y que
podamos explicar**. No se añade complejidad técnica sin una utilidad clara para
este proyecto.

### 11.1 Fuentes y categorías

| Fuente | `fuente` | Qué es | Qué aporta |
|---|---|---|---|
| ElToque | `eltoque` | Medio de prensa. **No es una institución oficial.** | Información sobre el mercado informal (en la implementación actual, el extractor la registra como `mercado_informal`). |
| Banco Central de Cuba (BCC) | `bcc` | Banco central. **Institución oficial.** | Tasas oficiales. |

Página de referencia del BCC: `https://www.bc.gob.cu/tasas-de-cambio`.

- Las cotizaciones de ElToque son **informativas**: no son tasas oficiales y no
  representan necesariamente todas las operaciones reales del mercado.
- **No** se usa la denominación «Banco Nacional de Cuba (BNC)»: la institución
  que se consulta es el Banco Central de Cuba y su identificador es `bcc`.
- `fuente` y `categoria` son dimensiones distintas. `fuente` indica **quién
  publica**; `categoria` indica el **tipo de mercado** (`oficial` o
  `mercado_informal`) y el criterio previsto es asignarla **por cotización**,
  no por la página. En la implementación actual, el extractor de ElToque fija
  `mercado_informal` y el del BCC fija `oficial`; no hay un caso de «categoría
  indeterminable». Si una cotización no declara una `fuente` o `categoria`
  admitidas, o combina ambas de forma no admitida, `registrar_cotizaciones()`
  rechaza el lote completo con `ValueError` y no crea una incidencia por ese
  motivo.
- No se asume que cada fuente publique una única tasa: se registran por separado
  `moneda_origen`, `moneda_destino`, `tipo_tasa` (modalidad) y `segmento` cuando
  la fuente los distinga. Esto es especialmente relevante en el BCC, que puede
  publicar varias tasas oficiales para distintas monedas u operaciones.
- Las publicaciones concretas del BCC, sus formatos y sus condiciones de uso
  **deben verificarse antes de implementar**; la página de referencia no
  garantiza por sí sola permiso de automatización.
- Las cotizaciones de ElToque y del BCC **no se mezclan ni se promedian**. Se
  conservan por separado para poder compararlas después.

### 11.2 Almacenamiento y estructura

- Archivo único: `data/raw/exchange_rates/historial_tasas.json`.
- Historial **append-only**: nunca se sobrescriben ni eliminan registros.
- El historial **sí se versiona**: `.gitignore` lo excluye con una excepción
  explícita. No toda la carpeta `data/` se versiona; las excepciones son este
  historial, el unificado de anuncios saneado y los tres CSV de referencia
  salarial. El resto de los datos locales sigue excluido.
- La carpeta `data/raw/exchange_rates/` se crea durante la captura si no existe.

Estructura de nivel superior:

```json
{
  "version_esquema": "1.0",
  "ultima_actualizacion": "2026-11-01T09:05:00Z",
  "cotizaciones": [],
  "actualizaciones": [],
  "incidencias": []
}
```

No se guardan totales ni resúmenes por fuente: se calculan a partir de los
registros y, si se guardaran aparte, podrían quedar desincronizados.

> La fecha del ejemplo es ficticia y solo ilustra el formato.

### 11.3 Registros

- **Cotizaciones:** cada observación concreta de una tasa. Incluye `id` (UUID),
  `id_actualizacion` (UUID), `fuente`, `categoria`, `tipo_tasa`, `segmento`,
  `moneda_origen`, `moneda_destino`, `valor`, `valor_texto_original`,
  `fecha_publicacion`, `fecha_vigencia`, `fecha_captura`, `url_fuente`,
  `estado`, `motivo_sospecha` y `reemplaza_a` (opcional).
- **Actualizaciones:** una ejecución del proceso. Incluye `id` (UUID),
  `fecha_inicio`, `fecha_fin`, `fuentes_consultadas` y `resultado_por_fuente`
  (`ok`, `parcial`, `error`, `sin_novedad`). Permite distinguir "hoy no había
  tasa nueva" de "hoy falló la consulta".
- **Incidencias:** fallos y anomalías. Incluye `id` (UUID), `id_actualizacion`,
  `fuente`, `categoria`, `fecha_captura`, `tipo`, `descripcion`, `estado`,
  `url_fuente` y `detalle_tecnico`. **Nunca es una tasa.**

**Registros históricos sin procedencia.** De las 41 cotizaciones actuales,
26 no tienen `fuente` ni `categoria`: son capturas antiguas realizadas antes de
que el extractor guardara esos metadatos. Esos valores se conservan como `null`
y no se completan por inferencia: no hay prueba directa de procedencia a nivel
de cotización. `listar_cotizaciones()` no los asigna a ninguna procedencia; sin
filtros devuelve el historial completo y, al filtrar por `fuente` o `categoria`,
exige igualdad exacta, así que estos registros solo aparecen en consultas
generales. Se mantienen en el historial y no se eliminan por carecer de esos
metadatos.

`estado` de una cotización es `valida` o `sospechosa` por convención (el
registro no comprueba ese valor). No existe una validación de datos que
descarte cotizaciones creando una incidencia: los extractores **omiten en
silencio** las de moneda no rastreada o `valor` nulo, no numérico o ≤ 0, y
`registrar_cotizaciones()` rechaza el lote completo con `ValueError` si la
procedencia no es válida, sin crear una incidencia. Las incidencias las
registra `capturar.py` ante fallos de la fuente —autenticación de elTOQUE,
errores de conexión, errores HTTP de elTOQUE o del BCC y errores de estructura
de la respuesta del BCC—, no por cada cotización descartada. elTOQUE no tiene
un control equivalente: si su respuesta no es un objeto JSON, el extractor
falla con un `AttributeError` no capturado y no se registra incidencia.

**Todo identificador es un UUID.** Se descartaron campos técnicos como
`hash_contenido`, `metodo_extraccion`, `unidad_original`,
`fecha_publicacion_texto` y `notas` porque no aportaban una utilidad clara a
este proyecto (ver la justificación en `docs/sistema_tasas_cambio.md` §5.4).

### 11.4 Reglas de actualización diaria

1. Frecuencia **diaria**.
2. No se sobrescribe: cada ejecución añade registros.
3. **Conservar las capturas:** cada cotización nueva registra su
   `fecha_captura`. Si la fuente repite una cotización sin cambios y no hay
   información que permita identificarla como una observación nueva, se
   registra la consulta en `actualizaciones`, sin duplicar la cotización.
4. Varias cotizaciones de la misma moneda (distinta modalidad, segmento o fecha)
   se conservan por separado.
5. Si no hay tasa nueva, **no** se copia la anterior como cotización nueva; se
   registra `sin_novedad`.
6. Un fallo **no** borra ni sobrescribe la última tasa válida.
7. Los fallos se registran como **incidencias**, separadas de las cotizaciones.
8. Una actualización parcial no invalida los registros correctos de otras
   fuentes: se guardan las cotizaciones válidas y se registran incidencias para
   las fallidas.
9. Antes de escribir, se conserva una copia del archivo anterior.

### 11.5 Validación y sospecha

Se **rechaza** un lote en `registrar_cotizaciones()` —lanza `ValueError` y no
escribe nada— si alguna cotización no es un diccionario, no declara `fuente` o
`categoria` válidas, o combina una fuente y una categoría que no corresponden.
Es la única validación de registro: no se comprueban `valor`, las monedas,
`fecha_captura`, `tipo_tasa` ni `url_fuente`.

Las cotizaciones con moneda no rastreada o con `valor` nulo, no numérico o ≤ 0
se **omiten** antes, en la extracción, sin incidencia (ver §11.1 de
`docs/sistema_tasas_cambio.md`).

Un duplicado exacto **no** es un error de validación: no se añade y se
contabiliza como `duplicados_omitidos` (si había fechas) o `sin_novedad` (si no
las había), sin incidencia ni excepción (ver la sección 12 de
`docs/sistema_tasas_cambio.md`).

Se **conserva como sospechosa** una cotización con una anomalía que no impide
registrar el dato pero desaconseja usarlo por defecto. La convención es que
`estado = "sospechosa"` y que `motivo_sospecha` explique la razón;
`registrar_cotizaciones()` no comprueba esa combinación ni rechaza una
cotización sospechosa sin motivo. Se puede recuperar en el historial.

**No** se marca como sospechosa una cotización **solo** porque su valor sea muy
distinto al anterior: una variación grande puede ser real. No se inventan
umbrales automáticos.

Reglas generales: no se imputan valores; la ausencia de cotización **no** es
`0`; no se considera duplicada una cotización solo por coincidir en el valor; no
se convierte una moneda sin tasa documentada; no se confunden
`fecha_publicacion`, `fecha_vigencia` y `fecha_captura`.

**Deduplicación.** La clave de una cotización es `(fuente, categoria,
moneda_origen, moneda_destino, tipo_tasa, segmento)`; un campo ausente cuenta
como `null` y forma parte de la clave, no es un comodín. Para cada cotización
nueva, `registrar_cotizaciones()` busca la cotización existente más reciente con
esa misma clave comparando `fecha_captura` como texto, no por la posición en la
lista. Una `fecha_captura` ausente se trata como cadena vacía (nunca supera a
una fecha presente); si hay empate, se conserva la última que aparece en el
historial.

Con la cotización encontrada:

- Si coincide en `fuente`, `categoria`, `tipo_tasa`, `segmento`,
  `moneda_origen`, `moneda_destino`, `fecha_publicacion`, `fecha_vigencia` y
  `valor_texto_original`, es un duplicado exacto y no se añade. Se registra como
  `sin_novedad` si ambas carecen de `fecha_publicacion` y `fecha_vigencia`; en
  caso contrario, como `duplicados_omitidos`. No se comparan `valor`,
  `fecha_captura` ni `url_fuente`.
- Si no es idéntica y ambas carecen de `fecha_publicacion` y `fecha_vigencia`,
  se compara `valor_texto_original` (no el campo numérico `valor`): si coincide,
  no se añade y se registra como `sin_novedad`; si cambia, se guarda como nueva
  cotización.
- Si hay fechas y no es idéntica, se guarda como nueva cotización.

La comparación de fechas es lexicográfica sobre el texto de `fecha_captura`, así
que asume un formato y una zona horaria uniformes en todo el historial. Sin
fecha no se puede distinguir "no hay tasa nueva" de "la fuente repitió el mismo
valor": es una limitación asumida. Los registros históricos con `fuente` o
`categoria` en `null` conservan su clave y no se comparan con las cotizaciones
nuevas, que siempre declaran procedencia.

### 11.6 Consultas

La clave de consulta es `(fuente, categoria, moneda_origen, moneda_destino,
tipo_tasa, segmento)`; `segmento = null` es un valor de la clave, no un comodín.
Como `fuente` y `categoria` forman parte de la clave, una consulta **nunca
mezcla** ElToque con BCC ni tasas oficiales con informales. Tampoco se calculan
promedios ni agregados entre fuentes; la comparación, si se hace, es explícita y
posterior.

| Consulta | Qué devuelve | Estado actual |
|---|---|---|
| **Última capturada** (por defecto) | Cotización válida más reciente por `fecha_captura`. Si no hay ninguna, `null`. | No hay función en `src/`. El notebook selecciona la tasa con `obtener_tasa()`, que usa `fecha_publicacion` y no filtra por `estado`. |
| **Última vigente** | La de la cotización válida más reciente, solo si declara `fecha_vigencia` aplicable. Si no la declara, "no determinable"; no se recurre a una tasa antigua. | No implementada; ni `src/` ni el notebook leen `fecha_vigencia`. |
| **Historial** | Todas las cotizaciones de la clave, incluidas las sospechosas con su motivo. | `listar_cotizaciones()` solo filtra por `fuente` y `categoria`, devuelve el orden guardado y no filtra por el resto de la clave ni por `estado`. |

**Consultas implementadas y registros sin procedencia.** `listar_cotizaciones()`
devuelve el historial completo, en el orden guardado, cuando no se pasan
filtros; eso incluye los registros históricos que tienen `fuente` y `categoria`
en `null`. Los filtros por `fuente` y por `categoria` son de igualdad exacta y
se combinan con AND si se pasan ambos. Un campo ausente se trata igual que
`null` (`dict.get()`), y como no se puede filtrar por `null`, esos registros
nunca coinciden con un filtro por fuente o categoría: no se les atribuye
ninguna procedencia. En el historial actual, 26 cotizaciones tienen `fuente` y
`categoria` en `null`.

`registrar_cotizaciones()` valida la procedencia de **todo** el lote antes de
escribir y solo admite `eltoque`/`mercado_informal` y `bcc`/`oficial`. Si una
cotización no declara `fuente` o `categoria` válidas, o combina una fuente con
una categoría que no le corresponde, lanza `ValueError` y no escribe nada. Los
registros históricos sin procedencia se conservan tal cual y no se completan ni
se reatribuyen.

Si una fuente no proporciona `fecha_vigencia`, **no** se supone que coincida con
`fecha_captura`: se guarda `null`. No existe todavía una función de consulta de
vigencia; solo se aplicará a fuentes que declaren esa fecha de forma
sistemática, lo que debe verificarse antes de implementarla.

`obtener_tasa()` no aplica la clave completa: `tipo_tasa` y `segmento` en `None`
actúan como comodín y no filtra por `categoria`.

### 11.7 Vinculación con los anuncios

`precio` y `moneda` originales nunca se pierden. Las conversiones oficiales e
informales no se mezclan. Cada conversión se rastrea mediante `tasa_id` (ver
§1.4.1); el resto de datos de la tasa se recuperan del historial.

### 11.8 Lo que queda pendiente

- **Tasa de referencia definitiva** para los análisis. No se decide aquí.
- **Triangulación** entre monedas. No se implementa por ahora.
- **Relación precios-salarios:** se abordará en la fase de análisis, siempre que
  existan datos y referencias cambiarias suficientemente justificables.
- **Criterios concretos de sospecha**, hora exacta de la actualización y
  crecimiento del archivo (ver sección 6 y `docs/sistema_tasas_cambio.md` §17).

---

## 12. Registro de cambios

- Versión inicial: definición del esquema común y políticas de moneda, datos
  personales, valores ausentes y duplicados.
- 2026-10-08: se añade la sección 8 (resultados de la inspección técnica
  preliminar), la sección 9 (política de privacidad para la extracción) y la
  sección 10 (estado de las fuentes). Se documenta que CasasOasis queda fuera
  de la extracción automatizada y que Revolico, GAOS y Mambbu continúan como
  candidatas sujetas a verificación.
- 2026-10-31: se añade la sección 11 (sistema de tasas de cambio) y el documento
  `docs/sistema_tasas_cambio.md`. Se fijan las fuentes, categorías,
  almacenamiento append-only, reglas de actualización diaria, validación,
  incidencias separadas y vinculación con los anuncios. Se propone la
  trazabilidad de conversión en §1.4.1.
- 2026-11-01: se simplifica el diseño del sistema de tasas para ajustarlo al
  nivel y los objetivos del proyecto. Se eliminan campos técnicos sin utilidad
  clara (`hash_contenido`, `metodo_extraccion`, `unidad_original`,
  `fecha_publicacion_texto`, `notas`), se aplana la estructura del JSON
  (`version_esquema`, `ultima_actualizacion`, `cotizaciones`, `actualizaciones`,
  `incidencias`) y se adoptan UUID. Se añade `motivo_sospecha`, se separa con
  claridad la última tasa capturada de la última vigente y se reduce la
  trazabilidad inmobiliaria a un único campo (`tasa_id`). Se documenta el
  razonamiento para poder defenderlo. Se precisa además la regla de duplicados
  cuando la fuente no declara fechas y se evita que la consulta de "última
  vigente" devuelva una tasa antigua.
- 2026-11-01 (aclaración de fuentes): se sustituye «Banco Nacional de Cuba
  (BNC)» por **Banco Central de Cuba (BCC)**, con identificador `bcc` y página de
  referencia `https://www.bc.gob.cu/tasas-de-cambio`. Se establece que
  `fuente` (quién publica) y `categoria` (tipo de mercado) son dimensiones
  distintas: la categoría se asigna por cotización y no por la página, de modo
  que un dato oficial publicado por ElToque se registra como `oficial`. Se
  documenta que los datos de ElToque son informativos y no representan
  necesariamente todas las operaciones del mercado, y se prohíbe mezclar o
  promediar cotizaciones de ambas fuentes.
- 2026-11-08: se añaden la sección 13 (almacenamiento y unificación de capturas
  de anuncios) y la sección 14 (entonces 15; datos salariales de referencia).
- 2026-11-19: se actualiza el estado de CasasOasis: sus datos están disponibles,
  pero la integración sigue pendiente.
- 2026-11-24: auditoría documental. Se ajustan las secciones 1.4 (validación del
  precio al guardar), 4 y 9 (privacidad), 11.5 (validación y deduplicación),
  11.6 (consultas) y 13.1 (escritura atómica de capturas) para que describan el
  comportamiento implementado. Se elimina el «Registro de cambios» vacío que
  duplicaba el de la sección 12.

---

## 13. Almacenamiento y unificación de capturas de anuncios

### 13.1 Almacenamiento por fuente

Cada fuente de anuncios (GAOS, Revolico) tiene sus propios archivos de captura
cruda y procesada, organizados en carpetas independientes:

- `data/raw/anuncios/<fuente>/crudo/` — datos crudos tal como llegan del portal.
- `data/processed/anuncios/<fuente>/` — anuncios ya mapeados al esquema común.

Cada ejecución guarda un par de archivos (crudo y procesado) con el mismo
`id_captura` y `fecha_captura`, para que crudos y procesados puedan
relacionarse por esos metadatos. El nombre combina un sufijo del `id_captura` y
una marca de tiempo; como el identificador es aleatorio, es muy improbable que
dos ejecuciones generen el mismo nombre, pero **no se garantiza** que no se
sobrescriba una captura anterior: no hay una comprobación previa de existencia
y `os.replace()` sustituye el archivo de destino si ya existe. La protección
depende, por tanto, de la unicidad del nombre, no de una verificación explícita.

**Escritura por archivo.** `_escribir_json_atomico()` crea el directorio si no
existe y escribe en un temporal del mismo directorio que el destino
(`<nombre>.json.tmp`), hace `flush` y `fsync`, y publica con `os.replace()`.
Si falla la escritura o la sustitución, intenta eliminar el temporal y propaga
la excepción.

**Publicación del par.** Los dos archivos se publican de forma independiente y
en orden (primero el crudo, después el procesado). Si falla el segundo, se
intenta eliminar el crudo ya publicado y el error se propaga. Es un *rollback*
de mejor esfuerzo, no una transacción atómica: una interrupción abrupta del
proceso entre ambas publicaciones puede dejar solo el crudo. Una captura
incompleta se detecta al leerla, porque `leer_captura()` devuelve `None` cuando
falta alguno de los dos archivos o sus `id_captura` internos no coinciden.

**Temporales.** Antes de escribir, se eliminan los `*.tmp` que hayan quedado en
las carpetas de crudos y procesados por ejecuciones fallidas anteriores; los
errores de borrado se ignoran. Los temporales de la escritura en curso se
eliminan si esta falla.

### 13.2 Unificación de capturas

El módulo `src/data/unificacion.py` combina los archivos **procesados** de GAOS y
Revolico en un único archivo JSON, sin modificar los archivos originales.

**Características:**

- Recibe la ruta del archivo procesado de cada fuente; no lee los crudos.
- Añade el campo `fuente` a cada anuncio para identificar su procedencia
  (`gaos` o `revolico`).
- Para Revolico, reclasifica `tipo_inmueble` a partir del `titulo` con
  `_clasificar_tipo_inmueble` (`casa`, `apartamento`, `indeterminado`,
  `no_vivienda`). No vuelve a ejecutar `mapear_anuncio_revolico`: el mapeo al
  esquema común ya se hizo al guardar la captura procesada.
- Para GAOS, conserva los campos procesados y solo añade `fuente: "gaos"`.
- Genera un `id_captura` único para la captura unificada y un envoltorio con
  `fuente: "multifuente"` y `url_fuente: null`.
- Registra en `capturas_origen` los metadatos de cada captura de origen
  (fuente, id_captura, fecha_captura, archivo y cantidad de anuncios).
- En la entrada de Revolico añade `url_fuente_correcta` con la URL de búsqueda
  del portal y una `nota` que explica que la captura histórica tenía metadatos
  de GAOS y que en el archivo unificado se corrige a Revolico.

**Resultado:** un archivo JSON con todos los anuncios unificados, donde cada
registro conserva su `fuente` (`gaos` o `revolico`) y su `id_fuente` original,
permitiendo distinguir claramente la procedencia de cada anuncio.

### 13.3 Metadatos de fuente

Cada archivo de captura incluye en su envoltorio los campos `fuente` y
`url_fuente` que identifican el portal de origen. Cada anuncio individual
también incluye el campo `fuente`. Para archivos históricos de Revolico
capturados antes de esta corrección, los metadatos pueden contener
`fuente: "gaos"` y `url_fuente: "https://gaos.app/propiedades"` debido a un
error previo en la extracción; dichos archivos no se modifican y se conservan
como están.

---

## 14. Datos salariales de referencia

### 14.1 Procedencia y naturaleza de los datos

Los datos salariales utilizados en este proyecto provienen del documento
`salarios_cuba_gaceta_2026.pdf`, que es una **estructuración secundaria**
realizada a partir de la Gaceta Oficial Ordinaria No. 60 (Resoluciones
12/2026 a 26/2026). No es la publicación original de las Resoluciones, por lo
que los valores aquí registrados deben considerarse **referencia secundaria**
y requieren contraste con las Resoluciones originales para cualquier uso
jurídico o definitivo.

Todos los salarios están expresados en Pesos Cubanos (CUP).

### 14.2 Conjuntos de datos

Se mantienen tres archivos independientes en `data/reference/salarios/`:

#### `escala_general.csv`

Contiene los 32 grupos de complejidad de la Escala Salarial Única del Sector
Presupuestado (Resolución 15/2026), con los valores del salario base mensual
para regímenes de 44 horas y 40 horas semanales. Cada grupo aparece una sola
vez, ordenado del Grupo I al Grupo XXXII.

#### `cargos_sectoriales.csv`

Contiene 51 cargos de distintas fuentes sectoriales (Salud Pública, Educación
General, Educación Superior, Ciencia y Tecnología, Poder Popular, Prensa y
Medios, Cultura, Deporte, Servicio Exterior), con su identificador de fuente,
resolución aplicable, grupo de escala, salario base mensual en CUP y jornada
laboral.

**Clasificación de los cargos:**

- **42 cargos** se clasifican con la **escala general** (grupos I a XXXII de
  la Resolución 15/2026).
- **5 cargos** pertenecen al sector **Deporte** y utilizan una clasificación
  propia (Categorías 1 a 5 de la Resolución 12/26), no equivalente a los
  grupos de escala general.
- **4 cargos** pertenecen a **Servicio Exterior** y utilizan una clasificación
  propia (Grupos I a IX de la Resolución 26/26), no equivalente a los grupos
  de escala general.

**Nota:** Los grupos del Servicio Exterior (Grupo I, II, VII, IX) no son
equivalentes a los grupos del escalafón general del sector presupuestado, a
pesar de compartir la notación numérica.

#### `pagos_adicionales.csv`

Contiene 8 tipos de bonificaciones y coeficientes de ajuste (bonos por
antigüedad, grado científico, nocturnidad, condiciones especiales), con sus
respectivos importes, unidades y condiciones de aplicación.

**Estos pagos NO se suman automáticamente al salario base de ningún cargo.**
Se almacenan por separado para uso futuro, y su aplicación a cargos
específicos requiere información adicional no disponible en el documento
fuente.

### 14.3 Limitaciones

- Los datos son precios salariales nominales en CUP, no salarios netos ni
  ingresos efectivos de los trabajadores.
- No se incluyen datos de gastos de vida, remesas, pluriempleo ni ingresos
  informales.
- No existe tasa de cambio documentada en este documento para convertir
  salarios CUP a otras monedas.
- Las bonificaciones no están vinculadas a cargos específicos del dataset
  sectorial; su aplicación a cargos específicos requiere información
  adicional no disponible en el documento fuente.
- La bonificación de antigüedad por 30 años o más incluye un incremento
  adicional de 400 CUP por cada dos años adicionales, según se indica en
  el documento fuente; sin embargo, no se ha podido determinar si existe
  un límite máximo para este incremento.

