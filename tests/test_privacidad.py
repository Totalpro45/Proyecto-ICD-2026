"""Pruebas para la limpieza de datos personales de contacto.

Usa únicamente ejemplos ficticios. Comprueba que se eliminan teléfonos,
enlaces de WhatsApp, correos e instrucciones de contacto, y que se conserva
el contenido inmobiliario útil.
"""

import re
import sys

sys.path.insert(0, "src")

from data.privacidad import (
    contiene_datos_contacto,
    eliminar_datos_contacto,
    sanitizar_anuncio_procesado,
    sanitizar_crudo,
)


def test_eliminar_datos_contacto_conserva_descripcion_util():
    texto = (
        "Casa de 3 habitaciones y 2 baños. "
        "Teléfono: 5550 0000. Patio amplio y garaje."
    )

    limpio = eliminar_datos_contacto(texto)

    assert limpio is not None
    assert "Casa de 3 habitaciones" in limpio
    assert "2 baños" in limpio
    assert "Patio amplio y garaje" in limpio
    assert "5550" not in limpio
    assert "Teléfono" not in limpio


def test_eliminar_datos_contacto_quita_enlace_whatsapp():
    texto = "Apartamento con balcón. WhatsApp: https://wa.me/5355500000"

    limpio = eliminar_datos_contacto(texto)

    assert limpio is not None
    assert "Apartamento con balcón" in limpio
    assert "wa.me" not in limpio
    assert "whatsapp" not in limpio.lower()
    assert "5355500000" not in limpio


def test_eliminar_datos_contacto_quita_instruccion_sin_perder_clausulas():
    texto = "Casa en Playa, 3 cuartos, llamar al 55500000"

    limpio = eliminar_datos_contacto(texto)

    assert limpio is not None
    assert "Casa en Playa" in limpio
    assert "3 cuartos" in limpio
    assert "llamar" not in limpio.lower()
    assert "55500000" not in limpio


def test_eliminar_datos_contacto_conserva_precio_y_anio():
    texto = "Precio 25000000 CUP, construida en 2020. Casa con garaje."

    assert eliminar_datos_contacto(texto) == texto


def test_eliminar_datos_contacto_quita_correo():
    texto = "Casa colonial. Escríbeme a correo@ejemplo.com"

    limpio = eliminar_datos_contacto(texto)

    assert limpio is not None
    assert "Casa colonial" in limpio
    assert "correo@ejemplo.com" not in limpio
    assert "Escríbeme" not in limpio


def test_eliminar_datos_contacto_solo_contacto_devuelve_none():
    assert eliminar_datos_contacto("Teléfono 55500000") is None


def test_eliminar_datos_contacto_none_y_vacio():
    assert eliminar_datos_contacto(None) is None
    assert eliminar_datos_contacto("") is None
    assert eliminar_datos_contacto("   ") is None


def test_sanitizar_crudo_gaos_elimina_publisher_personal():
    crudo = {
        "ulistingid": "gaos-ficticio-001",
        "vctitle": "Casa en Playa 55500000",
        "vcaddress": "Calle 3ra, Playa. WhatsApp 5355500000",
        "sdescription_eng": "House with 2 bedrooms. Call +53 55500000.",
        "sdescription_ita": "Casa con 2 camere. Telefono 55500000.",
        "stittle_eng": "House in Playa 55500000",
        "stittle_ita": "Casa en Playa 55500000",
        "gem_reason": "Call 55500000",
        "features": ["garage", "Call 55500000"],
        "publisher": {
            "accountType": "private",
            "isVerified": True,
            "name": "Persona de Prueba",
            "phone": "55500000",
            "avatarUrl": "https://example.com/avatar-ficticio",
            "slug": "persona-de-prueba",
        },
    }

    sano = sanitizar_crudo(crudo)

    assert "Casa en Playa" in sano["vctitle"]
    assert "55500000" not in sano["vctitle"]
    assert "Calle 3ra, Playa" in sano["vcaddress"]
    assert "whatsapp" not in sano["vcaddress"].lower()
    assert "House with 2 bedrooms" in sano["sdescription_eng"]
    assert "55500000" not in sano["sdescription_eng"]
    assert "Casa con 2 camere" in sano["sdescription_ita"]
    assert "Telefono" not in sano["sdescription_ita"]
    assert sano["gem_reason"] is None
    assert sano["features"] == ["garage"]

    assert set(sano["publisher"]) == {"accountType", "isVerified"}
    assert sano["publisher"]["accountType"] == "private"

    # El crudo original no se modifica.
    assert "name" in crudo["publisher"]
    assert "phone" in crudo["publisher"]


