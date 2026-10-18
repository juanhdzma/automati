from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    dev_id: str
    ip: str | None
    version: float | None
    kind: str
    label: str


DEVICES: dict[str, Device] = {
    "light": Device(
        dev_id="eb93b7f6c0ff38d8dfureh",
        ip=None,
        version=None,
        kind="switch",
        label="Luz",
    ),
    "fan": Device(
        dev_id="eb96bf610504ba299ef0ty",
        ip="192.168.78.2",
        version=3.5,
        kind="switch",
        label="Ventilador",
    ),
    "curtain": Device(
        dev_id="ebc63f8e72bd985670oq9c",
        ip="192.168.78.3",
        version=3.4,
        kind="cover",
        label="Cortina",
    ),
}
