import pytest
from fastapi.testclient import TestClient

from automati.main import app
from automati.routers.smart_home import get_ha_client


class FakeClient:
    def __init__(self, states: list[str | None]):
        self._states = list(states)
        self.calls: list[tuple] = []

    async def get_state(self, entity_id: str) -> dict:
        state = self._states.pop(0) if len(self._states) > 1 else self._states[0]
        self.calls.append(("get_state", entity_id))
        return {"state": state}

    async def call_service(self, domain: str, service: str, data: dict):
        self.calls.append(("call_service", domain, service, data["entity_id"]))
        return []


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("HA_URL", "http://smart-home.test:8123")
    monkeypatch.setenv("HOME_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "timers.db"))
    app.dependency_overrides[get_ha_client] = lambda: FakeClient(["off"])
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