def test_sanitizar_crudo_revolico_limpia_titulo_y_descripcion():
    crudo = {
        "id_fuente": "12345678",
        "url": "https://www.revolico.com/item/casa-ficticia-12345678",
        "precio": 100000,
        "moneda": "USD",
        "titulo": "Casa en Playa 55500000",
        "descripcion": "Llamar al 55500000",
    }

    sano = sanitizar_crudo(crudo)

    assert sano["titulo"] == "Casa en Playa"
    assert sano["descripcion"] is None
    assert sano["id_fuente"] == "12345678"
    assert sano["precio"] == 100000


def test_sanitizar_anuncio_procesado_limpia_campos_texto():
    anuncio = {
        "id_fuente": "gaos-ficticio-002",
        "precio": 50000,
        "titulo": "Casa en Marianao 55500000",
        "descripcion": "Casa amplia. WhatsApp: https://wa.me/5355500000",
        "direccion_texto": "Calle 10, Marianao. Teléfono 55500000",
        "notas_calidad": "Contactar por correo@ejemplo.com",
    }

    sano = sanitizar_anuncio_procesado(anuncio)

    assert sano["id_fuente"] == "gaos-ficticio-002"
    assert sano["precio"] == 50000
    assert "Casa en Marianao" in sano["titulo"]
    assert "55500000" not in sano["titulo"]
    assert "Casa amplia" in sano["descripcion"]
    assert "whatsapp" not in sano["descripcion"].lower()
    assert "Calle 10, Marianao" in sano["direccion_texto"]
    assert "Teléfono" not in sano["direccion_texto"]
    assert sano["notas_calidad"] is None
    assert anuncio["descripcion"] is not None


def test_textos_sin_contacto_no_se_modifican():
    """Un texto limpio se devuelve exactamente igual, sin normalizar."""
    textos = [
        "Casa de 3 habitaciones, 2 baños, 120 m2.",
        "Casa  con  3 cuartos",  # espacios intencionales
        "Precio 25000000 CUP, construida en 2020.",
        "It has a landline phone. Permanent water supply.",
        "☎️ Telephone line 🌐 Nauta Hogar 💧 Water tank",
        "Cell phone chargers and small devices · Computer / Laptop",
        "Phone or nauta home: No",
        "por el Correo y la Notaría",
    ]

    for texto in textos:
        assert eliminar_datos_contacto(texto) == texto
        assert contiene_datos_contacto(texto) is False


def test_contiene_datos_contacto_detecta_casos_problematicos():
    assert contiene_datos_contacto("Teléfono: 55500000") is True
    assert contiene_datos_contacto("WhatsApp: https://wa.me/5355500000") is True
    assert contiene_datos_contacto("Escribir a correo@ejemplo.com") is True
    assert contiene_datos_contacto("Interesados llamar al 55500000") is True
    assert contiene_datos_contacto("Contactar con el vendedor") is True
    assert contiene_datos_contacto(None) is False
    assert contiene_datos_contacto("") is False


