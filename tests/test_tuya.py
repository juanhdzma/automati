"""Tests del reload de Tuya.

El caso importante es el de varias config entries: esta casa tiene dos, y los
scripts originales recargaban solo la primera, dejando muertos los devices que
colgaban de la otra.
"""

from automati.logic.smart_home import tuya
from automati.logic.smart_home.devices import DEVICES

from conftest import FakeClient

LIGHT = DEVICES["light"]


async def test_recarga_todas_las_entries_de_tuya():
    client = FakeClient(["on"])

    reloaded = await tuya.reload(client)

    assert reloaded == 2
    assert [c for c in client.calls if c[0] == "reload"] == [
        ("reload", "tuya-loaded"),
        ("reload", "tuya-broken"),
    ]


async def test_ignora_integraciones_que_no_son_tuya():
    client = FakeClient(["on"])

    await tuya.reload(client)

    assert ("reload", "otra-integracion") not in client.calls


async def test_una_entry_rota_no_impide_recargar_las_demas():
    """Una entry en setup_error puede rechazar el reload. La sana igual se recarga."""
    client = FakeClient(["on"], failing_entries={"tuya-broken"})

    reloaded = await tuya.reload(client)

    assert reloaded == 1
    assert ("reload", "tuya-loaded") in client.calls


async def test_sin_tuya_instalada_no_revienta():
    client = FakeClient(["on"], entries=[{"domain": "hue", "entry_id": "x"}])

    assert await tuya.reload(client) == 0
