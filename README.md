# Automati

Self-hosted personal automation hub — smart home devices, scheduled actions, and small personal integrations behind one HTTP API. FastAPI backend, Docker-ready, image published to GHCR on every push.

> ⚠️ These are **very** personal automations. They are wired to my own house, my own devices, and my own habits, and they are necessary for *me* — not a general-purpose tool. Nothing here is meant to be installed and used as-is. Take it as inspiration for building your own.

## Qué hace hoy

Togglea la luz, el ventilador y la cortina del cuarto hablando directo con los devices Tuya por la LAN, prende y apaga la TV con el protocolo de Android TV Remote, y le da datos a un widget de iOS. Reemplaza una carpeta de scripts sueltos donde cada aparato era un archivo copiado del anterior con un ID distinto, mas la escena `Timer Ventilador` de Tuya que estaba fija en 2 horas y solo para un device.

Schema exacto, para probar a mano o integrar con algo: `/docs` (Swagger) una vez que el servicio esta corriendo.

### `POST /smart-home/toggle`

Invierte el estado de un device ya mismo.

| Param  | Tipo   | Requerido | Valores       |
| ------ | ------ | :-------: | ------------- |
| `item` | string |     sí    | `light`, `fan`, `curtain`, `tv` |

<table>
<tr><td>

`200 OK`
```json
{
  "item": "light",
  "label": "Luz",
  "previous_state": "off",
  "state": "on"
}
```

</td><td>

**Errores** — compartidos con `/timer`

| Código | Cuándo |
| ------ | ------ |
| `422` | `item` no es `light`, `fan`, `curtain` ni `tv` |
| `503` | el device no responde por LAN: offline, sin IP configurada, con la key equivocada, o la TV sin `TV_HOST` o sin emparejar |

</td></tr>
</table>

### `POST /smart-home/timer`

Prende un device ya, y lo apaga solo despues de `seconds`. Sin forma de cancelarse por HTTP, a propósito: apagar es idempotente, así que si apagás el device a mano antes de tiempo, el apagado programado no cambia nada cuando llega. No hay estado que romper por dejarlo correr de más.

| Param     | Tipo   | Requerido | Valores            |
| --------- | ------ | :-------: | ------------------- |
| `item`    | string |     sí    | `light`, `fan`       |
| `seconds` | int    |     sí    | `1`–`86400` (1 día máx) |

`200 OK`
```json
{
  "item": "fan",
  "label": "Ventilador",
  "state": "on",
  "off_in_seconds": 1800
}
```

Mismos errores que `/toggle` (`422` / `503`).

### `GET /scriptable-ios/payday`

Próxima fecha de pago y cuántos días faltan, ajustada a día hábil. Sin parámetros.

`200 OK`
```json
{
  "next_payday": "2026-08-24",
  "days_left": 1
}
```

### `POST /telegram/message`

Manda un mensaje de texto a un chat fijo de Telegram. El chat sale de `TELEGRAM_CHAT_ID`, no del request: como el servicio no tiene auth, un `chat_id` por parámetro dejaría usar el bot contra cualquier chat.

Body JSON:

| Campo  | Tipo   | Requerido | Valores |
| ------ | ------ | :-------: | ------- |
| `text` | string |     sí    | `1`–`4096` caracteres |

`200 OK`
```json
{ "message_id": 7 }
```

| Código | Cuándo |
| ------ | ------ |
| `422` | `text` vacío o de más de 4096 caracteres |
| `502` | Telegram no respondió o rechazó el mensaje |

### `GET /health`

Healthcheck del container. Sin parámetros.

`200 OK`
```json
{ "status": "ok" }
```

## scriptable_ios

