import asyncio

from androidtvremote2 import AndroidTVRemote

from .config import load_settings
from .logic.smart_home.tv import CLIENT_NAME


async def main() -> None:
    settings = load_settings()
    if settings.tv_host is None:
        raise SystemExit("Falta TV_HOST")

    remote = AndroidTVRemote(
        CLIENT_NAME, settings.tv_certfile, settings.tv_keyfile, settings.tv_host
    )
    await remote.async_generate_cert_if_missing()
    await remote.async_start_pairing()
    code = await asyncio.to_thread(input, "Codigo que muestra la TV: ")
    await remote.async_finish_pairing(code.strip())
    print(f"TV emparejada, cert en {settings.tv_certfile}")


if __name__ == "__main__":
    asyncio.run(main())
