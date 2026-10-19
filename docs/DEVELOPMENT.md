# Development

## Setup

Python 3.12, the same version as the image and CI.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Tests

```bash
pytest tests -q
```

They cover toggle and timer logic, the HTTP status codes (422, 503, 502), the scheduler (due, not yet due, expired, failed), the Tuya status translation (switch on/off, curtain 100/0/in-between, the `"Error"` dict), the TV toggle and pairing errors, payday, and Telegram. None of them touch the network: `tests/conftest.py` has a `FakeClient` for the device layer, and the transport tests replace `tinytuya.OutletDevice` and `AndroidTVRemote` with fakes.

## Running against the real devices

From a machine on the home LAN. Put the real values in `.env.local` (ignored by git) and point `DB_PATH` outside the repo, because the TV certificate is written next to it:

```bash
pip install python-dotenv
DB_PATH=/tmp/automati/automati.db PYTHONPATH=src uvicorn automati.main:app --env-file .env.local --port 8000
```

`--env-file` needs `python-dotenv`. Don't `source` the file in the shell: the keys contain characters the shell interprets.

To try the TV, pair it once with the same environment:

```bash
DB_PATH=/tmp/automati/automati.db PYTHONPATH=src python -c "import dotenv, runpy; dotenv.load_dotenv('.env.local'); runpy.run_module('automati.pair_tv', run_name='__main__')"
```

The curtain position updates only when the motor stops, about 25 s later. Wait at least that long between two curtain toggles.

## Adding an automation

1. Put the logic in a new package, `src/automati/logic/<section>/`. Clients for external services are built in `main.py`'s lifespan from settings in `config.py`.
2. Add a router in `src/automati/routers/<section>.py` with prefix `/<section>`, and include it in `main.py`.
3. Add its tests under `tests/` with a fake for anything that leaves the process, and its endpoints to the README.

## Conventions

- Code, names and files in English; log lines and error messages in Spanish, like the existing ones.
- No comments, except the why of a non-obvious workaround.
- Routers validate and format; device and API access lives in `logic/`.
- Real keys never go in the repo, the tests or the examples. Tests use fake values.
- Every new public function gets at least one test, with no network.
