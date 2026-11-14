"""Pruebas para normalizar_moneda.

Comprueba cada moneda admitida, variantes de escritura, espacios, valores
desconocidos y valores ausentes.
"""

import sys

sys.path.insert(0, "src")

from data.normalization import (
    identificar_municipio_en_texto,
    identificar_municipio_en_titulo_revolico,
    identificar_municipio_gaos,
    _es_referencia_playa_geografica,
    _es_municipio_compuesto,
    normalizar_moneda,
    normalizar_tipo_inmueble,
    normalizar_tipo_operacion,
    normalizar_municipio,
    normalizar_tipo_area,
    normalizar_estado_conservacion,
    normalizar_amueblado,
    normalizar_fecha,
    normalizar_precio,
)

def test_moneda_usd():
    assert normalizar_moneda("USD") == "USD"


def test_moneda_mlc():
    assert normalizar_moneda("MLC") == "MLC"


def test_moneda_cup():
    assert normalizar_moneda("CUP") == "CUP"


def test_moneda_eur():
    assert normalizar_moneda("EUR") == "EUR"


def test_moneda_otra():
    assert normalizar_moneda("OTRA") == "OTRA"


def test_moneda_minusculas():
    assert normalizar_moneda("usd") == "USD"
    assert normalizar_moneda("mlc") == "MLC"
    assert normalizar_moneda("cup") == "CUP"
    assert normalizar_moneda("eur") == "EUR"
    assert normalizar_moneda("otra") == "OTRA"


def test_moneda_con_espacios():
    assert normalizar_moneda("  USD  ") == "USD"
    assert normalizar_moneda("\tMLC\n") == "MLC"
    assert normalizar_moneda("  CUP  ") == "CUP"


def test_moneda_mixta():
    assert normalizar_moneda("UsD") == "USD"
    assert normalizar_moneda("MlC") == "MLC"


def test_valor_desconocido_devuelve_none():
    assert normalizar_moneda("MXN") is None
    assert normalizar_moneda("GBP") is None
    assert normalizar_moneda("dolar") is None


def test_valor_ausente_devuelve_none():
    assert normalizar_moneda(None) is None


def test_valor_no_string_devuelve_none():
    assert normalizar_moneda(123) is None
    assert normalizar_moneda(0) is None


# --- Pruebas para normalizar_tipo_inmueble ---


def test_tipo_inmueble_casa():
    assert normalizar_tipo_inmueble("casa") == "casa"


def test_tipo_inmueble_apartamento():
    assert normalizar_tipo_inmueble("apartamento") == "apartamento"


def test_tipo_inmueble_apto():
    assert normalizar_tipo_inmueble("apto") == "apartamento"


def test_tipo_inmueble_apto_con_punto():
    assert normalizar_tipo_inmueble("apto.") == "apartamento"


def test_tipo_inmueble_habitacion():
    assert normalizar_tipo_inmueble("habitacion") == "habitacion"


def test_tipo_inmueble_habitacion_con_tilde():
    assert normalizar_tipo_inmueble("habitación") == "habitacion"


def test_tipo_inmueble_solar():
    assert normalizar_tipo_inmueble("solar") == "solar"


def test_tipo_inmueble_otra():
    assert normalizar_tipo_inmueble("otro") == "otro"


def test_tipo_inmueble_minusculas_y_espacios():
    assert normalizar_tipo_inmueble("  CASA  ") == "casa"
    assert normalizar_tipo_inmueble("\tApartamento\n") == "apartamento"


def test_tipo_inmueble_mixta():
    assert normalizar_tipo_inmueble("CaSa") == "casa"
    assert normalizar_tipo_inmueble("APTO.") == "apartamento"


def test_tipo_inmueble_desconocido_devuelve_none():
    assert normalizar_tipo_inmueble("chalet") is None
    assert normalizar_tipo_inmueble("oficina") is None


def test_tipo_inmueble_ausente_devuelve_none():
    assert normalizar_tipo_inmueble(None) is None


