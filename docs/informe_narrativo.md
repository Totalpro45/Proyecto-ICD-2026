# ¿Es asequible el precio de la vivienda para el cubano promedio?
## Estudio de caso: La Habana

**Proyecto académico — Introducción a la Ciencia de Datos (ICD 2026)**

---

### 1. Introducción

Este proyecto analiza si el precio de la vivienda en La Habana es asequible para el cubano promedio, a partir de anuncios publicados en portales inmobiliarios y tasas de cambio. El caso de estudio se centra en La Habana y utiliza anuncios de venta de casas y apartamentos publicados en GAOS y Revolico.

El objetivo principal es responder a cinco preguntas concretas:

1. ¿Cuánto cuesta una casa en La Habana?
2. ¿Cuánto cuesta un apartamento en La Habana?
3. ¿Cómo se distribuyen los precios de las viviendas entre los municipios de La Habana?
4. ¿Qué características aparecen con mayor frecuencia en los anuncios cuyo precio supera la mediana?
5. ¿Cuál es el inmueble más representativo de los anuncios analizados y cómo se compara su precio con el salario mínimo legal?

El trabajo se enmarca en la asignatura Introducción a la Ciencia de Datos, primer año de Ciencias de Datos. No es una aplicación comercial ni un servicio web: es un proyecto de análisis de datos con fines exclusivamente académicos.

Los precios analizados son **precios anunciados**, no precios finales de compraventa. Esa diferencia se mantiene a lo largo de todo el documento.

---

### 2. Contexto del mercado inmobiliario cubano

Durante casi medio siglo, la compraventa de viviendas en Cuba estuvo limitada legalmente y muchas operaciones se realizaban mediante mecanismos como las donaciones y las permutas. Esta situación cambió en noviembre de 2011, cuando se modificó la Ley General de la Vivienda mediante el Decreto-Ley 288 y sus disposiciones complementarias, legalizando la compraventa de viviendas entre ciudadanos cubanos y extranjeros con residencia permanente [1].

Tras este cambio, el mercado experimentó un crecimiento importante. Según una especialista del Registro de la Propiedad del Ministerio de Justicia, citada en el estudio *Mercado inmobiliario en Cuba: algunos indicios y consideraciones*, a finales de 2013 se estimaban unas 80 000 transacciones, el doble de las registradas el año anterior [2]. Sin embargo, no existía un instrumento público que permitiera medir adecuadamente su comportamiento, por lo que los investigadores recurrieron a los anuncios publicados en sitios de clasificados como Porlalivre, Revolico y Cubisima [2].

La apertura del mercado coincidió con una situación habitacional compleja. Aunque el Censo de 2012 registró aproximadamente tres personas por vivienda y una relación cercana a un hogar por inmueble, estas cifras no reflejaban completamente las necesidades de la población [3]. En el país existían alrededor de 54 000 hogares agregados, es decir, hogares que compartían vivienda con otros, y el déficit estimado aumentaba hasta unos 170 000 inmuebles al excluir las cuarterías, los bohíos y las viviendas improvisadas [2]. A esto se sumaban los daños ocasionados por fenómenos meteorológicos y el deterioro acumulado del fondo habitacional [2].

En cuanto al comportamiento de los precios, el estudio analizó 15 387 anuncios de Porlalivre publicados entre agosto y diciembre de 2013 [2]. La mediana nacional se situaba alrededor de los 22 000 CUC, mientras que para La Habana alcanzaba aproximadamente los 24 000 CUC [2]. Los autores señalaron que estos precios superaban ampliamente la capacidad adquisitiva de buena parte de la población [2]. Según los datos salariales utilizados en la investigación, el salario medio mensual rondaba los 20 CUC [2], mientras que el acceso al crédito hipotecario era prácticamente inexistente [2].

Estos precios de 2013, expresados en CUC, pertenecen a un contexto monetario distinto al actual y no pueden compararse directamente con los precios en USD registrados en el presente estudio.

El estudio también describió una diferencia entre los perfiles económicos de compradores y vendedores. Entre los primeros destacaban personas con acceso a remesas, ahorros procedentes de contratos en el exterior o capital para invertir, mientras que entre los vendedores aparecían quienes necesitaban financiar otros proyectos, emigraban o no podían mantener sus viviendas. Esto llevó a los autores a señalar que quienes tenían mayores necesidades habitacionales no necesariamente contaban con los recursos para adquirir una vivienda.

La Habana presentaba características particulares dentro de este mercado: era el principal destino y la provincia más ofertada, y su mediana de precios se situaba en torno a los 24.000 CUC, frente a los 22.000 CUC de la mediana nacional [2]. Estas diferencias territoriales constituyen un antecedente importante para estudiar el comportamiento de los precios dentro de la capital.

#### Evolución demográfica de Cuba y La Habana (2012-2025)

La evolución demográfica constituye otro elemento de contexto para comprender la situación actual de la vivienda. Los datos del Censo de 2012 y de los Anuarios Estadísticos de la ONEI permiten observar cambios importantes en la población cubana durante los años posteriores.

