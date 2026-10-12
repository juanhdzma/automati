from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import holidays

PAYDAY_DAY = 24
# El container corre en UTC: "hoy" se calcula en Bogota para no correrse un dia.
TIMEZONE = ZoneInfo("America/Bogota")


def _is_business_day(day: date, co_holidays: holidays.HolidayBase) -> bool:
    return day.weekday() < 5 and day not in co_holidays


def _adjusted_payday(year: int, month: int, co_holidays: holidays.HolidayBase) -> date:
    day = date(year, month, PAYDAY_DAY)
    while not _is_business_day(day, co_holidays):
        day -= timedelta(days=1)
    return day


def _today_in_bogota() -> date:
    return datetime.now(TIMEZONE).date()


def next_payday(today: date | None = None) -> date:
    today = today or _today_in_bogota()
    co_holidays = holidays.Colombia(years=[today.year, today.year + 1])

    candidate = _adjusted_payday(today.year, today.month, co_holidays)
    if candidate >= today:
        return candidate

    return _adjusted_payday(
        today.year + today.month // 12, today.month % 12 + 1, co_holidays
    )


def days_left(today: date | None = None) -> dict:
    today = today or _today_in_bogota()
    payday = next_payday(today)
    return {"next_payday": payday.isoformat(), "days_left": (payday - today).days}
