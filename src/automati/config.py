import os
from dataclasses import dataclass

TUYA_KEYS = {
    "fan": "TUYA_KEY_FAN",
    "light": "TUYA_KEY_LIGHT",
    "curtain": "TUYA_KEY_CURTAIN",
}
REQUIRED = (*TUYA_KEYS.values(), "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")


@dataclass(frozen=True)
class Settings:
    tuya_keys: dict[str, str]
    telegram_bot_token: str
    telegram_chat_id: str
    db_path: str


def load_settings() -> Settings:
    env = {name: os.getenv(name) for name in REQUIRED}

    missing = [name for name, value in env.items() if not value]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")

    return Settings(
        tuya_keys={item: env[name] for item, name in TUYA_KEYS.items()},
        telegram_bot_token=env["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=env["TELEGRAM_CHAT_ID"],
        db_path=os.getenv("DB_PATH", "/data/automati.db"),
    )
