import os
from dataclasses import dataclass

REQUIRED = ("HA_URL", "HOME_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")


@dataclass(frozen=True)
class Settings:
    ha_url: str
    ha_token: str
    telegram_bot_token: str
    telegram_chat_id: str
    db_path: str


def load_settings() -> Settings:
    env = {name: os.getenv(name) for name in REQUIRED}

    missing = [name for name, value in env.items() if not value]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")

    return Settings(
        ha_url=env["HA_URL"].rstrip("/"),
        ha_token=env["HOME_TOKEN"],
        telegram_bot_token=env["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=env["TELEGRAM_CHAT_ID"],
        db_path=os.getenv("DB_PATH", "/data/automati.db"),
    )
