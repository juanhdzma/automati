"""Tests de la regla de pago: el 24, corrido hacia atras al dia habil anterior.

Los casos de "24 en festivo" se prueban con un festivo sintetico inyectado en
`_adjusted_payday`, no buscando una coincidencia real en el calendario: que el
24 caiga justo en festivo un año dado es azar del calendario, no algo en lo que
apoyar un test que tiene que seguir pasando en cualquier año futuro.
"""

from datetime import date

from automati.logic.scriptable_ios import payday


def test_24_domingo_paga_el_viernes_anterior():
    # Mayo 2026: el 24 cae domingo, sin festivos de por medio.
    assert date(2026, 5, 24).weekday() == 6
    assert payday.next_payday(date(2026, 5, 1)) == date(2026, 5, 22)


def test_24_habil_paga_el_mismo_24():
    # Septiembre 2026: el 24 cae jueves, ni festivo ni fin de semana.
    assert date(2026, 9, 24).weekday() == 3
    assert payday.next_payday(date(2026, 9, 1)) == date(2026, 9, 24)


def test_24_lunes_festivo_paga_el_viernes_anterior():
    festivo_sintetico = {date(2026, 8, 24)}  # lunes

    resultado = payday._adjusted_payday(2026, 8, festivo_sintetico)

    assert resultado == date(2026, 8, 21)  # viernes: salta sab y dom tambien


def test_24_jueves_festivo_paga_el_miercoles_anterior():
    festivo_sintetico = {date(2026, 9, 24)}  # jueves

    resultado = payday._adjusted_payday(2026, 9, festivo_sintetico)

    assert resultado == date(2026, 9, 23)


def test_si_ya_paso_el_pago_de_este_mes_devuelve_el_del_siguiente():
    # El pago de septiembre 2026 (jueves 24, habil) ya paso el dia 25.
    # Octubre 2026 el 24 cae sabado, sin festivo cerca -> corre a viernes 23.
    despues_del_pago = date(2026, 9, 25)

    assert payday.next_payday(despues_del_pago) == date(2026, 10, 23)


def test_el_dia_del_pago_faltan_cero_dias():
    resultado = payday.days_left(date(2026, 9, 24))

    assert resultado == {"next_payday": "2026-09-24", "days_left": 0}


def test_diciembre_a_enero_cruza_el_año():
    despues_del_pago_de_diciembre = date(2026, 12, 25)  # 24 dic 2026 = jueves, habil

    resultado = payday.next_payday(despues_del_pago_de_diciembre)

    assert resultado.year == 2027
    assert resultado.month == 1
