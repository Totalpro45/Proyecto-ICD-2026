# Especificación del análisis de datos

**Proyecto:** ¿Es asequible el precio de la vivienda para el cubano promedio?
**Caso de estudio:** La Habana
**Estado:** borrador de planificación; no contiene código ni resultados.
**Documento relacionado:** `docs/decisiones.md` (esquema de datos común y políticas).

Este documento traduce las preguntas del proyecto en un **plan de análisis de
datos**. No introduce variables nuevas en el esquema común: cuando un cálculo
necesita información que aún no está documentada, se indica explícitamente.

> **Regla de honestidad metodológica.** No se inventan variables disponibles,
> datos, cifras ni conclusiones. Todo campo usado aquí o bien **ya existe** en
> `docs/decisiones.md`, o bien se marca como **derivado**, **externo** o
> **pendiente de definir**. Cuando no haya datos suficientes, el resultado es
> "no calculable", no un valor estimado a ojo.

Convención de estado de cada variable:

- **(esquema)**: ya definida en `docs/decisiones.md`.
- **(derivado)**: se calcula a partir de campos del esquema.
- **(externo)**: proviene de fuentes que el autor ya tiene (Resolución 14,
  Anuario Estadístico de Cuba 2024, Decreto-Ley 17 de 2020, prensa). No forma
  parte del dataset de anuncios.
- **(pendiente)**: requiere una decisión aún no tomada (ver `docs/decisiones.md`,
  sección 6, y la sección 9 de este documento).

---

## 1. Variables necesarias por análisis y su disponibilidad

### 1.1 Variables del esquema común que sí existen

| Variable | Estado | Uso principal en el análisis |
|---|---|---|
| `fuente` | (esquema) | Trazabilidad y comparación entre portales. |
| `id_fuente`, `url` | (esquema) | Trazabilidad; evitar doble conteo. |
| `fecha_captura` | (esquema) | Fechar el análisis; distinguir capturas. |
| `fecha_publicacion`, `fecha_actualizacion` | (esquema) | Solo si el portal las expone fiablemente (hoy no confirmadas). |
| `provincia`, `municipio`, `reparto`, `direccion_texto` | (esquema) | Agrupación territorial. |
| `tipo_operacion` | (esquema) | Filtrar `venta`. |
| `tipo_inmueble` | (esquema) | Separar `casa` y `apartamento`. |
| `area_m2` | (esquema) | Cálculo de precio por m². |
| `habitaciones`, `banos` | (esquema) | Caracterización del inmueble típico; análisis exploratorio. |
| `planta`, `estado_conservacion`, `amueblado` | (esquema) | Análisis exploratorio (cobertura baja esperada). |
| `precio`, `moneda` | (esquema) | Estadística en moneda original. |
| `precio_usd`, `tasa_conversion_usd`, `tasa_fecha`, `tasa_fuente`, `tasa_id` | (esquema) | Comparaciones normalizadas y trazabilidad de la conversión (condicionadas a la decisión de tasa). |
| `precio_m2_usd` | (esquema/derivado) | Comparación de precios por m². |
| `titulo`, `descripcion` | (esquema) | Análisis exploratorio de texto; extracción de señales cuando falten campos. |
| `es_posible_duplicado`, `duplicado_grupo` | (esquema) | Decidir qué registros entran en los cálculos. |
| `estado_parseo`, `notas_calidad` | (esquema) | Control de calidad y filtrado. |

### 1.2 Variables o insumos que aún no están en el esquema

| Insumo | Estado | Comentario |
|---|---|---|
| Tabla de tasas de cambio (fuente y fecha) | (pendiente) | `docs/decisiones.md` §2 y §6.1. Sin ella, `precio_usd` y `precio_m2_usd` quedan `null`. |
| Serie de salario mínimo | (externo) | Resolución 14 (Gaceta Oficial n.º 60 ordinaria de 2026); se incorporará como tabla de referencia. |
| Escalas salariales por oficio | (externo) | Resolución 14; requiere decidir cómo se mapean a los anuncios (que no tienen oficio). |
| Salario medio | (externo) | Resolución 14; es un valor de referencia único o por período, no por anuncio. |
| Series demográficas 2011–2024 | (externo) | Anuario Estadístico de Cuba 2024. |
| Contexto monetario (Decreto-Ley 17 de 2020) | (externo) | Contexto interpretativo, no una variable del dataset. |
| Lista canónica de municipios de La Habana | (pendiente) | `docs/decisiones.md` §6.3. Necesaria para agrupar por municipio. |
| Criterio de `area_m2` (total / construcción / parcela) | (pendiente) | `docs/decisiones.md` §6.4. Afecta el precio por m². |

