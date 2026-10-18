import pytest

from automati.logic.smart_home import client as client_module
from automati.logic.smart_home.client import DeviceUnavailable, TuyaClient
from automati.logic.smart_home.devices import DEVICES

KEYS = {"fan": "fake-fan-key", "light": "fake-light-key", "curtain": "fake-curtain-key"}


class FakeOutlet:
    response: dict = {}
    instances: list["FakeOutlet"] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls: list[tuple] = []
        self.closed = False
        FakeOutlet.instances.append(self)

    def status(self):
        self.calls.append(("status",))
        return FakeOutlet.response

    def set_status(self, on):
        self.calls.append(("set_status", on))
        return FakeOutlet.response

    def set_value(self, index, value):
        self.calls.append(("set_value", index, value))
        return FakeOutlet.response

    def close(self):
        self.closed = True


@pytest.fixture
def outlet(monkeypatch):
    FakeOutlet.instances = []
    monkeypatch.setattr(client_module.tinytuya, "OutletDevice", FakeOutlet)
    return FakeOutlet


@pytest.mark.parametrize(
    ("item", "dps", "state"),
    [
        ("fan", {"1": True}, "on"),
        ("fan", {"1": False}, "off"),
        ("curtain", {"1": "open", "3": 100}, "open"),
        ("curtain", {"1": "close", "3": 0}, "closed"),
        ("curtain", {"1": "open", "3": 40}, "open"),
    ],
)
async def test_get_state_traduce_los_dps(outlet, item, dps, state):
    outlet.response = {"dps": dps}

    assert await TuyaClient(KEYS).get_state(DEVICES[item]) == state
    assert outlet.instances[0].kwargs["local_key"] == KEYS[item]
    assert outlet.instances[0].closed


async def test_dict_con_error_es_device_unavailable(outlet):
    outlet.response = {"Error": "Network Error: Unable to Connect", "Err": "901"}

    with pytest.raises(DeviceUnavailable):
        await TuyaClient(KEYS).get_state(DEVICES["fan"])
    assert outlet.instances[0].closed


async def test_device_sin_ip_no_intenta_conectar(outlet):
    with pytest.raises(DeviceUnavailable):
        await TuyaClient(KEYS).get_state(DEVICES["light"])
    assert outlet.instances == []


@pytest.mark.parametrize(
    ("item", "on", "call"),
    [
        ("fan", True, ("set_status", True)),
        ("fan", False, ("set_status", False)),
        ("curtain", True, ("set_value", 1, "open")),
        ("curtain", False, ("set_value", 1, "close")),
    ],
)
async def test_set_power_manda_el_comando_del_tipo(outlet, item, on, call):
    outlet.response = {"dps": {}}

    await TuyaClient(KEYS).set_power(DEVICES[item], on)

    assert outlet.instances[0].calls == [call]
