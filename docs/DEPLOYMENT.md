# Deployment

GitHub Actions runs the tests and publishes `ghcr.io/juanhdzma/automati:latest` (plus a `:<sha>` tag) on every push to `master`. The server runs it as a Portainer stack.

## Stack

`docker-compose.yml` in this repo is the base:

```yaml
services:
  automati:
    image: ghcr.io/juanhdzma/automati:latest
    container_name: automati
    restart: unless-stopped
    environment:
      TUYA_KEY_FAN: ${TUYA_KEY_FAN}
      TUYA_KEY_LIGHT: ${TUYA_KEY_LIGHT}
      TUYA_KEY_CURTAIN: ${TUYA_KEY_CURTAIN}
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_CHAT_ID: ${TELEGRAM_CHAT_ID}
      TV_HOST: ${TV_HOST:-}
    volumes:
      - db:/data
```

It publishes no ports and joins no network on purpose. Attach it to an internal network (a `docker-compose.override.yml` or the stack config in Portainer). The API is then at `http://automati:8000`, with Swagger at `/docs`.

The container must be able to reach the device IPs on the LAN (TCP 6668 for Tuya, 6466 and 6467 for the TV). A regular bridge network does, since outbound traffic is routed through the host. No ports need to be opened on the host firewall.

## Environment

Upload a `stack.env` with the variables from the [Configuration](../README.md#configuration) section. `DB_PATH` keeps its default, `/data/automati.db`.

Tuya keys contain characters such as `#`, `*` and `|`. Wrap each value in single quotes so `#` isn't read as a comment. If a device answers 503 with a key error after deploying, check how the value was loaded.

## Tuya local keys

The keys come from the Smart Life account:

1. In Smart Life, open Me, Settings, Account and Security, User Code.
2. Run `~/tuya-keys/fetch_keys.py <user_code>` and scan the QR it opens with the Smart Life app.
3. It writes `devices-qr.json`; the `key` of each device, found by `id`, goes into its `TUYA_KEY_*` variable.

Re-pairing a device (for example after the Wi-Fi name changes; the devices are 2.4 GHz and store the SSID) changes its key, and its IP can change too. A new IP or protocol version goes into `src/automati/logic/smart_home/devices.py` and ships with a new image.

## TV pairing

Once per volume, with the container running and `TV_HOST` set:

```bash
docker exec -it automati python -m automati.pair_tv
```

The TV shows a 6-character code; type it in the console. The certificate is written to `/data/tv-cert.pem` and `/data/tv-key.pem`. Until then, `item=tv` answers 503 saying the TV isn't paired.

## Upgrades

Push to `master`, wait for the Actions run, then redeploy the stack in Portainer with "pull latest image". Pending timers are reloaded from the database at startup.

## Backups

The `db` volume holds the timers database and the TV certificate. Losing it loses pending timers (the devices stay as they are) and requires pairing the TV again. The keys are not on the volume; they are in `stack.env`, and `fetch_keys.py` can recover them as long as the devices haven't been re-paired.
