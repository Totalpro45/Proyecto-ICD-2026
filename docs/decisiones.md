# Esquema de datos común y decisiones iniciales

**Proyecto:** ¿Es asequible el precio de la vivienda para el cubano promedio?
**Caso de estudio:** La Habana
**Fuentes iniciales:** Revolico, GAOS, Mambbu, CasasOasis
**Fuentes candidatas a extracción:** Revolico, GAOS y Mambbu (sujetas a verificar
condiciones de acceso y uso). CasasOasis queda **fuera** de la extracción
automatizada mientras no haya autorización expresa.
**Estado:** borrador; incluye resultados de la inspección técnica preliminar
(sección 8) y el diseño del sistema de tasas de cambio (sección 11). No describe
todavía ninguna implementación de scraping ni de consulta de tasas.

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

#### 1.4.1 Trazabilidad de la conversión

Para que `precio_usd` sea reproducible hasta la cotización concreta, se propone
añadir **un solo campo**, sin eliminar los existentes:

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `tasa_id` | UUID | no | `id` de la cotización aplicada (ver sección 11 y `docs/sistema_tasas_cambio.md`). `null` si no hubo conversión. |

**Justificación:** `tasa_conversion_usd`, `tasa_fecha` y `tasa_fuente` permiten
leer una conversión, pero no identifican de forma única la cotización usada. Con
`tasa_id` se recuperan del historial la categoría, la modalidad, el segmento y
las fechas exactas, sin duplicar esos datos en cada anuncio. El campo se incorpora al esquema para garantizar la trazabilidad de las conversiones.

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

- **No** se almacenan teléfonos, nombres completos, correos, ni cualquier otro
  dato personal de los anunciantes.
- Solo se conserva `vendedor_tipo` (`particular` / `agencia` / `desconocido`)
  cuando sea razonablemente identificable.
- Si durante el parseo aparece información personal, debe descartarse antes de
  guardar. Los datos crudos con información personal no se publican ni se
  versionan (ya excluidos por `.gitignore` en `data/`).

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
- [V] Términos, Privacidad y Cookies son enlaces `#` no publicados. Sin permiso
  explícito de scraping.

### 8.4 CasasOasis

- [V] `robots.txt` explícitamente contrario al scraping: bloquea
  `python-requests`, `python-urllib`, `curl`, `wget`, `Scrapy`,
  `Go-http-client`, `node-fetch` y `HTTrack`; menciona defensas **ScrapeShield**
  y **Cloudflare** e incluye una ruta **honeypot**; permite buscadores y
  crawlers de IA declarados.
- **Decisión:** queda **fuera de la extracción automatizada** mientras no
  exista autorización expresa. No se accedió a su catálogo durante la
  inspección.

### 8.5 URLs consultadas

- **Revolico:** `robots.txt`; listado de La Habana
  (`/search?category=inmobiliaria&province=la-habana&subcategory=inmobiliaria-casas`);
  condiciones de uso en `help.revolico.com`.
- **GAOS:** `robots.txt`; portada; `/venta-viviendas/la-habana`;
  `sitemap.xml`; `/es/privacidad`.
- **Mambbu:** `robots.txt`; `/propiedades`; `/propiedades?page=2`;
  `sitemap.xml`; `/sobre-mambbu`.
- **CasasOasis:** `robots.txt` (y resultados de búsqueda; **sin** acceder a su
  catálogo).

### 8.6 Resumen de identificadores y paginación

| Fuente | Identificador | Paginación conocida | Estado |
|---|---|---|---|
| Revolico | id numérico en `/item/<slug>-<id>` | `?page=N` [V] | Falta confirmar total y fin de lista |
| GAOS | UUID en `/properties/<uuid>` | No verificada | **Pendiente** |
| Mambbu | slug en `/propiedades/<slug>` | "Cargar más" [V] | **Pendiente** (endpoint/JS) |
| CasasOasis | No inspeccionado | No aplica | Excluida |

---

## 9. Política de privacidad para la extracción

1. **No** recopilar deliberadamente contactos personales: teléfonos, WhatsApp,
   correos, nombres completos ni cualquier otro dato identificativo.
2. Las fichas de los portales **sí contienen** datos personales; el parser debe
   descartarlos. Solo se conserva `vendedor_tipo` cuando sea razonablemente
   identificable.
3. **Evitar conservar HTML sin filtrar** cuando incluya datos personales. Si se
   guarda el HTML crudo para auditoría, debe redactarse o someterse a una
   política de retención definida.
4. **No publicar ni versionar** datos personales. El directorio `data/` ya está
   excluido por `.gitignore`.
5. No eludir CAPTCHA ni autenticación, y no realizar peticiones masivas;
   aplicar un `Crawl-delay` conservador y un `User-Agent` identificable.

---

## 10. Estado de las fuentes

- **Candidatas a extracción:** Revolico, GAOS y Mambbu, **sujetas a verificar
  las condiciones de acceso y uso** antes de automatizar.
