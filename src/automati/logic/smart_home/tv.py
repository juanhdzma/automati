import asyncio
import logging

from androidtvremote2 import AndroidTVRemote, CannotConnect, ConnectionClosed, InvalidAuth

from .client import DeviceUnavailable
from .toggle import ToggleResult

logger = logging.getLogger(__name__)

CLIENT_NAME = "automati"
LABEL = "TV"
CONNECT_TIMEOUT_SECONDS = 5
PRESS_SECONDS = 0.2
SETTLE_SECONDS = 1


class TvRemote:
    def __init__(self, host: str | None, certfile: str, keyfile: str) -> None:
        self._host = host
        self._certfile = certfile
        self._keyfile = keyfile

    async def toggle(self) -> ToggleResult:
        if self._host is None:
            raise DeviceUnavailable(f"'{LABEL}' no tiene TV_HOST configurado")
        remote = AndroidTVRemote(CLIENT_NAME, self._certfile, self._keyfile, self._host)
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT_SECONDS):
                await remote.async_connect()
            was_on = remote.is_on
            # La Hisense ignora POWER SHORT desde standby y descarta la tecla si la
            # conexion se cierra apenas se manda: se simula apretar y soltar, y se espera.
            remote.send_key_command("POWER", "START_LONG")
            await asyncio.sleep(PRESS_SECONDS)
            remote.send_key_command("POWER", "END_LONG")
            await asyncio.sleep(SETTLE_SECONDS)
        except InvalidAuth:
            raise DeviceUnavailable(
                f"'{LABEL}' no esta emparejada: correr python -m automati.pair_tv"
            ) from None
        except (CannotConnect, ConnectionClosed, TimeoutError) as exc:
            raise DeviceUnavailable(f"'{LABEL}' no responde: {type(exc).__name__}") from None
        finally:
            remote.disconnect()

        result = ToggleResult(
            label=LABEL,
            previous_state="on" if was_on else "off",
            state="off" if was_on else "on",
        )
        logger.info(
            "Device aplicado",
            extra={
                "host": self._host,
                "previous_state": result.previous_state,
                "state": result.state,
            },
        )
        return result
