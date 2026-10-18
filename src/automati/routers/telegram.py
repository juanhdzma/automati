from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..logic.telegram.client import TelegramClient

router = APIRouter(prefix="/telegram", tags=["telegram"])


class Message(BaseModel):
    text: str = Field(min_length=1, max_length=4096)


def get_telegram_client(request: Request) -> TelegramClient:
    return request.app.state.telegram_client


@router.post("/message")
async def send_message(
    message: Message,
    client: TelegramClient = Depends(get_telegram_client),
) -> dict[str, int]:
    """Manda un mensaje de texto al chat de Telegram configurado."""
    return {"message_id": await client.send_message(message.text)}