A escala nacional, la población pasó de aproximadamente 11,17 millones de habitantes en 2012 a 9,43 millones en 2025, según la cifra de población efectiva recogida en el AEC 2025 [4]. Este comportamiento estuvo acompañado por una disminución de los nacimientos, un aumento de las defunciones y un saldo migratorio externo negativo. Asimismo, la proporción de personas de 60 años y más aumentó al 26,7 %, reflejando el progresivo envejecimiento de la población [4].

En La Habana estos cambios también fueron significativos. La población registrada pasó de 2 106 146 habitantes en 2012 a 1 673 208 en 2025 [4]. Paralelamente, la proporción de personas de 60 años y más aumentó al 29,08 %, un cálculo propio a partir de los grupos de edad del AEC 2025 [4]. La capital también presentó un saldo migratorio externo negativo, aunque continuó recibiendo población de otras provincias mediante la migración interna.

Estos cambios permiten contextualizar la transformación demográfica de la capital y del país durante el período estudiado. No obstante, deben interpretarse teniendo en cuenta que las cifras de 2012 proceden del Censo de Población y Viviendas [3], mientras que los datos posteriores corresponden a estimaciones y registros estadísticos de la ONEI [4]. Además, desde 2021 se utiliza el concepto de población efectiva, lo que introduce diferencias metodológicas respecto a las cifras de población residente de años anteriores [4].

La disminución de la población plantea una interrogante: si cada vez hay menos habitantes, ¿por qué esto no se traduce necesariamente en una reducción de los precios de las viviendas? ¿Existe alguna relación observable entre la evolución demográfica y el comportamiento de los precios inmobiliarios? Aunque ambos fenómenos pueden estar relacionados, su evolución también depende de otros factores, por lo que resulta necesario analizar los datos del mercado antes de establecer cualquier relación.

#### Situación económica y monetaria actual

Para estudiar la asequibilidad de la vivienda no basta con conocer los salarios nominales: también es necesario considerar la evolución del poder adquisitivo del peso cubano y los distintos tipos de cambio existentes. Esta cuestión resulta especialmente importante porque los precios inmobiliarios pueden expresarse en divisas, mientras que los ingresos salariales se reciben principalmente en CUP.

Uno de los principales cambios monetarios recientes ocurrió el 1 de enero de 2021, con el inicio de la Tarea Ordenamiento, establecida mediante el Decreto-Ley 17 de 2020 [5]. El proceso implicó la retirada del peso convertible y la unificación monetaria y cambiaria, con una tasa inicial de 24 CUP por USD [5]. El salario mínimo quedó establecido en 2 100 CUP mensuales [5], cifra distinta al salario mínimo de 3 210 CUP utilizado en el análisis actual de este proyecto.

Sin embargo, posteriormente se mantuvo una diferencia entre la tasa oficial vigente entonces y las cotizaciones del mercado informal. En este contexto, el medio elTOQUE comenzó a registrar desde enero de 2021 una referencia de la cotización informal de las divisas [6], calculada a partir de la mediana de los valores publicados en anuncios de compraventa. Aunque no constituye una tasa oficial, esta referencia permite observar el comportamiento de un mercado que adquirió relevancia ante la diferencia entre las cotizaciones oficiales y las informales.

En agosto de 2022, el Gobierno estableció una tasa de 120 CUP por USD para determinadas operaciones con personas naturales y otros actores económicos [5], mientras que la tasa de 24 CUP se mantuvo para personas jurídicas [5]. Posteriormente, el Banco Central de Cuba estableció un nuevo mercado cambiario compuesto por tres segmentos: dos con tasas fijas de 24 y 120 CUP por USD, y un tercer segmento cuya tasa se publica diariamente [7].

La coexistencia de estas referencias cambiarias hace necesario distinguirlas al estudiar los precios de las viviendas y su relación con los ingresos de la población. Por ello, este proyecto considera tanto las tasas oficiales como las referencias del mercado informal para analizar distintos escenarios de conversión y aproximarse a la capacidad adquisitiva frente a los precios anunciados.

El proyecto conserva ambas referencias por separado, cada una con su procedencia y su fecha, y no las mezcla ni las promedia: la **tasa especial del Segmento III**, publicada por el Banco Central de Cuba (BCC) [7], y la **tasa del mercado informal**, documentada por el medio de prensa elTOQUE [6].

En cuanto al marco regulatorio, el proyecto menciona el **Decreto-Ley 17 de 2020** como parte del contexto monetario [5], y la **Resolución 15/2026** de la Gaceta Oficial Ordinaria No. 60 (2026) como fuente de datos salariales de referencia [10]. Estos documentos no se han desarrollado en detalle en la documentación existente, por lo que no se citan artículos concretos.

---

### 3. Fuentes de datos y metodología

#### 3.1 Fuentes de anuncios

Los anuncios utilizados provienen de dos portales inmobiliarios:

- **GAOS** — portal con extracción implementada mediante el Edge Function de Supabase.
- **Revolico** — portal con extracción implementada.

