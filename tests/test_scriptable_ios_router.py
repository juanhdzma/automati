import re


def test_payday_devuelve_fecha_y_dias_no_negativos(client):
    resp = client.get("/scriptable-ios/payday")

    assert resp.status_code == 200
    body = resp.json()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", body["next_payday"])
    assert body["days_left"] >= 0
