from fastapi import APIRouter

from ..logic.scriptable_ios import payday

router = APIRouter(prefix="/scriptable-ios", tags=["scriptable-ios"])


@router.get("/payday")
async def get_payday() -> dict:
    """Proxima fecha de pago y cuantos dias faltan, ya ajustada a dia habil."""
    return payday.days_left()