Ambos portales presentan restricciones de acceso en pruebas de acceso directo, por lo que la recopilación de datos está sujeta a estas limitaciones técnicas. Mambbu y CasasOasis fueron identificadas como fuentes candidatas, pero no se utilizaron en el análisis actual: Mambbu por prohibición de extracción automatizada en sus términos de uso, y CasasOasis por exclusión deliberada mientras no exista autorización expresa.

#### 3.2 Proceso de recopilación y tratamiento

Cada anuncio se transforma a un **esquema de datos común** que permite consolidar y comparar la información procedente de diferentes fuentes. El esquema incluye campos de trazabilidad, ubicación, características del inmueble, precio y moneda, y campos de calidad de los datos.

Las capturas crudas y procesadas se guardan por fuente en carpetas independientes (`data/raw/anuncios/<fuente>/crudo/` y `data/processed/anuncios/<fuente>/`). Un módulo de unificación combina las capturas de diferentes fuentes en un único archivo JSON, añadiendo el campo `fuente` a cada anuncio para identificar su procedencia, sin modificar los archivos originales.

#### 3.3 Alcance geográfico y tipo de anuncios

El estudio se limita a **La Habana** y a anuncios de **venta** (`tipo_operacion = venta`). Los tipos de inmueble analizados son **casa** y **apartamento**, tratados por separado en todos los cálculos. Otros tipos (`indeterminado`, `no_vivienda`, `habitacion`, `solar`) no se incluyen en el análisis principal.

#### 3.4 Variables utilizadas

Las variables principales utilizadas en el análisis son:

- `tipo_inmueble` — para separar casas y apartamentos.
- `moneda` — para filtrar anuncios en USD.
- `precio` — valor numérico original en la moneda declarada.
- `habitaciones` — número de habitaciones declarado.
- `banos` — número de baños declarado.
- `municipio` — para agrupación territorial (con cobertura limitada).

#### 3.5 Limitaciones de cobertura y calidad

Los datos presentan varias limitaciones que deben tenerse en cuenta:

- **Cobertura incompleta:** no todos los anuncios tienen información sobre todas las características. Por ejemplo, en las casas en USD solo el 69,1 % informa habitaciones y el 66,4 % informa baños.
- **Datos ausentes:** los campos vacíos se conservan como `null`; no se imputan ni se inventan valores.
- **Precios anunciados:** los precios son los publicados en los anuncios, no precios de transacción realizada.
- **Posibles duplicados:** el esquema incluye campos para detectar posibles duplicados (`es_posible_duplicado`, `duplicado_grupo`), pero no se elimina información automáticamente.
- **Identificación de municipios:** la identificación de municipios a partir de texto libre tiene cobertura limitada; los casos ambiguos o contradictorios no reciben asignación municipal, por lo que parte de los anuncios queda sin municipio y los resultados municipales deben interpretarse con cautela.
- **Cobertura de superficie:** el campo `area_m2` está disponible en menos de un tercio de los anuncios y `tipo_area` tampoco está identificado, lo que impide calcular precios por metro cuadrado como análisis general del proyecto.

#### 3.6 Uso diferenciado de las tasas de elTOQUE y BCC

El proyecto dispone de un sistema de tasas de cambio que consulta dos fuentes independientes:

- **elTOQUE** — mercado informal, con autenticación mediante clave API [6].
- **BCC** — tasa especial del Banco Central de Cuba, Segmento III («Tasa Población y FGNE») [7].

Las cotizaciones de ambas fuentes se guardan en el mismo historial (`data/raw/exchange_rates/historial_tasas.json`), pero **no se mezclan ni se promedian**. Cada fuente mantiene su categoría (`mercado_informal` para elTOQUE, `oficial` para BCC) y su segmento cuando aplica. En el análisis actual se utilizan las cotizaciones registradas en el historial local con fecha 16/11/2026: la de elTOQUE [6] y la del BCC, obtenida de la API oficial [8], ambas identificadas por fuente y categoría.

---

### 4. Análisis de resultados

Los resultados se presentan a continuación siguiendo las cinco preguntas implementadas en el notebook `notebooks/analisis_vivienda.ipynb`.

#### 4.1 Precio de las casas

Se analizaron los anuncios de casas en La Habana con precio válido registrado en dólares estadounidenses (USD). Se obtuvieron **148 anuncios** de este tipo, tras excluir un registro sospechoso de 90 USD.

| Estadístico | Valor |
|---|---:|
| Anuncios con precio válido en USD | 148 |
| Mínimo | 2 300 USD |
| Máximo | 600 000 USD |
| Promedio | 59 139,53 USD |
| Mediana | 31 000 USD |

La **mediana** de precio es de **31.000 USD**. Esto significa que la mitad de las casas anunciadas en USD con precio válido tienen un precio igual o inferior a 31.000 USD, y la otra mitad tiene un precio igual o superior.

El **promedio** es de 59 139,53 USD, un valor superior a la mediana debido a la influencia de precios muy elevados que tiran el promedio hacia arriba. Por esta razón, la mediana es una medida más representativa del precio típico de una casa anunciada en USD que el promedio, que se ve distorsionado por los valores extremos.