def test_tipo_inmueble_no_string_devuelve_none():
    assert normalizar_tipo_inmueble(123) is None
    assert normalizar_tipo_inmueble(0) is None


# --- Pruebas para normalizar_tipo_operacion ---


def test_tipo_operacion_venta():
    assert normalizar_tipo_operacion("venta") == "venta"


def test_tipo_operacion_alquiler():
    assert normalizar_tipo_operacion("alquiler") == "alquiler"


def test_tipo_operacion_otro():
    assert normalizar_tipo_operacion("otro") == "otro"


def test_tipo_operacion_minusculas_y_espacios():
    assert normalizar_tipo_operacion("  VENTA  ") == "venta"
    assert normalizar_tipo_operacion("\tAlquiler\n") == "alquiler"


def test_tipo_operacion_mixta():
    assert normalizar_tipo_operacion("VeNtA") == "venta"
    assert normalizar_tipo_operacion("ALQUILER") == "alquiler"


def test_tipo_operacion_desconocido_devuelve_none():
    assert normalizar_tipo_operacion("permuta") is None
    assert normalizar_tipo_operacion("compra") is None


def test_tipo_operacion_ausente_devuelve_none():
    assert normalizar_tipo_operacion(None) is None


def test_tipo_operacion_no_string_devuelve_none():
    assert normalizar_tipo_operacion(123) is None
    assert normalizar_tipo_operacion(0) is None


# --- Pruebas para normalizar_municipio ---


def test_municipio_mayusculas_a_titulo():
    assert normalizar_municipio("PLAYA") == "Playa"


def test_municipio_minusculas_a_titulo():
    assert normalizar_municipio("playa") == "Playa"


def test_municipio_espaciado():
    assert normalizar_municipio("  Plaza de la Revolución  ") == "Plaza De La Revolución"


def test_municipio_espacios_tab():
    assert normalizar_municipio("\tBoyeros\n") == "Boyeros"


def test_municipio_vacio_devuelve_none():
    assert normalizar_municipio("") is None


def test_municipio_solo_espacios_devuelve_none():
    assert normalizar_municipio("   ") is None


def test_municipio_none_devuelve_none():
    assert normalizar_municipio(None) is None


def test_municipio_no_string_devuelve_none():
    assert normalizar_municipio(123) is None
    assert normalizar_municipio(0) is None


def test_municipio_no_corrige_ortografia():
    assert normalizar_municipio("Playya") == "Playya"


# --- Pruebas para normalizar_tipo_area ---


def test_tipo_area_construida():
    assert normalizar_tipo_area("construida") == "construida"


def test_tipo_area_total():
    assert normalizar_tipo_area("total") == "total"


def test_tipo_area_parcela():
    assert normalizar_tipo_area("parcela") == "parcela"


def test_tipo_area_area_construida():
    assert normalizar_tipo_area("área construida") == "construida"


def test_tipo_area_area_construida_sin_tilde():
    assert normalizar_tipo_area("area construida") == "construida"


def test_tipo_area_construccion():
    assert normalizar_tipo_area("construcción") == "construida"


def test_tipo_area_construccion_sin_tilde():
    assert normalizar_tipo_area("construccion") == "construida"


def test_tipo_area_area_total():
    assert normalizar_tipo_area("área total") == "total"


def test_tipo_area_superficie_total():
    assert normalizar_tipo_area("superficie total") == "total"


def test_tipo_area_area_de_parcela():
    assert normalizar_tipo_area("área de parcela") == "parcela"


def test_tipo_area_terreno():
    assert normalizar_tipo_area("terreno") == "parcela"


def test_tipo_area_minusculas_y_espacios():
    assert normalizar_tipo_area("  CONSTRUIDA  ") == "construida"
    assert normalizar_tipo_area("\tTotal\n") == "total"
    assert normalizar_tipo_area("  Parcela  ") == "parcela"