def test_eliminar_datos_contacto_no_inventa_palabras():
    """El saneado solo elimina; nunca añade contenido nuevo."""
    texto = (
        "Casa de 3 habitaciones y garaje. "
        "Teléfono: 55500000. Patio amplio."
    )

    limpio = eliminar_datos_contacto(texto)
    palabras_originales = set(re.findall(r"[a-záéíóúñü]+", texto.lower()))
    palabras_limpias = set(re.findall(r"[a-záéíóúñü]+", (limpio or "").lower()))

    assert palabras_limpias <= palabras_originales
    assert "Casa" in limpio
    assert "garaje" in limpio
    assert "Patio amplio" in limpio


def test_eliminar_datos_contacto_quita_etiqueta_aunque_no_quede_numero():
    assert eliminar_datos_contacto("Teléfono 55500000") is None
    assert eliminar_datos_contacto("Tel: 55500000 / 5355500000. Patio.") == "Patio."


def test_eliminar_datos_contacto_conserva_saltos_de_linea():
    texto = "Casa con 3 habitaciones.\nPatio amplio.\nTel: 55500000"

    limpio = eliminar_datos_contacto(texto)

    assert limpio is not None
    assert "Casa con 3 habitaciones" in limpio
    assert "Patio amplio" in limpio
    assert "55500000" not in limpio
    assert "\n" in limpio


def test_eliminar_datos_contacto_conserva_comodidades_mencionadas():
    texto = (
        "Casa con garaje. Tel: 55500000. "
        "Incluye landline phone y cell phone chargers."
    )

    limpio = eliminar_datos_contacto(texto)

    assert limpio is not None
    assert "landline phone" in limpio
    assert "cell phone chargers" in limpio
    assert "55500000" not in limpio


def test_sanitizar_anuncio_procesado_no_cambia_textos_limpios():
    anuncio = {
        "id_fuente": "gaos-ficticio-003",
        "titulo": "Casa en Playa",
        "descripcion": "Casa  con  patio.\nBuen estado.",
        "direccion_texto": "",
        "notas_calidad": None,
    }

    sano = sanitizar_anuncio_procesado(anuncio)

    assert sano == anuncio


def test_eliminar_datos_contacto_quita_nombre_autodeclarado():
    texto = (
        "Soy el propietario, my name is Ficticio, vendo la casa por "
        "50.000 USD. Patio amplio."
    )

    limpio = eliminar_datos_contacto(texto)

    assert limpio is not None
    assert "Ficticio" not in limpio
    assert "my name is" not in limpio.lower()
    assert "Soy el propietario" in limpio
    assert "vendo la casa" in limpio
    assert "50.000 USD" in limpio
    assert "Patio amplio" in limpio


def test_eliminar_datos_contacto_quita_nombre_en_espanol():
    casos = (
        "Me llamo Ficticia, vendo casa en Playa con 3 cuartos.",
        "Mi nombre es Ficticio y vendo apartamento en Marianao.",
    )

    for texto in casos:
        limpio = eliminar_datos_contacto(texto)

        assert limpio is not None
        assert "Fictici" not in limpio
        assert "Casa" in limpio or "vendo" in limpio


def test_eliminar_datos_contacto_no_quita_nombres_de_lugares():
    texto = "Casa en Vedado, La Habana. Vista al mar."

    assert eliminar_datos_contacto(texto) == texto
    assert contiene_datos_contacto(texto) is False


def test_eliminar_datos_contacto_quita_llamadas_acentuadas():
    casos = (
        ("Casa en Playa. Llámanos para más información.", "Casa en Playa."),
        ("Apartamento en Vedado. Llámame y te cuento.", "Apartamento en Vedado."),
        ("Casa amplia. Envíame un mensaje.", "Casa amplia."),
    )

    for texto, esperado in casos:
        limpio = eliminar_datos_contacto(texto)

        assert limpio == esperado
        assert "llama" not in (limpio or "").lower()
        assert "env" not in (limpio or "").lower()


