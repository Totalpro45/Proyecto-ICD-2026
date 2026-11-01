# Sistema de tasas de cambio: diseño y reglas

**Proyecto:** ¿Es asequible el precio de la vivienda para el cubano promedio?
**Caso de estudio:** La Habana
**Estado:** documento de diseño; **no implementado**. No contiene código,
scrapers, peticiones HTTP ni tasas reales.
**Documento relacionado:** `docs/decisiones.md` (decisiones generales y esquema
inmobiliario).

---

## 1. Propósito y principio de diseño

Queremos **registrar, conservar y consultar** las tasas de cambio de dos fuentes
para poder convertir después, de forma **reproducible**, algunos precios de
anuncios inmobiliarios a USD.

El principio que guía este diseño es sencillo:

> **La solución más simple que conserve bien los datos y que podamos explicar.**

No estamos construyendo un sistema financiero profesional ni una base de datos
compleja. Es un proyecto universitario de primer año: necesitamos algo fiable,
auditable y comprensible.

**Qué sí queremos:**

- guardar las tasas una vez al día;
- conservar todo el historial sin sobrescribir;
- consultar la última tasa disponible;
- distinguir tasas oficiales de tasas del mercado informal;
- conservar ambas fuentes por separado, sin mezclarlas ni promediarlas;
- registrar los fallos sin confundirlos con tasas;
- poder rastrear qué tasa se usó en cada conversión.

**Qué no decidimos aquí:**

- qué tasa será la referencia definitiva para los análisis;
- cómo triangular entre monedas;
- cómo relacionar precios con salarios.

Esas son decisiones metodológicas posteriores.

---

## 2. Glosario para poder explicar el sistema

| Término | Qué significa en este proyecto |
|---|---|
| **Tasa de cambio** | Cuántas unidades de una moneda se necesitan para obtener 1 unidad de otra. |
| **Cotización** | Un dato concreto de tasa publicado por una fuente: "1 USD = X CUP", por ejemplo. |
| **Actualización** | Una ejecución del proceso de consulta. Previsiblemente, una vez al día. |
| **Incidencia** | Un fallo o anomalía durante una actualización. **No es una tasa.** |
| **Historial** | Todos los registros acumulados, sin borrar los anteriores. |
| **JSON** | Formato de texto con llaves `{}` y corchetes `[]` para guardar datos de forma ordenada. Es fácil de leer y de escribir por programas. |
| **UUID** | Identificador único de 36 caracteres con guiones, por ejemplo `00000000-0000-4000-8000-000000000001`. Sirve para que cada registro tenga un nombre que no se repita. |
| **ISO 8601** | Formato estándar de fecha y hora, por ejemplo `2026-11-01T09:30:00Z`. La `Z` indica hora UTC. |
| **Append-only** | "Solo añadir": nunca se modifica ni se borra un registro anterior; solo se agregan nuevos. |
| **Normalizar** | Convertir un dato a una forma común para poder compararlo. Aquí, expresar el valor por **1 unidad** de moneda de origen. |
| **Mercado informal** | Cambio de divisas fuera de los canales oficiales. No es una tasa oficial. En el proyecto lo documenta ElToque. |
| **Tasa oficial** | Tasa publicada por la institución oficial correspondiente. En el proyecto, el Banco Central de Cuba (BCC). |
| **Fuente** | Quién publica el dato: `eltoque` o `bcc`. |
| **Categoría** | Tipo de mercado al que pertenece la cotización: `oficial` o `mercado_informal`. **No** se deduce del nombre de la página. |
| **Fecha de publicación** | Cuándo la fuente dice que publicó la tasa. |
| **Fecha de vigencia** | Desde cuándo aplica la tasa, si la fuente lo declara. |
| **Fecha de captura** | Cuándo **nosotros** obtuvimos el dato. |
| **Sospechosa** | Cotización que se conserva, pero que no se usa por defecto porque tiene una anomalía documentada. |

---

## 3. Fuentes y categorías

### 3.1 Las dos fuentes

| Fuente | `fuente` | Qué es | Qué aporta al proyecto |
|---|---|---|---|
| ElToque | `eltoque` | Medio de prensa cubano. **No es una institución oficial.** | Información sobre el mercado informal (la categoría se asigna por cotización). |
| Banco Central de Cuba (BCC) | `bcc` | Banco central del país; **institución oficial**. | Tasas oficiales. |

Página de referencia del BCC:
`https://www.bc.gob.cu/tasas-de-cambio`.

Aclaraciones importantes:

- Las cotizaciones de **ElToque** son **informativas**. No son tasas oficiales y
  no necesariamente representan todas las operaciones reales del mercado. Al
  citarlas debe quedar claro que son datos publicados por ElToque sobre el
  mercado informal, no una medición completa de ese mercado.
- La página del BCC es la referencia indicada para el proyecto. Las
  publicaciones concretas, los formatos y las condiciones de uso deben
  verificarse antes de implementar la extracción.