def test_tipo_area_mixta():
    assert normalizar_tipo_area("ConStrUiDa") == "construida"
    assert normalizar_tipo_area("ÁREA TOTAL") == "total"


def test_tipo_area_desconocido_devuelve_none():
    assert normalizar_tipo_area("chalet") is None
    assert normalizar_tipo_area("oficina") is None


def test_tipo_area_ausente_devuelve_none():
    assert normalizar_tipo_area(None) is None


def test_tipo_area_no_string_devuelve_none():
    assert normalizar_tipo_area(123) is None
    assert normalizar_tipo_area(0) is None


# --- Pruebas para normalizar_estado_conservacion ---


def test_estado_conservacion_bueno():
    assert normalizar_estado_conservacion("bueno") == "bueno"


def test_estado_conservacion_buen_estado():
    assert normalizar_estado_conservacion("buen estado") == "bueno"


def test_estado_conservacion_regular():
    assert normalizar_estado_conservacion("regular") == "regular"


def test_estado_conservacion_estado_regular():
    assert normalizar_estado_conservacion("estado regular") == "regular"


def test_estado_conservacion_malo():
    assert normalizar_estado_conservacion("malo") == "malo"


def test_estado_conservacion_mal_estado():
    assert normalizar_estado_conservacion("mal estado") == "malo"


def test_estado_conservacion_a_reparar():
    assert normalizar_estado_conservacion("a_reparar") == "a_reparar"


def test_estado_conservacion_necesita_reparacion():
    assert normalizar_estado_conservacion("necesita reparación") == "a_reparar"


def test_estado_conservacion_necesita_reparacion_sin_tilde():
    assert normalizar_estado_conservacion("necesita reparacion") == "a_reparar"


def test_estado_conservacion_para_reparar():
    assert normalizar_estado_conservacion("para reparar") == "a_reparar"


def test_estado_conservacion_desconocido():
    assert normalizar_estado_conservacion("desconocido") == "desconocido"


def test_estado_conservacion_minusculas_y_espacios():
    assert normalizar_estado_conservacion("  BUENO  ") == "bueno"
    assert normalizar_estado_conservacion("\tMalo\n") == "malo"
    assert normalizar_estado_conservacion("  A_REPARAR  ") == "a_reparar"


def test_estado_conservacion_mixta():
    assert normalizar_estado_conservacion("BuEnO") == "bueno"
    assert normalizar_estado_conservacion("NEcesita RePARACIÓN") == "a_reparar"


def test_estado_conservacion_desconocido_devuelve_none():
    assert normalizar_estado_conservacion("excelente") is None
    assert normalizar_estado_conservacion("nuevo") is None


def test_estado_conservacion_ausente_devuelve_none():
    assert normalizar_estado_conservacion(None) is None


def test_estado_conservacion_no_string_devuelve_none():
    assert normalizar_estado_conservacion(123) is None
    assert normalizar_estado_conservacion(0) is None


# --- Pruebas para normalizar_amueblado ---


def test_amueblado_si_con_tilde():
    assert normalizar_amueblado("sí") is True


def test_amueblado_si_sin_tilde():
    assert normalizar_amueblado("si") is True


def test_amueblado_true():
    assert normalizar_amueblado("true") is True


def test_amueblado_uno():
    assert normalizar_amueblado("1") is True


def test_amueblado_amueblado():
    assert normalizar_amueblado("amueblado") is True


def test_amueblado_amueblada():
    assert normalizar_amueblado("amueblada") is True


def test_amueblado_no():
    assert normalizar_amueblado("no") is False


def test_amueblado_false():
    assert normalizar_amueblado("false") is False


def test_amueblado_cero():
    assert normalizar_amueblado("0") is False


def test_amueblado_sin_amueblar():
    assert normalizar_amueblado("sin amueblar") is False


def test_amueblado_minusculas_y_espacios():
    assert normalizar_amueblado("  SÍ  ") is True
    assert normalizar_amueblado("\tNo\n") is False
    assert normalizar_amueblado("  AMUEBLADO  ") is True