Es importante destacar que este resultado se refiere únicamente a precios anunciados en USD y no incluye los anuncios publicados en otras monedas (por ejemplo, EUR), los cuales no se convierten ni se mezclan con los de USD. Si se incluye el registro sospechoso de 90 USD, la base es de 149 anuncios y la mediana desciende a 30.000 USD; ese es el escenario de sensibilidad de §4.5, no el resultado principal.

#### 4.2 Precio de los apartamentos

Se analizaron los anuncios de apartamentos en La Habana con precio válido registrado en dólares estadounidenses (USD). Se obtuvieron **110 anuncios** de este tipo, tras excluir dos registros sospechosos de 5 y 5,5 USD.

| Estadístico | Valor |
|---|---:|
| Anuncios con precio válido en USD | 110 |
| Mínimo | 1 500 USD |
| Máximo | 180 000 USD |
| Promedio | 26 922,73 USD |
| Mediana | 15 000 USD |

La **mediana** de precio es de **15.000 USD**. Esto significa que la mitad de los apartamentos anunciados en USD con precio válido tienen un precio igual o inferior a 15.000 USD, y la otra mitad tiene un precio igual o superior.

El **promedio** es de 26 922,73 USD, un valor superior a la mediana debido a la influencia de precios muy elevados. Como en el caso de las casas, la mediana es una medida más representativa del precio típico de un apartamento anunciado en USD que el promedio, que se ve afectado por los valores extremos.

Al igual que en el caso de las casas, este resultado se refiere exclusivamente a anuncios en USD y no incluye los anuncios publicados en otras monedas. Si se incluyen los dos registros sospechosos, la base es de 112 anuncios y la mediana se mantiene en 15.000 USD; ese escenario no sustituye al resultado principal.

#### 4.3 Distribución de precios por municipio

El análisis por municipio presenta limitaciones importantes:

- De los 307 anuncios totales, 187 tienen municipio identificado (60,91 %); los 120 restantes no lo tienen.
- De esos 187 anuncios con municipio, 183 corresponden a casas o apartamentos: 103 casas y 80 apartamentos. Los otros 4 son 3 registros de tipo indeterminado y 1 sin tipo identificado; no se afirma que no sean viviendas, pero no pueden clasificarse como casa ni como apartamento.
- De las 183 casas y apartamentos con municipio, 179 tienen un precio numérico en USD. De ellos, 176 son válidos y 3 están marcados como sospechosos en el registro de incidencias de precio del notebook (sección 6.1): una casa de 90 USD y dos apartamentos de 5 y 5,5 USD. Los 4 restantes no tienen un precio utilizable en USD: tres anuncios están denominados en EUR (dos con importe y uno sin importe) y un anuncio está denominado en USD sin importe.
- La cobertura municipal depende principalmente de GAOS, que identifica municipio en el 81,5 % de sus anuncios, mientras que Revolico solo lo hace en el 22,4 %.

**Qué base utiliza la tabla.** La tabla siguiente incluye únicamente las **176 viviendas con municipio y precio válido en USD**: 98 casas y 78 apartamentos. Este subconjunto no debe confundirse con la base principal de precios válidos de las secciones 4.1 y 4.2, que reúne 148 casas y 110 apartamentos, es decir, 258 viviendas. La diferencia son los 82 anuncios válidos que no tienen municipio identificado: 50 casas y 32 apartamentos. Por tanto, 176 + 82 = 258: ambas bases son correctas, pero responden a preguntas distintas.

| Municipio | Casas (n) | Mediana casas (USD) | Apartamentos (n) | Mediana apartamentos (USD) | Total (n) |
|---|---:|---:|---:|---:|---:|
| Plaza de la Revolución | 12 | 61 500 | 22 | 35 000 | 34 |
| Playa | 17 | 70 000 | 7 | 24 000 | 24 |
| Centro Habana | 4 † | 16 500 | 12 | 13 000 | 16 |
| La Habana del Este | 10 | 67 500 | 5 | 18 500 | 15 |
| La Lisa | 5 | 30 000 | 8 | 8 000 | 13 |
| Boyeros | 9 | 80 000 | 2 † | 16 000 | 11 |
| Marianao | 7 | 17 000 | 4 † | 9 500 | 11 |
| Arroyo Naranjo | 7 | 5 000 | 2 † | 13 000 | 9 |
| Diez de Octubre | 6 | 16 500 | 3 † | 12 000 | 9 |
| Habana Vieja | 3 † | 20 000 | 5 | 15 000 | 8 |
| San Miguel del Padrón | 6 | 6 250 | 1 † | 3 000 | 7 |
| Cerro | 2 † | 17 500 | 4 † | 12 000 | 6 |
| Guanabacoa | 4 † | 42 500 | 2 † | 3 750 | 6 |
| Cotorro | 3 † | 14 000 | 1 † | 11 000 | 4 |
| Regla | 3 † | 15 000 | 0 † | — | 3 |
| **Total** | **98** | — | **78** | — | **176** |

