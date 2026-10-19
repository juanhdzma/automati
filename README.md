<div align="center">

# Automati

**A general-purpose HTTP API for my personal automations.**

<img src="https://cdn.simpleicons.org/python" height="14" alt=""> Python &nbsp;·&nbsp; <img src="https://cdn.simpleicons.org/fastapi" height="14" alt=""> FastAPI &nbsp;·&nbsp; <img src="https://cdn.simpleicons.org/sqlite" height="14" alt=""> SQLite &nbsp;·&nbsp; <img src="https://cdn.simpleicons.org/docker" height="14" alt=""> Docker &nbsp;·&nbsp; <img src="https://cdn.simpleicons.org/telegram" height="14" alt=""> Telegram

[Features](#features) · [Docs](docs/ARCHITECTURE.md) · [License](LICENSE)

</div>

**The problem:** small automations end up as loose scripts, each with its own copy of the setup and its own place to run. Toggling a device, sending myself a message or feeding an iPhone widget each needed something to call, and there was no single place for it.

**What Automati does:** it puts every automation behind one HTTP API that iPhone Shortcuts, Scriptable widgets or anything else on the network can call. Each automation is a section with its own router and logic: today the house (lights, fan, curtain and TV, controlled directly on the LAN, with timers), Telegram messages and data for Scriptable widgets. A new automation is a new section next to the others, without touching the existing ones.

**Who it's for:** me. It is wired to my own devices, accounts and habits. Take it as a starting point for your own, not as something to install as-is.

> [!WARNING]
> There is no authentication: anyone who reaches the container can run every automation, devices and Telegram included. Keep it on an internal network only. Details in [Security](#security).

[Features](#features) · [How do I…](#how-do-i) · [Running](#running) · [Configuration](#configuration) · [Documentation](#documentation) · [Security](#security)

## Features

**Smart home**

- Toggle the light, fan, curtain and TV with one request
- Turn a switch on now and off after N seconds
- Get a 503 in seconds when a device is offline, never a silent no-op

```bash
curl -X POST 'http://automati:8000/smart-home/toggle?item=fan'
# {"item": "fan", "label": "Ventilador", "previous_state": "off", "state": "on"}

curl -X POST 'http://automati:8000/smart-home/timer?item=fan&seconds=1800'
# {"item": "fan", "label": "Ventilador", "state": "on", "off_in_seconds": 1800}
```

`item` is `light`, `fan`, `curtain` or `tv` for toggle, and only the switches (`light`, `fan`) for timer. `seconds` goes from 1 to 86400. Errors: `422` for an unknown item or out-of-range seconds, `503` when the device doesn't answer, has no IP configured, has the wrong key, or (the TV) has no `TV_HOST` or isn't paired.

**Scriptable widget**

- Next payday (the 24th, moved back to the last business day)
- Colombian holidays from the `holidays` library, no scraping
- Client code in `scriptable/payday.js`, pasted into the Scriptable app

```bash
curl http://automati:8000/scriptable-ios/payday
# {"next_payday": "2026-10-23", "days_left": 5}
```

**Telegram**

- Send a text message to one fixed chat
- The chat comes from `TELEGRAM_CHAT_ID`, never from the request

```bash
curl -X POST http://automati:8000/telegram/message -H 'Content-Type: application/json' -d '{"text": "hola"}'
# {"message_id": 7}
```

`text` must be 1 to 4096 characters (`422` otherwise); `502` when Telegram fails or rejects the message.

The full schema is in Swagger at `/docs` once the service is running. `GET /health` is the container healthcheck and never touches devices.

## How do I…

### Toggle a device from the iPhone
Create a Shortcut with a "Get contents of URL" action, method `POST`, URL `http://automati:8000/smart-home/toggle?item=light`. Show `state` from the response to see where it ended up.

### Leave the fan on for a while
`POST /smart-home/timer?item=fan&seconds=1800`. The fan turns on now and off in 30 minutes, even if the container restarts in between. There is no cancel: turning it off by hand early is fine, the scheduled off is a no-op.

### Pair the TV
With the container running, `docker exec -it automati python -m automati.pair_tv`, then type the code the TV shows. Once is enough; the certificate lives on the `/data` volume.

### Update a key after re-pairing a Tuya device
Re-pairing changes the local key. Run `~/tuya-keys/fetch_keys.py <user_code>`, copy the device's `key` into its `TUYA_KEY_*` variable and redeploy. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#tuya-local-keys).

## Running

| I want to… | Run |
|---|---|
| Try it | `docker run --env-file .env -v automati-data:/data -p 8000:8000 ghcr.io/juanhdzma/automati:latest` |
| Work on the code | `pip install -r requirements-dev.txt && pytest tests -q`, details in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| Deploy | A Portainer stack with `docker-compose.yml`, in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |

## Configuration

Copy `.env.example` to `.env`. The service refuses to start if a required variable is missing.

```bash
TUYA_KEY_FAN=          # Required. Local key of the fan plug.
TUYA_KEY_LIGHT=        # Required. Local key of the light switch.
TUYA_KEY_CURTAIN=      # Required. Local key of the curtain motor.
TELEGRAM_BOT_TOKEN=    # Required. From @BotFather.
TELEGRAM_CHAT_ID=      # Required. The only chat that receives messages; it must have sent /start to the bot.
TV_HOST=               # Optional. TV IP; without it, item=tv answers 503.
DB_PATH=/data/automati.db   # Timers database. The TV certificate is stored in the same directory.
```

Device IDs, IPs and protocol versions are not configuration: they live in `src/automati/logic/smart_home/devices.py`.

## Documentation

| Doc | Read it when |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | You want to know how it works and why it's built this way |
| [Deployment](docs/DEPLOYMENT.md) | You're running it on a server, getting keys or upgrading |
| [Development](docs/DEVELOPMENT.md) | You're changing code: setup, tests, conventions |

## Security

Automati is built for a trusted home network, not the internet.

- **No auth, no users, no rate limiting.** Anyone who reaches the container can call every automation: toggle the devices, message the Telegram chat. That is deliberate for a LAN-only service; it stops being acceptable the moment the network has internet ingress.
- **The compose file publishes no ports and joins no network.** Whoever deploys it attaches it to an internal network on purpose.
- **The local keys control the devices** from any machine on the LAN. They live only in env vars, never in the repo, tests or examples. A leaked key is rotated by re-pairing the device.
- **The Telegram chat is fixed.** A `chat_id` parameter would let anyone use the bot against any chat.

For remote access, use a VPN such as Tailscale or WireGuard instead of exposing the container.

---

AGPL-3.0 · [LICENSE](LICENSE)