def test_amueblado_mixta():
    assert normalizar_amueblado("Si") is True
    assert normalizar_amueblado("AMUEBLADA") is True


def test_amueblado_desconocido_devuelve_none():
    assert normalizar_amueblado("tal vez") is None
    assert normalizar_amueblado("parcialmente") is None


def test_amueblado_ausente_devuelve_none():
    assert normalizar_amueblado(None) is None


def test_amueblado_vacio_devuelve_none():
    assert normalizar_amueblado("") is None


def test_amueblado_solo_espacios_devuelve_none():
    assert normalizar_amueblado("   ") is None


def test_amueblado_bool_true_devuelve_true():
    assert normalizar_amueblado(True) is True


def test_amueblado_bool_false_devuelve_false():
    assert normalizar_amueblado(False) is False


def test_amueblado_int_uno_devuelve_none():
    assert normalizar_amueblado(1) is None


def test_amueblado_int_cero_devuelve_none():
    assert normalizar_amueblado(0) is None


def test_amueblado_numero_distinto_devuelve_none():
    assert normalizar_amueblado(2) is None
    assert normalizar_amueblado(10) is None


# --- Pruebas para normalizar_fecha ---


from datetime import date, datetime


def test_fecha_iso_solo_fecha():
    assert normalizar_fecha("2026-11-04") == "2026-11-04"


def test_fecha_iso_con_hora():
    assert normalizar_fecha("2026-11-04T10:30:00") == "2026-11-04"


def test_fecha_iso_con_hora_y_zona_horaria():
    assert normalizar_fecha("2026-11-04T10:30:00+00:00") == "2026-11-04"


def test_fecha_iso_con_hora_y_zona_horaria_negativa():
    assert normalizar_fecha("2026-11-04T10:30:00-05:00") == "2026-11-04"


def test_fecha_objeto_date():
    assert normalizar_fecha(date(2026, 11, 4)) == "2026-11-04"


def test_fecha_objeto_datetime():
    assert normalizar_fecha(datetime(2026, 11, 4, 10, 30, 0)) == "2026-11-04"


def test_fecha_con_espacios():
    assert normalizar_fecha("  2026-11-04  ") == "2026-11-04"


def test_fecha_desconocida_devuelve_none():
    assert normalizar_fecha("04/11/2026") is None
    assert normalizar_fecha("4 de noviembre de 2026") is None
    assert normalizar_fecha("hoy") is None


def test_fecha_ausente_devuelve_none():
    assert normalizar_fecha(None) is None


def test_fecha_vacia_devuelve_none():
    assert normalizar_fecha("") is None


def test_fecha_solo_espacios_devuelve_none():
    assert normalizar_fecha("   ") is None


def test_fecha_no_string_devuelve_none():
    assert normalizar_fecha(123) is None
    assert normalizar_fecha(0) is None
    assert normalizar_fecha(True) is None
    assert normalizar_fecha(False) is None


# --- Pruebas para normalizar_precio ---


def test_precio_simple_usd():
    importe, moneda = normalizar_precio("150000 USD")
    assert importe == 150000.0
    assert moneda == "USD"


def test_precio_con_espacios_miles():
    importe, moneda = normalizar_precio("150 000 USD")
    assert importe == 150000.0
    assert moneda == "USD"


def test_precio_con_punto_miles_devuelve_none():
    """150.000 es ambiguo sin contexto: puede ser miles o decimales."""
    assert normalizar_precio("150.000 USD") == (None, None)


def test_precio_con_coma_miles_devuelve_none():
    """150,000 es ambiguo sin contexto: puede ser miles o decimales."""
    assert normalizar_precio("150,000 USD") == (None, None)


def test_precio_con_decimal_punto():
    importe, moneda = normalizar_precio("150.50 USD")
    assert importe == 150.50
    assert moneda == "USD"


