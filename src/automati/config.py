"""Configuracion del servicio, leida del entorno.

Ninguna variable tiene default y no hay archivo de config en el repo. El token de
Home Assistant da control total sobre la casa, asi que nunca se commitea: vive como
variable de entorno del stack en Portainer.

Si falta alguna, el servicio no arranca. Es preferible que el container muera en el
boot, donde se ve en los logs, y no que falle el primer toggle de la noche.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ha_url: str  # base de Home Assistant, ej. http://smart-home.co:8123
    ha_token: str  # long-lived access token, se genera en el perfil de HA

    # Timeout por request individual contra HA. Un toggle hace dos (leer estado y
    # llamar el servicio), asi que en total responde en ~0.3s.
    request_timeout: float = 15.0


def load_settings() -> Settings:
    url = os.getenv("HA_URL")
    token = os.getenv("HOME_TOKEN")

    missing = [n for n, v in (("HA_URL", url), ("HOME_TOKEN", token)) if not v]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")

    # Se normaliza la barra final para poder concatenar paths sin cuidarse despues.
    return Settings(ha_url=url.rstrip("/"), ha_token=token)
