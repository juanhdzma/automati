"""Prende o apaga un switch de la casa segun el estado en que este.

Reemplaza `light.py` y `fan.py` de los scripts originales, que eran el mismo
archivo copiado con un `entity_id` distinto. Aca el device es un parametro.

# El flujo

  1. se lee el estado actual del device
  2. si es `unavailable`, se corta: mandar el comando seria tirarlo al vacio
  3. se elige el servicio contrario al estado leido
  4. se llama `switch/turn_on` o `switch/turn_off`

# Por que `ensure_available` esta comentado (2026-08-22)

Durante mucho tiempo el paso 1 fue `ensure_available`, que recargaba la
integracion Tuya antes de leer. La prueba contra la casa real mostro lo
contrario de lo esperado: **con el device sano, el reload rompe el comando que
va inmediatamente despues**. Corriendo con reload, el `turn_on` salio 200 y el
estado nunca se movio; sin reload, el mismo comando funciono al instante.

La explicacion probable es que recargar el config entry corta la sesion con la
nube de Tuya, y el comando siguiente cae en esa ventana.

El desync que motivo el reload resulto ser otra cosa: los devices se habian
quedado sin WiFi despues de un cambio de SSID. Ningun reload podia arreglar eso,
y de hecho no lo arreglo en ninguno de los ~10 intentos.

Se deja el codigo comentado, no borrado, hasta acumular unos dias de uso. Si el
desync no reaparece, se elimina junto con `availability.py`.

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


async def toggle(client: HomeAssistantClient, device: Device) -> ToggleResult:
    # Version con reload previo. Rompe el comando siguiente; ver el docstring.
    # state = await ensure_available(client, device.entity_id)

    state = (await client.get_state(device.entity_id)).get("state")
    if state in UNAVAILABLE_STATES:
        raise DeviceUnavailable(device.entity_id)

    # Cualquier estado que no sea "on" se trata como apagado. HA puede devolver
    # otros valores en el medio de una transicion; ante la duda, prender.
    turning_off = state == "on"
    service = "turn_off" if turning_off else "turn_on"
    await client.call_service(
        SWITCH_DOMAIN, service, {"entity_id": device.entity_id}
    )

    result = ToggleResult(
        entity_id=device.entity_id,
        label=device.label,
        previous_state=state,
        state="off" if turning_off else "on",
    )
    logger.info(
        "Toggle aplicado",
        extra={
            "entity_id": result.entity_id,
            "previous_state": result.previous_state,
            "state": result.state,
        },
    )
    return result
