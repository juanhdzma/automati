import httpx2
import pytest

from automati.logic.telegram.client import TelegramClient, TelegramError
from automati.main import app
from automati.routers.telegram import get_telegram_client

BASE_URL = "https://api.telegram.org/bot123:secret"


def _client(handler) -> TelegramClient:
    http = httpx2.AsyncClient(
        base_url=BASE_URL, transport=httpx2.MockTransport(handler)
    )
    return TelegramClient(http, chat_id="42")


async def test_send_message_manda_el_texto_al_chat_configurado():
    seen = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append((str(request.url), request.read()))
        return httpx2.Response(200, json={"ok": True, "result": {"message_id": 7}})

    assert await _client(handler).send_message("hola") == 7
    url, body = seen[0]
    assert url == f"{BASE_URL}/sendMessage"
    assert b'"chat_id":"42"' in body
    assert b'"text":"hola"' in body


async def test_error_de_telegram_devuelve_su_descripcion():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            400, json={"ok": False, "description": "Bad Request: chat not found"}
        )

    with pytest.raises(TelegramError, match="chat not found"):
        await _client(handler).send_message("hola")


async def test_error_de_red_no_filtra_el_token():
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError(f"fallo {request.url}")

    with pytest.raises(TelegramError) as exc_info:
        await _client(handler).send_message("hola")

    assert "secret" not in str(exc_info.value)


class FakeTelegram:
    def __init__(self, error: TelegramError | None = None):
        self.error = error
        self.sent: list[str] = []

    async def send_message(self, text: str) -> int:
        if self.error:
            raise self.error
        self.sent.append(text)
        return 7


def test_endpoint_manda_el_mensaje(client):
    fake = FakeTelegram()
    app.dependency_overrides[get_telegram_client] = lambda: fake

    resp = client.post("/telegram/message", json={"text": "hola"})

    assert resp.status_code == 200
    assert resp.json() == {"message_id": 7}
    assert fake.sent == ["hola"]


def test_endpoint_rechaza_texto_vacio_o_demasiado_largo(client):
    assert client.post("/telegram/message", json={"text": ""}).status_code == 422
    assert client.post("/telegram/message", json={"text": "a" * 4097}).status_code == 422


def test_endpoint_telegram_caido_es_502(client):
    app.dependency_overrides[get_telegram_client] = lambda: FakeTelegram(
        TelegramError("ConnectError")
    )

    resp = client.post("/telegram/message", json={"text": "hola"})

    assert resp.status_code == 502
    assert resp.json() == {"detail": "Telegram no respondio: ConnectError"}
