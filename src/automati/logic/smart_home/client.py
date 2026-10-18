import asyncio
from collections.abc import Callable
from typing import Any

import tinytuya

from .devices import DEVICES, Device


class DeviceUnavailable(Exception):
    pass


class TuyaClient:
    def __init__(self, keys: dict[str, str]) -> None:
        self._keys = {DEVICES[item].dev_id: key for item, key in keys.items()}

    async def get_state(self, device: Device) -> str:
        dps = (await asyncio.to_thread(self._run, device, lambda d: d.status()))["dps"]
        if device.kind == "cover":
            return "open" if dps["3"] > 0 else "closed"
        return "on" if dps["1"] else "off"

    async def set_power(self, device: Device, on: bool) -> None:
        if device.kind == "cover":
            command = lambda d: d.set_value(1, "open" if on else "close")
        else:
            command = lambda d: d.set_status(on)
        await asyncio.to_thread(self._run, device, command)

    # Cada device acepta una sola conexion TCP: se abre y se cierra en cada comando.
    def _run(self, device: Device, command: Callable[[tinytuya.OutletDevice], Any]) -> Any:
        if device.ip is None:
            raise DeviceUnavailable(f"'{device.label}' no tiene IP configurada")
        tuya = tinytuya.OutletDevice(
            dev_id=device.dev_id,
            address=device.ip,
            local_key=self._keys[device.dev_id],
            version=device.version,
            connection_timeout=3,
            connection_retry_limit=1,
            connection_retry_delay=1,
        )
        try:
            response = command(tuya)
        finally:
            tuya.close()
        # tinytuya no lanza si el device esta offline: devuelve un dict con "Error".
        if isinstance(response, dict) and "Error" in response:
            raise DeviceUnavailable(f"'{device.label}' no responde: {response['Error']}")
        return response
