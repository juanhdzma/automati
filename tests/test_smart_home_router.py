import pytest
from fastapi.testclient import TestClient

from automati.dependencies import get_ha_client
from automati.logic.smart_home.devices import DEVICES
from automati.main import app
from automati.routers.smart_home import Item

from conftest import FakeClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("HA_URL", "http://smart-home.test:8123")
    monkeypatch.setenv("HOME_TOKEN", "test-token")
    app.dependency_overrides[get_ha_client] = lambda: FakeClient(["off"])
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_items_del_router_coinciden_con_el_registry():
    assert {item.value for item in Item} == set(DEVICES)


def test_toggle_devuelve_el_estado_nuevo(client):
    resp = client.post("/smart-home/toggle", params={"item": "fan"})

    assert resp.status_code == 200
    assert resp.json()["state"] == "on"
    assert resp.json()["entity_id"] == DEVICES["fan"].entity_id


def test_item_desconocido_es_422(client):
    assert client.post("/smart-home/toggle", params={"item": "microondas"}).status_code == 422
