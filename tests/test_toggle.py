import pytest

from automati.logic.smart_home import toggle as toggle_logic
from automati.logic.smart_home.devices import DEVICES

from conftest import FakeClient

LIGHT = DEVICES["light"]
CURTAIN = DEVICES["curtain"]


async def test_prendido_lo_apaga():
    client = FakeClient(["on"])

    result = await toggle_logic.toggle(client, LIGHT)

    assert ("set_power", LIGHT.dev_id, False) in client.calls
    assert result.previous_state == "on"
    assert result.state == "off"


async def test_apagado_lo_prende():
    client = FakeClient(["off"])

    result = await toggle_logic.toggle(client, LIGHT)

    assert ("set_power", LIGHT.dev_id, True) in client.calls
    assert result.state == "on"


async def test_unavailable_no_manda_comando():
    client = FakeClient(["unavailable"])

    with pytest.raises(toggle_logic.DeviceUnavailable):
        await toggle_logic.toggle(client, LIGHT)

    assert [c for c in client.calls if c[0] == "set_power"] == []


@pytest.mark.parametrize(
    ("current_state", "on", "result_state"),
    [("open", False, "closed"), ("closed", True, "open")],
)
async def test_cortina_invierte_entre_abierta_y_cerrada(
    current_state, on, result_state
):
    client = FakeClient([current_state])

    result = await toggle_logic.toggle(client, CURTAIN)

    assert ("set_power", CURTAIN.dev_id, on) in client.calls
    assert result.state == result_state


async def test_toggle_lee_una_vez_y_manda_un_comando():
    client = FakeClient(["off"])

    await toggle_logic.toggle(client, LIGHT)

    assert client.calls == [
        ("get_state", LIGHT.dev_id),
        ("set_power", LIGHT.dev_id, True),
    ]
