import asyncio
import logging
from contextlib import asynccontextmanager

import httpx2
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import load_settings
from .logic.smart_home.client import HomeAssistantClient
from .logic.smart_home.schedule import runner
from .logic.smart_home.store import TimerStore
from .logic.smart_home.toggle import DeviceUnavailable
from .logic.telegram.client import TelegramClient, TelegramError
from .routers import scriptable_ios, smart_home, telegram

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
# httpx2 loguea cada URL en INFO y la de Telegram lleva el token del bot.
logging.getLogger("httpx2").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    store = TimerStore(settings.db_path)

    # Telegram va en un cliente aparte: el de HA manda el HOME_TOKEN en cada request.
    async with (
        httpx2.AsyncClient(
            base_url=settings.ha_url,
            headers={"Authorization": f"Bearer {settings.ha_token}"},
            timeout=15.0,
        ) as http,
        httpx2.AsyncClient(
            base_url=f"https://api.telegram.org/bot{settings.telegram_bot_token}",
            timeout=15.0,
        ) as telegram_http,
    ):
        client = HomeAssistantClient(http)
        app.state.ha_client = client
        app.state.timer_store = store
        app.state.telegram_client = TelegramClient(
            telegram_http, settings.telegram_chat_id
        )

        scheduler = asyncio.create_task(runner(client, store), name="scheduler")
        try:
            yield
        finally:
            scheduler.cancel()
            # Se espera la cancelacion para que no quede un job a medias con httpx ya cerrandose.
            await asyncio.gather(scheduler, return_exceptions=True)
            store.close()


app = FastAPI(
    title="Automati",
    description="Automatizaciones personales. Solo LAN, sin auth.",
    lifespan=lifespan,
)

app.include_router(smart_home.router)
app.include_router(scriptable_ios.router)
app.include_router(telegram.router)


@app.exception_handler(DeviceUnavailable)
async def device_unavailable(request: Request, exc: DeviceUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(httpx2.HTTPError)
async def home_assistant_error(request: Request, exc: httpx2.HTTPError) -> JSONResponse:
    return JSONResponse(
        status_code=502, content={"detail": f"Home Assistant no respondio: {exc}"}
    )


@app.exception_handler(TelegramError)
async def telegram_error(request: Request, exc: TelegramError) -> JSONResponse:
    return JSONResponse(
        status_code=502, content={"detail": f"Telegram no respondio: {exc}"}
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Healthcheck del container. No toca Home Assistant a proposito."""
    return {"status": "ok"}
