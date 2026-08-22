"""Prende un device y lo apaga solo despues de un rato: "el ventilador, 30 minutos".

# Como funciona

`start_timer` prende el device en el momento, dentro del mismo request, y guarda
un apagado diferido en el store. Un solo task de background despierta cada
`TICK_SECONDS`, le pregunta al store que apagados vencieron, y los ejecuta.

Con granularidad de 10 segundos alcanza de sobra: nadie necesita que el ventilador
se apague al segundo exacto.

# Por que no hace falta poder cancelar

Apagar es idempotente. Si el device se apago a mano antes de que venza el timer,
cuando venza el `turn_off` no pasa nada — ya estaba apagado. No hay estado que
"romper" por dejar un timer corriendo de mas, asi que no hace falta poder
cancelarlo ni consultarlo desde afuera.

# Por que los vencidos muy viejos se descartan

Si el server se apaga por un corte de luz (paso el 19/08/2026), al volver puede
haber timers que vencieron hace horas. Apagar el ventilador seis horas tarde no
cumple ninguna intencion — probablemente ya lo apagaste a mano. Los que vencieron
hace mas de `MAX_LATE_SECONDS` se marcan `expired` y no se tocan.

# Errores

Un timer que falla se marca `failed` con el motivo y no se reintenta. Reintentar
una accion fisica sin que nadie mire es peor que fallar: si el device volvio
recien, no se sabe si el comando anterior llego. Queda registrado en el log.
"""

import asyncio
import logging
import time

from .client import HomeAssistantClient
from .devices import DEVICES
from .store import Timer, TimerStore
from .toggle import DeviceUnavailable, ToggleResult, set_power

logger = logging.getLogger(__name__)

TICK_SECONDS = 10.0
MAX_LATE_SECONDS = 3600.0


async def start_timer(
    client: HomeAssistantClient, store: TimerStore, item: str, seconds: float
) -> ToggleResult:
    """Prende `item` ya mismo y guarda su apagado para dentro de `seconds`."""
    device = DEVICES[item]
    result = await set_power(client, device, on=True)
    store.add(item=item, seconds=seconds)
    return result


async def run_due(client: HomeAssistantClient, store: TimerStore, now: float) -> None:
    """Apaga todos los timers vencidos. Aislado del loop para poder testearlo."""
    for timer in store.due(now):
        late = now - timer.run_at
        if late > MAX_LATE_SECONDS:
            logger.warning(
                "Timer vencido hace demasiado, se descarta",
                extra={"timer_id": timer.id, "late_seconds": round(late)},
            )
            store.mark(timer.id, "expired", f"vencio hace {round(late)}s")
            continue

        device = DEVICES[timer.item]
        try:
            await set_power(client, device, on=False)
        except DeviceUnavailable as exc:
            logger.error("Timer fallo: device desconectado", extra={"timer_id": timer.id})
            store.mark(timer.id, "failed", str(exc))
        except Exception as exc:
            logger.exception("Timer fallo", extra={"timer_id": timer.id})
            store.mark(timer.id, "failed", f"{type(exc).__name__}: {exc}")
        else:
            logger.info("Timer aplicado", extra={"timer_id": timer.id, "item": timer.item})
            store.mark(timer.id, "done")


async def runner(client: HomeAssistantClient, store: TimerStore) -> None:
    """Loop de background. Se cancela solo cuando la app se apaga."""
    pendientes = len(store.pending())
    if pendientes:
        logger.info("Timers pendientes recuperados del store", extra={"count": pendientes})

    while True:
        try:
            await run_due(client, store, time.time())
        except asyncio.CancelledError:
            raise
        except Exception:
            # Un error inesperado no puede matar el loop: si muere, todos los
            # apagados futuros quedan colgados en silencio.
            logger.exception("Error en el loop del scheduler")
        await asyncio.sleep(TICK_SECONDS)
