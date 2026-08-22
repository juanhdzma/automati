# Automati

Self-hosted personal automation hub — smart home devices, scheduled actions, and small personal integrations behind one HTTP API. FastAPI backend, Docker-ready, image published to GHCR on every push.

> ⚠️ These are **very** personal automations. They are wired to my own house, my own devices, and my own habits, and they are necessary for *me* — not a general-purpose tool. Nothing here is meant to be installed and used as-is. Take it as inspiration for building your own.

## Qué hace hoy

Un endpoint que togglea la luz y el ventilador del cuarto vía Home Assistant.

```
POST /smart-home/toggle?item=light|fan
POST /smart-home/timer?item=light|fan&seconds=N    # prende ya, apaga solo en N segundos (1-86400)
GET  /health
```

Schema exacto, para probar a mano o integrar con algo: `/docs` (Swagger) una vez que el servicio esta corriendo.

Reemplaza una carpeta de scripts sueltos donde cada aparato era un archivo copiado del anterior con un `entity_id` distinto, mas la escena `Timer Ventilador` de Tuya que estaba fija en 2 horas y solo para un device.

`/timer` no tiene forma de cancelarse por HTTP, a proposito: apagar es idempotente, asi que si apagas el device a mano antes de tiempo, el apagado programado no cambia nada cuando llega. No hay estado que romper por dejarlo correr de mas.

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
  dependencies.py
  routers/
    smart_home.py            # HTTP: valida, formatea, mapea errores
  logic/
    smart_home/
      client.py              # transporte contra la API de Home Assistant
      devices.py             # registry: item -> entity_id
      toggle.py              # prende/apaga un switch
      schedule.py            # timer: prende ya, apaga solo despues
      store.py               # persistencia de los timers en SQLite
tests/
```

Dos reglas sostienen esto:

- **Los routers no hablan con Home Assistant.** Validan, llaman a `logic/`, formatean. Toda la lógica vive de un solo lado.
- **`logic/` se parte por sección de automatización.** Hoy solo `smart_home/`. Mañana un `iphone_widgets/` entra al lado, con su router, sin tocar nada de lo existente.

Cada módulo de `logic/` arranca con un docstring que explica qué automatiza y por qué hace lo que hace. El porqué de los workarounds no se deduce del código y se pierde si no está escrito.

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

Docs interactivas en `http://<host>:8000/docs`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests -q
```

## Seguridad

**Este servicio corre solo en la LAN de casa y no tiene autenticación. Es a propósito, y no se puede exponer a internet.**

No hay auth, ni usuarios, ni rate limiting porque no hacen falta: el único que le pega es el dueño de la red. Montar un sistema de tokens y sesiones para dos endpoints que prenden una luz sería sobreingeniería — el tipo de complejidad que después hay que mantener sin que nadie la haya pedido. Para algo local, lo simple es lo correcto.

La contrapartida es real y hay que tenerla presente: **detrás de este servicio está el token de Home Assistant**, que da control total sobre la casa. Cualquiera que alcance el puerto 8000 puede usarlo. Por eso:

- El puerto **no se abre en el router**. Nada de port forwarding, nada de DMZ.
- El `.env` con el `HOME_TOKEN` **nunca entra al repo** (está en `.gitignore`).
- Si algún día hace falta llegar desde afuera, la respuesta es una **VPN** (Tailscale, WireGuard), no abrir el puerto. La VPN resuelve el acceso remoto sin obligar a construir auth acá adentro.
- La conexión con Home Assistant es **HTTP plano** (`http://smart-home.co:8123`), así que el `HOME_TOKEN` viaja sin cifrar por la LAN. Es aceptable en una red doméstica y no justifica montar TLS interno, pero deja de serlo en cualquier red compartida o con invitados.

Si esto se expusiera, la decisión de no tener auth deja de ser razonable y pasa a ser un agujero. La simplicidad de acá depende de que se quede en la LAN.

## Deploy

Imagen en `ghcr.io/juanhdzma/automati`, construida y publicada por GitHub Actions en cada push a `master`. Corre en el server de casa vía Docker Compose sobre Portainer.

## License

GPL — ver [LICENSE](LICENSE).
