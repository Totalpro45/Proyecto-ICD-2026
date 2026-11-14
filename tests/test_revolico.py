"""Pruebas para el extractor de anuncios inmobiliarios de Revolico.

Utiliza datos de ejemplo ficticios. No realiza peticiones HTTP reales.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "src")

import requests

from sources.revolico import (
    capturar_y_guardar_revolico,
    extraer_listings_revolico,
    mapear_anuncio_revolico,
    _clasificar_tipo_inmueble,
    REVOLICO_URL,
)
from data.almacenamiento_anuncios import guardar_captura_completa
from data.models import AnuncioInmobiliario


# --- Datos de ejemplo basados en la respuesta real de Revolico ---

CRUDOS_REVOLICO_EJEMPLO = [
    {
        "id_fuente": "58169727",
        "url": "https://www.revolico.com/item/vendo-propiedad-horizontal-en-el-vedado-58169727?p",
        "precio": 99000,
        "moneda": "USD",
        "titulo": "Vendo Propiedad Horizontal en el Vedado",
        "descripcion": None,
    },
    {
        "id_fuente": "58397137",
        "url": "https://www.revolico.com/item/oportunidad-en-playa-37-y-42-58397137?p",
        "precio": 25000,
        "moneda": "USD",
        "titulo": "Oportunidad en Playa | 37 y 42",
        "descripcion": None,
    },
    {
        "id_fuente": "56318726",
        "url": "https://www.revolico.com/item/apartamento-en-venta-56318726?p",
        "precio": 40000,
        "moneda": "EUR",
        "titulo": "Apartamento en el Vedado",
        "descripcion": None,
    },
]


# --- Pruebas de mapeo ---


def test_mapear_anuncio_revolico_campos_completos():
    """mapear_anuncio_revolico mapea correctamente los campos del crudo."""
    dato = {
        "id_fuente": "58169727",
        "url": "https://www.revolico.com/item/test-58169727",
        "precio": 99000,
        "moneda": "USD",
        "titulo": "Vendo Propiedad Horizontal en el Vedado",
        "descripcion": None,
    }
    fecha_captura = "2026-11-07T12:00:00Z"

    anuncio = mapear_anuncio_revolico(dato, fecha_captura)

    assert anuncio.fuente == "revolico"
    assert anuncio.id_fuente == "58169727"
    assert anuncio.url == "https://www.revolico.com/item/test-58169727"
    assert anuncio.fecha_captura == "2026-11-07T12:00:00Z"
    assert anuncio.fecha_publicacion is None
    assert anuncio.fecha_actualizacion is None
    assert anuncio.provincia == "La Habana"
    assert anuncio.municipio is None
    assert anuncio.reparto is None
    assert anuncio.direccion_texto is None
    assert anuncio.tipo_operacion == "venta"
    assert anuncio.tipo_inmueble == "indeterminado"
    assert anuncio.area_m2 is None
    assert anuncio.tipo_area is None
    assert anuncio.habitaciones is None
    assert anuncio.banos is None
    assert anuncio.planta is None
    assert anuncio.estado_conservacion is None
    assert anuncio.amueblado is None
    assert anuncio.precio == 99000
    assert anuncio.moneda == "USD"
    assert anuncio.precio_usd is None
    assert anuncio.tasa_conversion_usd is None
    assert anuncio.tasa_fecha is None
    assert anuncio.tasa_fuente is None
    assert anuncio.precio_m2_usd is None
    assert anuncio.tasa_id is None
    assert anuncio.titulo == "Vendo Propiedad Horizontal en el Vedado"
    assert anuncio.descripcion is None
    assert anuncio.vendedor_tipo is None
    assert anuncio.estado_parseo == "ok"
    assert anuncio.notas_calidad is None
    assert anuncio.es_posible_duplicado is False
    assert anuncio.duplicado_grupo is None


def test_mapear_anuncio_revolico_datos_minimos():
    """mapear_anuncio_revolico acepta datos mínimos y deja nulos lo ausente."""
    dato = {
        "id_fuente": "12345",
        "url": "https://www.revolico.com/item/test-12345",
        "precio": None,
        "moneda": None,
        "titulo": None,
        "descripcion": None,
    }

    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")

    assert anuncio.id_fuente == "12345"
    assert anuncio.precio is None
    assert anuncio.moneda is None
    assert anuncio.titulo is None
    assert anuncio.descripcion is None


def test_mapear_anuncio_revolico_precio_eur():
    """mapear_anuncio_revolico acepta precios en EUR."""
    dato = {
        "id_fuente": "56318726",
        "url": "https://www.revolico.com/item/test-56318726",
        "precio": 40000,
        "moneda": "EUR",
        "titulo": "Apartamento en el Vedado",
        "descripcion": None,
    }

    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")

    assert anuncio.precio == 40000
    assert anuncio.moneda == "EUR"


# --- Pruebas de extraer_listings_revolico ---


def test_extraer_listings_revolico_extrae_anuncios():
    """extraer_listings_revolico extrae anuncios del HTML simulado."""
    html = """
    <html>
        <body>
            <a href="/item/casa-en-venta-la-habana-12345678?p">
                150000 USDCasa en venta en La Habana
            </a>
            <a href="/item/apartamento-en-playa-87654321?p">
                200000 EURApartamento en Playa
            </a>
            <a href="/item/casa-sin-precio-99999999?p">
                Casa sin precio ni moneda
            </a>
        </body>
    </html>
    """

    with patch("sources.revolico.requests.get") as mock_get:
        mock_respuesta = mock_get.return_value
        mock_respuesta.status_code = 200
        mock_respuesta.text = html

        anuncios = extraer_listings_revolico()

    assert len(anuncios) == 3

    # Primer anuncio
    assert anuncios[0]["id_fuente"] == "12345678"
    assert anuncios[0]["url"] == "https://www.revolico.com/item/casa-en-venta-la-habana-12345678?p"
    assert anuncios[0]["precio"] == 150000
    assert anuncios[0]["moneda"] == "USD"
    assert anuncios[0]["titulo"] == "Casa en venta en La Habana"
    assert anuncios[0]["descripcion"] is None

    # Segundo anuncio
    assert anuncios[1]["id_fuente"] == "87654321"
    assert anuncios[1]["url"] == "https://www.revolico.com/item/apartamento-en-playa-87654321?p"
    assert anuncios[1]["precio"] == 200000
    assert anuncios[1]["moneda"] == "EUR"
    assert anuncios[1]["titulo"] == "Apartamento en Playa"
    assert anuncios[1]["descripcion"] is None

    # Tercer anuncio: sin precio
    assert anuncios[2]["id_fuente"] == "99999999"
    assert anuncios[2]["url"] == "https://www.revolico.com/item/casa-sin-precio-99999999?p"
    assert anuncios[2]["precio"] is None
    assert anuncios[2]["moneda"] is None
    assert anuncios[2]["titulo"] == "Casa sin precio ni moneda"
    assert anuncios[2]["descripcion"] is None


def test_extraer_listings_revolico_error_http():
    """extraer_listings_revolico lanza excepción si la petición falla."""
    with patch("sources.revolico.requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Timeout")

        try:
            extraer_listings_revolico()
            assert False, "Debió lanzar excepción"
        except requests.exceptions.ConnectionError:
            pass


def test_extraer_listings_revolico_error_403():
    """extraer_listings_revolico lanza excepción si la respuesta es 403."""
    with patch("sources.revolico.requests.get") as mock_get:
        mock_respuesta = mock_get.return_value
        mock_respuesta.status_code = 403
        mock_respuesta.reason = "Forbidden"

        try:
            extraer_listings_revolico()
            assert False, "Debió lanzar excepción"
        except OSError as e:
            assert "403" in str(e)


# --- Pruebas de capturar_y_guardar_revolico ---


def test_capturar_y_guardar_revolico_guarda_captura():
    """capturar_y_guardar_revolico guarda crudos y procesados en rutas dadas."""
    crudos = [
        {
            "id_fuente": "12345678",
            "url": "https://www.revolico.com/item/test-12345678",
            "precio": 150000,
            "moneda": "USD",
            "titulo": "Casa en venta en La Habana",
            "descripcion": None,
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "revolico" / "crudo"
        ruta_procesado = Path(tmpdir) / "revolico" / "procesado"

        id_captura = capturar_y_guardar_revolico(
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
        )

        assert id_captura is not None

        archivos_crudo = list(ruta_crudo.glob("revolico_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("revolico_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1


def test_capturar_y_guardar_revolico_usa_rutas_por_defecto():
    """capturar_y_guardar_revolico usa rutas propias de Revolico por defecto."""
    crudos = [
        {
            "id_fuente": "12345678",
            "url": "https://www.revolico.com/item/test-12345678",
            "precio": 150000,
            "moneda": "USD",
            "titulo": "Casa en venta en La Habana",
            "descripcion": None,
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "revolico" / "crudo"
        ruta_procesado = Path(tmpdir) / "revolico" / "procesado"

        id_captura = capturar_y_guardar_revolico(
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
        )

        assert id_captura is not None

        archivos_crudo = list(ruta_crudo.glob("revolico_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("revolico_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1


def test_capturar_y_guardar_revolico_anuncio_sin_precio_se_conserva():
    """capturar_y_guardar_revolico conserva anuncios sin precio válido."""
    crudos = [
        {
            "id_fuente": "12345678",
            "url": "https://www.revolico.com/item/test-12345678",
            "precio": None,
            "moneda": None,
            "titulo": "Casa sin precio",
            "descripcion": None,
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "revolico" / "crudo"
        ruta_procesado = Path(tmpdir) / "revolico" / "procesado"

        with patch("sources.revolico.extraer_listings_revolico", return_value=crudos):
            id_captura = capturar_y_guardar_revolico(
                ruta_crudo=ruta_crudo,
                ruta_procesado=ruta_procesado,
            )

        assert id_captura is not None

        archivos_crudo = list(ruta_crudo.glob("revolico_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("revolico_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1

        # Leer el archivo procesado y verificar que el precio es None
        import json

        archivo_procesado = list(ruta_procesado.glob("revolico_procesado_*.json"))[0]
        with open(archivo_procesado, encoding="utf-8") as f:
            datos_procesados = json.load(f)

        anuncio_procesado = datos_procesados["datos"][0]
        assert anuncio_procesado["precio"] is None
        assert anuncio_procesado["moneda"] is None


def test_capturar_y_guardar_revolico_no_guarda_si_no_hay_datos():
    """capturar_y_guardar_revolico no guarda si extraer_listings_revolico devuelve vacío."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "revolico" / "crudo"
        ruta_procesado = Path(tmpdir) / "revolico" / "procesado"

        with patch("sources.revolico.extraer_listings_revolico", return_value=[]):
            id_captura = capturar_y_guardar_revolico(
                ruta_crudo=ruta_crudo,
                ruta_procesado=ruta_procesado,
            )

        assert id_captura is None
        assert list(ruta_crudo.glob("revolico_crudo_*.json")) == []
        assert list(ruta_procesado.glob("revolico_procesado_*.json")) == []