**Principio de alcance:** los análisis que dependan de una variable hoy
mayormente ausente (p. ej. `area_m2` o la tasa de cambio) se calcularán **solo
sobre el subconjunto que la tenga**, reportando siempre el tamaño de ese
subconjunto, y se abstendrán de extrapolar al total.

---

## 2. Distribución de precios de casas y apartamentos

**Pregunta:** ¿cómo se distribuyen los precios de venta de casas y apartamentos
en La Habana?

**Filtros base (idénticos en todos los análisis descriptivos):**

- `tipo_operacion = venta`.
- `tipo_inmueble` en {`casa`, `apartamento`} (las dos categorías se analizan
  **por separado**).
- Registros con `estado_parseo = ok` (o `parcial` solo si `precio` y
  `moneda` están presentes), con `precio` numérico y mayor que cero.
- Se reportará el efecto de `es_posible_duplicado`: métricas con y sin posibles
  duplicados, para medir su sensibilidad.

**Universo de cálculo y moneda:** como las monedas son mixtas, la estadística
principal se hará **por cada moneda presente en la muestra**, sin mezclar
categorías (`USD`, `CUP`, `MLC`, `EUR` u `otra`). Si la tasa queda documentada,
también se calculará sobre `precio_usd` como vista comparable.

**Estadísticos por `tipo_inmueble` y por moneda (y para `precio_usd` cuando
exista):**

- Media (`mean`), marcada como sensible a valores extremos.
- **Mediana** (medida principal de tendencia central).
- Mínimo y máximo.
- Cuantiles (p. ej. p10, p25, p75, p90) y rango intercuartílico (IQR) para
  describir la dispersión sin depender de supuestos de normalidad.
- Histograma y/o diagrama de caja de la distribución; en su caso, escala
  logarítmica si la distribución de precios es muy asimétrica (a decidir tras
  ver los datos, no de antemano).

**Reporte obligatorio:** tamaño de muestra (`n`) por grupo, número de valores
`null` descartados y advertencia de que son **precios anunciados**, no precios de
transacción.

**Pendiente asociado:** la elección de la tasa (§9) determina si además se
publica la estadística en `precio_usd`.

---

## 3. Comparación por municipio y precio por metro cuadrado

### 3.1 Precios por municipio

- Agrupar por `municipio` (categoría, tras fijar la lista canónica — pendiente).
- Para cada municipio y cada `tipo_inmueble`, calcular **mediana**, **media**,
  **n**, p25 y p75 en `precio_usd` (si hay tasa) o en `moneda` original.
- **Regla de robustez:** si un municipio tiene `n` muy bajo, no se interpreta su
  estadístico; se reporta como "muestra insuficiente" y se agrega el conteo al
  total. El umbral mínimo exacto se decide en §8.
- Anuncios con `municipio = null` se agrupan en una categoría explícita
  "municipio no especificado" y **no** se reparten ni se imputan.
- Cuando no exista una tasa de conversión justificable, las comparaciones
  territoriales se harán por separado para cada moneda. Nunca se compararán
  directamente valores expresados en monedas diferentes.

### 3.2 Precio por metro cuadrado

- Usar `precio_m2_usd` (derivado) **solo** cuando `precio_usd` no es `null` y
  `area_m2 > 0`.
- Para cada municipio y tipo de inmueble: mediana de `precio_m2_usd`, `n` y IQR.
- Se usa la mediana como estadístico principal porque el precio por m² suele ser
  asimétrico y sensible a valores extremos.

### 3.3 Tratamiento de superficies o monedas ausentes

- `area_m2` ausente o `0` → el anuncio **no** entra en el cálculo de precio por
  m². Nunca se estima el área. Se informa qué fracción del total queda fuera.
- `moneda` ausente o ambigua → el anuncio no entra en comparaciones
  normalizadas; se conserva para la estadística en moneda original solo si la
  moneda puede determinarse; si no, se excluye y se cuenta.
- `precio_usd = null` (por falta de tasa) → el anuncio se excluye de toda
  comparación entre municipios en USD y se reporta su proporción.
- Los tres casos anteriores se documentan en una tabla de "cobertura por
  municipio" (n con `area_m2`, n con `precio_usd`, n excluidos), de modo que el
  lector vea la base real de cada comparación.

