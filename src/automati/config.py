import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ha_url: str
    ha_token: str
    db_path: str


def load_settings() -> Settings:
    url = os.getenv("HA_URL")
    token = os.getenv("HOME_TOKEN")

    missing = [n for n, v in (("HA_URL", url), ("HOME_TOKEN", token)) if not v]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")

    return Settings(
        ha_url=url.rstrip("/"),
        ha_token=token,
        db_path=os.getenv("DB_PATH", "/data/automati.db"),
    )
