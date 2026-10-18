import pytest
from androidtvremote2 import InvalidAuth

from automati.logic.smart_home import tv as tv_module
from automati.logic.smart_home.tv import TvRemote
from automati.main import app
from automati.routers.smart_home import get_tv_remote


class FakeRemote:
    is_on: bool = False
    connect_error: Exception | None = None
    instances: list["FakeRemote"] = []

    def __init__(self, client_name, certfile, keyfile, host):
        self.keys: list[tuple[str, str]] = []
        self.disconnected = False
        FakeRemote.instances.append(self)

    async def async_connect(self):
        if FakeRemote.connect_error:
            raise FakeRemote.connect_error

    def send_key_command(self, key, direction):
        self.keys.append((key, direction))

    def disconnect(self):
        self.disconnected = True


@pytest.fixture
def remote(monkeypatch):
    FakeRemote.instances = []
    FakeRemote.connect_error = None
    monkeypatch.setattr(tv_module, "AndroidTVRemote", FakeRemote)
    monkeypatch.setattr(tv_module, "PRESS_SECONDS", 0)
    monkeypatch.setattr(tv_module, "SETTLE_SECONDS", 0)
    return FakeRemote


def tv() -> TvRemote:
    return TvRemote("192.0.2.10", "cert.pem", "key.pem")


@pytest.mark.parametrize(("is_on", "previous", "state"), [(True, "on", "off"), (False, "off", "on")])
async def test_toggle_manda_power_y_devuelve_el_estado_nuevo(remote, is_on, previous, state):
    remote.is_on = is_on

    result = await tv().toggle()

    assert (result.previous_state, result.state) == (previous, state)
    assert remote.instances[0].keys == [("POWER", "START_LONG"), ("POWER", "END_LONG")]
    assert remote.instances[0].disconnected


def test_tv_sin_emparejar_es_503(client, remote):
    remote.connect_error = InvalidAuth()
    app.dependency_overrides[get_tv_remote] = tv

    resp = client.post("/smart-home/toggle", params={"item": "tv"})

    assert resp.status_code == 503
    assert "emparejada" in resp.json()["detail"]
    assert remote.instances[0].keys == []


def test_timer_no_acepta_la_tv(client):
    assert client.post("/smart-home/timer", params={"item": "tv", "seconds": 60}).status_code == 422