- No se usa la denominación «Banco Nacional de Cuba (BNC)»: la institución que
  se consulta es el **Banco Central de Cuba (BCC)** y su identificador es `bcc`.

### 3.2 La categoría no se deduce de la página

`fuente` y `categoria` son dos dimensiones distintas:

- **`fuente`**: quién publica el dato (`eltoque` o `bcc`).
- **`categoria`**: a qué tipo de mercado pertenece la cotización (`oficial` o
  `mercado_informal`).

La categoría se asigna **por cotización**, según lo que la publicación indique
sobre esa tasa, y **no** por el simple hecho de aparecer en una página:

- La mayoría de los datos de ElToque serán `mercado_informal`, pero si ElToque
  publica una tasa que corresponde al mercado oficial, esa cotización se
  registra como `oficial`.
- La mayoría de los datos del BCC serán `oficial`, pero la categoría se asigna
  igualmente cotización por cotización.
- Si no se puede determinar a qué mercado pertenece una cotización, **no se
  registra como válida**: se registra una incidencia. No se adivina.

### 3.3 No se asume una única tasa

**No se asume que cada fuente publique una única tasa.** Una misma fuente puede
distinguir monedas, operaciones, modalidades o segmentos, y el sistema debe poder
guardarlos por separado:

- `moneda_origen` y `moneda_destino`;
- `tipo_tasa` (la modalidad que la fuente indique, si la indica);
- `segmento`, si la fuente lo distingue;
- `fecha_publicacion` y, si existe, `fecha_vigencia`.

Esto es especialmente importante en el BCC, que puede publicar varias tasas
oficiales para distintas monedas u operaciones. **No se inventan categorías ni
campos para modalidades que todavía no se hayan comprobado.**

### 3.4 Lo que todavía no sabemos y no inventamos

- las modalidades, operaciones y segmentos reales de cada fuente;
- las URLs y la forma exacta de acceso (de ElToque no se fija ninguna aquí; del
  BCC solo se conoce la página de referencia);
- los horarios de publicación;
- si ElToque publica ocasionalmente datos que correspondan al mercado oficial y
  cómo los identifica.

Todo eso se verificará antes de implementar la extracción.

---

## 4. Estructura del archivo

- **Ruta propuesta:** `data/raw/exchange_rates/historial_tasas.json`.
- **Un solo archivo JSON** con un objeto raíz.
- **Historial append-only:** solo se añaden registros.
- El archivo vive bajo `data/raw/`, que ya está excluido por `.gitignore`. Los
  **datos** no se versionan; el **esquema** se documenta aquí.
- La carpeta no se crea en esta fase: se creará al implementar la primera
  captura.

### 4.1 Estructura general

```json
{
  "version_esquema": "1.0",
  "ultima_actualizacion": "2026-11-01T09:05:00Z",
  "cotizaciones": [],
  "actualizaciones": [],
  "incidencias": []
}
```

| Bloque | Qué guarda |
|---|---|
| `version_esquema` | Versión de este diseño. Sirve para saber si el formato cambió. |
| `ultima_actualizacion` | Fecha y hora de la última escritura correcta del archivo. |
| `cotizaciones` | Las tasas obtenidas (válidas o marcadas como sospechosas). |
| `actualizaciones` | Un resumen de cada ejecución del proceso. |
| `incidencias` | Los fallos y anomalías, separados de las tasas. |

**Por qué no hay totales ni resúmenes por fuente en la cabecera:** se pueden
calcular a partir de los registros. Guardarlos aparte obligaría a mantenerlos
sincronizados y podrían quedar mal. Menos campos, menos errores.

---

## 5. Cotizaciones

Una cotización es **una observación concreta** de una tasa. No es "la tasa de
ElToque" en general: es la tasa de una fuente, una categoría, una modalidad, un
segmento y un par de monedas, en un momento dado.

### 5.1 Campos

| Campo | Tipo | Obligatorio | Explicación |
|---|---|---|---|
| `id` | UUID | sí | Identificador único de esta cotización. No se reutiliza. |
| `id_actualizacion` | UUID | sí | Identifica la actualización que obtuvo esta cotización. |
| `fuente` | texto | sí | `eltoque` o `bcc`. |
| `categoria` | texto | sí | Tipo de mercado: `oficial` o `mercado_informal`. No se deduce del nombre de la fuente. |
| `tipo_tasa` | texto | sí | Modalidad que indique la fuente. Si no la indica, `no_especificado`. |
| `segmento` | texto o `null` | no | Segmento, solo si la fuente lo distingue. Si no, `null`. |
| `moneda_origen` | texto | sí | Moneda que se convierte (`USD`, `CUP`, `MLC`, `EUR`, …). |
| `moneda_destino` | texto | sí | Moneda que se recibe. Debe ser distinta de la de origen. |
| `valor` | número | sí | Cuántas unidades de `moneda_destino` equivalen a **1** de `moneda_origen`. Debe ser mayor que cero. |
| `valor_texto_original` | texto | sí | El valor tal como lo publica la fuente, sin reinterpretar. |
| `fecha_publicacion` | ISO 8601 o `null` | no | Cuándo lo publicó la fuente, si lo dice. |
| `fecha_vigencia` | ISO 8601 o `null` | no | Desde cuándo aplica, si la fuente lo declara. |
| `fecha_captura` | ISO 8601 | sí | Cuándo lo obtuvimos nosotros. |
| `url_fuente` | texto | sí | Dirección exacta consultada. Se registrará al implementar. |
| `estado` | texto | sí | `valida` o `sospechosa`. |
| `motivo_sospecha` | texto o `null` | no | Obligatorio si `estado = sospechosa`; `null` si es válida. |
| `reemplaza_a` | UUID o `null` | no | Si esta cotización corrige a otra, aquí va el `id` de la anterior. |