---

## 4. Comparación entre precios inmobiliarios y salarios

**Objetivo:** expresar el precio de la vivienda en términos de cuánto representa
frente a distintos referentes salariales, **sin** confundirlos entre sí.

Tres referentes, que **no** son intercambiables:

1. **Salario mínimo** (externo, Resolución 14): piso legal de ingresos.
2. **Escalas salariales por oficio** (externo, Resolución 14): remuneración
   asociada a ocupaciones concretas.
3. **Salario medio** (externo, Resolución 14): referente agregado único o por
   período.

**Cómo se relacionan con los anuncios:**

- Los anuncios **no** tienen oficio ni salario: la relación se construye con
  **tablas de referencia externas** (por escala/ocupación y por período), no
  campo a campo.
- Los salarios se expresan en la moneda en que los publique la fuente (con toda
  probabilidad CUP, a confirmar al leer la Resolución 14). Para compararlos con
  `precio_usd` hace falta la **tasa de conversión documentada** (decisión
  pendiente §9). Sin tasa, la comparación queda **en CUP** contra precios en CUP
  y se declara que no cubre el resto de anuncios.
- Indicadores propuestos (todos afectados por la decisión de tasa):
  - **Años de salario** = precio (mediana del inmueble típico) ÷ (salario de
    referencia × 12), indicando qué salario se usó.
  - **Meses de salario** para la misma relación.
  - **Índice precio/salario** comparando la mediana de precio por municipio con
    cada referente salarial.
- Se presentan **los tres referentes por separado**; no se promedian ni se
  elige uno como "el" salario del cubano sin justificarlo.

**Interpretación de los indicadores:** estos indicadores representan
equivalencias matemáticas entre el precio anunciado y el salario de referencia.
No representan el tiempo real necesario para comprar una vivienda, pues no
consideran gastos de vida, ahorro, financiación ni otras fuentes de ingresos.

**Advertencias que deben acompañar cada cifra:** el salario formal no captura
ingresos informales, remesas ni pluriempleo; el salario de referencia puede ser
nacional y no de La Habana; y los precios son anunciados, no transados.

**Pendientes:** fuente exacta dentro de la Resolución 14 para cada referente, el
período de vigencia y cómo se alinean temporalmente con la captura de anuncios.

---

## 5. Análisis exploratorio de los anuncios por encima de la mediana

**Pregunta:** ¿qué características acompañan a los anuncios con precio superior a
la mediana?

**Método (exploratorio, no causal):**

1. Calcular la mediana de precio **por** `tipo_inmueble` y, si procede, **por**
   `municipio` (evitando comparar municipios caros con baratos de forma
   engañosa).
2. Definir el grupo "por encima de la mediana" y el grupo "en o por debajo".
3. Comparar la **distribución** de variables descriptivas entre grupos:
   `area_m2`, `habitaciones`, `banos`, `planta`, `estado_conservacion`,
   `amueblado`, `municipio`, `reparto`, `vendedor_tipo`, `fuente`.
4. Usar estadística descriptiva (medianas, proporciones, tablas de contingencia)
   y, con cautela, medidas de asociación (p. ej. diferencias de medianas o
   correlación de rangos) **solo** sobre los subconjuntos con datos presentes.
5. Reportar tamaño de cada grupo y cobertura de cada variable.

**Regla explícita:** estos resultados describen **asociaciones**, no relaciones
causales. No se afirmará que una característica "provoca" un precio mayor, ni se
"controlará" por variables que no estén presentes. Anuncios con campos `null` se
excluyen por variable, no del análisis entero.

**Pendientes:** umbral de cobertura mínima por variable para que su comparación
sea interpretable (§8), y decisión sobre si se usa `descripcion` con `spaCy`
(`docs/decisiones.md` §6.7).

---

## 6. Definición operativa de "inmueble típico" y comparación con ingresos

### 6.1 Definición operativa

El "inmueble típico" se define **de forma transparente y reproducible** como un
**resumen estadístico de la muestra**, no como un inmueble real:

- Conjunto: anuncios de `tipo_operacion = venta` en La Habana, con
  `tipo_inmueble` ∈ {`casa`, `apartamento`}. El inmueble típico se calculará
  aplicando la política de duplicados que se defina para la muestra; se
  comprobará también la sensibilidad del resultado con y sin posibles
  duplicados (ver §8.2).
