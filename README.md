# automati

Self-hosted personal automation hub — scheduled jobs, integrations, and notifications in one place. FastAPI backend, Docker-ready, image published to GHCR on every push.

> ⚠️ These are **very** personal automations. They are wired to my own accounts, services, and habits, and they are necessary for *me* — not a general-purpose tool. Nothing here is meant to be installed and used as-is. Take it as inspiration for building your own.

## Stack

- **Backend:** FastAPI (Python 3.12)
- **Deploy:** Docker, image at `ghcr.io/juanhdzma/automati`
- **CI:** GitHub Actions — tests + build & push on every commit to `master`

## Run

```bash
docker compose up -d
```

## License

GPL — see [LICENSE](LICENSE).
