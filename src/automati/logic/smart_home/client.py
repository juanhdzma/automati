"""Transporte HTTP contra la API REST de Home Assistant.

Habla el protocolo de Home Assistant y nada mas: leer el estado de una entidad,
llamar un servicio, listar y recargar config entries.

Este modulo **no sabe que existe Tuya** ni conoce ninguna automatizacion. Esa
separacion es a proposito: lo especifico de un vendor no se mezcla con el
protocolo de Home Assistant. Si algun dia los devices dejan de ser Tuya, este
archivo no cambia.

Todos los metodos hacen `raise_for_status()`, asi que un error de HA sube como
`httpx.HTTPStatusError` y el router lo traduce a un 502.
"""

from typing import Any

import httpx

from ...config import Settings


class HomeAssistantClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        # El AsyncClient se recibe ya construido y se comparte para todo el proceso:
        # asi se reusa el connection pool en vez de abrir una conexion por request.
        self._http = http

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.ha_token}",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self._settings.ha_url}{path}"

    async def get_state(self, entity_id: str) -> dict[str, Any]:
        """Estado actual de una entidad. El valor util viene en la clave `state`."""
        resp = await self._http.get(
            self._url(f"/api/states/{entity_id}"),
            headers=self._headers,
            timeout=self._settings.request_timeout,
        )
        resp.raise_for_status()
        return resp.json()

    async def call_service(
        self, domain: str, service: str, data: dict[str, Any]
    ) -> Any:
        """Ejecuta un servicio, por ejemplo `switch` / `turn_on`.

        Ojo: un 200 aca significa que Home Assistant acepto el comando, no que el
        aparato lo haya recibido. Un device desconectado de la nube de Tuya
        devuelve 200 y no hace nada. Por eso `toggle` lee el estado antes.
        """
        resp = await self._http.post(
            self._url(f"/api/services/{domain}/{service}"),
            headers=self._headers,
            json=data,
            timeout=self._settings.request_timeout,
        )
        resp.raise_for_status()
        return resp.json()

    async def config_entries(self) -> list[dict[str, Any]]:
        """Integraciones instaladas en Home Assistant, cada una con su `entry_id`."""
        resp = await self._http.get(
            self._url("/api/config/config_entries/entry"),
            headers=self._headers,
            timeout=self._settings.request_timeout,
        )
        resp.raise_for_status()
        return resp.json()

    async def reload_config_entry(self, entry_id: str) -> None:
        """Recarga una integracion. No devuelve nada util, solo el status."""
        resp = await self._http.post(
            self._url(f"/api/config/config_entries/entry/{entry_id}/reload"),
            headers=self._headers,
            timeout=self._settings.request_timeout,
        )
        resp.raise_for_status()