- En lugar de "el" inmueble, se reportan **medianas** de `area_m2`,
  `habitaciones` y `banos`, junto con la **mediana de `precio_usd`** del
  subconjunto.
- Se presenta por separado para `casa` y `apartamento` y, cuando la muestra lo
  permita, por municipio.

**Aclaración:** las medianas de precio, área, habitaciones y baños se calculan
independientemente. Por tanto, sus valores no describen necesariamente un mismo
anuncio ni deben interpretarse como las características de una vivienda real
concreta.

Justificación: la mediana es robusta a valores extremos y no exige supuestos
distribucionales; usar un promedio daría una imagen engañosa en un mercado con
precios muy dispersos.

### 6.2 Comparación transparente con los ingresos

Para cada referente salarial (mínimo, escala correspondiente, medio):

- **Años de salario del inmueble típico** = mediana de `precio_usd` del inmueble
  típico ÷ (salario de referencia convertido a USD × 12).
- Se acompaña siempre de: el valor de la mediana de precio usada, la fuente y
  fecha del salario, y la fuente y fecha de la tasa de conversión.
- Si falta la tasa o el salario, la comparación **no se calcula**; se declara la
  carencia en lugar de rellenarla.

**Pendientes:** tasa de cambio (§9), referente(s) salarial exacto(s) y alineación
temporal con `fecha_captura`.

---

## 7. Limitaciones para relacionar precios actuales con la demografía 2011–2024

Esta sección fija los límites de lo que se puede afirmar al poner en relación los
precios de los anuncios con las series demográficas (Anuario Estadístico de Cuba
2024):

1. **Desajuste temporal:** los anuncios son una **instantánea actual**; las
   series demográficas son **anuales y retrospectivas** (2011–2024). No hay
   precios históricos comparables en el dataset.
2. **Desajuste de resolución:** la demografía suele ser agregada (provincia o
   país); los anuncios son individuales. No hay correspondencia fina entre ambos.
3. **Sin identificadores comunes:** no existe una variable que enlace un anuncio
   con una serie demográfica; la relación es **descriptiva y a nivel agregado**.
4. **Causalidad no identificable:** no se dispone de diseño que permita aislar
   efectos (migración, envejecimiento, etc.) sobre precios. Cualquier relación
   será **contextual**, no causal.
5. **Sesgos de selección:** los anuncios reflejan lo que se publica (oferta
   visible), no las transacciones ni la demanda real ni la vivienda ocupada.
6. **Contexto monetario cambiante:** la inflación, las reformas y los distintos
   regímenes cambiarios (Decreto-Ley 17 de 2020 y posteriores) dificultan
   comparar montos a lo largo del tiempo.
7. **Cobertura limitada:** los portales no representan necesariamente todo el
   mercado ni todos los municipios por igual.

**Conclusión operativa:** la demografía se usará como **contexto descriptivo**,
presentada en paralelo a los precios actuales, nunca como explicación causal.

---

## 8. Orden recomendado de implementación y criterios de validación

### 8.1 Orden de implementación

1. **Preparar el dataset consolidado** una vez exista la extracción: unificar
   fuentes al esquema común, marcar duplicados y fijar la muestra de análisis
   (una vez decidido el alcance, `docs/decisiones.md` §6.5).

2. **Realizar la estadística descriptiva inicial por moneda original**
   (sección 2): calcular mediana, media, mínimo, máximo y distribución de
   precios para casas y apartamentos, sin mezclar monedas diferentes.

3. **Evaluar la cobertura y calidad de los datos:** revisar la cantidad de
   registros válidos, los valores ausentes, los posibles duplicados y la
   disponibilidad de variables como `municipio` y `area_m2`.

4. **Decidir y documentar la tasa de cambio** (fuente, categoría y fecha),
   siempre que existan cotizaciones suficientemente justificables para
   realizar conversiones. Si no se dispone de ellas, se mantienen los análisis
   en moneda original.

5. **Calcular precios comparables en USD y precios por metro cuadrado**
   (secciones 2 y 3), únicamente para los registros que dispongan de una
   conversión válida y de una superficie utilizable.

6. **Realizar las agregaciones territoriales** (sección 3), por municipio y
   tipo de inmueble, teniendo en cuenta el tamaño y la cobertura de cada
   muestra.

7. **Preparar la tabla de referencia salarial** y realizar la comparación
   precio-salario (sección 4), siempre que existan datos salariales y tasas de
   conversión adecuadas.

