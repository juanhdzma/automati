import asyncio
import logging
import time

from .client import TuyaClient
from .devices import DEVICES
from .store import TimerStore
from .toggle import ToggleResult, set_power

logger = logging.getLogger(__name__)

TICK_SECONDS = 10.0
MAX_LATE_SECONDS = 3600.0


async def start_timer(
    client: TuyaClient, store: TimerStore, item: str, seconds: float
) -> ToggleResult:
    device = DEVICES[item]
    result = await set_power(client, device, on=True)
    store.add(item=item, seconds=seconds)
    return result


async def run_due(client: TuyaClient, store: TimerStore, now: float) -> None:
    for timer in store.due(now):
        late = now - timer.run_at
        # Tras un corte largo, apagar horas tarde no cumple ninguna intencion: se descarta.
        if late > MAX_LATE_SECONDS:
            logger.warning(
                "Timer vencido hace demasiado, se descarta",
                extra={"timer_id": timer.id, "late_seconds": round(late)},
            )
            store.mark(timer.id, "expired", f"vencio hace {round(late)}s")
            continue

        device = DEVICES[timer.item]
        # No se reintenta: no se sabe si el comando anterior llego al device.
        try:
            await set_power(client, device, on=False)
        except Exception as exc:
            logger.exception("Timer fallo", extra={"timer_id": timer.id})
            store.mark(timer.id, "failed", f"{type(exc).__name__}: {exc}")
        else:
            logger.info("Timer aplicado", extra={"timer_id": timer.id, "item": timer.item})
            store.mark(timer.id, "done")


async def runner(client: TuyaClient, store: TimerStore) -> None:
    pendientes = len(store.pending())
    if pendientes:
        logger.info("Timers pendientes recuperados del store", extra={"count": pendientes})

    while True:
        try:
            await run_due(client, store, time.time())
        except Exception:
            # Si el loop muere, los apagados pendientes quedan colgados en silencio.
            logger.exception("Error en el loop del scheduler")
        await asyncio.sleep(TICK_SECONDS)