### 5.2 Ejemplo ficticio

```json
{
  "id": "00000000-0000-4000-8000-000000000001",
  "id_actualizacion": "00000000-0000-4000-8000-000000000010",
  "fuente": "eltoque",
  "categoria": "mercado_informal",
  "tipo_tasa": "no_especificado",
  "segmento": null,
  "moneda_origen": "USD",
  "moneda_destino": "CUP",
  "valor": 123.45,
  "valor_texto_original": "123,45 (ficticio)",
  "fecha_publicacion": "2026-11-01T00:00:00Z",
  "fecha_vigencia": null,
  "fecha_captura": "2026-11-01T09:00:00Z",
  "url_fuente": "https://ejemplo.invalid/fuente",
  "estado": "valida",
  "motivo_sospecha": null,
  "reemplaza_a": null
}
```

> `123.45`, las fechas y la URL son **ficticios**. No representan ninguna tasa
> real.

### 5.3 Qué campos se eliminaron y por qué

| Campo que se quitó | Por qué no lo necesitamos |
|---|---|
| `hash_contenido` | Para detectar duplicados basta comparar unos pocos campos. Guardar una "huella" técnica añade un concepto difícil de explicar sin beneficio claro para este volumen de datos. |
| `metodo_extraccion` | La trazabilidad ya queda con `fuente`, `url_fuente`, `fecha_captura` e `id_actualizacion`. Si más adelante hace falta distinguir captura manual de automática, se puede añadir entonces. |
| `unidad_original` | No sabemos todavía si alguna fuente publica "por 100". No inventamos el caso. Si se verifica, se documenta y se añade el campo. |
| `fecha_publicacion_texto` | Guardamos la fecha normalizada; si el formato es ambiguo, se marca la cotización como sospechosa y se explica el motivo. |
| `notas` | El único texto que necesitamos conservar es el motivo de sospecha. Para lo demás, están `descripcion` (incidencias) y la documentación del proyecto. |

---

## 6. Actualizaciones

Una **actualización** es una ejecución del proceso: "hoy consultamos ElToque y el
BCC". Sirve para distinguir una ejecución correcta que no trajo tasas nuevas de
una ejecución que falló.

### 6.1 Campos

| Campo | Tipo | Obligatorio | Explicación |
|---|---|---|---|
| `id` | UUID | sí | Identificador único de la ejecución. |
| `fecha_inicio` | ISO 8601 | sí | Cuándo empezó. |
| `fecha_fin` | ISO 8601 | sí | Cuándo terminó. |
| `fuentes_consultadas` | arreglo | sí | Fuentes incluidas en la ejecución. |
| `resultado_por_fuente` | arreglo | sí | Un resumen por cada fuente. |

Cada elemento de `resultado_por_fuente` tiene:

| Campo | Valores | Explicación |
|---|---|---|
| `fuente` | `eltoque`, `bcc` | Fuente a la que corresponde el resultado. |
| `estado` | `ok`, `parcial`, `error`, `sin_novedad` | Cómo terminó esa fuente. |
| `cotizaciones_nuevas` | número | Cuántas cotizaciones se añadieron. |
| `incidencias` | número | Cuántas incidencias se registraron. |

Significado de los estados:

- **`ok`**: se pudo consultar y se obtuvo al menos una cotización nueva.
- **`sin_novedad`**: se pudo consultar, pero no había una tasa nueva que
  registrar.
- **`parcial`**: se obtuvo una parte, pero no todo.
- **`error`**: no se pudo completar la consulta.

### 6.2 Ejemplo ficticio

```json
{
  "id": "00000000-0000-4000-8000-000000000010",
  "fecha_inicio": "2026-11-01T09:00:00Z",
  "fecha_fin": "2026-11-01T09:05:00Z",
  "fuentes_consultadas": ["eltoque", "bcc"],
  "resultado_por_fuente": [
    {
      "fuente": "eltoque",
      "estado": "ok",
      "cotizaciones_nuevas": 1,
      "incidencias": 0
    },
    {
      "fuente": "bcc",
      "estado": "error",
      "cotizaciones_nuevas": 0,
      "incidencias": 1
    }
  ]
}
```

