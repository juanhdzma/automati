import pytest
from fastapi.testclient import TestClient

from automati.logic.smart_home.client import DeviceUnavailable
from automati.main import app
from automati.routers.smart_home import get_device_client


class FakeClient:
    def __init__(self, states: list[str | None]):
        self._states = list(states)
        self.calls: list[tuple] = []

    async def get_state(self, device) -> str:
        state = self._states.pop(0) if len(self._states) > 1 else self._states[0]
        self.calls.append(("get_state", device.dev_id))
        if state == "unavailable":
            raise DeviceUnavailable(f"'{device.label}' no responde")
        return state

    async def set_power(self, device, on: bool) -> None:
        self.calls.append(("set_power", device.dev_id, on))


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("TUYA_KEY_FAN", "fake-fan-key")
    monkeypatch.setenv("TUYA_KEY_LIGHT", "fake-light-key")
    monkeypatch.setenv("TUYA_KEY_CURTAIN", "fake-curtain-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "timers.db"))
    app.dependency_overrides[get_device_client] = lambda: FakeClient(["off"])
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
