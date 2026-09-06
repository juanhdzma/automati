"""Registry de los devices que la API expone.

En los scripts originales cada device era un archivo entero, copiado del anterior,
con una sola linea distinta: el `entity_id`. Aca agregar un device es agregar una
entrada a este diccionario y su valor al enum `Item` del router.

# Como se saca un entity_id

Se ve en Home Assistant, en Developer Tools > States, o pegandole a
`GET /api/states`. Son los ids internos de Tuya, feos y en espanol, porque asi los
nombro la app cuando se emparejaron los aparatos. No conviene renombrarlos: si se
cambian en HA, hay que cambiarlos aca tambien.

"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    entity_id: str  # id de la entidad en Home Assistant
    label: str  # nombre lindo, solo para logs y para la respuesta de la API
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