**Por qué guardamos las actualizaciones:** sin ellas, no podríamos distinguir
"hoy no había tasa nueva" de "hoy falló la consulta". Las dos situaciones son
distintas y deben quedar registradas.

---

## 7. Incidencias

Una **incidencia** es un fallo o una anomalía. **Nunca es una tasa** y nunca se
guarda en `cotizaciones`.

### 7.1 Campos

| Campo | Tipo | Obligatorio | Explicación |
|---|---|---|---|
| `id` | UUID | sí | Identificador único de la incidencia. |
| `id_actualizacion` | UUID | sí | Actualización en la que ocurrió. |
| `fuente` | texto | sí | `eltoque` o `bcc`. |
| `categoria` | texto o `null` | no | Tipo de mercado de la cotización afectada: `oficial` o `mercado_informal`. Puede ser `null` si no se puede determinar. |
| `fecha_captura` | ISO 8601 | sí | Cuándo se detectó. |
| `tipo` | texto | sí | Tipo de fallo (ver abajo). |
| `descripcion` | texto | sí | Explicación breve y legible. |
| `estado` | texto | sí | `abierta` o `resuelta`. |
| `url_fuente` | texto o `null` | no | Dirección afectada, si aplica. |
| `detalle_tecnico` | texto o `null` | no | Texto técnico del error, si ayuda a revisarlo. |

### 7.2 Tipos de incidencia

| `tipo` | Cuándo se usa |
|---|---|
| `conexion` | No se pudo acceder a la fuente. |
| `estructura` | La página o respuesta cambió y ya no coincide con lo esperado. |
| `extraccion` | El dato existe, pero no se pudo extraer o interpretar. |
| `validacion` | El dato se obtuvo, pero no pasó las reglas de validación. |
| `parcial` | Solo se pudo procesar una parte de la fuente. |
| `otro` | Cualquier otro fallo documentado. |

### 7.3 Ejemplo ficticio

```json
{
  "id": "00000000-0000-4000-8000-000000000020",
  "id_actualizacion": "00000000-0000-4000-8000-000000000010",
  "fuente": "bcc",
  "categoria": "oficial",
  "fecha_captura": "2026-11-01T09:02:00Z",
  "tipo": "conexion",
  "descripcion": "No se pudo completar la consulta (ejemplo ficticio).",
  "estado": "abierta",
  "url_fuente": "https://ejemplo.invalid/fuente",
  "detalle_tecnico": null
}
```

### 7.4 Por qué las incidencias van separadas

Si guardáramos un error en `cotizaciones`, una consulta de "última tasa" podría
devolver un fallo como si fuera un dato económico. Mantenerlas en `incidencias`:

1. evita mezclar errores con tasas;
2. permite contar fallos por fuente y por tipo;
3. deja claro que la última tasa válida no se ha perdido.

Se guardan en el **mismo archivo**, pero en un arreglo distinto. Un archivo
aparte complicaría mantener la coherencia entre una actualización, sus
cotizaciones y sus incidencias. Si algún día el volumen lo justifica, se podrá
separar.

---

## 8. Conservación del historial

Reglas:

1. **Append-only:** cada ejecución añade registros; no se sobrescribe ni se
   elimina nada.
2. **Conservar las capturas:** cada cotización nueva registra su
   `fecha_captura`. Si la fuente repite una cotización sin cambios y no hay
   información que permita identificarla como una observación nueva, se
   registra la consulta en `actualizaciones`, sin duplicar la cotización.
3. **Correcciones:** si una cotización se corrige, se añade una nueva con un
   `id` nuevo y, opcionalmente, `reemplaza_a` apuntando al `id` anterior. La
   anterior **no se borra**.
4. **UUID:** cada registro tiene un identificador único; no se reutiliza.
5. **Sin purga automática:** el historial se conserva completo.
6. **Crecimiento:** si el archivo se vuelve inmanejable, se evaluará separar por
   año o por fuente. No es un problema para el volumen previsto (dos fuentes,
   una vez al día).
7. **Sin mezcla entre fuentes:** las cotizaciones de ElToque y del BCC se
   conservan por separado, cada una con su `fuente` y su `categoria`. No se
   combinan, no se promedian y no se agregan entre sí. La comparación, si se
   hace, es explícita y posterior.

**Excepción:** el campo `estado` de una incidencia puede pasar de `abierta`
a `resuelta` cuando se solucione el problema. El resto de sus datos se
conserva sin modificaciones. Las cotizaciones y las actualizaciones no se
sobrescriben.

---

## 9. Consultas

### 9.1 Clave de consulta

Una consulta se identifica por:

```text
(fuente, categoria, moneda_origen, moneda_destino, tipo_tasa, segmento)
```

