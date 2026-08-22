"""Cuando es el proximo pago y cuantos dias faltan.

# La regla

Pago fijo el 24 de cada mes, pero solo en dia habil: si el 24 cae en fin de
semana o festivo en Colombia, se corre hacia atras (nunca hacia adelante) hasta
el primer dia habil anterior. Ejemplos, tal como los describio Juan:

  24 domingo          -> viernes anterior
  24 lunes festivo    -> viernes anterior (salta el fin de semana entero)
  24 jueves festivo   -> miercoles anterior

Es la misma regla en los tres casos: retroceder dia por dia desde el 24 hasta
encontrar uno que no sea sabado, domingo, ni festivo.

# Festivos: por que una libreria y no un fetch a una pagina

Los festivos colombianos no son un dato que cambie: siguen la Ley Emiliani
(Ley 51 de 1983), una regla fija y calculable — festivos como Año Nuevo o
Navidad quedan en su fecha, y los demas se corren al lunes siguiente si no
caen ya en lunes. Scrapear una pagina web para esto agrega una dependencia de
red y de HTML ajeno para calcular algo que es pura aritmetica de calendario.
La libreria `holidays` (PyPI) ya lo implementa, mantenida y verificada contra
el calendario oficial; se probo contra 2026 antes de usarla.

# Zona horaria

"Hoy" se calcula en America/Bogota explicitamente, no con la hora del sistema.
El container puede correr en UTC; sin esto, cerca de la medianoche colombiana
el calculo podria adelantarse o atrasarse un dia respecto a lo que Juan ve en
su reloj.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import holidays

PAYDAY_DAY = 24
TIMEZONE = ZoneInfo("America/Bogota")


def _is_business_day(day: date, co_holidays: holidays.HolidayBase) -> bool:
    return day.weekday() < 5 and day not in co_holidays


def _adjusted_payday(year: int, month: int, co_holidays: holidays.HolidayBase) -> date:
    """El 24 de `month`, corrido hacia atras hasta el primer dia habil."""
    day = date(year, month, PAYDAY_DAY)
    while not _is_business_day(day, co_holidays):
        day -= timedelta(days=1)
    return day


def _today_in_bogota() -> date:
    return datetime.now(TIMEZONE).date()


def next_payday(today: date | None = None) -> date:
    """Proximo pago desde `today` (o desde hoy en Bogota si no se pasa)."""
    today = today or _today_in_bogota()

    # Rango de dos años natural para cubrir el caso "hoy es enero, el pago
    # ajustado de diciembre pasado ya paso, hay que mirar el de este mes".
    co_holidays = holidays.Colombia(years=[today.year, today.year + 1])

    candidate = _adjusted_payday(today.year, today.month, co_holidays)
    if candidate >= today:
        return candidate

    next_month = today.month + 1
    next_year = today.year
    if next_month > 12:
        next_month = 1
        next_year += 1
    return _adjusted_payday(next_year, next_month, co_holidays)


def days_left(today: date | None = None) -> dict:
    today = today or _today_in_bogota()
    payday = next_payday(today)
    return {"next_payday": payday.isoformat(), "days_left": (payday - today).days}