def test_eliminar_datos_contacto_quita_restos_de_emoji():
    texto = "Casa en Playa, 3 cuartos.\n•Interested\n📲.\nPatio amplio."

    limpio = eliminar_datos_contacto(texto)

    assert limpio is not None
    assert "Interested" not in limpio
    assert "📲" not in limpio
    assert "Casa en Playa" in limpio
    assert "Patio amplio" in limpio


def test_eliminar_datos_contacto_conserva_emoji_de_comodidad():
    texto = "☎️ Telephone line 🌐 Nauta Hogar 💧 Water tank"

    assert eliminar_datos_contacto(texto) == texto
    assert contiene_datos_contacto(texto) is False


def test_eliminar_datos_contacto_separa_signo_pegado():
    texto = "EXPERIENCIA!SI VENDES EN PLAYA llámanos"

    limpio = eliminar_datos_contacto(texto)

    assert limpio == "EXPERIENCIA! SI VENDES EN PLAYA"


def test_eliminar_datos_contacto_conserva_precio_con_miles():
    texto = "My name is Ficticio, vendo casa por 5,000 USD. Patio."

    limpio = eliminar_datos_contacto(texto)

    assert limpio is not None
    assert "Ficticio" not in limpio
    assert "5,000 USD" in limpio
    assert "Patio" in limpio


def test_contiene_datos_contacto_detecta_nombre_y_restos():
    assert contiene_datos_contacto("my name is Ficticio") is True
    assert contiene_datos_contacto("Me llamo Ficticia") is True
    assert contiene_datos_contacto("Casa en Playa\n📲.") is True
    assert contiene_datos_contacto("Casa en Playa") is False


def test_eliminar_datos_contacto_conserva_texto_tras_punto():
    casos = (
        ("My name is Ficticio. Patio amplio.", "Patio amplio."),
        ("Name is Ficticio. Casa en Marianao.", "Casa en Marianao."),
        (
            "I am called Ficticio. Apartamento en Vedado.",
            "Apartamento en Vedado.",
        ),
        (
            "My name's Ficticio. Casa con patio y garaje.",
            "Casa con patio y garaje.",
        ),
    )

    for texto, esperado in casos:
        assert eliminar_datos_contacto(texto) == esperado


def test_eliminar_datos_contacto_conserva_municipio_tras_punto():
    texto = "Me llamo Ficticio. Centro Habana, casa amplia con patio."

    limpio = eliminar_datos_contacto(texto)

    assert limpio == "Centro Habana, casa amplia con patio."


def test_eliminar_datos_contacto_quita_nombre_seguido_de_coma():
    texto = "Me llamo Ficticio, vendo casa en Cerro con 3 cuartos."

    limpio = eliminar_datos_contacto(texto)

    assert limpio == "vendo casa en Cerro con 3 cuartos."


def test_eliminar_datos_contacto_conserva_segunda_oracion():
    texto = "Mi nombre es Ficticio. La casa tiene 3 cuartos y patio."

    limpio = eliminar_datos_contacto(texto)

    assert limpio == "La casa tiene 3 cuartos y patio."


def test_eliminar_datos_contacto_quita_nombres_de_una_a_tres_palabras():
    casos = (
        ("Me llamo Ficticio, vendo casa.", "vendo casa."),
        ("Me llamo Ficticio Segundo, vendo casa.", "vendo casa."),
        (
            "Me llamo Ficticio Segundo Tercero, vendo casa.",
            "vendo casa.",
        ),
        ("Me llamo Ana de la Cruz, vendo casa.", "vendo casa."),
    )

    for texto, esperado in casos:
        assert eliminar_datos_contacto(texto) == esperado


def test_eliminar_datos_contacto_conserva_instrucciones_comerciales():
    casos = (
        "Ask for more information about the house.",
        "Pregunte por las condiciones de la casa.",
        "Pregunte por el precio en la oficina.",
    )

    for texto in casos:
        assert eliminar_datos_contacto(texto) == texto
        assert contiene_datos_contacto(texto) is False