`segmento = null` es un valor de la clave, **no** un comodín. Es decir, "sin
segmento" es una categoría en sí misma.

La `fuente` y la `categoria` forman parte de la clave: **una consulta nunca
mezcla ElToque con BCC ni tasas oficiales con informales**. Tampoco se calculan
promedios ni agregados entre fuentes; si se comparan, se hace después de forma
explícita y mostrando cada fuente por separado.

### 9.2 Última tasa capturada (la consulta habitual)

Es la cotización **válida** más reciente por `fecha_captura` para esa clave.

Pasos:

1. filtrar por la clave exacta;
2. quedarse solo con `estado = valida`;
3. ordenar por `fecha_captura` de más reciente a más antigua;
4. si hay empate, ordenar por `id` para que el resultado sea siempre el mismo;
5. devolver la primera;
6. si no hay ninguna, devolver `null`. **Nunca `0`.**

Esta es la consulta que usaremos por defecto para "la última tasa disponible".

### 9.3 Última tasa vigente

Es la cotización **válida** cuya `fecha_vigencia` declarada sea anterior o igual a
una fecha de referencia.

**Condición previa:** esta consulta solo tiene sentido para fuentes que declaran
`fecha_vigencia` de forma sistemática. Debe comprobarse, fuente por fuente, antes
de usarla.

Pasos:

1. filtrar por la clave exacta;
2. quedarse solo con `estado = valida`;
3. localizar la cotización válida **más reciente por `fecha_captura`**;
4. si esa cotización **no** declara `fecha_vigencia`, devolver
   **"no determinable"**. No se recurre a una cotización más antigua que sí la
   declare, porque podría estar desactualizada;
5. si declara `fecha_vigencia`:
   - si `fecha_vigencia <= fecha_referencia`, devolverla;
   - si es futura, buscar la más reciente con `fecha_vigencia <= fecha_referencia`
     y, si no existe, devolver **"no determinable"**;
6. en caso de empate, ordenar por `fecha_captura` y luego por `id`.

**Importante:** si una fuente no da `fecha_vigencia`, **no** suponemos que sea
igual a `fecha_captura`. Se guarda `null` y la consulta de vigencia no la usa.
Tampoco se devuelve una tasa antigua como si fuera la vigente: si no se puede
determinar, se dice explícitamente.

### 9.4 Historial completo

Se pueden recuperar todas las cotizaciones de una clave, ordenadas por
`fecha_captura`. Incluye las `sospechosa`, con su marca y su motivo. No se
elimina nada.

### 9.5 Qué se puede consultar y qué no

| Consulta | Qué devuelve | Qué no devuelve |
|---|---|---|
| Última capturada | La cotización válida más reciente. | Tasas sospechosas ni incidencias. |
| Última vigente | La tasa vigente según la fecha declarada por la fuente, si la cotización más reciente la declara. | Una fecha de vigencia inventada ni una tasa antigua presentada como actual. |
| Historial | Todas las cotizaciones de la clave, incluidas las sospechosas. | Incidencias mezcladas con tasas. |
| Incidencias | Fallos por fuente, tipo o fecha. | Tasas. |
| Actualizaciones | Resumen de cada ejecución. | Cotizaciones concretas (se enlazan por `id_actualizacion`). |

---

## 10. Reglas de actualización diaria

1. **Frecuencia:** una vez al día.
2. **No sobrescribir:** una actualización añade; no modifica registros previos.
3. **Nueva cotización, nueva captura:** cada cotización conserva su
   `fecha_captura`.
4. **Varias cotizaciones de la misma moneda:** si la fuente publica varias
   (distinta modalidad, segmento o fecha), se conservan por separado.
5. **Sin novedad:** si no hay tasa nueva, **no** se copia la anterior como si
   fuera nueva. Se registra `sin_novedad` en la actualización.
6. **Fallo:** si una fuente falla, se añade una incidencia. La última tasa válida
   **no se borra ni se sobrescribe**.
7. **Aislamiento por fuente:** un fallo en una fuente no invalida los registros
   correctos de la otra.
8. **Actualización parcial:** si dentro de una fuente se obtienen unas
   cotizaciones y otras no, se guardan las válidas y se registran incidencias
   para las fallidas.
9. **Copia de seguridad:** antes de escribir, conviene conservar una copia del
   archivo anterior. Es una medida sencilla y fácil de explicar.

---

## 11. Validación y sospecha

### 11.1 Cuándo se rechaza una cotización

Se rechaza (y se registra una incidencia de tipo `validacion`) si:

1. `valor` es nulo, no numérico o **menor o igual que cero**.
2. `moneda_origen` o `moneda_destino` faltan o no están identificadas.
3. Las dos monedas son la misma.
4. Falta `fecha_captura` o no es una fecha válida.
5. Faltan `fuente`, `categoria`, `tipo_tasa` o `url_fuente`.
6. No se puede determinar a qué mercado pertenece la cotización (`oficial` o
   `mercado_informal`) a partir de lo que publica la fuente.
