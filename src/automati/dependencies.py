"""Dependencias compartidas por los routers.

El cliente de Home Assistant se construye una sola vez en el lifespan de la app
(ver `main.py`) y se guarda en `app.state`. Esta funcion solo lo saca de ahi.

Pasarlo como dependencia de FastAPI en vez de importarlo como global permite que
los tests lo reemplacen por un doble con `app.dependency_overrides`.
"""

from fastapi import Request

from .logic.smart_home.client import HomeAssistantClient
from .logic.smart_home.store import TimerStore


def get_ha_client(request: Request) -> HomeAssistantClient:
    return request.app.state.ha_client


def get_timer_store(request: Request) -> TimerStore:
    return request.app.state.timer_store
