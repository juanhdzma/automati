from typing import Any

import httpx


class HomeAssistantClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def get_state(self, entity_id: str) -> dict[str, Any]:
        resp = await self._http.get(f"/api/states/{entity_id}")
        resp.raise_for_status()
        return resp.json()

    async def call_service(
        self, domain: str, service: str, data: dict[str, Any]
    ) -> Any:
        resp = await self._http.post(f"/api/services/{domain}/{service}", json=data)
        resp.raise_for_status()
        return resp.json()