7. No se puede asociar a una actualización.
9. Está marcada como `sospechosa` pero no tiene `motivo_sospecha`.

Los duplicados no se consideran errores de validación: se gestionan según
las reglas de la sección 12. Si no hay una observación nueva, no se añade
otra cotización y la actualización se registra como `sin_novedad`.

### 11.2 Cuándo se conserva como sospechosa

Una cotización **sí se guarda** si tiene una anomalía que no impide registrar el
dato, pero que aconseja no usarlo por defecto. En ese caso:

- `estado = "sospechosa"`;
- `motivo_sospecha` explica la razón;
- se excluye de las consultas normales;
- se puede recuperar en el historial o con una consulta explícita.

**Lo que no hacemos:** marcar como sospechosa una cotización **solo** porque su
valor sea muy distinto al anterior. Una variación grande puede ser real. La
sospecha debe tener una razón documentada (por ejemplo, una fecha incoherente,
una moneda ambigua o una duda de interpretación). No inventamos umbrales
automáticos.

### 11.3 Las tres fechas

| Fecha | Significado | Quién la fija |
|---|---|---|
| `fecha_publicacion` | Cuándo la fuente dice que publicó la tasa. | La fuente. |
| `fecha_vigencia` | Desde cuándo aplica, si lo declara. | La fuente. |
| `fecha_captura` | Cuándo lo obtuvimos nosotros. | Nuestro sistema. |

No se confunden entre sí. Si falta una, se guarda `null`; no se rellena por
conveniencia.

### 11.4 Reglas generales

- La ausencia de una cotización **no** es `0`.
- No se imputan valores.
- No se convierte una moneda sin una tasa documentada.
- No se considera que dos cotizaciones son iguales solo porque tengan el mismo
  `valor`.

---

## 12. Duplicados y ejecuciones repetidas

No guardamos una "huella" técnica. Comparamos directamente estos campos:

`fuente`, `categoria`, `tipo_tasa`, `segmento`, `moneda_origen`,
`moneda_destino`, `fecha_publicacion`, `fecha_vigencia` y
`valor_texto_original`.

Reglas:

1. Si todos coinciden, es la **misma observación**: no se añade otra.
2. Si `fecha_publicacion` y `fecha_vigencia` son `null`, no podemos saber si la
   fuente publicó una tasa nueva o repitió la anterior. En ese caso se compara
   con la **última cotización guardada de la misma clave** (fuente, categoría,
   tipo de tasa, segmento y monedas):
   - si `valor_texto_original` coincide → es la misma observación: no se añade
     nada y la actualización se registra como `sin_novedad`;
   - si cambia → es una observación nueva y se guarda con su `fecha_captura`.
3. Si solo una de las dos fechas está disponible, se utiliza la información
   existente para comparar la cotización con las observaciones anteriores.
   Si no es posible determinar si se trata de una observación nueva, no se
   añade automáticamente y se registra una incidencia para su revisión.
4. Un mismo `valor` con distinta fuente, moneda, modalidad, segmento o fecha
   **sí** genera registros separados.
5. No se borra un duplicado detectado: simplemente no se añade.

**Limitación asumida:** sin fecha de publicación, "la fuente no publicó nada
nuevo" y "la fuente repitió el mismo valor" son indistinguibles. Ante la duda,
preferimos **no** duplicar la observación y dejar constancia de la consulta en
`actualizaciones` (`sin_novedad`). Así se cumple la regla de no registrar la
tasa anterior como si fuera nueva.

**Por qué no usamos un hash:** un hash es una huella digital de un conjunto de
datos. Es útil con millones de registros, pero aquí añade un concepto técnico y
un campo que habría que explicar. Comparar unos pocos campos es suficiente y más
fácil de auditar.

---

## 13. Fallos, cambios de formato y campos faltantes

| Situación | Qué hacemos |
|---|---|
| **Campo obligatorio ausente** | Rechazar la cotización, registrar incidencia (`estructura` o `validacion`) y conservar la última tasa válida. |
| **Campo opcional ausente** | Guardar `null`; no inventar el valor. |
| **Cambio de estructura de la página** | Detener la extracción de esa fuente en esa ejecución, registrar incidencia `estructura` y no intentar adivinar. |
| **Moneda o modalidad desconocida** | Rechazar y registrar incidencia; no mapear a ciegas. |
| **Categoría no determinable** | Si no se puede saber si la tasa es oficial o informal, no se registra como válida; se registra una incidencia `validacion`. |
| **La fuente deja de publicar una modalidad** | No se crea una cotización nueva; la última válida permanece y se puede consultar su antigüedad. |
| **Actualización parcial** | Conservar las cotizaciones válidas ya obtenidas y registrar incidencias para las fallidas. |
| **La fuente no responde** | Registrar incidencia `conexion`; no tocar las tasas anteriores. |

