from enum import Enum

from fastapi import APIRouter, Depends, Query, Request

from ..logic.smart_home import toggle as toggle_logic
from ..logic.smart_home.client import TuyaClient
from ..logic.smart_home.devices import DEVICES
from ..logic.smart_home.schedule import start_timer
from ..logic.smart_home.store import TimerStore

router = APIRouter(prefix="/smart-home", tags=["smart-home"])

Item = Enum("Item", {k: k for k in DEVICES}, type=str)
TimerItem = Enum(
    "TimerItem", {k: k for k, d in DEVICES.items() if d.kind == "switch"}, type=str
)


def get_device_client(request: Request) -> TuyaClient:
    return request.app.state.device_client


def get_timer_store(request: Request) -> TimerStore:
    return request.app.state.timer_store


@router.post("/toggle")
async def toggle_item(
    item: Item,
    client: TuyaClient = Depends(get_device_client),
) -> dict[str, str]:
    """Invierte el estado de un device: `POST /smart-home/toggle?item=light`."""
    device = DEVICES[item.value]
    result = await toggle_logic.toggle(client, device)

    return {
        "item": item.value,
        "label": result.label,
        "previous_state": result.previous_state,
        "state": result.state,
    }


@router.post("/timer")
async def timer_item(
    item: TimerItem,
    seconds: int = Query(gt=0, le=86400, description="Cuanto tiempo queda prendido"),
    client: TuyaClient = Depends(get_device_client),
    store: TimerStore = Depends(get_timer_store),
) -> dict[str, str | int]:
    """Prende un device y lo apaga solo despues: `POST /smart-home/timer?item=fan&seconds=1800`."""
    result = await start_timer(client, store, item.value, seconds)

    return {
        "item": item.value,
        "label": result.label,
        "state": result.state,
        "off_in_seconds": seconds,
    }
