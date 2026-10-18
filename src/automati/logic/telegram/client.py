import logging

import httpx2

logger = logging.getLogger(__name__)


class TelegramError(Exception):
    pass


class TelegramClient:
    def __init__(self, http: httpx2.AsyncClient, chat_id: str) -> None:
        self._http = http
        self._chat_id = chat_id

    async def send_message(self, text: str) -> int:
        try:
            resp = await self._http.post(
                "/sendMessage", json={"chat_id": self._chat_id, "text": text}
            )
        except httpx2.HTTPError as exc:
            # El mensaje de httpx2 trae la URL, que lleva el token del bot: no se propaga.
            raise TelegramError(type(exc).__name__) from None
        if not resp.is_success:
            raise TelegramError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        message_id = resp.json()["result"]["message_id"]
        logger.info("Mensaje enviado a Telegram", extra={"message_id": message_id})
        return message_id
