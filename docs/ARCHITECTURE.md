# Architecture

Automati is a single FastAPI process that hosts unrelated personal automations as sections: `smart_home`, `telegram` and `scriptable_ios` today. Each section is a router in `routers/` plus a package in `logic/`, and a new automation is added as a new section without touching the others. Smart home also runs a background scheduler task for timers. The boundary that matters most is between routers and logic: routers validate and format, and only `logic/` talks to devices or external APIs.

## System context

iPhone Shortcuts and a Scriptable widget call the API over the home network. The container runs on the home server and needs a route to the LAN where the devices live:

- **Tuya devices** (fan plug, light switch, curtain motor): local protocol on TCP 6668, AES-encrypted with each device's local key. No cloud, no Home Assistant.
- **TV** (Hisense, Google TV): Android TV Remote protocol on 6466 (commands) and 6467 (pairing), authenticated with a client certificate.
- **Telegram Bot API**: outbound HTTPS, only for `POST /telegram/message`.

When a device doesn't answer, the request fails with 503 in a few seconds instead of hanging. When Telegram fails, the request fails with 502. `/health` touches neither, so a dead device never marks the container unhealthy.

## Layer map and dependency rule

| Layer | Lives in | May depend on |
|---|---|---|
| HTTP | `src/automati/routers/` | logic, FastAPI |
| Device control | `src/automati/logic/smart_home/toggle.py`, `schedule.py` | transports, store |
| Transports | `logic/smart_home/client.py` (tinytuya), `logic/smart_home/tv.py` (androidtvremote2), `logic/telegram/client.py` (httpx2) | the device or API they wrap |
| Persistence | `logic/smart_home/store.py` | sqlite3 |
| Wiring | `main.py`, `config.py` | everything; builds the clients from env vars |

Routers never talk to devices and never compute anything, so every behavior is testable with a fake transport and no network.

## Project structure

```
src/automati/
  main.py                  App, lifespan (clients, scheduler task), error handlers
  config.py                Settings from env vars; fails at boot if one is missing
  pair_tv.py               One-off TV pairing: python -m automati.pair_tv
  routers/                 smart_home, scriptable_ios, telegram
  logic/smart_home/
    devices.py             Registry: item -> dev_id, IP, protocol version, kind
    client.py              TuyaClient: one TCP connection per command
    toggle.py              Read state, then switch; ToggleResult
    tv.py                  TvRemote: POWER press and release
    schedule.py            Timers: on now, off later; scheduler loop
    store.py               SQLite timers table
  logic/scriptable_ios/
    payday.py              Next payday adjusted to a business day
  logic/telegram/
    client.py              sendMessage against the Bot API
scriptable/
  payday.js                Scriptable widget, runs on the iPhone, not here
tests/                     pytest; fakes for every transport, no network
```

## Data and storage

One SQLite table, `timers`, at `DB_PATH`. Each row is a scheduled turn-off with `status` `pending`, `done`, `failed` or `expired`. Rows are never deleted. The scheduler polls every 10 seconds for pending rows whose `run_at` has passed.

The TV pairing certificate (`tv-cert.pem`, `tv-key.pem`) sits in the same directory as `DB_PATH`, so both live on the `/data` volume and survive redeploys.

## Glossary

| In code | Meaning |
|---|---|
| `item` | Public name of a device in the API: `light`, `fan`, `curtain`, `tv`. |
| `dev_id` | Tuya device ID. |
| `kind` | `switch` (on/off) or `cover` (open/close). Decides the command and which states exist. |
| Local key | Per-device AES key for the Tuya local protocol. Changes when the device is re-paired. |
| DP | Tuya data point. Switches use DP `1` (bool). The curtain uses DP `1` for the command and DP `3` for the position (100 open, 0 closed). |

Logs and error messages are in Spanish; code is in English.

## Decision log

| Decision | Why | Trade-off |
|---|---|---|
| Control devices directly on the LAN instead of through Home Assistant | Home Assistant was heavy and buggy, and it was the only reason the devices went through a middleman. | Keys live in env vars, IPs and protocol versions are hardcoded in `devices.py`, and re-pairing a device means fetching its key again. |
| Open and close a TCP connection on every Tuya command | Each Tuya device accepts a single TCP connection at a time; a persistent one would lock out every other client, including the Smart Life app. | A toggle opens two connections (read, then write), about 0.1 to 1 s total. |
| Short Tuya timeouts: 3 s, one retry | tinytuya's defaults take close to a minute to give up on an offline device. | A device on flaky Wi-Fi can return a 503 that a longer wait would have avoided. |
| Read the state before every command, and stop if the device doesn't answer | Under Home Assistant, a 200 did not mean the device received anything. Reading first turns "no answer" into an explicit 503. | One extra round trip per toggle. |
| tinytuya's `"Error"` dict becomes `DeviceUnavailable` | tinytuya doesn't raise when a device is offline; it returns a dict with `"Error"`. | Every response is checked in one place, `TuyaClient._run`. |
| Curtain state comes from the position DP, not the motor state | DP `3` is the only real position; DP `7` only says the last direction. | DP `3` updates only when the motor finishes (about 25 s), so a second toggle during travel repeats the same command. |
| TV POWER is sent as press and release, and the connection stays open 1 s | Verified against the TV on 2026-10-18: a short POWER doesn't wake it from standby, and a key sent right before closing the connection is dropped. Wake-on-LAN and WAKEUP don't wake it either. | The TV toggle takes about 1.3 s. |
| TV certificate stored next to `DB_PATH` | It must survive redeploys, and `/data` is already the persistent volume. Deriving the path avoids a new variable. | Moving the database moves the certificate; losing the volume means pairing again. |
| Timers can't be cancelled over HTTP | Turning off is idempotent: if the device was turned off by hand early, the scheduled off changes nothing. | No way to cancel a scheduled off without touching the database. |
| A timer more than 1 hour late is dropped, not applied | After a long outage, turning something off hours late matches no one's intent. | It is marked `expired` with the delay, and the device stays on. |
| A failed timer is not retried | There is no way to know whether the previous command reached the device. | It is marked `failed` with the error and logged. |
| The Telegram chat is fixed by `TELEGRAM_CHAT_ID` | The service has no auth; a `chat_id` parameter would let anyone use the bot against any chat. | Messaging another chat needs a config change. |
| Colombian holidays come from the `holidays` library | The payday calculation shouldn't depend on a website staying up or keeping its HTML. | Holidays depend on the library being kept up to date. |
| No authentication | It runs only on an internal network; auth would be machinery to maintain that no one asked for. | Anyone who reaches the container controls the house. See Security in the README. |