---

## 14. Relación con los anuncios inmobiliarios

### 14.1 Lo que nunca se pierde

- `precio` original del anuncio.
- `moneda` original del anuncio.
- `fecha_captura` del anuncio.

### 14.2 Cómo se rastrea una conversión

Se propone añadir al esquema inmobiliario un solo campo nuevo: **`tasa_id`**, con
el UUID de la cotización aplicada. Los demás datos de la tasa (fuente,
categoría, modalidad, segmento, fechas) se obtienen del historial de tasas
mediante ese `id`, sin duplicarlos en el anuncio.

Los campos existentes `tasa_conversion_usd`, `tasa_fecha` y `tasa_fuente` se
mantienen como resumen legible.

### 14.3 Casos

| Caso | `moneda` original | `precio_usd` | `tasa_id` |
|---|---|---|---|
| Precio ya publicado en USD | `USD` | Igual a `precio` (sin conversión) | `null` |
| Precio en CUP convertido con tasa oficial | `CUP` | Calculado | UUID de la cotización oficial |
| Precio en CUP convertido con tasa informal | `CUP` | Calculado | UUID de la cotización informal |
| Precio en MLC convertido | `MLC` | Calculado | UUID de la cotización usada |
| Precio en EUR convertido | `EUR` | Calculado | UUID de la cotización usada |
| Sin tasa documentada | cualquiera | `null` | `null` |

### 14.4 Reglas

1. **Nunca** se pierde el precio original ni su moneda.
2. Las tasas oficiales e informales **no se mezclan** ni se tratan como
   equivalentes. La categoría se obtiene de la cotización enlazada.
3. Las cotizaciones de **ElToque y del BCC no se mezclan ni se promedian**. Cada
   conversión usa una cotización concreta de una fuente concreta, identificada
   por `tasa_id`.
4. **No** se convierte una moneda si no hay una cotización documentada para ese
   par.
5. **No** se decide aquí qué tasa será la referencia definitiva.
6. **No** se implementan triangulaciones entre monedas.
7. Toda conversión debe poder rastrearse a `tasa_id`.

---

## 15. Por qué diseñamos así (para defenderlo)

### 15.1 Un solo archivo JSON, no una base de datos

Con dos fuentes y una consulta diaria, el volumen es pequeño. Un JSON es fácil
de abrir, revisar, copiar y explicar. Una base de datos añadiría instalación,
consultas y mantenimiento sin una ventaja clara para este proyecto.

**Limitación:** el archivo se reescribe completo al añadir datos y no está
pensado para varias personas escribiendo a la vez. Para este proyecto no es un
problema. Si creciera mucho, se podría migrar a SQLite o separar por año.

### 15.2 Append-only, no sobrescribir

Si sobrescribiéramos la tasa de ayer, perderíamos la posibilidad de reconstruir
qué tasa se usó en una conversión y de comparar la evolución. El historial es la
base de la reproducibilidad.

### 15.3 Tres arreglos separados

Una cotización, una actualización y una incidencia son cosas distintas:

- una cotización es un dato económico;
- una actualización es una ejecución del proceso;
- una incidencia es un fallo.

Mezclarlas haría difícil distinguir "no había tasa" de "falló la consulta" y
podría contaminar los cálculos.

### 15.4 UUID, no números consecutivos

Un UUID no depende de un contador ni de la fecha. No se repite y permite enlazar
una cotización con una actualización sin ambigüedad. La desventaja es que es
largo y menos legible; a cambio, evita colisiones y reutilizaciones.

### 15.5 Conservar el valor original

`valor` es el número normalizado; `valor_texto_original` es lo que publicó la
fuente. Si hay una duda de formato, podemos volver al texto original. Sin ese
campo, una conversión podría ser imposible de auditar.

### 15.6 Tres fechas, no una

Publicación, vigencia y captura responden a preguntas distintas. Si las
mezclamos, podríamos afirmar que una tasa "estaba vigente" cuando solo sabemos
cuándo la vimos. Preferimos un `null` honesto a una fecha inventada.

### 15.7 Sospechosa, no descartada

Un valor muy distinto al anterior puede ser un error o puede ser real. Si lo
descartamos, perdemos información; si lo usamos sin más, contaminamos el
análisis. La solución intermedia es conservarlo, marcarlo y documentar el motivo.

### 15.8 Sin detección automática de anomalías

Detectar anomalías automáticamente requiere umbrales, históricos y reglas que
todavía no tenemos. En esta fase, la revisión es manual y el motivo queda
escrito. Es más simple y más honesto.

### 15.9 Sin triangulación ni tasa de referencia

Triangular (por ejemplo, EUR→USD→CUP) inventaría una tasa que la fuente no
publicó. Elegir una tasa de referencia definitiva es una decisión metodológica
que afecta a los resultados y debe hacerse con más información. Por eso el
sistema solo almacena; no decide.

