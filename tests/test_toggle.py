import pytest

from automati.logic.smart_home import toggle as toggle_logic
from automati.logic.smart_home.devices import DEVICES

from conftest import FakeClient

LIGHT = DEVICES["light"]
CURTAIN = DEVICES["curtain"]


async def test_prendido_manda_turn_off():
    client = FakeClient(["on"])

    result = await toggle_logic.toggle(client, LIGHT)

    assert ("call_service", "switch", "turn_off", LIGHT.entity_id) in client.calls
    assert result.previous_state == "on"
    assert result.state == "off"


async def test_apagado_manda_turn_on():
    client = FakeClient(["off"])

    result = await toggle_logic.toggle(client, LIGHT)

    assert ("call_service", "switch", "turn_on", LIGHT.entity_id) in client.calls
    assert result.state == "on"


async def test_unavailable_no_manda_comando():
    client = FakeClient(["unavailable"])

    with pytest.raises(toggle_logic.DeviceUnavailable):
        await toggle_logic.toggle(client, LIGHT)

    assert [c for c in client.calls if c[0] == "call_service"] == []


@pytest.mark.parametrize(
    ("current_state", "service", "result_state"),
    [("open", "close_cover", "closed"), ("closed", "open_cover", "open")],
)
async def test_cortina_invierte_entre_abierta_y_cerrada(
    current_state, service, result_state
):
    client = FakeClient([current_state])

    result = await toggle_logic.toggle(client, CURTAIN)

    assert ("call_service", "cover", service, CURTAIN.entity_id) in client.calls
    assert result.state == result_state


async def test_toggle_lee_una_vez_y_manda_un_comando():
    client = FakeClient(["off"])

    await toggle_logic.toggle(client, LIGHT)

    assert client.calls == [
        ("get_state", LIGHT.entity_id),
        ("call_service", "switch", "turn_on", LIGHT.entity_id),
    ]
