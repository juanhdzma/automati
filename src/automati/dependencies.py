from fastapi import Request

from .logic.smart_home.client import HomeAssistantClient
from .logic.smart_home.store import TimerStore


def get_ha_client(request: Request) -> HomeAssistantClient:
    return request.app.state.ha_client


def get_timer_store(request: Request) -> TimerStore:
    return request.app.state.timer_store