### 15.10 Dos fuentes independientes, no una sola «tasa de cambio»

ElToque y el BCC no son intercambiables. ElToque es un medio de prensa que
publica información sobre el mercado informal; sus datos son informativos y no
representan necesariamente todas las operaciones reales. El BCC es la
institución oficial y publica tasas oficiales. Por eso `fuente` y `categoria`
son campos separados: permiten decir «qué publicó quién» y «a qué mercado
pertenece», sin confundir ambos. Mezclarlas o promediarlas produciría una cifra
que ninguna de las dos fuentes publicó y que no podríamos justificar.

---

## 16. Cómo explicarlo en cinco minutos

1. Tenemos dos fuentes: ElToque, un medio de prensa que publica información del
   mercado informal, y el Banco Central de Cuba (BCC), que publica tasas
   oficiales.
2. Una vez al día consultamos sus tasas y las guardamos en un archivo JSON.
3. Cada cotización tiene un UUID, la fuente, la categoría, las monedas, el valor,
   las fechas, la URL y un estado.
4. La categoría indica el tipo de mercado (`oficial` o `mercado_informal`); no
   se deduce del nombre de la página.
5. Las actualizaciones y las incidencias se guardan aparte: un fallo no es una
   tasa.
6. Nunca sobrescribimos: el historial completo permite auditar.
7. Podemos consultar la última tasa capturada y, si la fuente declara vigencia,
   la última vigente.
8. Si una cotización parece anómala, se conserva como sospechosa con su motivo y
   no se usa por defecto.
9. Cuando convirtamos un anuncio, guardaremos el `tasa_id` para saber
   exactamente qué cotización se usó.
10. No mezclamos ni promediamos las fuentes: se conservan por separado para
    compararlas después.
11. Todavía no decidimos qué tasa usar para los análisis ni triangulamos.
12. Es un diseño simple a propósito: prioriza conservar los datos y poder
    explicarlos.

---

## 17. Decisiones pendientes

1. **Publicaciones concretas del BCC**: qué tasas publica, con qué periodicidad y
   en qué formato. La institución ya está identificada, pero sus publicaciones
   deben verificarse antes de implementar.
2. **URLs y forma de acceso** a ElToque y al BCC, y verificación de sus
   condiciones de uso. Del BCC solo se conoce la página de referencia; de
   ElToque no se fija ninguna en este documento. No se asume permiso de
   automatización.
3. **Modalidades y segmentos reales** que publica cada fuente.
4. **Hora exacta** de la actualización diaria y zona horaria de referencia.
5. **Criterios de sospecha:** qué anomalías concretas justifican marcar una
   cotización. Debe documentarse antes de usarlo de forma sistemática.
6. **Tasa de referencia definitiva** para los análisis. No se decide aquí.
7. **Triangulación** entre monedas. No se implementa por ahora.
8. **Relación precios-salarios.** Fuera del alcance de este documento.
9. **Crecimiento del archivo:** si conviene separar por año o por fuente.
10. **Copia de seguridad:** dónde y con qué frecuencia guardar la copia anterior.
11. **Dirección de las cotizaciones:** verificar cómo publica cada fuente los
    pares de monedas y decidir si se permite utilizar la inversa matemática
    de una cotización directa, conservando la trazabilidad mediante `tasa_id`.

---

## 18. Registro de cambios

- Versión inicial: diseño del archivo histórico único, esquema de cotizaciones,
  incidencias y actualizaciones, reglas de conservación, consulta, validación,
  duplicados, fallos y vinculación con anuncios inmobiliarios.
- 2026-11-01: simplificación del diseño. Se eliminan campos técnicos
  innecesarios (`hash_contenido`, `metodo_extraccion`, `unidad_original`,
  `fecha_publicacion_texto`, `notas`), se aplana la estructura del JSON, se
  adopta UUID, se añade `motivo_sospecha`, se separa con más claridad la última
  tasa capturada de la última vigente y se documenta el razonamiento para poder
  defenderlo.
- 2026-11-01 (corrección): se precisa la regla de duplicados cuando la fuente no
  declara fechas (se compara con la última cotización de la misma clave y se
  registra `sin_novedad` si el valor no cambia) y se evita que la consulta de
  "última vigente" devuelva una tasa antigua cuando la más reciente no declara
  `fecha_vigencia`.
- 2026-11-01 (aclaración de fuentes): se sustituye «Banco Nacional de Cuba
  (BNC)» por **Banco Central de Cuba (BCC)**, con identificador `bcc` y página
  de referencia `https://www.bc.gob.cu/tasas-de-cambio`. Se separa `fuente`
  (quién publica) de `categoria` (tipo de mercado), se aclara que la categoría se
  asigna por cotización y no por la página, y se documenta que ElToque es un
  medio de prensa cuyos datos son informativos. Se prohíbe mezclar o promediar
  cotizaciones de ambas fuentes.
