"""Prende o apaga un switch de la casa segun el estado en que este.

Reemplaza `light.py` y `fan.py` de los scripts originales, que eran el mismo
archivo copiado con un `entity_id` distinto. Aca el device es un parametro.

# El flujo

  1. se lee el estado actual del device
  2. si es `unavailable`, se corta: mandar el comando seria tirarlo al vacio
  3. se elige el servicio contrario al estado leido
  4. se llama `switch/turn_on` o `switch/turn_off`

# Historial (2026-08-22)

Hubo una version que recargaba la integracion Tuya antes de leer el estado,
pensando que los devices se desincronizaban del docker de Home Assistant.
Probado contra la casa real, resulto contraproducente: con el device sano, ese
reload rompia el comando que iba justo despues (200 de HA, el aparato sin
moverse). Y el desync real que lo motivo era otra cosa: un cambio de SSID habia
dejado los devices sin WiFi. Se elimino ese codigo (`availability.py`, `tuya.py`)
una vez confirmado que no hacia falta.

# Por que no se usa el servicio `toggle` de Home Assistant

Despues del paso 1 ya tenemos el estado real en la mano, asi que mandar el servicio
explicito no cuesta nada extra y deja dos ventajas: la respuesta de la API puede
decir de que estado a cual se paso, y queda registrado en el log que se pidio
exactamente. Con `toggle` habria que confiar en que HA decida bien y no sabriamos
que decidio.
"""

import logging
from dataclasses import dataclass

from .client import HomeAssistantClient
from .devices import Device

logger = logging.getLogger(__name__)

SWITCH_DOMAIN = "switch"

# Home Assistant usa `unavailable` cuando la entidad no responde. Tratamos la
# ausencia de estado (None) igual: en ninguno de los dos casos se puede actuar.
UNAVAILABLE_STATES = frozenset({"unavailable", None})


class DeviceUnavailable(Exception):
    """El device reporta `unavailable`: no esta conectado a la nube de Tuya.

    Es un error real y hay que propagarlo: si se ignorara y se mandara el comando
    igual, Home Assistant contestaria 200 y el aparato no haria nada.
    """

    def __init__(self, entity_id: str) -> None:
        super().__init__(f"'{entity_id}' sigue unavailable")
        self.entity_id = entity_id


@dataclass(frozen=True)
class ToggleResult:
    entity_id: str
    label: str
    previous_state: str
    state: str


async def read_state(client: HomeAssistantClient, device: Device) -> str:
    """Estado actual del device. Revienta si no esta conectado.

    Cortar aca es el punto: si el device esta desconectado de la nube de Tuya,
    Home Assistant acepta el comando con 200 y el aparato no hace nada.
    """
    # Version con reload previo. Rompe el comando siguiente; ver el docstring.
    # state = await ensure_available(client, device.entity_id)

    state = (await client.get_state(device.entity_id)).get("state")
    if state in UNAVAILABLE_STATES:
        raise DeviceUnavailable(device.entity_id)
    return state


async def set_power(
    client: HomeAssistantClient, device: Device, on: bool
) -> ToggleResult:
    """Prende o apaga sin importar como estaba. Idempotente."""
    previous = await read_state(client, device)
    service = "turn_on" if on else "turn_off"
    await client.call_service(
        SWITCH_DOMAIN, service, {"entity_id": device.entity_id}
    )

    result = ToggleResult(
        entity_id=device.entity_id,
        label=device.label,
        previous_state=previous,
        state="on" if on else "off",
    )
    logger.info(
        "Switch aplicado",
        extra={
            "entity_id": result.entity_id,
            "service": service,
            "previous_state": result.previous_state,
            "state": result.state,
        },
    )
    return result


async def toggle(client: HomeAssistantClient, device: Device) -> ToggleResult:
    # Cualquier estado que no sea "on" se trata como apagado. HA puede devolver
    # otros valores en el medio de una transicion; ante la duda, prender.
    state = await read_state(client, device)
    return await set_power(client, device, on=state != "on")
