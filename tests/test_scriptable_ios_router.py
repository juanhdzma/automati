import re

import pytest
from fastapi.testclient import TestClient

from automati.main import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("HA_URL", "http://smart-home.test:8123")
    monkeypatch.setenv("HOME_TOKEN", "test-token")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "timers.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_payday_devuelve_fecha_y_dias_no_negativos(client):
    resp = client.get("/scriptable-ios/payday")

    assert resp.status_code == 200
    body = resp.json()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", body["next_payday"])
    assert body["days_left"] >= 0
