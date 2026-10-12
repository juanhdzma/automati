# Automati

Self-hosted personal automation hub — smart home devices, scheduled actions, and small personal integrations behind one HTTP API. FastAPI backend, Docker-ready, image published to GHCR on every push.

> ⚠️ These are **very** personal automations. They are wired to my own house, my own devices, and my own habits, and they are necessary for *me* — not a general-purpose tool. Nothing here is meant to be installed and used as-is. Take it as inspiration for building your own.

## Qué hace hoy

Togglea la luz, el ventilador y la cortina del cuarto vía Home Assistant, y le da datos a un widget de iOS. Reemplaza una carpeta de scripts sueltos donde cada aparato era un archivo copiado del anterior con un `entity_id` distinto, mas la escena `Timer Ventilador` de Tuya que estaba fija en 2 horas y solo para un device.

Schema exacto, para probar a mano o integrar con algo: `/docs` (Swagger) una vez que el servicio esta corriendo.

### `POST /smart-home/toggle`

Invierte el estado de un device ya mismo.

| Param  | Tipo   | Requerido | Valores       |
| ------ | ------ | :-------: | ------------- |
| `item` | string |     sí    | `light`, `fan`, `curtain` |

<table>
<tr><td>

`200 OK`
```json
{
  "item": "light",
  "label": "Luz",
  "entity_id": "switch.luz_switch_1",
  "previous_state": "off",
  "state": "on"
}
```

</td><td>

**Errores** — compartidos con `/timer`

| Código | Cuándo |
| ------ | ------ |
| `422` | `item` no es `light`, `fan` ni `curtain` |
| `503` | el device reporta `unavailable` |
| `502` | Home Assistant no respondió |

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
  "entity_id": "switch.enchufe_ventilador_socket_1",
  "state": "on",
  "off_in_seconds": 1800
}
```

Mismos errores que `/toggle` (`422` / `503` / `502`).

### `GET /scriptable-ios/payday`

Próxima fecha de pago y cuántos días faltan, ajustada a día hábil. Sin parámetros.

`200 OK`
```json
{
  "next_payday": "2026-08-24",
  "days_left": 1
}
```

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

Al principio este servicio recargaba la integracion Tuya antes de cada comando (`ensure_available`), porque los aparatos parecian desincronizarse del docker de Home Assistant: se mandaba el toggle, HA devolvia 200, y la luz no se movia.

Probandolo contra la casa real el 22/08/2026 resulto ser al reves. **El reload previo es lo que rompe el comando.** Con reload, el `turn_on` sale 200 y el estado nunca cambia; sin reload, funciona en 0.2s. La causa probable es que recargar el config entry corta la sesion con la nube de Tuya y el comando siguiente cae en esa ventana.

El desync que motivo todo el workaround era otra cosa: **habia cambiado el nombre de la WiFi**. Los aparatos Tuya son 2.4GHz y guardan el SSID internamente, asi que los 5 quedaron fuera de la red — la nube los reportaba `online: False` y ninguno aparecia en la LAN. Ningun reload podia arreglar eso, y no lo arreglo en ninguno de los ~10 intentos. Se resolvio re-emparejandolos.

Queda una leccion que si vale: **un 200 de Home Assistant no significa que el aparato haya recibido nada.** Por eso `toggle` lee el estado antes de actuar y corta si es `unavailable`, en vez de mandar el comando y asumir que llego.

## Estructura

```
src/automati/
  main.py                    # crea la app, monta los routers
  config.py                  # settings desde el entorno
  routers/
    smart_home.py            # HTTP: valida, formatea, mapea errores
    scriptable_ios.py        # HTTP: datos de solo lectura para widgets
  logic/
    smart_home/
      client.py              # transporte contra la API de Home Assistant
      devices.py             # registry: item -> entity_id
      toggle.py              # prende/apaga un switch
      schedule.py            # timer: prende ya, apaga solo despues
      store.py               # persistencia de los timers en SQLite
    scriptable_ios/
      payday.py              # proximo pago, ajustado a dia habil
tests/
scriptable/
  payday.js                  # widget de Scriptable, pegar tal cual en la app
```

Dos reglas sostienen esto:

- **Los routers no hablan con Home Assistant ni calculan nada.** Validan, llaman a `logic/`, formatean. Toda la lógica vive de un solo lado.
- **`logic/` se parte por sección.** `smart_home/` automatiza, `scriptable_ios/` informa — no todo lo que hay aca es una automatizacion, y el nombre de la carpeta lo dice. Una seccion nueva entra al lado, con su router, sin tocar nada de lo existente.

## Correr

```bash
cp .env.example .env    # completar HOME_TOKEN
docker compose up -d
```

| Variable | Qué es |
|---|---|
| `HA_URL` | Base de Home Assistant, ej. `http://smart-home.co:8123` |
| `HOME_TOKEN` | Long-lived access token de HA (perfil → Long-lived access tokens) |

Ninguna tiene default: si falta alguna, el container muere en el boot en vez de fallar en el primer toggle.

El compose del repo no publica ningún puerto al host ni se une a ninguna red a propósito — eso es config de infraestructura personal, no algo para hardcodear en un repo pensado como inspiración. Para llegarle hace falta sumar el container a la red interna que corresponda (via `docker-compose.override.yml`, ya en `.gitignore`, o la config del stack en Portainer). Ahí las docs interactivas quedan en `http://automati:8000/docs`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests -q
```

## Seguridad

**Este servicio no tiene autenticación. Es a propósito, y depende por completo de que quien lo deploye lo una solo a una red interna, sin salida a internet.**

No hay auth, ni usuarios, ni rate limiting porque no hacen falta si el acceso queda limitado a la red interna. Montar un sistema de tokens y sesiones para dos endpoints que prenden una luz sería sobreingeniería — el tipo de complejidad que después hay que mantener sin que nadie la haya pedido. Para algo local, lo simple es lo correcto.

La contrapartida es real y hay que tenerla presente: **detrás de este servicio está el token de Home Assistant**, que da control total sobre la casa. Cualquiera que alcance el container puede usarlo. Por eso:

- El compose del repo **no publica ningún puerto ni define ninguna red** — es responsabilidad de quien deploye sumarlo solo a una red que no tenga ingreso público.
- El `.env` con el `HOME_TOKEN` **nunca entra al repo** (está en `.gitignore`).
- Si algún día hace falta llegar desde afuera de la LAN, la respuesta es una **VPN** (Tailscale, WireGuard), no exponer el container. La VPN resuelve el acceso remoto sin obligar a construir auth acá adentro.
- La conexión con Home Assistant es **HTTP plano**, así que el `HOME_TOKEN` viaja sin cifrar por la LAN. Es aceptable en una red doméstica y no justifica montar TLS interno, pero deja de serlo en cualquier red compartida o con invitados.

Si la red a la que se una este container alguna vez tuviera salida a internet, la decisión de no tener auth deja de ser razonable y pasa a ser un agujero. La simplicidad de acá depende enteramente de que se quede interna.

## Deploy

Imagen en `ghcr.io/juanhdzma/automati`, construida y publicada por GitHub Actions en cada push a `master`. Corre en el server de casa vía Docker Compose sobre Portainer.

## License

AGPL-3.0 — ver [LICENSE](LICENSE).
