from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    entity_id: str
    label: str
    domain: str


DEVICES: dict[str, Device] = {
    "light": Device(entity_id="switch.luz_switch_1", label="Luz", domain="switch"),
    "fan": Device(
        entity_id="switch.enchufe_ventilador_socket_1",
        label="Ventilador",
        domain="switch",
    ),
    "curtain": Device(
        entity_id="cover.wifi_curtain_motor_curtain",
        label="Cortina",
        domain="cover",
    ),
}
