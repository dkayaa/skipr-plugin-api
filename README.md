# Skipr API

Flask backend for [Skipr](https://github.com/dkayaa/skipr-plugin-browser): fetches YouTube transcripts, classifies overlapping text windows with a fine-tuned DistilBERT model, and returns ad-read skip intervals.

The browser extension lives in the [skipr-plugin](https://github.com/dkayaa/skipr-plugin-browser) repo.

## Prerequisites

| Requirement | Used for |
|-------------|----------|
| **Docker** + **Docker Compose v2** (`docker compose`) | Dev/prod stacks (`./run.sh api-dev`, `api-prod`) |
| **Python 3.11** | `./run.sh unit-tests`, `mypy`, `autopep8-check` (installs `pyproject.toml` + `[dev]` extras) |

Dependencies are declared in `pyproject.toml` at repo root. `./run.sh` installs runtime + dev extras into `server/.venv` automatically.

Install Docker from [docker.com](https://docs.docker.com/get-docker/). Verify Compose v2 with `docker compose version`.

Copy `server/.env.example` to `server/.env` before starting a stack.

## Commands

| Command | Description |
|---------|-------------|
| `./run.sh api-dev` | Dev stack in Docker (db + app on http://127.0.0.1:8090) |
| `./run.sh api-dev --clear-volumes` | Dev stack with fresh DB volume |
| `./run.sh api-prod` | Prod stack in Docker (db + app + caddy) |
| `./run.sh unit-tests` | Python unit tests (`tests/`) |
| `./run.sh integration-tests` | Bruno smoke tests (API must be running) |
| `./run.sh mypy` | Static type checks |
| `./run.sh autopep8-check` | PEP 8 formatting check |

`./run.sh --help` for all options.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR to `main`:

- autopep8
- mypy
- unit tests
- Bruno integration smoke tests (Docker stack + `/health` + `/api/v2/timestamps` validation)

## Production deployment

See [deploy/digitalocean.md](deploy/digitalocean.md) for DigitalOcean Droplet setup (gunicorn, Caddy TLS, compose MySQL on the same machine).

From repo root on the server:

```bash
cp server/.env.example server/.env   # fill in secrets + DOMAIN
./run.sh api-prod
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | DB connectivity check |
| `GET /api/v2/timestamps?link=<youtube-url>` | Returns `202 pending`, then `200 ready` or `200 failed` |

See `plan.md` for the full v2 response contract.