- **Excluida:** CasasOasis, mientras no haya autorización expresa.
- `robots.txt` **no equivale por sí solo a una autorización de scraping**:
  debe revisarse además las condiciones de uso aplicables de cada portal.

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
| ElToque | `eltoque` | Medio de prensa. **No es una institución oficial.** | Información sobre el mercado informal (la categoría se asigna por cotización). |
| Banco Central de Cuba (BCC) | `bcc` | Banco central. **Institución oficial.** | Tasas oficiales. |

Página de referencia del BCC: `https://www.bc.gob.cu/tasas-de-cambio`.

- Las cotizaciones de ElToque son **informativas**: no son tasas oficiales y no
  representan necesariamente todas las operaciones reales del mercado.
- **No** se usa la denominación «Banco Nacional de Cuba (BNC)»: la institución
  que se consulta es el Banco Central de Cuba y su identificador es `bcc`.
- `fuente` y `categoria` son dimensiones distintas. `fuente` indica **quién
  publica**; `categoria` indica el **tipo de mercado** (`oficial` o
  `mercado_informal`) y se asigna **por cotización**, no por la página. Si
  ElToque publica una tasa que corresponde al mercado oficial, se registra como
  `oficial`. Si no se puede determinar la categoría, la cotización no se
  registra como válida y se documenta una incidencia.
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
- El archivo queda bajo `data/raw/`, ya excluido por `.gitignore`; los datos no
  se versionan, el esquema sí.
- La carpeta no se crea en esta fase.

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

`estado` de una cotización admite `valida` o `sospechosa`. Las cotizaciones que
no superan la validación **no** entran en `cotizaciones`: se registran como
incidencia de tipo `validacion`.

**Todo identificador es un UUID.** Se descartaron campos técnicos como
`hash_contenido`, `metodo_extraccion`, `unidad_original`,
`fecha_publicacion_texto` y `notas` porque no aportaban una utilidad clara a
este proyecto (ver la justificación en `docs/sistema_tasas_cambio.md` §5.3).

### 11.4 Reglas de actualización diaria

1. Frecuencia **diaria**.
2. No se sobrescribe: cada ejecución añade registros.
3. 3. **Conservar las capturas:** cada cotización nueva registra su
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

Se **rechaza** una cotización si: `valor` es nulo, no numérico o ≤ 0; faltan o
son ambiguas las monedas; ambas monedas son iguales; falta o es inválida
`fecha_captura`; faltan `fuente`, `categoria`, `tipo_tasa` o `url_fuente`; no se
puede determinar la categoría (`oficial` o `mercado_informal`) a partir de lo
que publica la fuente; no se puede asociar a una actualización; es un duplicado
exacto; o está marcada como sospechosa sin `motivo_sospecha`.

Se **conserva como sospechosa** una cotización con una anomalía que no impide
registrar el dato pero desaconseja usarlo por defecto. En ese caso se exige
`motivo_sospecha`, se excluye de las consultas normales y se puede recuperar en
el historial.

**No** se marca como sospechosa una cotización **solo** porque su valor sea muy
distinto al anterior: una variación grande puede ser real. No se inventan
umbrales automáticos.

Reglas generales: no se imputan valores; la ausencia de cotización **no** es
`0`; no se considera duplicada una cotización solo por coincidir en el valor; no
se convierte una moneda sin tasa documentada; no se confunden
`fecha_publicacion`, `fecha_vigencia` y `fecha_captura`.

**Duplicados sin fecha de publicación:** si la fuente no declara
`fecha_publicacion` ni `fecha_vigencia`, se compara con la última cotización
guardada de la misma clave. Si el valor es idéntico, no se añade una cotización
nueva y la ejecución se registra como `sin_novedad`; si cambia, se guarda con su
`fecha_captura`. Es una limitación asumida: sin fecha no se puede distinguir
"no hay tasa nueva" de "la fuente repitió el mismo valor".

### 11.6 Consultas

La clave de consulta es `(fuente, categoria, moneda_origen, moneda_destino,
tipo_tasa, segmento)`; `segmento = null` es un valor de la clave, no un comodín.
Como `fuente` y `categoria` forman parte de la clave, una consulta **nunca
mezcla** ElToque con BCC ni tasas oficiales con informales. Tampoco se calculan
promedios ni agregados entre fuentes; la comparación, si se hace, es explícita y
posterior.

| Consulta | Qué devuelve |
|---|---|
| **Última capturada** (por defecto) | Cotización válida más reciente por `fecha_captura`. Si no hay ninguna, `null`. |
| **Última vigente** | La de la cotización válida más reciente, solo si declara `fecha_vigencia` aplicable. Si no la declara, "no determinable"; no se recurre a una tasa antigua. |
| **Historial** | Todas las cotizaciones de la clave, incluidas las sospechosas con su motivo. |

Si una fuente no proporciona `fecha_vigencia`, **no** se supone que coincida con
`fecha_captura`: se guarda `null`. La consulta de vigencia solo se aplicará a
fuentes que declaren esa fecha de forma sistemática, lo que debe verificarse
antes de implementar.

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
