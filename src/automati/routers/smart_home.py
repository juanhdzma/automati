"""Rutas HTTP de las automatizaciones de smart home.

Esta capa valida la entrada, traduce el resultado a JSON y mapea errores a codigos
HTTP. **No habla con Home Assistant**: para eso llama a `logic/smart_home/`.

Mantener ese limite es lo que hace que la estructura sirva. Una seccion nueva de
automatizaciones (widgets de iPhone, por ejemplo) es una carpeta en `logic/` y un
router como este, sin tocar nada de lo que ya existe.

# Codigos de error

  503 — el device reporta `unavailable`, o sea que no esta conectado a la nube
        de Tuya. Casi siempre es un problema de WiFi del aparato.
  502 — Home Assistant no contesto o devolvio error. El problema esta un nivel mas
        arriba: HA caido, token vencido, URL mal.
  422 — el `item` no esta en el registry. Lo valida FastAPI con el enum.
"""

from enum import Enum

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_ha_client
from ..logic.smart_home import toggle as toggle_logic
from ..logic.smart_home.client import HomeAssistantClient
from ..logic.smart_home.devices import DEVICES

router = APIRouter(prefix="/smart-home", tags=["smart-home"])


class Item(str, Enum):
    """Devices toggleables, tal como se mandan en el query param `item`.

    Se escriben a mano en vez de generarse desde `DEVICES` para que FastAPI los
    liste en la documentacion de /docs. Un test verifica que no se desincronicen.
    """

    light = "light"
    fan = "fan"


@router.post("/toggle")
async def toggle_item(
    item: Item,
    client: HomeAssistantClient = Depends(get_ha_client),
) -> dict[str, str]:
    """Invierte el estado de un device: `POST /smart-home/toggle?item=light`.

    Responde en ~0.3s: una lectura de estado y una llamada de servicio.
    """
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