def test_eliminar_datos_contacto_conserva_titulos_con_name():
    casos = (
        "Name: Casa en venta.",
        "Nombre: Apartamento en Playa.",
        "Name: House with patio and garage.",
    )

    for texto in casos:
        assert eliminar_datos_contacto(texto) == texto
        assert contiene_datos_contacto(texto) is False


def test_eliminar_datos_contacto_conserva_toponimos_tras_expresiones_ambiguas():
    casos = (
        "Pregunte por Centro Habana. Casa amplia.",
        "Pregunte por Marianao. Casa con patio.",
        "Ask for Playa. House near the sea.",
        "Nombre: Vedado.",
        "Name: Marianao.",
    )

    for texto in casos:
        assert eliminar_datos_contacto(texto) == texto
        assert contiene_datos_contacto(texto) is False


def test_eliminar_datos_contacto_conserva_toponimo_como_nombre_dudoso():
    casos = (
        "Me llamo Playa.",
        "Mi nombre es Vedado.",
        "Me llamo Centro Habana.",
    )

    for texto in casos:
        assert eliminar_datos_contacto(texto) == texto
        assert contiene_datos_contacto(texto) is False


def test_eliminar_datos_contacto_no_incorpora_palabras_inmuebles():
    casos = (
        ("Me llamo Ficticio Casa, vendo.", "Casa, vendo."),
        ("My name is Ficticio Patio amplio.", "Patio amplio."),
        ("Me llamo Casa.", "Me llamo Casa."),
        ("My name is Apartamento.", "My name is Apartamento."),
    )

    for texto, esperado in casos:
        assert eliminar_datos_contacto(texto) == esperado


def test_contiene_datos_contacto_coincide_con_el_saneador():
    casos = (
        "My name is Ficticio. Patio amplio.",
        "Me llamo Ficticio, vendo casa.",
        "Mi nombre es Ficticio. Casa en Cerro.",
        "Me llamo Playa.",
        "Nombre: Vedado.",
        "Pregunte por las condiciones de la casa.",
        "Casa en Playa con patio.",
        "Casa en Playa. Teléfono: 55500000.",
        "Casa en Playa\n📲.",
    )

    for texto in casos:
        limpio = eliminar_datos_contacto(texto)
        assert contiene_datos_contacto(texto) is (limpio != texto)


def test_sanitizar_anuncio_procesado_conserva_texto_tras_punto():
    anuncio = {
        "id_fuente": "gaos-ficticio-004",
        "titulo": "Casa en Playa",
        "descripcion": "My name is Ficticio. Casa con patio y garaje.",
        "direccion_texto": "",
        "notas_calidad": None,
    }

    sano = sanitizar_anuncio_procesado(anuncio)

    assert sano["descripcion"] == "Casa con patio y garaje."
    assert sano["titulo"] == anuncio["titulo"]
    assert sano["id_fuente"] == anuncio["id_fuente"]
    assert sano["direccion_texto"] == anuncio["direccion_texto"]
    assert sano["notas_calidad"] is None


def test_eliminar_datos_contacto_iniciales_limitacion_conocida():
    """Limitación conocida: las iniciales pueden dejar el apellido.

    El punto de la inicial no se atraviesa para no consumir la primera palabra
    de la oración siguiente. Se documenta el comportamiento actual, que
    conserva la información inmobiliaria aunque el saneamiento sea parcial.
    """
    casos = (
        ("My name is J. Pérez. Casa con patio.", "Pérez. Casa con patio."),
        (
            "Me llamo A. García, vendo apartamento.",
            "Me llamo A. García, vendo apartamento.",
        ),
        ("My name is Ana Pérez. Casa en Playa.", "Casa en Playa."),
        ("My name is J. Casa en venta.", "Casa en venta."),
    )

    for texto, esperado in casos:
        limpio = eliminar_datos_contacto(texto)

        assert limpio == esperado
        assert contiene_datos_contacto(texto) is (limpio != texto)
