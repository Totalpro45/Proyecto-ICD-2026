"""Limpieza y comprobación de datos personales de contacto en anuncios.

Conserva el contenido útil del anuncio (tipo de inmueble, habitaciones,
baños, área, estado, etc.) y elimina teléfonos, enlaces de WhatsApp,
correos, instrucciones de contacto y presentaciones personales que
revelan el nombre del anunciante. Solo usa la biblioteca estándar.

La limpieza se aplica antes de guardar una captura, tanto a los campos de
texto de los crudos como a los del esquema común. Los textos sin datos de
contacto se conservan exactamente iguales y no se completa ni inventa
información: si tras limpiar un texto no queda contenido útil, se guarda
como ``None``. El módulo también permite revisar archivos ya guardados sin
exponer los valores personales.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Campos de texto libre que pueden aparecer en los crudos de las fuentes.
# Incluye las claves de GAOS y las de Revolico.
CAMPOS_TEXTO_CRUDO = (
    "titulo",
    "descripcion",
    "direccion_texto",
    "notas_calidad",
    "vctitle",
    "vcaddress",
    "sdescription_eng",
    "sdescription_ita",
    "stittle_eng",
    "stittle_ita",
    "gem_reason",
)

# Campos de texto libre del esquema común que se escriben en los procesados.
CAMPOS_TEXTO_PROCESADO = (
    "titulo",
    "descripcion",
    "direccion_texto",
    "notas_calidad",
)

# Todos los campos de texto libre que puede tener un anuncio, tanto en crudo
# como en el esquema común. Se usa para revisar archivos ya guardados.
CAMPOS_TEXTO_ANUNCIO = tuple(
    dict.fromkeys(CAMPOS_TEXTO_CRUDO + CAMPOS_TEXTO_PROCESADO)
)

# Subcampos de publisher que identifican o permiten contactar al anunciante.
# Se conserva el resto (por ejemplo, accountType, que usa el mapeador).
CAMPOS_PERSONALES_PUBLISHER = ("name", "phone", "avatarUrl", "slug")

# Enlaces de WhatsApp y esquemas de contacto.
_PATRON_URL_WHATSAPP = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"(?:wa\.me|api\.whatsapp\.com|chat\.whatsapp\.com|web\.whatsapp\.com)"
    r"/[^\s,;]+",
    re.IGNORECASE,
)
_PATRON_ESQUEMA_WHATSAPP = re.compile(
    r"whatsapp://[^\s,;]+",
    re.IGNORECASE,
)

_PATRON_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

# Presentaciones personales que revelan el nombre del anunciante. Se elimina
# la frase completa junto con el nombre para no dejar texto colgando. Solo se
# incluyen formas explícitas de primera persona: instrucciones ambiguas como
# "pregunte por" o "ask for" y etiquetas como "Nombre:" o "Name:" se dejaron
# fuera porque también pueden referirse a lugares, condiciones o al título del
# anuncio. Ante la duda, se prefiere conservar el texto.
_PALABRAS_NOMBRE = (
    r"my[ \t]+name(?:'s|[ \t]+is)|name[ \t]+is|i[ \t]+am[ \t]+called|"
    r"me[ \t]+llamo|mi[ \t]+nombre[ \t]+es"
)

# Palabras que no pueden formar parte de un nombre. Se aplican a cada token,
# no solo al primero. La lista es corta y deliberada: vocabulario inmobiliario,
# conectores que abren frases y topónimos frecuentes en el corpus. No pretende
# ser exhaustiva; si un candidato no es claramente un nombre, no se elimina.
_PALABRAS_INMUEBLE = (
    r"I|A|An|The|El|La|Los|Las|Un|Una|Soy|Estoy|Es|"
    r"Casa|Casas|Apartamento|Apartamentos|Vivienda|Viviendas|Inmueble|"
    r"Inmuebles|Patio|Garaje|Garage|Terraza|Balc[oó]n|Habitaci[oó]n|"
    r"Habitaciones|Cuarto|Cuartos|Ba[nñ]o|Ba[nñ]os|Cocina|Sala|Comedor|"
    r"Piso|Solar|Lote|Finca|Local|Oficina|Edificio|Precio|Venta|Vendo|"
    r"Alquiler|Alquilo|Compra|Compro|Permuta|Permuto"
)
_PALABRAS_LUGAR = (
    r"Habana|Cuba|Vedado|Miramar|Playa|Plaza|Cerro|Marianao|Guanabacoa|"
    r"Regla|Boyeros|Cotorro|Centro|Diez|Arroyo|Naranjo|San|Guanabo|"
    r"Coj[ií]mar|Alamar|Siboney|Jaimanitas|Fontanar|Lawton|V[ií]bora|Reparto"
)
_PALABRAS_NO_NOMBRE = rf"{_PALABRAS_INMUEBLE}|{_PALABRAS_LUGAR}"

# Un nombre propio: de una a tres palabras capitalizadas. El token no incluye
# el punto ni otros signos, para no atravesar el final de una oración y
# consumir la primera palabra de la siguiente ("Ficticio. Patio").
# Limitación conocida: una inicial ("J.") se captura sola, sin el apellido que
# la sigue, para no atravesar el punto y borrar la primera palabra de la
# oración siguiente. El apellido puede quedar en el texto; se prefiere eso a
# eliminar información inmobiliaria.
_TOKEN_NOMBRE = r"[A-ZÁÉÍÓÚÜÑ][\wáéíóúüñ'’-]*"
_NOMBRE_TOKEN = rf"(?!(?:{_PALABRAS_NO_NOMBRE})\b){_TOKEN_NOMBRE}"
_CONECTOR_NOMBRE = r"(?:(?:de|del|la|los|las)[ \t]+){0,2}"
_NOMBRE_PROPIO = (
    rf"{_NOMBRE_TOKEN}"
    rf"(?:[ \t]+{_CONECTOR_NOMBRE}{_NOMBRE_TOKEN}){{0,2}}"
)
_PATRON_NOMBRE_DECLARADO = re.compile(
    rf"\b(?i:{_PALABRAS_NOMBRE})\b[ \t]*:?[ \t]*(?P<nombre>{_NOMBRE_PROPIO})"
)

# Candidatos a número de teléfono: 7 a 13 dígitos, con separadores
# habituales y un prefijo internacional opcional (por ejemplo, +53).
_PATRON_NUMERO = re.compile(
    r"(?<![\w])"
    r"(?P<prefijo>\+\s?\(?\d{1,3}\)?[\s.\-]?)?"
    r"(?P<numero>\d(?:[\s.\-()]?\d){6,12})"
    r"(?![\w])"
)

# Palabras que indican una instrucción de contacto, en español e inglés.
# No incluye nombres de servicios o comodidades ("teléfono fijo", "landline
# phone"), que son información inmobiliaria útil y deben conservarse.
_PALABRAS_INSTRUCCION = (
    r"ll[aá]m(?:ar|e|en|a|ame|anos|an|ado|ada|ando)|"
    r"cont[aá]ct(?:ar|e|en|a|ame|anos|an|ado|ada|o|os)?|"
    r"escr[ií]b(?:ir|e|eme|anos|a|an|iendo)|"
    r"env[ií](?:ar|e|en|ame|anos)\s+(?:un\s+)?mensaje|"
    r"texte(?:ar|a|ame|anos)|"
    r"whats?\s*app|wasap|wsp|telegram|messenger|"
    r"call|text|message|write|sms|"
    r"correos?\s+electr[oó]nic\w*|e-?mail"
)
_PATRON_INSTRUCCION = re.compile(
    rf"\b(?:{_PALABRAS_INSTRUCCION})\b",
    re.IGNORECASE,
)

# Palabras que, junto a un número, indican que ese número es un teléfono.
# Aquí sí se incluyen los nombres de servicios ("teléfono", "phone").
_PALABRAS_CONTEXTO = _PALABRAS_INSTRUCCION + (
    r"|tel[eé]fonos?|tels?|phone|telephone|celulares?|cell(?:ular)?|"
    r"m[oó]vil(?:es)?|mobile|correos?"
)
_PATRON_CONTEXTO_CONTACTO = re.compile(
    rf"\b(?:{_PALABRAS_CONTEXTO})\b",
    re.IGNORECASE,
)
_PATRON_SIMBOLO_CONTACTO = re.compile(r"[📲📞☎📱]")

# Etiquetas de contacto que pueden quedar vacías tras eliminar el número o
# enlace. La etiqueta se reconoce si lleva dos puntos o si abre una cláusula
# y no le queda contenido; así no se confunde con comodidades como
# "landline phone" o "Phone or nauta home: No".
_ETIQUETAS_CONTACTO = (
    r"tel[eé]fonos?|tels?|phone|telephone|celulares?|cell(?:ular)?|"
    r"m[oó]vil(?:es)?|mobile|whats?\s*app|wasap|wsp|"
    r"correos?\s+electr[oó]nic\w*|e-?mail"
)
_PATRON_ETIQUETA_CONTACTO = re.compile(
    rf"\b(?:{_ETIQUETAS_CONTACTO})\s*:\s*(?=[,.;:!?/\-]|$)",
    re.IGNORECASE,
)
_PATRON_ETIQUETA_INICIO = re.compile(
    rf"(?:^|(?<=[,.;:!?\n]))[ \t]*(?:{_ETIQUETAS_CONTACTO})"
    rf"[ \t]*:?[ \t]*(?=[,.;:!?/\-]|$)",
    re.IGNORECASE | re.MULTILINE,
)

# Cláusulas que, tras quitar la instrucción de contacto, no aportan nada.
# Se admite un prefijo de viñeta y variantes en inglés.
_PATRON_RELLENO = re.compile(
    r"^[\s•·*\-–—>»\"'(\[]*(?:interesad[oa]s?|interested|informes?|"
    r"informaci[oó]n|info|detalles?|details?|contacto?|para|m[aá]s|y|o|con|sin)"
    r"\s*$",
    re.IGNORECASE,
)

_DELIMITADORES_CLAUSULA = ",.;\n!?"


def _clausula_de(texto: str, inicio: int, fin: int) -> str:
    """Devuelve la cláusula que contiene el fragmento [inicio, fin)."""
    inicio_clausula = max(
        texto.rfind(delimitador, 0, inicio)
        for delimitador in _DELIMITADORES_CLAUSULA
    )
    inicio_clausula += 1

    finales = [
        posicion
        for delimitador in _DELIMITADORES_CLAUSULA
        if (posicion := texto.find(delimitador, fin)) != -1
    ]
    fin_clausula = min(finales) if finales else len(texto)
    return texto[inicio_clausula:fin_clausula]


def _es_telefono(match: re.Match, texto: str) -> bool:
    """Decide si un número candidato es un teléfono y no un dato inmobiliario.

    Se descartan precios, años, áreas y superficies: un número solo se
    considera teléfono si tiene prefijo internacional, si usa un formato
    típico de Cuba, o si aparece en una cláusula con palabras de contacto.
    """
    prefijo = match.group("prefijo") or ""
    digitos = re.sub(r"\D", "", match.group("numero"))

    if prefijo.startswith("+"):
        return True
    if digitos.startswith("53") and len(digitos) >= 10:
        return True
    if digitos[0] == "0" and len(digitos) in (9, 10, 11):
        return True
    if len(digitos) == 8 and digitos[0] in "57":
        return True
    if 7 <= len(digitos) <= 13:
        clausula = _clausula_de(texto, match.start(), match.end())
        if _PATRON_CONTEXTO_CONTACTO.search(clausula):
            return True
        if _PATRON_SIMBOLO_CONTACTO.search(clausula):
            return True
    return False


def _quitar_numeros(texto: str) -> str:
    """Elimina teléfonos y conserva otros números (precios, años, áreas)."""

    def reemplazar(match: re.Match) -> str:
        return "" if _es_telefono(match, texto) else match.group(0)

    return _PATRON_NUMERO.sub(reemplazar, texto)


def _quitar_instrucciones(texto: str) -> str:
    """Recorta las cláusulas que contienen instrucciones de contacto."""
    partes = re.split(r"([,.;\n!?])", texto)
    resultado: list[str] = []

    for indice in range(0, len(partes), 2):
        clausula = partes[indice]
        delimitador = partes[indice + 1] if indice + 1 < len(partes) else ""

        coincidencia = _PATRON_INSTRUCCION.search(clausula)
        if coincidencia:
            clausula = clausula[: coincidencia.start()]
            # Evitar dejar conectores colgando al final de la cláusula.
            clausula = re.sub(
                r"\s+(?:con|al|a|por|v[ií]a|para|desde|el|la|los|las|y|o)\s*$",
                "",
                clausula,
                flags=re.IGNORECASE,
            )

        nucleo = clausula.strip()
        if (
            not nucleo
            or _PATRON_RELLENO.match(nucleo)
            or (
                _PATRON_SIMBOLO_CONTACTO.search(nucleo)
                and not re.search(r"\w", nucleo)
            )
        ):
            clausula = ""
        else:
            # Conservar el espacio inicial de la cláusula para no pegar la
            # puntuación con la palabra siguiente ("EXPERIENCIA!SI").
            inicio = clausula[: len(clausula) - len(clausula.lstrip())]
            clausula = inicio + nucleo

        if clausula:
            resultado.append(clausula)
        if delimitador:
            resultado.append(delimitador)

    return "".join(resultado)


def contiene_datos_contacto(texto: str | None) -> bool:
    """Indica si un texto contiene teléfonos, WhatsApp, correos o contacto.

    También detecta presentaciones personales que revelan el nombre del
    anunciante y restos de contacto (por ejemplo, un emoji de teléfono que
    quedó solo en una cláusula). Se usa para comprobar archivos ya guardados
    sin modificarlos y para no alterar los textos que no tienen ningún dato
    personal.
    """
    if not isinstance(texto, str) or not texto.strip():
        return False

    if _PATRON_URL_WHATSAPP.search(texto):
        return True
    if _PATRON_ESQUEMA_WHATSAPP.search(texto):
        return True
    if _PATRON_CORREO.search(texto):
        return True
    if _PATRON_NOMBRE_DECLARADO.search(texto):
        return True
    if _PATRON_INSTRUCCION.search(texto):
        return True
    if _PATRON_ETIQUETA_CONTACTO.search(texto):
        return True
    if _PATRON_ETIQUETA_INICIO.search(texto):
        return True
    for clausula in re.split(r"[,.;\n!?]", texto):
        if _PATRON_SIMBOLO_CONTACTO.search(clausula) and not re.search(
            r"\w", clausula
        ):
            return True
    return any(
        _es_telefono(coincidencia, texto)
        for coincidencia in _PATRON_NUMERO.finditer(texto)
    )


def eliminar_datos_contacto(texto: str | None) -> str | None:
    """Devuelve el texto sin teléfonos, WhatsApp, correos ni contacto.

    También elimina las presentaciones personales que revelan el nombre del
    anunciante. El resto del contenido se conserva. Si tras la limpieza no
    queda texto útil, devuelve ``None`` para no inventar una descripción. Los
    textos que no contienen ningún dato de contacto se devuelven exactamente
    iguales.
    """
    if not isinstance(texto, str) or not texto.strip():
        return None

    if not contiene_datos_contacto(texto):
        return texto

    limpio = _PATRON_URL_WHATSAPP.sub("", texto)
    limpio = _PATRON_ESQUEMA_WHATSAPP.sub("", limpio)
    limpio = _PATRON_CORREO.sub("", limpio)
    limpio = _PATRON_NOMBRE_DECLARADO.sub("", limpio)
    limpio = _quitar_numeros(limpio)
    limpio = _PATRON_ETIQUETA_CONTACTO.sub("", limpio)
    limpio = _PATRON_ETIQUETA_INICIO.sub("", limpio)
    limpio = _quitar_instrucciones(limpio)

    # Normalizar espacios y puntuación sobrante de los recortes, sin tocar
    # los saltos de línea que pueda tener la descripción original.
    limpio = re.sub(r"[ \t]+", " ", limpio)
    limpio = re.sub(r"[ \t]+([,.;:])", r"\1", limpio)
    limpio = re.sub(r"(?<!\d)([,.;:])(?=[^ \t\n])", r"\1 ", limpio)
    limpio = re.sub(r"([!?])(?=[^\s!?])", r"\1 ", limpio)
    limpio = re.sub(r"([,.;:!?])(?:[ \t]*[,.;:!?])+", r"\1", limpio)
    # Quitar líneas que solo contenían un resto de contacto ("." suelto).
    limpio = re.sub(r"(?m)^[ \t]*[.,;:!?•·*\-–—]+[ \t]*$", "", limpio)
    limpio = re.sub(r"\n{3,}", "\n\n", limpio)
    limpio = limpio.strip(" \t\n,;:-/")
    limpio = limpio.lstrip(". \t\n")

    if not re.search(r"\w", limpio):
        return None
    return limpio


def sanitizar_crudo(dato: dict) -> dict:
    """Copia un crudo y elimina sus datos personales de contacto.

    Limpia los campos de texto conocidos y retira del objeto ``publisher``
    los subcampos que identifican al anunciante. No modifica el original.
    """
    if not isinstance(dato, dict):
        return dato

    sano = dict(dato)

    for campo in CAMPOS_TEXTO_CRUDO:
        valor = sano.get(campo)
        if isinstance(valor, str) and contiene_datos_contacto(valor):
            sano[campo] = eliminar_datos_contacto(valor)

    publisher = sano.get("publisher")
    if isinstance(publisher, dict):
        publisher_sano = dict(publisher)
        for campo in CAMPOS_PERSONALES_PUBLISHER:
            publisher_sano.pop(campo, None)
        sano["publisher"] = publisher_sano

    features = sano.get("features")
    if isinstance(features, list):
        features_sanas = []
        for feature in features:
            if isinstance(feature, str) and contiene_datos_contacto(feature):
                limpia = eliminar_datos_contacto(feature)
                if limpia:
                    features_sanas.append(limpia)
            else:
                features_sanas.append(feature)
        sano["features"] = features_sanas

    return sano


def sanitizar_anuncio_procesado(datos: dict) -> dict:
    """Copia un anuncio del esquema común y limpia sus campos de texto."""
    if not isinstance(datos, dict):
        return datos

    sano = dict(datos)
    for campo in CAMPOS_TEXTO_PROCESADO:
        valor = sano.get(campo)
        if isinstance(valor, str) and contiene_datos_contacto(valor):
            sano[campo] = eliminar_datos_contacto(valor)
    return sano


def campos_personales(dato: dict) -> list[str]:
    """Devuelve las claves de un anuncio con datos de contacto, sin valores.

    Revisa los campos de texto libre, el objeto ``publisher`` y la lista
    ``features``. Se usa para comprobar archivos ya guardados.
    """
    if not isinstance(dato, dict):
        return []

    hallados: list[str] = []

    for campo in CAMPOS_TEXTO_ANUNCIO:
        valor = dato.get(campo)
        if isinstance(valor, str) and contiene_datos_contacto(valor):
            hallados.append(campo)

    publisher = dato.get("publisher")
    if isinstance(publisher, dict):
        for campo in CAMPOS_PERSONALES_PUBLISHER:
            if publisher.get(campo) not in (None, ""):
                hallados.append(f"publisher.{campo}")

    features = dato.get("features")
    if isinstance(features, list):
        for indice, feature in enumerate(features):
            if isinstance(feature, str) and contiene_datos_contacto(feature):
                hallados.append(f"features[{indice}]")

    return hallados


def revisar_archivo_json(ruta: str | Path) -> dict:
    """Resume los datos de contacto de un archivo JSON de anuncios.

    Devuelve cuántos anuncios contiene y qué campos están afectados, sin
    incluir los valores personales. Sirve para comprobar archivos
    versionados sin exponer información de contacto.
    """
    with open(ruta, encoding="utf-8") as archivo:
        contenido = json.load(archivo)

    if isinstance(contenido, dict) and isinstance(contenido.get("datos"), list):
        anuncios = contenido["datos"]
    elif isinstance(contenido, list):
        anuncios = contenido
    else:
        anuncios = [contenido]

    campos: dict[str, int] = {}
    for anuncio in anuncios:
        for campo in campos_personales(anuncio):
            campos[campo] = campos.get(campo, 0) + 1

    return {"anuncios": len(anuncios), "campos": campos}
