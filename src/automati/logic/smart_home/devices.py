"""Registry de los devices que la API expone.

En los scripts originales cada device era un archivo entero, copiado del anterior,
con una sola linea distinta: el `entity_id`. Aca agregar un device es agregar una
entrada a este diccionario y su valor al enum `Item` del router.

# Como se saca un entity_id

Se ve en Home Assistant, en Developer Tools > States, o pegandole a
`GET /api/states`. Son los ids internos de Tuya, feos y en espanol, porque asi los
nombro la app cuando se emparejaron los aparatos. No conviene renombrarlos: si se
cambian en HA, hay que cambiarlos aca tambien.

# Alcance

Solo entidades del dominio `switch` por ahora, que son las que togglean con
turn_on/turn_off. La cortina es un `cover` y no funciona asi (se maneja invirtiendo
su posicion), asi que cuando entre va a necesitar su propio handler y este registry
va a tener que llevar tambien el dominio de cada entidad.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    entity_id: str  # id de la entidad en Home Assistant
    label: str  # nombre lindo, solo para logs y para la respuesta de la API


DEVICES: dict[str, Device] = {
    "light": Device(entity_id="switch.luz_switch_1", label="Luz"),
    "fan": Device(entity_id="switch.enchufe_ventilador_socket_1", label="Ventilador"),
}