def test_precio_con_decimal_coma():
    importe, moneda = normalizar_precio("150,50 USD")
    assert importe == 150.50
    assert moneda == "USD"


def test_precio_mlc():
    importe, moneda = normalizar_precio("750 MLC")
    assert importe == 750.0
    assert moneda == "MLC"


def test_precio_cup():
    importe, moneda = normalizar_precio("50000 CUP")
    assert importe == 50000.0
    assert moneda == "CUP"


def test_precio_eur():
    importe, moneda = normalizar_precio("1200 EUR")
    assert importe == 1200.0
    assert moneda == "EUR"


def test_precio_moneda_desconocida_devuelve_none():
    """Moneda no admitida: se rechaza sin asignar moneda por defecto."""
    assert normalizar_precio("100 XYZ") == (None, None)
    assert normalizar_precio("100 MON") == (None, None)


def test_precio_sin_moneda():
    importe, moneda = normalizar_precio("150000")
    assert importe == 150000.0
    assert moneda is None


def test_precio_con_ambos_separadores_devuelve_none():
    """Ambos separadores sin contexto es ambiguo."""
    assert normalizar_precio("1.000,50 USD") == (None, None)
    assert normalizar_precio("1,000.50 USD") == (None, None)


def test_precio_mayusculas_minusculas():
    importe, moneda = normalizar_precio("150000 usd")
    assert importe == 150000.0
    assert moneda == "USD"


def test_precio_con_espacios_sobrantes():
    importe, moneda = normalizar_precio("  150000 USD  ")
    assert importe == 150000.0
    assert moneda == "USD"


def test_precio_ambiguo_punto_un_digito():
    """Punto seguido de 1 dígito es decimal."""
    importe, moneda = normalizar_precio("150.0 USD")
    assert importe == 150.0
    assert moneda == "USD"


def test_precio_valor_desconocido_devuelve_none():
    assert normalizar_precio("abc USD") == (None, None)
    assert normalizar_precio("USD 150000") == (None, None)
    assert normalizar_precio("150000 MON") == (None, None)


def test_precio_ambiguo_devuelve_none():
    """Punto seguido de 4 dígitos es ambiguo."""
    assert normalizar_precio("150.0000 USD") == (None, None)


def test_precio_nulo_devuelve_none():
    assert normalizar_precio(None) == (None, None)


def test_precio_vacio_devuelve_none():
    assert normalizar_precio("") == (None, None)


def test_precio_solo_espacios_devuelve_none():
    assert normalizar_precio("   ") == (None, None)


def test_precio_no_string_devuelve_none():
    assert normalizar_precio(123) == (None, None)
    assert normalizar_precio(0) == (None, None)
    assert normalizar_precio(True) == (None, None)


# --- Pruebas para _es_referencia_playa_geografica ---


def test_es_referencia_playa_geografica_cerca_de_la_playa():
    assert _es_referencia_playa_geografica("cerca de la playa") is True


def test_es_referencia_playa_geografica_playa_de():
    assert _es_referencia_playa_geografica("playa de Bacuranao") is True


def test_es_referencia_playa_geografica_en_playa():
    """'en playa' al final del título se considera referencia a playa geográfica."""
    assert _es_referencia_playa_geografica("en playa") is True


def test_es_referencia_playa_geografica_no_playa():
    """'Casa en Playa' sola se considera posible referencia a playa geográfica."""
    assert _es_referencia_playa_geografica("Casa en Playa") is True
    assert _es_referencia_playa_geografica("Oportunidad en Playa") is True


def test_es_referencia_playa_geografica_none():
    assert _es_referencia_playa_geografica(None) is False


# --- Pruebas para _es_municipio_compuesto ---


def test_es_municipio_compuesto_guion():
    assert _es_municipio_compuesto("Cerro", "el Cerro-plaza") is True


def test_es_municipio_compuesto_no_compuesto():
    assert _es_municipio_compuesto("Cerro", "en el Cerro") is False