8. **Definir el inmueble típico** (sección 6) y realizar su comparación con
   los ingresos cuando los datos lo permitan.

9. **Realizar el análisis exploratorio** por encima de la mediana (sección 5)
   y presentar el contexto demográfico descriptivo (sección 7), junto con las
   limitaciones correspondientes.

Cada paso se realiza sobre datos previamente validados. Si la cobertura de una
variable clave es insuficiente, se limita el análisis que depende de ella, sin
detener los análisis que sí pueden realizarse.

### 8.2 Criterios mínimos de validación

- **Trazabilidad:** cada cifra del informe debe poder reproducirse desde los
  datos y quedar etiquetada con `fecha_captura`.
- **Tamaño de muestra:** reportar siempre `n` por grupo; todo grupo por debajo
  del umbral mínimo (a fijar explícitamente antes de interpretar) se marca como
  "muestra insuficiente" y no se interpreta.
- **Cobertura:** informar el porcentaje de valores no nulos de cada variable
  clave (`municipio`, `area_m2`, `precio_usd`) antes de usarla.
- **Duplicados:** repetir los estadísticos principales con y sin duplicados
  marcados y comprobar que las conclusiones no dependen de esa decisión.
- **Calidad de parseo:** excluir o marcar `estado_parseo = error`; revisar
  `notas_calidad`.
- **Reproducibilidad:** documentar filtros, fechas y supuestos para que otra
  persona obtenga el mismo resultado.
- **Sin inventos:** ningún valor imputado ni estimado a ojo; lo no calculable se
  declara como tal.

Los umbrales numéricos concretos (mínimo de `n`, cobertura mínima, periodicidad
de tasas) son **decisiones pendientes** y deben fijarse y registrarse antes de
interpretar resultados.

---

## 9. Decisiones pendientes

Recogidas también en `docs/decisiones.md` §6; se listan aquí por su impacto en el
análisis:

1. **Fuente y metodología de la tasa de cambio** a USD (oficial vs. informal) y
   su fecha de vigencia: bloquea `precio_usd`, el precio por m² en USD y toda
   comparación con salarios en USD.
2. **Referente salarial exacto** dentro de la Resolución 14, su período, y cómo
   se presentan los tres referentes (mínimo, escalas por oficio, medio).
3. **Lista canónica de municipios** de La Habana y reglas de mapeo desde texto
   libre.
4. **Criterio de `area_m2`** (total / construcción / parcela).
5. **Alcance del dataset:** solo venta o también alquiler; período y tamaño de
   muestra.
6. **Política de duplicados aplicada al análisis** (¿se incluyen los marcados?).
7. **Umbrales de validación** (§8.2) y uso o no de `spaCy` sobre `descripcion`.

---

## 10. Requisitos de autorización antes de automatizar la extracción de Revolico

Antes de cualquier extracción automatizada de anuncios de Revolico deben
verificarse y quedar documentados los siguientes puntos (ninguno se da por
resuelto aquí):

1. **Condiciones de uso aplicables:** revisar los términos de
   `https://help.revolico.com/es/articles/7263759-condiciones-de-uso` y
   confirmar si **permiten** la recolección automatizada. Tal como se registró en
   `docs/decisiones.md` (§8.1), **no** constituyen un permiso explícito.
2. **Alcance de `robots.txt`:** recordar que `robots.txt` permisivo **no**
   equivale a autorización de scraping (`docs/decisiones.md` §10) y que deben
   revisarse además los términos de uso.
3. **Autorización expresa** del titular del portal cuando el uso pretendido no
   esté cubierto por los términos.
4. **Límites de acceso:** respetar `Crawl-delay` si la fuente lo declara,
   peticiones moderadas, `User-Agent` identificable, no eludir CAPTCHA ni
   autenticación.
5. **Datos personales:** excluir teléfonos y nombres de los anuncios durante el
   parseo (`docs/decisiones.md` §9).
6. **Volumen y finalidad:** al ser un trabajo académico, limitar el volumen y no
   redistribuir datos personales ni el contenido íntegro de los anuncios.

Mientras estos puntos no estén resueltos, la extracción de Revolico **no** se
automatiza.

---

## 11. Registro de cambios

- Versión inicial: traducción de las preguntas del proyecto a un plan de
  análisis, con variables, cálculos, tratamiento de datos ausentes, comparación
  con salarios, definición de inmueble típico, limitaciones, orden de
  implementación, validación, decisiones pendientes y requisitos de autorización
  para Revolico.
