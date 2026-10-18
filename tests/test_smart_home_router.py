import pytest

from automati.logic.smart_home.devices import DEVICES
from automati.main import app
from automati.routers.smart_home import get_device_client

from conftest import FakeClient


def test_toggle_devuelve_el_estado_nuevo(client):
    resp = client.post("/smart-home/toggle", params={"item": "fan"})

    assert resp.status_code == 200
    assert resp.json()["state"] == "on"


def test_toggle_cortina_devuelve_el_estado_nuevo(client):
    resp = client.post("/smart-home/toggle", params={"item": "curtain"})

    assert resp.status_code == 200
    assert resp.json()["state"] == "open"


def test_item_desconocido_es_422(client):
    assert client.post("/smart-home/toggle", params={"item": "microondas"}).status_code == 422


def test_timer_prende_y_devuelve_cuando_se_apaga(client):
    resp = client.post("/smart-home/timer", params={"item": "fan", "seconds": 1800})

    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "on"
    assert body["off_in_seconds"] == 1800


def test_timer_seconds_fuera_de_rango_es_422(client):
    assert client.post("/smart-home/timer", params={"item": "fan", "seconds": 0}).status_code == 422
    assert client.post("/smart-home/timer", params={"item": "fan", "seconds": 99999}).status_code == 422


def test_timer_solo_acepta_switches(client):
    assert client.post("/smart-home/timer", params={"item": "curtain", "seconds": 60}).status_code == 422
    assert client.post("/smart-home/timer", params={"item": "light", "seconds": 60}).status_code == 200


@pytest.mark.parametrize("path", ["/smart-home/toggle", "/smart-home/timer"])
def test_device_unavailable_es_503(client, path):
    app.dependency_overrides[get_device_client] = lambda: FakeClient(["unavailable"])

    resp = client.post(path, params={"item": "fan", "seconds": 60})

    assert resp.status_code == 503
    assert resp.json() == {"detail": f"'{DEVICES['fan'].label}' no responde"}