def test_es_municipio_compuesto_none():
    assert _es_municipio_compuesto(None, "texto") is False
    assert _es_municipio_compuesto("Cerro", None) is False


# --- Pruebas para identificar_municipio_en_titulo_revolico ---


def test_identificar_municipio_revolico_playa_geografica_devuelve_none():
    """Referencia a playa geográfica no debe asignar municipio Playa."""
    assert identificar_municipio_en_titulo_revolico(
        "cercanía a la playa y tranquilidad en brisas del mar, guanabo"
    ) is None
    assert identificar_municipio_en_titulo_revolico(
        "Se vende casa en Celimar(playa de Bacuranao)"
    ) is None


def test_identificar_municipio_revolico_playa_ambigua_devuelve_none():
    """'en playa' al final o seguido de separador se considera playa geográfica."""
    assert identificar_municipio_en_titulo_revolico("Venta de casas en la playa") is None
    assert identificar_municipio_en_titulo_revolico("VENTA EN LA PLAYA") is None
    assert identificar_municipio_en_titulo_revolico("Oportunidad en Playa | 37 y 42") is None
    assert identificar_municipio_en_titulo_revolico("Venta de casas en playa") is None


def test_identificar_municipio_revolico_playa_municipio():
    """'en la zona de Playa' con contexto de zona se asigna al municipio."""
    assert identificar_municipio_en_titulo_revolico("Apartamento en la zona de Playa") == "Playa"
    assert identificar_municipio_en_titulo_revolico("Casa en zona de Playa | 37 y 42") == "Playa"


def test_identificar_municipio_revolico_cerro_compuesto_devuelve_none():
    """'cerro-plaza' es expresión compuesta, no se asigna Cerro."""
    assert identificar_municipio_en_titulo_revolico("Hermosa casa en el Cerro-plaza") is None


def test_identificar_municipio_revolico_cerro_claro():
    """'en el Cerro' con artículo claro se asigna al municipio Cerro."""
    assert identificar_municipio_en_titulo_revolico("Casa en el Cerro") == "Cerro"


def test_identificar_municipio_revolico_none():
    assert identificar_municipio_en_titulo_revolico(None) is None
    assert identificar_municipio_en_titulo_revolico("") is None


# --- Pruebas para identificar_municipio_gaos ---


def test_identificar_municipio_gaos_titulo_y_direccion_coinciden():
    """Título y dirección coinciden: se usa ese municipio."""
    municipio, contradiccion = identificar_municipio_gaos(
        "Casa en Playa", "Playa, La Habana"
    )
    assert municipio == "Playa"
    assert contradiccion is False


def test_identificar_municipio_gaos_solo_titulo():
    """Solo el título identifica municipio."""
    municipio, contradiccion = identificar_municipio_gaos(
        "Casa en zona de Playa", None
    )
    assert municipio == "Playa"
    assert contradiccion is False


def test_identificar_municipio_gaos_solo_direccion():
    """Solo la dirección identifica municipio."""
    municipio, contradiccion = identificar_municipio_gaos(
        None, "Playa, La Habana"
    )
    assert municipio == "Playa"
    assert contradiccion is False


def test_identificar_municipio_gaos_contradiccion():
    """Título y dirección indican municipios diferentes: None y contradicción."""
    municipio, contradiccion = identificar_municipio_gaos(
        "Casa en Centro Habana", "Playa, La Habana"
    )
    assert municipio is None
    assert contradiccion is True


def test_identificar_municipio_gaos_sin_identificacion():
    """Ninguno identifica municipio: None."""
    municipio, contradiccion = identificar_municipio_gaos(
        "Casa en venta", "Calle 23"
    )
    assert municipio is None
    assert contradiccion is False


def test_identificar_municipio_gaos_none_argumentos():
    assert identificar_municipio_gaos(None, None) == (None, False)


