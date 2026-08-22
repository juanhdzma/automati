"""Rutas HTTP que le dan de comer a los widgets de Scriptable en iOS.

No es una seccion de automatizaciones como `smart_home`: aca no se acciona nada,
solo se calculan y devuelven datos de solo lectura. Cada endpoint es informacion
chica y personal (dias para el proximo pago, y lo que se sume despues) pensada
para que un widget la pinte con su propio diseño — Scriptable hace fetch, esto
le contesta JSON.
"""

from fastapi import APIRouter

from ..logic.scriptable_ios import payday

router = APIRouter(prefix="/scriptable-ios", tags=["scriptable-ios"])


@router.get("/payday")
async def get_payday() -> dict:
    """Proxima fecha de pago y cuantos dias faltan, ya ajustada a dia habil."""
    return payday.days_left()
