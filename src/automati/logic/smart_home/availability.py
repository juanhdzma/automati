# =============================================================================
# CODIGO MUERTO - NO SE EJECUTA
#
# Nada llama a este modulo. Se conserva a proposito, no por olvido.
#
# Espera validacion: queremos ver si vuelve a aparecer el bug de sincronizacion
# con Home Assistant (los devices Tuya reportando estado viejo, o comandos que
# HA acepta con 200 y el aparato nunca ejecuta). Mientras ese bug no reaparezca,
# este codigo se queda quieto.
#
# Si pasan unos dias sin incidentes -> BORRAR este archivo.
# Si el bug vuelve -> aca esta el workaround, listo para reactivar.
#
# Contexto completo en el docstring de abajo y en toggle.py.
# =============================================================================

"""Recarga Tuya y espera a que una entidad reporte estado real. ACTUALMENTE SIN USO.

# Este modulo esta desactivado (2026-08-22)

`toggle.py` ya no lo llama. Se conserva porque la decision de sacarlo es reciente
y puede haber que volver atras, no porque este en uso.

La idea original era: los devices se desincronizaban del docker de Home Assistant,
asi que antes de cada comando se recargaba la integracion Tuya y se confirmaba que
la entidad respondiera. Probado contra la casa real, resulto ser **contraproducente**:
con el device sano, el reload previo hace que el comando siguiente no llegue. HA
devuelve 200 y el estado no se mueve. Sin reload, el mismo comando funciona en 0.2s.

Y el desync que motivo todo esto era otra cosa: habia cambiado el nombre de la WiFi
y los aparatos (2.4GHz, guardan el SSID internamente) quedaron fuera de la red. La
nube los daba `online: False`. Ningun reload arreglaba eso, y no lo arreglo en los
~10 intentos que hicimos.

Lo unico que sobrevivio de la idea es el chequeo de `unavailable`, que ahora vive
directo en `toggle.py`: un 200 de Home Assistant no garantiza que el aparato haya
recibido nada, asi que conviene leer el estado antes de actuar.

Si pasan unos dias sin que el desync reaparezca, este archivo y `tuya.py` se borran.

# Como funcionaba

  1. recargar Tuya primero, antes de la primera lectura
  2. leer el estado; si no era `unavailable`, devolverlo
  3. si lo era, esperar y recargar de nuevo, hasta agotar reintentos

Corria bajo un lock global porque `tuya.reload` recarga la integracion completa y
dos requests en paralelo se pisarian. Costaba hasta ~20s en el peor caso.
"""

import asyncio
import logging

from . import tuya
from .client import HomeAssistantClient

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 5.0

from .toggle import UNAVAILABLE_STATES

# Global al proceso: protege la integracion Tuya entera, no una entidad puntual.
_sync_lock = asyncio.Lock()


async def ensure_available(
    client: HomeAssistantClient,
    entity_id: str,
    max_retries: int = MAX_RETRIES,
    wait: float = RETRY_WAIT_SECONDS,
) -> str | None:
    """Devuelve el estado real de la entidad, o None si nunca llego a responder.

    Un None de vuelta significa "no le mandes nada a este device": el comando se
    perderia sin aviso.
    """
    async with _sync_lock:
        # Recarga incondicional. Si esto se saltea, el resto de la funcion mide un
        # estado que puede venir de una conexion ya rota.
        await tuya.reload(client)

        for attempt in range(1, max_retries + 1):
            state = (await client.get_state(entity_id)).get("state")
            if state not in UNAVAILABLE_STATES:
                logger.info(
                    "Entidad disponible",
                    extra={"entity_id": entity_id, "state": state},
                )
                return state

            logger.warning(
                "Entidad unavailable",
                extra={"entity_id": entity_id, "attempt": attempt},
            )

            # En el ultimo intento no tiene sentido esperar ni recargar: no queda
            # ninguna lectura despues que pudiera aprovecharlo.
            if attempt < max_retries:
                await asyncio.sleep(wait)
                await tuya.reload(client)

    logger.error(
        "Entidad sigue unavailable tras agotar reintentos",
        extra={"entity_id": entity_id, "max_retries": max_retries},
    )
    return None
