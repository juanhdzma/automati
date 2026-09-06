"""Rutas HTTP de las automatizaciones de smart home.

Esta capa valida la entrada, traduce el resultado a JSON y mapea errores a codigos
HTTP. **No habla con Home Assistant**: para eso llama a `logic/smart_home/`.

Mantener ese limite es lo que hace que la estructura sirva. Una seccion nueva de
automatizaciones (widgets de iPhone, por ejemplo) es una carpeta en `logic/` y un
router como este, sin tocar nada de lo que ya existe.

# Codigos de error

  503 — el device no responde. Reintentar mas tarde.
  502 — Home Assistant no contesto o devolvio error. El problema esta un nivel mas
        arriba: HA caido, token vencido, URL mal.
  422 — el `item` no esta en el registry, o `seconds` esta fuera de rango.
"""

from enum import Enum

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_ha_client, get_timer_store
from ..logic.smart_home import toggle as toggle_logic
from ..logic.smart_home.client import HomeAssistantClient
from ..logic.smart_home.devices import DEVICES
from ..logic.smart_home.schedule import start_timer
from ..logic.smart_home.store import TimerStore

router = APIRouter(prefix="/smart-home", tags=["smart-home"])


class Item(str, Enum):
    """Devices controlables, tal como se mandan en el query param `item`.

    Se escriben a mano en vez de generarse desde `DEVICES` para que FastAPI los
    liste en la documentacion de /docs. Un test verifica que no se desincronicen.
    """

    light = "light"
    fan = "fan"
    curtain = "curtain"


class TimerItem(str, Enum):
    light = "light"
    fan = "fan"


@router.post("/toggle")
async def toggle_item(
    item: Item,
    client: HomeAssistantClient = Depends(get_ha_client),
) -> dict[str, str]:
    """Invierte el estado de un device: `POST /smart-home/toggle?item=light`."""
    device = DEVICES[item.value]
    try:
        result = await toggle_logic.toggle(client, device)
    except toggle_logic.DeviceUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Home Assistant no respondio: {exc}",
        ) from exc

    return {
        "item": item.value,
        "label": result.label,
        "entity_id": result.entity_id,
        "previous_state": result.previous_state,
        "state": result.state,
    }


@router.post("/timer")
async def timer_item(
    item: TimerItem,
    seconds: int = Query(gt=0, le=86400, description="Cuanto tiempo queda prendido"),
    client: HomeAssistantClient = Depends(get_ha_client),
    store: TimerStore = Depends(get_timer_store),
) -> dict[str, str | int]:
    """Prende un device y lo apaga solo despues: `POST /smart-home/timer?item=fan&seconds=1800`.

    Responde apenas prende, sin esperar el apagado. El apagado corre despues en
    background y sobrevive a un redeploy del servicio.

    No hay forma de cancelarlo por HTTP a proposito: apagar es idempotente, asi
    que si el device se apaga a mano antes de tiempo, el apagado programado no
    cambia nada cuando llegue.

    El tope de 86400 (un dia) es arbitrario pero deliberado: mas alla de eso ya no
    es un timer, es una automatizacion recurrente, y eso necesita otra cosa.
    """
    device = DEVICES[item.value]
    try:
        result = await start_timer(client, store, item.value, seconds)
    except toggle_logic.DeviceUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Home Assistant no respondio: {exc}",
        ) from exc

    return {
        "item": item.value,
        "label": result.label,
        "entity_id": device.entity_id,
        "state": result.state,
        "off_in_seconds": seconds,
    }