El símbolo † indica que la columna correspondiente tiene menos de cinco observaciones. Esos valores se muestran por transparencia, pero no se interpretan: con ese número de anuncios una mediana puede variar mucho ante un solo registro distinto. Con este criterio quedan marcados 6 municipios en casas, que reúnen 19 de las 98 casas, y 8 municipios que tienen entre 1 y 4 apartamentos, que reúnen 19 de los 78. Regla aparece adicionalmente con 0 apartamentos y sin mediana. Cotorro y Regla se mantienen en la tabla con esa advertencia en lugar de excluirlos.

Debido a estas limitaciones, cualquier comparación de precios entre municipios debe interpretarse con cautela y solo para los municipios con suficiente cantidad de anuncios. La tabla no pretende ser una clasificación definitiva de los precios de toda La Habana, sino una descripción de la muestra disponible.

#### 4.4 Características de los inmuebles según su precio, por encima o por debajo de la mediana

Se separaron los anuncios de casas y apartamentos en dos grupos: aquellos con precio superior a la mediana y aquellos con precio igual o inferior. La clasificación utiliza todos los anuncios con precio en USD (149 casas y 112 apartamentos), con cortes en 30.000 y 15.000 USD respectivamente. Es la misma base de las frecuencias de habitaciones y baños de §4.5 y no debe confundirse con la base principal de precios válidos de esa sección (148 casas y 110 apartamentos). Luego se comparó la distribución de habitaciones y baños entre ambos grupos. Los porcentajes se calculan solo sobre los anuncios que tienen información disponible para cada variable.

**Casas por encima de la mediana (más de 30.000 USD):**
- Total: 74 anuncios.
- De estos, 48 informan habitaciones y 26 no.
- Distribución de habitaciones (sobre los que informan): 2 habitaciones (16,7 %), 3 habitaciones (27,1 %), 4 habitaciones (25,0 %), 5 habitaciones (14,6 %), 6 habitaciones (8,3 %), 7 habitaciones (4,2 %), 8 habitaciones (2,1 %), 10 habitaciones (2,1 %).
- 48 informan baños y 26 no.
- Distribución de baños: 1 baño (22,9 %), 2 baños (31,3 %), 3 baños (31,3 %), 4 baños (2,1 %), 6 baños (4,2 %), 7 baños (6,3 %), 8 baños (2,1 %).

**Casas igual o inferior a la mediana (30.000 USD o menos):**
- Total: 75 anuncios.
- 55 informan habitaciones y 20 no.
- Distribución de habitaciones: 1 habitación (14,5 %), 2 habitaciones (36,4 %), 3 habitaciones (32,7 %), 4 habitaciones (12,7 %), 5 habitaciones (3,6 %).
- 51 informan baños y 24 no.
- Distribución de baños: 1 baño (62,7 %), 2 baños (27,5 %), 3 baños (5,9 %), 4 baños (2,0 %), 5 baños (2,0 %).

**Apartamentos por encima de la mediana (más de 15.000 USD):**
- Total: 54 anuncios.
- 40 informan habitaciones y 14 no.
- Distribución de habitaciones: 1 habitación (15,0 %), 2 habitaciones (45,0 %), 3 habitaciones (27,5 %), 4 habitaciones (10,0 %), 5 habitaciones (2,5 %).
- 40 informan baños y 14 no.
- Distribución de baños: 1 baño (62,5 %), 2 baños (30,0 %), 3 baños (5,0 %), 4 baños (2,5 %).

**Apartamentos igual o inferior a la mediana (15.000 USD o menos):**
- Total: 58 anuncios.
- 48 informan habitaciones y 10 no.
- Distribución de habitaciones: 1 habitación (25,0 %), 2 habitaciones (47,9 %), 3 habitaciones (27,1 %).
- 43 informan baños y 15 no.
- Distribución de baños: 1 baño (90,7 %), 2 baños (9,3 %).

**Interpretación:** en ambos tipos de vivienda, los anuncios por encima de la mediana tienden a mostrar más habitaciones y más baños que los anuncios por debajo o iguales a la mediana. Sin embargo, estos resultados son **descriptivos y no implican una relación de causalidad**: tener más habitaciones o baños no implica necesariamente un precio más alto, ya que otros factores no disponibles en los datos (ubicación exacta, estado de conservación, acabados, etc.) también influyen en el precio. Además, varias categorías tienen muy pocos anuncios, por lo que no se deben sacar conclusiones firmes basadas en esos casos aislados.

#### 4.5 Inmueble más representativo y comparación con el salario mínimo legal

**Inmueble representativo:**

De los 267 inmuebles clasificados como casa o apartamento en la muestra total, **las casas son el tipo de inmueble más frecuente**:

| Tipo de inmueble | Cantidad | Porcentaje |
|---|---:|---:|
| Casa | 154 | 57,7 % |
| Apartamento | 113 | 42,3 % |

Es importante distinguir estos conteos de los utilizados en el análisis de precios. Las medianas principales se calculan sobre los anuncios con precio válido en USD: **148 casas y 110 apartamentos**. Las frecuencias de habitaciones y baños que se presentan a continuación, en cambio, se calculan sobre todos los anuncios con precio numérico en USD (149 casas y 112 apartamentos), porque describen el conjunto de anuncios disponibles y no solo el subconjunto con precios no marcados.