def test_identificar_municipio_gaos_playa_geografica_titulo_devuelve_none():
    """Título con referencia a playa geográfica no asigna municipio Playa."""
    municipio, contradiccion = identificar_municipio_gaos(
        "Venta de apartamento en Guanabo,a 7 cuadras de la playa aproximadamente",
        "Peñas Altas, La Habana",
    )
    assert municipio is None
    assert contradiccion is False


def test_identificar_municipio_gaos_playa_geografica_direccion_valida():
    """Dirección con municipio Playa se usa aunque el título tenga playa geográfica."""
    municipio, contradiccion = identificar_municipio_gaos(
        "Venta de apartamento en Guanabo,a 7 cuadras de la playa aproximadamente",
        "Playa, La Habana",
    )
    assert municipio == "Playa"
    assert contradiccion is False


def test_identificar_municipio_gaos_playa_legitima_titulo():
    """Título con 'Playa' sin referencia a playa geográfica se asigna."""
    municipio, contradiccion = identificar_municipio_gaos(
        "Casa en zona de Playa", None
    )
    assert municipio == "Playa"
    assert contradiccion is False


def test_identificar_municipio_gaos_playa_geografica_sin_direccion_devuelve_none():
    """Solo título con playa geográfica, sin dirección: None."""
    municipio, contradiccion = identificar_municipio_gaos(
        "7 cuadras de la playa aproximadamente", None
    )
    assert municipio is None
    assert contradiccion is False


# --- Pruebas para identificar_municipio_en_texto ---


def test_identificar_municipio_texto_claro():
    assert identificar_municipio_en_texto("Casa en Playa") == "Playa"
    assert identificar_municipio_en_texto("Apartamento en Centro Habana") == "Centro Habana"
    assert identificar_municipio_en_texto("Vivienda en La Lisa") == "La Lisa"


def test_identificar_municipio_con_tildes():
    assert identificar_municipio_en_texto("Casa en Plaza de la Revolución") == "Plaza de la Revolución"
    assert identificar_municipio_en_texto("Apartamento en San Miguel del Padrón") == "San Miguel del Padrón"
    assert identificar_municipio_en_texto("Venta en La Habana del Este") == "La Habana del Este"


def test_identificar_municipio_mayusculas():
    assert identificar_municipio_en_texto("CASA EN PLAYA") == "Playa"
    assert identificar_municipio_en_texto("Apartamento EN CENTRO HABANA") == "Centro Habana"


def test_identificar_municipio_sin_tildes_en_texto():
    assert identificar_municipio_en_texto("Casa en Plaza de la Revolucion") == "Plaza de la Revolución"
    assert identificar_municipio_en_texto("Vivienda en San Miguel del Padron") == "San Miguel del Padrón"


def test_identificar_municipio_ambiguo_devuelve_none():
    assert identificar_municipio_en_texto("Casa en Playa y Centro Habana") is None
    assert identificar_municipio_en_texto("Playa y Centro Habana") is None


def test_identificar_municipio_sin_coincidencia_devuelve_none():
    assert identificar_municipio_en_texto("Casa en Vedado") is None
    assert identificar_municipio_en_texto("Apartamento en Miramar") is None
    assert identificar_municipio_en_texto("Venta en Guanabo") is None
    assert identificar_municipio_en_texto("Casa en La Habana") is None


def test_identificar_municipio_none_devuelve_none():
    assert identificar_municipio_en_texto(None) is None


def test_identificar_municipio_vacio_devuelve_none():
    assert identificar_municipio_en_texto("") is None
    assert identificar_municipio_en_texto("   ") is None


def test_identificar_municipio_no_string_devuelve_none():
    assert identificar_municipio_en_texto(123) is None
    assert identificar_municipio_en_texto(0) is None


def test_identificar_municipio_word_boundary():
    # 'playa' como subcadena de otra palabra no debe coincidir
    assert identificar_municipio_en_texto("Casera en venta") is None
    # 'playa' como palabra completa sí debe coincidir
    assert identificar_municipio_en_texto("Casa en Playa") == "Playa"
