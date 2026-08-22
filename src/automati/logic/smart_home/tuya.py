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

"""Recarga la integracion Tuya para re-sincronizar los devices con Home Assistant.

# Por que existe este modulo

Los devices Tuya de esta casa **se desincronizan del docker de Home Assistant**.
No es que se caigan ni que reporten error: la integracion queda en un estado donde
Home Assistant cree que sigue conectada, acepta el comando y responde 200, pero el
aparato fisico nunca lo recibe. Mandas el toggle, HA dice que la luz quedo en `on`,
y la luz sigue apagada. Es como si el device no estuviera escuchando.

Recargar el config entry de Tuya reconstruye esa conexion. Despues del reload los
comandos vuelven a llegar de verdad.

# Por que se recargan TODAS las entries y no la primera

Esta instalacion tiene **mas de un config entry de Tuya**, con el mismo titulo:
una en `loaded` y otra en `setup_error`. Los scripts originales hacian un `next()`
y recargaban solo la primera que encontraban, asi que la rota nunca se tocaba y los
devices que colgaban de ella quedaban muertos sin explicacion.

Recargar todas cuesta un request extra y elimina esa clase entera de bug. Si una
falla, se loguea y se sigue con las demas: una entry rota no puede impedir que se
recargue la que si funciona.

# Lo que el reload NO arregla

Si la entry perdio la autenticacion contra la nube de Tuya (`Authentication failed.
Please re-authenticate` en el log de HA), recargar no sirve: hay que re-autenticar
a mano desde la UI de Home Assistant. Lo mismo si el container de HA no puede
resolver `apigw.tuyaus.com` por DNS. En esos casos `ensure_available` va a agotar
los reintentos y devolver None, que es lo correcto: mejor un 503 que un comando
mandado al vacio.

# Alcance

La recarga es de la **integracion completa**, no de una entidad: la API de HA no
permite re-sincronizar un solo device. Por eso `availability.ensure_available`
serializa las recargas con un lock.

Este modulo existe solo por este problema. Un device que no sea Tuya (Zigbee,
Shelly) no necesita este paso.
"""

import logging

import httpx

from .client import HomeAssistantClient

logger = logging.getLogger(__name__)

DOMAIN = "tuya"


async def reload(client: HomeAssistantClient) -> int:
    """Recarga todos los config entries de Tuya. Devuelve cuantos se recargaron."""
    entries = await client.config_entries()

    # Los entry_id se resuelven en cada llamada en vez de cachearse: reinstalar o
    # re-autenticar la integracion en HA genera ids nuevos, y un id viejo cacheado
    # haria fallar el reload en silencio, que es justo lo que este modulo evita.
    entry_ids = [e["entry_id"] for e in entries if e.get("domain") == DOMAIN]

    if not entry_ids:
        # No es fatal: si el device fuera de otra integracion, `ensure_available`
        # igual sigue adelante con el poll de estado.
        logger.warning("No se encontro ninguna integracion Tuya en Home Assistant")
        return 0

    reloaded = 0
    for entry_id in entry_ids:
        try:
            await client.reload_config_entry(entry_id)
        except httpx.HTTPError as exc:
            # Una entry en setup_error puede rechazar el reload. No es motivo para
            # abandonar: las otras entries todavia pueden recuperar sus devices.
            logger.warning(
                "Fallo el reload de una entry de Tuya",
                extra={"entry_id": entry_id, "error": str(exc)},
            )
            continue
        reloaded += 1

    logger.info(
        "Tuya recargada", extra={"reloaded": reloaded, "total": len(entry_ids)}
    )
    return reloaded