Para identificar el inmueble más representativo, se analizaron las características más frecuentes por separado en casas y apartamentos, utilizando solo los anuncios con precio en USD.

**Casas (149 anuncios en USD):**
- Habitaciones más frecuente: **3 habitaciones** (31 anuncios, el 30,1 % de los 103 que informan este dato; 46 anuncios no informan habitaciones).
- Baños más frecuente: **1 baño** (43 anuncios, el 43,4 % de los 99 que informan este dato; 50 anuncios no informan baños).

**Apartamentos (112 anuncios en USD):**
- Habitaciones más frecuente: **2 habitaciones** (41 anuncios, el 46,6 % de los 88 que informan este dato; 24 anuncios no informan habitaciones).
- Baños más frecuente: **1 baño** (64 anuncios, el 77,1 % de los 83 que informan este dato; 29 anuncios no informan baños).

**Nota metodológica:** estas son frecuencias individuales por característica. No se puede afirmar que exista una combinación de habitaciones y baños que represente a la mayoría de los inmuebles, ya que los datos no permiten identificar una combinación simultánea mayoritaria. Por ejemplo, en las casas solo 99 de 149 tienen ambos datos, y la combinación más frecuente (2 habitaciones y 1 baño) representa solo el 21,2 % de los que tienen ambos datos.

**Medianas de referencia para la comparación salarial:** la mediana principal de las casas es de **31.000 USD** (148 anuncios válidos) y la de los apartamentos, de **15.000 USD** (110 anuncios válidos). Para las casas se conserva además la mediana de **30.000 USD** de los 149 anuncios con precio en USD, que incluye el registro sospechoso de 90 USD, como escenario de sensibilidad. La diferencia entre ambos valores no es un error de cálculo: con 149 valores la mediana es un único valor central (30.000 USD) y, al retirar el mínimo de 90 USD, los 148 restantes dejan dos valores centrales (30.000 y 32.000 USD) cuyo promedio es 31.000 USD. Cambia la base y la posición central, no la aritmética. En apartamentos la mediana es 15.000 USD en ambas bases, porque los dos valores descartados son los mínimos y no alteran los valores centrales.

**Comparación con el salario mínimo legal:**

Las medianas principales se comparan con el salario mínimo legal mensual de **3.210 CUP [9]**, vigente desde el 1 de julio de 2026, en dos escenarios de tasa de cambio del 16 de noviembre de 2026. Se trata del **salario mínimo**, no de un salario promedio nacional: el proyecto no dispone de una fuente documentada de salario medio, por lo que la comparación describe a una persona que percibe el mínimo legal y no al conjunto de la población. La Resolución 15/2026 fija la escala del sector presupuestado [10]; el valor de 2.920 CUP del Grupo I a 40 horas no es el salario mínimo y no se usa en estos cálculos.

**Resultados principales:**

| Tipo | Anuncios válidos | Mediana (USD) | Tasa (CUP/USD) | Equivalencia en CUP | Meses de salario íntegro | Años de salario íntegro |
|---|---:|---:|---|---:|---:|---:|
| Casas | 148 | 31.000 | elTOQUE 925,0 | 28.675.000 | 8.933,0 | 744,4 |
| Casas | 148 | 31.000 | BCC 832,0 | 25.792.000 | 8.034,9 | 669,6 |
| Apartamentos | 110 | 15.000 | elTOQUE 925,0 | 13.875.000 | 4.322,4 | 360,2 |
| Apartamentos | 110 | 15.000 | BCC 832,0 | 12.480.000 | 3.887,9 | 324,0 |

**Escenario de sensibilidad (solo casas):** se añade la mediana de los 149 anuncios con precio en USD, incluido el registro sospechoso de 90 USD. No sustituye a los resultados principales y no se aplica a los apartamentos, cuya mediana no cambia entre bases.

| Base | Anuncios | Mediana (USD) | Tasa (CUP/USD) | Equivalencia en CUP | Meses de salario íntegro | Años de salario íntegro |
|---|---:|---:|---|---:|---:|---:|
| Casas, todos los anuncios en USD | 149 | 30.000 | elTOQUE 925,0 | 27.750.000 | 8.644,9 | 720,4 |
| Casas, todos los anuncios en USD | 149 | 30.000 | BCC 832,0 | 24.960.000 | 7.775,7 | 648,0 |

**Fórmula utilizada:** `(mediana × tasa USD/CUP) / 3.210`

**Fuentes:**
- Salario mínimo legal: dato normativo externo (3.210 CUP mensuales, Resolución 14/2026 de la Gaceta Oficial Ordinaria No. 60, 2026) [9].
- elTOQUE: 925 CUP/USD, 16/11/2026, categoría `mercado_informal`, tomada del historial local de tasas de cambio [6].
- BCC: 832 CUP/USD, 16/11/2026, `tasa_especial` del Segmento III («Tasa Población y FGNE»), categoría `oficial`, tomada de ese mismo historial, que la obtiene de la API oficial [8]. La identificación del segmento se apoya en la información oficial consultada [7]; la respuesta JSON de la API no incluye una etiqueta explícita de segmento. Esta tasa no representa por sí sola todas las tasas oficiales del BCC.

