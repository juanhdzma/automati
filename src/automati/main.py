"""Punto de entrada de Automati.

Monta un router por cada seccion de automatizaciones. Hoy solo `smart_home`; cuando
entre otra (widgets de iPhone, por ejemplo) se agrega su carpeta en `logic/`, su
router en `routers/`, y una linea de `include_router` aca.

El lifespan tambien levanta el loop que apaga los timers vencidos, y lo apaga
limpio al cerrar. Vive aca y no dentro del router porque es un proceso de fondo
del servicio entero, no algo que dispare un request.

# Sin autenticacion, a proposito

Este servicio corre en la LAN de casa y no se expone a internet. No tiene auth, ni
usuarios, ni rate limiting, porque no hace falta: el unico que le pega es el dueno
de la red. Meter un sistema de tokens para dos endpoints que prenden una luz seria
sobreingenieria pura.

La contrapartida es que **no se puede exponer**. Detras de este servicio esta el
token de Home Assistant, que da control total sobre la casa. Si algun dia hiciera
falta llegar desde afuera, la respuesta es una VPN (Tailscale, WireGuard), no
abrirle un puerto al router. Ver la seccion "Seguridad" del README.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from .config import load_settings
from .logic.smart_home.client import HomeAssistantClient
from .logic.smart_home.schedule import runner
from .logic.smart_home.store import TimerStore
from .routers import scriptable_ios, smart_home

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # La config se carga aca, al arrancar, para que un token faltante tumbe el
    # container en el boot en vez de fallar en el primer toggle.
    settings = load_settings()

    store = TimerStore(settings.db_path)

    # Un solo AsyncClient para todo el proceso: comparte el connection pool y evita
    # el handshake TCP en cada request contra Home Assistant.
    async with httpx.AsyncClient() as http:
        client = HomeAssistantClient(settings, http)
        app.state.settings = settings
        app.state.ha_client = client
        app.state.timer_store = store

        # El scheduler arranca aca y no antes: necesita el cliente HTTP vivo, y al
        # colgarlo del lifespan se cancela solo cuando la app se apaga.
        scheduler = asyncio.create_task(runner(client, store), name="scheduler")
        try:
            yield
        finally:
            scheduler.cancel()
            # Se espera la cancelacion para que el loop no quede a mitad de un job
            # mientras el AsyncClient de httpx ya se esta cerrando.
            await asyncio.gather(scheduler, return_exceptions=True)
            store.close()


app = FastAPI(
    title="Automati",
    description="Automatizaciones personales. Solo LAN, sin auth.",
    lifespan=lifespan,
)

app.include_router(smart_home.router)
app.include_router(scriptable_ios.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Healthcheck del container. No toca Home Assistant a proposito: reporta si
    este servicio esta vivo, no si la casa responde."""
    return {"status": "ok"}
