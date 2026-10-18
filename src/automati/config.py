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
    tv_host: str | None
    tv_certfile: str
    tv_keyfile: str


def load_settings() -> Settings:
    env = {name: os.getenv(name) for name in REQUIRED}

    missing = [name for name, value in env.items() if not value]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")

    db_path = os.getenv("DB_PATH", "/data/automati.db")
    data_dir = os.path.dirname(db_path)
    return Settings(
        tuya_keys={item: env[name] for item, name in TUYA_KEYS.items()},
        telegram_bot_token=env["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=env["TELEGRAM_CHAT_ID"],
        db_path=db_path,
        tv_host=os.getenv("TV_HOST") or None,
        tv_certfile=os.path.join(data_dir, "tv-cert.pem"),
        tv_keyfile=os.path.join(data_dir, "tv-key.pem"),
    )