**Sobre la fecha de las tasas:** los anuncios se capturaron el 15/11/2026, pero las tasas corresponden al 16/11/2026. Se eligió esa fecha porque es la primera del historial en la que ambas fuentes están identificadas. El registro de elTOQUE del 15/11/2026 (920 CUP/USD) tiene `fuente` y `categoria` nulas, por lo que no puede atribuirse con seguridad, y el BCC no tiene registro ese día.

**Advertencia importante:** este cálculo es una **equivalencia hipotética** que supone destinar el 100 % del salario mínimo a comprar la vivienda durante todos esos meses o años. No representa el tiempo real necesario para comprarla, pues no considera gastos de vida, ahorro parcial, financiación, remesas, múltiples empleos, bonificaciones ni otras fuentes de ingresos. El salario de 3.210 CUP es una referencia normativa nacional, no un salario específico de La Habana ni un salario promedio. Los precios son los anunciados y no necesariamente los precios finales de transacción, y las medianas describen la muestra de anuncios válidos, no la totalidad del mercado habanero. Las dos tasas se aplican por separado y no se promedian. Además, las tasas corresponden al 16/11/2026 y no representan necesariamente la situación de otras fechas.

---

### 5. Conclusiones

Los resultados del análisis permiten responder, de forma parcial y con las limitaciones señaladas, a la pregunta principal del proyecto:

**¿Es asequible el precio de la vivienda para el cubano promedio?**

Los datos no permiten determinar directamente la asequibilidad para el cubano promedio: el proyecto no dispone de una fuente documentada de salario medio nacional. Lo que sí puede medirse es la distancia entre los precios anunciados y el salario mínimo legal. En la muestra de anuncios en USD analizada, la mediana de precio de una casa es de 31.000 USD (148 anuncios con precios válidos) y la de un apartamento es de 15.000 USD (110 anuncios con precios válidos).

Comparadas con el salario mínimo legal de 3.210 CUP mensuales [9], establecido por la Resolución 14/2026, esas medianas equivalen a varios siglos de salario íntegro. En las casas, el equivalente es de 8.034,9 meses (unos 669,6 años) con la tasa especial del Segmento III del BCC (832 CUP/USD) y de 8.933,0 meses (unos 744,4 años) con la tasa informal de elTOQUE (925 CUP/USD). En los apartamentos la equivalencia es menor, pero igualmente extensa: 3.887,9 meses (unos 324,0 años) con el BCC y 4.322,4 meses (unos 360,2 años) con elTOQUE.

Como escenario de sensibilidad se conserva la mediana de 30.000 USD de los 149 anuncios de casas con precio en USD, que incluye el registro sospechoso de 90 USD: 7.775,7 meses (648,0 años) con el BCC y 8.644,9 meses (720,4 años) con elTOQUE. Este escenario no sustituye a los resultados principales; solo indica cuánto cambian las equivalencias al ampliar la base de casas.

Estas cifras son una equivalencia hipotética y no el tiempo real que necesitaría una persona para comprar una vivienda. Suponen destinar el 100 % del salario mínimo a ese fin, sin gastos de vida ni otras obligaciones, durante más de seis siglos en el caso de las casas y más de tres en el de los apartamentos. Se basan en precios anunciados, no en precios de transacción, y en una muestra que no representa necesariamente todo el mercado habanero. Por eso la conclusión debe leerse en sus términos: para quien percibe el salario mínimo legal, los precios anunciados quedan muy lejos de un ahorro posible; los resultados no permiten afirmar que esa sea la situación de todos los trabajadores cubanos ni de todos los hogares, ni medir la asequibilidad del mercado en su conjunto.

**Lo que los datos muestran:**
- En la muestra de anuncios en USD analizada, el precio mediano es de 31.000 USD para las casas (148 anuncios válidos) y de 15.000 USD para los apartamentos (110 anuncios válidos).
- Las características más frecuentes varían entre casas y apartamentos.
- La brecha entre los precios anunciados y el salario mínimo legal es muy grande en ambos escenarios de tasa de cambio.

**Lo que los datos no permiten afirmar:**
- Que los precios anunciados sean los precios reales de compraventa.
- Que los anuncios analizados representen todo el mercado inmobiliario de La Habana ni de Cuba.
- Que las características identificadas (número de habitaciones o baños) causen o expliquen los precios observados.
- Que la comparación salarial refleje la capacidad real de ahorro o acceso a vivienda de la población.

---

### 6. Limitaciones del estudio

Las limitaciones más relevantes del proyecto son:

