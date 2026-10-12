import logging
from dataclasses import dataclass

from .client import HomeAssistantClient
from .devices import Device

logger = logging.getLogger(__name__)

DOMAIN_ACTIONS = {
    "switch": ("on", "turn_on", "off", "turn_off"),
    "cover": ("open", "open_cover", "closed", "close_cover"),
}

UNAVAILABLE_STATES = frozenset({"unavailable", None})


class DeviceUnavailable(Exception):
    def __init__(self, entity_id: str) -> None:
        super().__init__(f"'{entity_id}' sigue unavailable")


@dataclass(frozen=True)
class ToggleResult:
    entity_id: str
    label: str
    previous_state: str
    state: str


# HA responde 200 a un comando para un device desconectado: se lee el estado antes.
async def read_state(client: HomeAssistantClient, device: Device) -> str:
    state = (await client.get_state(device.entity_id)).get("state")
    if state in UNAVAILABLE_STATES:
        raise DeviceUnavailable(device.entity_id)
    return state


async def set_power(
    client: HomeAssistantClient,
    device: Device,
    on: bool,
    previous: str | None = None,
) -> ToggleResult:
    if previous is None:
        previous = await read_state(client, device)
    active_state, activate_service, inactive_state, deactivate_service = DOMAIN_ACTIONS[
        device.domain
    ]
    service = activate_service if on else deactivate_service
    await client.call_service(
        device.domain, service, {"entity_id": device.entity_id}
    )

    result = ToggleResult(
        entity_id=device.entity_id,
        label=device.label,
        previous_state=previous,
        state=active_state if on else inactive_state,
    )
    logger.info(
        "Device aplicado",
        extra={
            "entity_id": result.entity_id,
            "service": service,
            "previous_state": result.previous_state,
            "state": result.state,
        },
    )
    return result


async def toggle(client: HomeAssistantClient, device: Device) -> ToggleResult:
    state = await read_state(client, device)
    active_state, _, _, _ = DOMAIN_ACTIONS[device.domain]
    return await set_power(
        client, device, on=state != active_state, previous=state
    )