No es una seccion de automatizaciones: no acciona nada, solo calcula y devuelve datos de solo lectura para que los pinte un widget de [Scriptable](https://scriptable.app) en iOS con su propio diseño. `smart_home/` automatiza; esto informa.

`GET /scriptable-ios/payday` calcula el proximo pago: fijo el 24 de cada mes, corrido hacia atras (nunca hacia adelante) hasta el primer dia habil si el 24 cae en fin de semana o festivo colombiano. Los festivos salen de la libreria `holidays` (Ley Emiliani, sin red ni scraping) en vez de una pagina web, para que el calculo no dependa de que un sitio externo siga respondiendo o mantenga su HTML.

### `scriptable/`

El codigo del lado cliente que consume estos endpoints — JavaScript real de Scriptable, para copiar y pegar directo en la app. Vive fuera de `src/` porque corre en otro runtime (el de Scriptable en el iPhone), no en Automati. Un archivo por widget: `scriptable/payday.js` pega contra `/scriptable-ios/payday` y arma un widget de home screen chico con los dias que faltan.

## El detalle que importa

automati habla con los devices por el protocolo local de Tuya (TCP 6668, cifrado AES con la local key de cada device) usando [`tinytuya`](https://github.com/jasonacox/tinytuya). No pasa por la nube y no hace falta abrir puertos. Hay tres cosas del protocolo que condicionan el código:

- **Cada device acepta una sola conexión TCP a la vez.** `TuyaClient` abre y cierra la conexión en cada comando. Una conexión persistente bloquearía cualquier otro cliente, incluida la app Smart Life en la LAN.
- **Un device offline no lanza excepción.** `status()` devuelve un dict con `"Error"`, y `TuyaClient` lo convierte en `DeviceUnavailable` (503). Los timeouts son cortos (3 s, un reintento) para que el 503 llegue en segundos y no después de casi un minuto, que es lo que tardan los defaults de tinytuya.
- **La posición de la cortina (DP `3`) solo se actualiza cuando el motor termina el recorrido**, unos 25 s después. Si se hace toggle mientras se mueve, se lee la posición vieja y se repite el mismo comando. Entre dos toggles de la cortina hay que esperar a que termine.

`toggle` lee el estado antes de actuar y corta si el device no responde, en vez de mandar el comando y asumir que llegó.

La TV (Hisense, Google TV) va por otro lado: [`androidtvremote2`](https://github.com/tronikos/androidtvremote2), el protocolo de la app Google TV Remote (puertos 6466 y 6467). Probado contra la TV real el 18/10/2026: **un `POWER` corto no la prende desde standby, y si la conexión se cierra apenas se manda la tecla, la TV la descarta.** Por eso el toggle simula apretar y soltar (`START_LONG` + `END_LONG`) y deja la conexión abierta un segundo antes de cerrarla. Wake-on-LAN y `WAKEUP` tampoco la despiertan. El toggle tarda alrededor de 1.3 s.

Los devices Tuya son de 2.4 GHz y guardan el SSID. Si cambia el nombre de la WiFi quedan fuera de la red y hay que re-emparejarlos, y **re-emparejar cambia la local key**: después hay que volver a sacar las keys y actualizar las env vars.

## Estructura

```
src/automati/
  main.py                    # crea la app, monta los routers
  config.py                  # settings desde el entorno
  routers/
    smart_home.py            # HTTP: valida, formatea, mapea errores
    scriptable_ios.py        # HTTP: datos de solo lectura para widgets
    telegram.py              # HTTP: manda un mensaje al chat configurado
  logic/
    smart_home/
      client.py              # transporte local contra los devices Tuya (tinytuya)
      devices.py             # registry: item -> dev_id, IP, versión del protocolo
      toggle.py              # prende/apaga un switch, abre/cierra la cortina
      tv.py                  # prende/apaga la TV por Android TV Remote
      schedule.py            # timer: prende ya, apaga solo despues
      store.py               # persistencia de los timers en SQLite
    scriptable_ios/
      payday.py              # proximo pago, ajustado a dia habil
    telegram/
      client.py              # sendMessage contra la Bot API
tests/
scriptable/
  payday.js                  # widget de Scriptable, pegar tal cual en la app
```

Dos reglas sostienen esto:

- **Los routers no hablan con los devices ni calculan nada.** Validan, llaman a `logic/`, formatean. Toda la lógica vive de un solo lado.
- **`logic/` se parte por sección.** `smart_home/` automatiza, `scriptable_ios/` informa — no todo lo que hay aca es una automatizacion, y el nombre de la carpeta lo dice. Una seccion nueva entra al lado, con su router, sin tocar nada de lo existente.

## Correr

```bash
cp .env.example .env    # completar las keys
docker compose up -d
```

| Variable | Qué es |
|---|---|
| `TUYA_KEY_FAN` | Local key del ventilador |
| `TUYA_KEY_LIGHT` | Local key de la luz |
| `TUYA_KEY_CURTAIN` | Local key de la cortina |
| `TELEGRAM_BOT_TOKEN` | Token del bot, lo da @BotFather |
| `TELEGRAM_CHAT_ID` | Chat que recibe los mensajes; tiene que haberle mandado `/start` al bot |

Ninguna tiene default: si falta alguna, el container muere en el boot en vez de fallar en el primer toggle.

`TV_HOST` (IP de la TV) es opcional: sin ella, `item=tv` responde 503. La TV se empareja una sola vez, con el container corriendo:

```bash
docker exec -it automati python -m automati.pair_tv
```

La TV muestra un código de 6 caracteres que se escribe en la consola. El cert queda en el mismo directorio que `DB_PATH` (`/data/tv-cert.pem` y `/data/tv-key.pem`), en el volumen persistente, así que sobrevive a cada redeploy. Si se pierde el volumen o la TV se resetea, hay que volver a emparejarla.

Las local keys salen de la cuenta de Smart Life con `~/tuya-keys/fetch_keys.py <user_code>`. El `user_code` está en Smart Life → Me → Settings → Account and Security → User Code. El script abre un QR que se escanea desde la app y escribe `devices-qr.json`, con el campo `key` de cada device buscado por `id`. El `dev_id`, la IP y la versión del protocolo de cada device están en `src/automati/logic/smart_home/devices.py`. Como los devices se alcanzan por IP, el container tiene que estar en una red que llegue a la LAN de la casa.

El compose del repo no publica ningún puerto al host ni se une a ninguna red a propósito — eso es config de infraestructura personal, no algo para hardcodear en un repo pensado como inspiración. Para llegarle hace falta sumar el container a la red interna que corresponda (via `docker-compose.override.yml`, ya en `.gitignore`, o la config del stack en Portainer). Ahí las docs interactivas quedan en `http://automati:8000/docs`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests -q
```

## Seguridad

**Este servicio no tiene autenticación. Es a propósito, y depende por completo de que quien lo deploye lo una solo a una red interna, sin salida a internet.**

No hay auth, ni usuarios, ni rate limiting porque no hacen falta si el acceso queda limitado a la red interna. Montar un sistema de tokens y sesiones para dos endpoints que prenden una luz sería sobreingeniería — el tipo de complejidad que después hay que mantener sin que nadie la haya pedido. Para algo local, lo simple es lo correcto.

La contrapartida es real y hay que tenerla presente: **detrás de este servicio están las local keys de los devices**, que permiten controlarlos desde cualquier equipo de la LAN. Cualquiera que alcance el container puede usarlo. Por eso:

- El compose del repo **no publica ningún puerto ni define ninguna red** — es responsabilidad de quien deploye sumarlo solo a una red que no tenga ingreso público.
- El `.env` con las keys **nunca entra al repo** (está en `.gitignore`), ni en tests ni en ejemplos.
- Si algún día hace falta llegar desde afuera de la LAN, la respuesta es una **VPN** (Tailscale, WireGuard), no exponer el container. La VPN resuelve el acceso remoto sin obligar a construir auth acá adentro.
- El tráfico con los devices va cifrado con la local key, pero cualquiera que tenga la key y esté en la LAN puede mandarles comandos. Si una key se filtra, re-emparejar el device la rota.

Si la red a la que se una este container alguna vez tuviera salida a internet, la decisión de no tener auth deja de ser razonable y pasa a ser un agujero. La simplicidad de acá depende enteramente de que se quede interna.

## Deploy

Imagen en `ghcr.io/juanhdzma/automati`, construida y publicada por GitHub Actions en cada push a `master`. Corre en el server de casa vía Docker Compose sobre Portainer.

## License

AGPL-3.0 — ver [LICENSE](LICENSE).