1. **Naturaleza de los precios:** los precios son anunciados, no precios de transacción realizada. Pueden diferir de los precios finales de negociación.
2. **Cobertura de la muestra:** los anuncios provienen de GAOS y Revolico y no representan necesariamente todo el mercado inmobiliario de La Habana ni de Cuba. Algunos municipios tienen muy pocos anuncios.
3. **Datos ausentes:** una proporción significativa de anuncios no informa características como habitaciones, baños, área o municipio. Los porcentajes se calculan solo sobre los anuncios que tienen dato.
4. **Sin causalidad:** no se establece relación causal entre características del inmueble y su precio. Los resultados son descriptivos.
5. **Tasas de cambio:** las tasas utilizadas corresponden al 16/11/2026 y pueden no reflejar la situación de otras fechas. Ambas están registradas en el historial local: elTOQUE con categoría `mercado_informal` y el BCC con categoría `oficial`, tipo `tasa_especial` y segmento III. Se aplican en escenarios separados y no se promedian; la tasa del Segmento III es una de las tasas oficiales del BCC, no la única.
6. **Salario mínimo:** el salario mínimo de 3.210 CUP es un dato normativo externo (Resolución 14/2026 de la Gaceta Oficial Ordinaria No. 60, 2026) [9] y no proviene de los anuncios. No equivale al salario medio nacional y el proyecto no dispone de una fuente documentada de salario medio, por lo que la comparación describe un escenario hipotético para quien percibe el mínimo, pero no permite determinar directamente la asequibilidad para el «cubano promedio». Además, la comparación no tiene en cuenta ingresos informales, remesas ni pluriempleo.
7. **Comparación salarial hipotética:** el cálculo de meses y años de salario supone ahorrar el 100 % del salario, lo cual no es realista y no representa el tiempo real necesario para comprar una vivienda.
8. **Identificación de municipios:** la identificación se realiza a partir de texto libre y tiene cobertura limitada; los casos ambiguos o contradictorios no reciben una asignación municipal. Por ello, parte de los anuncios queda sin municipio y los resultados municipales deben interpretarse con cautela.
9. **Cobertura de superficie:** el campo `area_m2` está disponible en menos de un tercio de los anuncios (99 de 307) y el tipo de superficie (`tipo_area`) tampoco está identificado, por lo que no puede realizarse un análisis general fiable del precio por metro cuadrado.

---

*Este documento integra el trabajo realizado en el proyecto ICD 2026 y sirve como base para la memoria final. Algunos apartados del contexto del mercado inmobiliario cubano (sección 2) quedan señalados para ser completados con fuentes documentadas adicionales.*

---

### 7. Referencias bibliográficas

[1] Consejo de Estado de la República de Cuba. Decreto-Ley No. 288, modificativo de la Ley No. 65, «Ley General de la Vivienda». Gaceta Oficial Extraordinaria No. 35, 2 de noviembre de 2011. Repositorio del proyecto: `docs/referencias/go_x_035_2011.pdf`.

[2] Pérez, Elizabeth y Yudivián Almeida. “Mercado inmobiliario en Cuba: algunos indicios y consideraciones”. OnCubaNews, 3 de marzo de 2014. https://oncubanews.com/cuba/mercado-inmobiliario-en-cuba-algunos-indicios-y-consideraciones/

[3] Oficina Nacional de Estadística e Información (ONEI). Censo de Población y Viviendas 2012. Repositorio del proyecto: `docs/referencias/censo_2012.pdf`.

[4] Oficina Nacional de Estadística e Información (ONEI). Anuario Estadístico de Cuba 2025 (AEC 2025). Hoja de cálculo de población. Repositorio del proyecto: `docs/referencias/03 Poblacion_AEC2025.xlsx`.

[5] Consejo de Estado de la República de Cuba. Decreto-Ley No. 17/2020, «De la implementación del Proceso de Ordenamiento Monetario». Gaceta Oficial Extraordinaria No. 68, 10 de diciembre de 2020. Repositorio del proyecto: `docs/referencias/goc-2020-ex68.pdf`.

[6] elTOQUE. Tasas de cambio del mercado informal. Medio de prensa cubano. https://tasas.eltoque.com/ (La URL redirige a la documentación de la API; el endpoint `/v1/trmi` requiere autenticación. La documentación describe las tasas como medianas de las ofertas de compra y venta de las últimas 24 horas.)

[7] Banco Central de Cuba (BCC). Página oficial de tasas de cambio. https://www.bc.gob.cu/tasas-de-cambio

[8] Banco Central de Cuba (BCC). API de tasas de cambio activas. https://api.bc.gob.cu/v1/tasas-de-cambio/activas

[9] Ministerio de Trabajo y Seguridad Social (MTSS). Resolución 14/2026. Establece el salario mínimo nacional en 3 210 CUP mensuales. Gaceta Oficial Ordinaria No. 60 (GOC-2026-393-O60), 17 de julio de 2026, p. 1838. Repositorio del proyecto: `docs/referencias/GOC-2026-392-O60.pdf`. (Esta es la fuente legal que respalda el salario mínimo utilizado en la comparación salarial del proyecto.)

[10] Ministerio de Trabajo y Seguridad Social (MTSS). Resolución 15/2026. Escala Salarial Única del Sector Presupuestado. Aprueba las tarifas salariales para trabajadores del sector presupuestado. Gaceta Oficial Ordinaria No. 60 (GOC-2026-394-O60), 17 de julio de 2026, p. 1839. Repositorio del proyecto: `docs/referencias/GOC-2026-392-O60.pdf`. (Referencia distinta de la Resolución 14/2026; respalda los archivos de datos salariales del repositorio en `data/reference/salarios/escala_general.csv`.)
