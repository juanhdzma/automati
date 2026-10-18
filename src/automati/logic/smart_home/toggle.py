import logging
from dataclasses import dataclass

from .client import DeviceUnavailable, TuyaClient
from .devices import Device

logger = logging.getLogger(__name__)

STATES = {"switch": ("on", "off"), "cover": ("open", "closed")}


@dataclass(frozen=True)
class ToggleResult:
    label: str
    previous_state: str
    state: str


async def set_power(
    client: TuyaClient,
    device: Device,
    on: bool,
    previous: str | None = None,
) -> ToggleResult:
    if previous is None:
        previous = await client.get_state(device)
    await client.set_power(device, on)

    active_state, inactive_state = STATES[device.kind]
    result = ToggleResult(
        label=device.label,
        previous_state=previous,
        state=active_state if on else inactive_state,
    )
    logger.info(
        "Device aplicado",
        extra={
            "dev_id": device.dev_id,
            "previous_state": result.previous_state,
            "state": result.state,
        },
    )
    return result


async def toggle(client: TuyaClient, device: Device) -> ToggleResult:
    state = await client.get_state(device)
    active_state, _ = STATES[device.kind]
    return await set_power(client, device, on=state != active_state, previous=state)