def test_guardar_captura_completa_prefijo_guarda_archivos_con_prefijo_revolico():
    """guardar_captura_completa con prefijo_archivo='revolico' guarda archivos
    con prefijo 'revolico_' en lugar de 'gaos_'."""
    crudos = [
        {
            "id_fuente": "12345678",
            "url": "https://www.revolico.com/item/test-12345678",
            "precio": 150000,
            "moneda": "USD",
            "titulo": "Casa en venta en La Habana",
            "descripcion": None,
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "mi_fuente" / "crudo"
        ruta_procesado = Path(tmpdir) / "mi_fuente" / "procesado"

        id_captura = guardar_captura_completa(
            crudos,
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
            prefijo_archivo="revolico",
        )

        assert id_captura is not None

        archivos_crudo = list(ruta_crudo.glob("revolico_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("revolico_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1


def test_guardar_captura_completa_prefijo_por_defecto_es_gaos():
    """guardar_captura_completa sin prefijo_archivo usa el prefijo 'gaos' por defecto."""
    crudos = [
        {
            "id_fuente": "87654321",
            "url": "https://www.revolico.com/item/test-87654321",
            "precio": 50000,
            "moneda": "USD",
            "titulo": "Apartamento en La Habana",
            "descripcion": None,
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "mi_fuente" / "crudo"
        ruta_procesado = Path(tmpdir) / "mi_fuente" / "procesado"

        id_captura = guardar_captura_completa(
            crudos,
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
        )

        assert id_captura is not None

        archivos_crudo = list(ruta_crudo.glob("gaos_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("gaos_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1


# --- Pruebas de metadatos de fuente para Revolico ---


def test_capturar_y_guardar_revolico_guarda_metadatos_revolico():
    """capturar_y_guardar_revolico guarda archivos con fuente y url_fuente de
    Revolico (no de GAOS) y ambos archivos comparten el mismo id_captura."""
    crudos = [
        {
            "id_fuente": "12345678",
            "url": "https://www.revolico.com/item/test-12345678",
            "precio": 150000,
            "moneda": "USD",
            "titulo": "Casa en venta en La Habana",
            "descripcion": None,
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "revolico" / "crudo"
        ruta_procesado = Path(tmpdir) / "revolico" / "procesado"

        id_captura = capturar_y_guardar_revolico(
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
        )

        assert id_captura is not None

        archivos_crudo = list(ruta_crudo.glob("revolico_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("revolico_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1

        # Ambos archivos comparten el mismo id_captura en su nombre
        assert id_captura[:8] in archivos_crudo[0].name
        assert id_captura[:8] in archivos_procesado[0].name

        # Leer ambos archivos y verificar metadatos de fuente
        import json

        with open(archivos_crudo[0], encoding="utf-8") as f:
            datos_crudos = json.load(f)
        with open(archivos_procesado[0], encoding="utf-8") as f:
            datos_procesados = json.load(f)

        assert datos_crudos["id_captura"] == id_captura
        assert datos_procesados["id_captura"] == id_captura
        assert datos_crudos["fuente"] == "revolico"
        assert datos_crudos["url_fuente"] == REVOLICO_URL
        assert datos_procesados["fuente"] == "revolico"
        assert datos_procesados["url_fuente"] == REVOLICO_URL


def test_guardar_captura_completa_revolico_metadatos_correctos():
    """guardar_captura_completa con prefijo 'revolico' guarda metadatos de
    fuente y url_fuente de Revolico en crudo y procesado."""
    crudos = [
        {
            "id_fuente": "12345678",
            "url": "https://www.revolico.com/item/test-12345678",
            "precio": 150000,
            "moneda": "USD",
            "titulo": "Casa en venta en La Habana",
            "descripcion": None,
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        ruta_crudo = Path(tmpdir) / "mi_fuente" / "crudo"
        ruta_procesado = Path(tmpdir) / "mi_fuente" / "procesado"

        id_captura = guardar_captura_completa(
            crudos,
            ruta_crudo=ruta_crudo,
            ruta_procesado=ruta_procesado,
            mapear_func=mapear_anuncio_revolico,
            prefijo_archivo="revolico",
            fuente="revolico",
            url_fuente=REVOLICO_URL,
        )

        assert id_captura is not None

        archivos_crudo = list(ruta_crudo.glob("revolico_crudo_*.json"))
        archivos_procesado = list(ruta_procesado.glob("revolico_procesado_*.json"))

        assert len(archivos_crudo) == 1
        assert len(archivos_procesado) == 1

        import json

        with open(archivos_crudo[0], encoding="utf-8") as f:
            datos_crudos = json.load(f)
        with open(archivos_procesado[0], encoding="utf-8") as f:
            datos_procesados = json.load(f)

        assert datos_crudos["id_captura"] == id_captura
        assert datos_procesados["id_captura"] == id_captura
        assert datos_crudos["fuente"] == "revolico"
        assert datos_crudos["url_fuente"] == REVOLICO_URL
        assert datos_procesados["fuente"] == "revolico"
        assert datos_procesados["url_fuente"] == REVOLICO_URL


# --- Pruebas de clasificación de tipo de inmueble ---


def test_clasificar_tipo_inmueble_casa():
    """_clasificar_tipo_inmueble detecta la palabra completa 'casa'."""
    assert _clasificar_tipo_inmueble("Casa en venta en La Habana") == "casa"
    assert _clasificar_tipo_inmueble("casa independiente en Playa") == "casa"
    assert _clasificar_tipo_inmueble("Vendo casa colonial") == "casa"
    assert _clasificar_tipo_inmueble("CASA EN VEDADO") == "casa"


def test_clasificar_tipo_inmueble_no_confunde_casa():
    """No se confunde 'casa' con palabras que la contienen."""
    assert _clasificar_tipo_inmueble("Casero en venta") == "indeterminado"
    assert _clasificar_tipo_inmueble("Casamiento en La Habana") == "indeterminado"


def test_clasificar_tipo_inmueble_apartamento():
    """_clasificar_tipo_inmueble detecta apartamento, apto y apt."""
    assert _clasificar_tipo_inmueble("Apartamento en el Vedado") == "apartamento"
    assert _clasificar_tipo_inmueble("APTO 2/4 en Lawton") == "apartamento"
    assert _clasificar_tipo_inmueble("apt 2do piso cerca de E y 19") == "apartamento"
    assert _clasificar_tipo_inmueble("APARTAMENTO EN BAJOS") == "apartamento"


def test_clasificar_tipo_inmueble_no_confunde_apto():
    """'apto' y 'apt' deben ser palabras completas, no subcadenas."""
    assert _clasificar_tipo_inmueble("Aptitudes del vendedor") == "indeterminado"
    assert _clasificar_tipo_inmueble("aptitud comercial") == "indeterminado"


def test_clasificar_tipo_inmueble_indeterminado():
    """Títulos genéricos se clasifican como indeterminado."""
    assert _clasificar_tipo_inmueble("Venta") == "indeterminado"
    assert _clasificar_tipo_inmueble("Oportunidad en Playa | 37 y 42") == "indeterminado"
    assert _clasificar_tipo_inmueble("Propiedad horizontal en el Vedado") == "indeterminado"
    assert _clasificar_tipo_inmueble("Biplanta en Playa") == "indeterminado"
    assert _clasificar_tipo_inmueble("Triplanta en Miramar") == "indeterminado"
    assert _clasificar_tipo_inmueble("Independiente en La Habana") == "indeterminado"


def test_clasificar_tipo_inmueble_propiedad_horizontal():
    """'propiedad horizontal' no se clasifica automáticamente como apartamento."""
    assert _clasificar_tipo_inmueble("Propiedad Horizontal en el Vedado") == "indeterminado"


def test_clasificar_tipo_inmueble_biplanta_triplanta():
    """biplanta y triplanta no se clasifican automáticamente como casa."""
    assert _clasificar_tipo_inmueble("Casa Biplanta en Altos Playa") == "casa"
    assert _clasificar_tipo_inmueble("Biplanta en Playa") == "indeterminado"
    assert _clasificar_tipo_inmueble("Triplanta en Miramar") == "indeterminado"


def test_clasificar_tipo_inmueble_no_vivienda():
    """Productos y servicios claramente no inmobiliarios se clasifican como no_vivienda."""
    assert _clasificar_tipo_inmueble("ESMLATE sintético blanco y varios colores") == "no_vivienda"
    assert _clasificar_tipo_inmueble("Se venden tanques de agua nuevos de paquete") == "no_vivienda"
    assert _clasificar_tipo_inmueble("Gestionamos la venta de tu vivienda llámanos 53614857") == "no_vivienda"
    assert _clasificar_tipo_inmueble("Asesoría inmobiliaria en La Habana") == "no_vivienda"


def test_clasificar_tipo_inmueble_no_falso_positivo_no_vivienda():
    """Palabras secundarias no deben clasificar un anuncio inmobiliario como no_vivienda."""
    assert _clasificar_tipo_inmueble("Casa con tanque de agua") == "casa"
    assert _clasificar_tipo_inmueble("Apartamento con esmalte nuevo") == "apartamento"


def test_clasificar_tipo_inmueble_none_y_vacio():
    """Títulos None o vacíos devuelven indeterminado."""
    assert _clasificar_tipo_inmueble(None) == "indeterminado"
    assert _clasificar_tipo_inmueble("") == "indeterminado"
    assert _clasificar_tipo_inmueble("   ") == "indeterminado"


def test_mapear_anuncio_revolico_municipio_desde_titulo():
    """Si el título menciona un municipio de La Habana sin ambigüedades, se identifica."""
    dato = {
        "id_fuente": "58397137",
        "url": "https://www.revolico.com/item/test-58397137?p",
        "precio": 25000,
        "moneda": "USD",
        "titulo": "Casa en zona de Playa | 37 y 42",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.municipio == "Playa"


def test_mapear_anuncio_revolico_municipio_playa_ambigua_sin_contexto_devuelve_none():
    """'Oportunidad en la playa | 37 y 42' es ambigua: no asigna municipio."""
    dato = {
        "id_fuente": "58397137",
        "url": "https://www.revolico.com/item/oportunidad-en-playa-37-y-42-58397137?p",
        "precio": 25000,
        "moneda": "USD",
        "titulo": "Oportunidad en Playa | 37 y 42",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.municipio is None


def test_mapear_anuncio_revolico_municipio_none_para_barrio():
    """Barrios como Vedado o Miramar no se confunden con municipios."""
    dato = {
        "id_fuente": "58169727",
        "url": "https://www.revolico.com/item/test-58169727?p",
        "precio": 99000,
        "moneda": "USD",
        "titulo": "Vendo Propiedad Horizontal en el Vedado",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.municipio is None


def test_mapear_anuncio_revolico_municipio_playa_geografica_devuelve_none():
    """Referencia a playa geográfica no asigna municipio Playa."""
    dato = {
        "id_fuente": "57851228",
        "url": "https://www.revolico.com/item/test-57851228",
        "precio": 120000,
        "moneda": "USD",
        "titulo": "GG-180 cercanía a la playa y tranquilidad en brisas del mar, guanabo",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.municipio is None


def test_mapear_anuncio_revolico_municipio_playa_de_devuelve_none():
    """'playa de Bacuranao' es referencia a playa, no al municipio."""
    dato = {
        "id_fuente": "58680047",
        "url": "https://www.revolico.com/item/test-58680047",
        "precio": 40000,
        "moneda": "USD",
        "titulo": "Se vende casa en Celimar(playa de Bacuranao)",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.municipio is None


def test_mapear_anuncio_revolico_municipio_playa_ambigua_devuelve_none():
    """'Venta de casas en la playa' no asigna municipio."""
    dato = {
        "id_fuente": "57162643",
        "url": "https://www.revolico.com/item/test-57162643",
        "precio": 12000,
        "moneda": "USD",
        "titulo": "Venta de casas en playa",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.municipio is None


def test_mapear_anuncio_revolico_municipio_venta_en_playa_devuelve_none():
    """'VENTA EN LA PLAYA' sin contexto no asigna municipio."""
    dato = {
        "id_fuente": "58679654",
        "url": "https://www.revolico.com/item/test-58679654",
        "precio": 200,
        "moneda": "USD",
        "titulo": "VENTA EN PLAYA",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.municipio is None


def test_mapear_anuncio_revolico_municipio_cerro_compuesto_devuelve_none():
    """'cerro-plaza' es expresión compuesta, no asigna Cerro."""
    dato = {
        "id_fuente": "58679794",
        "url": "https://www.revolico.com/item/test-58679794",
        "precio": 90000,
        "moneda": "USD",
        "titulo": "Hermosa casa en el Cerro-plaza",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.municipio is None


def test_mapear_anuncio_revolico_tipo_inmueble_casa():
    """mapear_anuncio_revolico asigna tipo_inmueble='casa' cuando el título lo indica."""
    dato = {
        "id_fuente": "58397137",
        "url": "https://www.revolico.com/item/test-58397137?p",
        "precio": 25000,
        "moneda": "USD",
        "titulo": "Casa en venta en La Habana",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.tipo_inmueble == "casa"
    assert anuncio.id_fuente == "58397137"
    assert anuncio.url == "https://www.revolico.com/item/test-58397137?p"


def test_mapear_anuncio_revolico_tipo_inmueble_apartamento():
    """mapear_anuncio_revolico asigna tipo_inmueble='apartamento' cuando el título lo indica."""
    dato = {
        "id_fuente": "56318726",
        "url": "https://www.revolico.com/item/test-56318726?p",
        "precio": 40000,
        "moneda": "USD",
        "titulo": "Apartamento en el Vedado",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.tipo_inmueble == "apartamento"


def test_mapear_anuncio_revolico_tipo_inmueble_indeterminado():
    """mapear_anuncio_revolico asigna tipo_inmueble='indeterminado' para títulos genéricos."""
    dato = {
        "id_fuente": "58169727",
        "url": "https://www.revolico.com/item/test-58169727?p",
        "precio": 99000,
        "moneda": "USD",
        "titulo": "Vendo Propiedad Horizontal en el Vedado",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.tipo_inmueble == "indeterminado"


def test_mapear_anuncio_revolico_tipo_inmueble_no_vivienda():
    """mapear_anuncio_revolico asigna tipo_inmueble='no_vivienda' para productos no inmobiliarios."""
    dato = {
        "id_fuente": "58491657",
        "url": "https://www.revolico.com/item/test-58491657?p",
        "precio": 1,
        "moneda": "USD",
        "titulo": "ESMLATE sintético blanco y varios colores",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.tipo_inmueble == "no_vivienda"


def test_mapear_anuncio_revolico_conserva_precio_bajo():
    """Precios bajos se conservan sin descartar."""
    dato = {
        "id_fuente": "55580966",
        "url": "https://www.revolico.com/item/test-55580966?p",
        "precio": 6.0,
        "moneda": "USD",
        "titulo": "Venta de Propiedad en Guanabo con Gran Potencial 870m2",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.precio == 6.0
    assert anuncio.moneda == "USD"


def test_mapear_anuncio_revolico_precio_moneda_nulos():
    """Precio y moneda ausentes se conservan como None."""
    dato = {
        "id_fuente": "58679550",
        "url": "https://www.revolico.com/item/test-58679550?p",
        "precio": None,
        "moneda": None,
        "titulo": "Venta Plsya",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.precio is None
    assert anuncio.moneda is None


def test_mapear_anuncio_revolico_conserva_id_y_url():
    """El identificador numérico y la URL de Revolico se conservan."""
    dato = {
        "id_fuente": "58397137",
        "url": "https://www.revolico.com/item/oportunidad-en-playa-37-y-42-58397137?p",
        "precio": 25000,
        "moneda": "USD",
        "titulo": "Oportunidad en Playa | 37 y 42",
        "descripcion": None,
    }
    anuncio = mapear_anuncio_revolico(dato, "2026-11-07T12:00:00Z")
    assert anuncio.id_fuente == "58397137"
    assert anuncio.url == "https://www.revolico.com/item/oportunidad-en-playa-37-y-42-58397137?p"
