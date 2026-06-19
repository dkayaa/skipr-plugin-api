# Skipr — Go-Live Plan

Roadmap to take Skipr from a working dev stack to something you can run live. The server v2 backend is largely done; the gaps are client integration, production ops, and hardening.

**Current state (baseline)**

| Layer | Status |
|-------|--------|
| API + ML + DB | Implemented (`/api/v2/timestamps`, async polling, SQLAlchemy cache, Alembic) |
| skipr-plugin | Separate repo — [skipr-plugin-browser](https://github.com/dkayaa/skipr-plugin-browser); must be updated for v2 polling |
| Deployment | `./run.sh api-dev` / `api-prod`; DigitalOcean guide in `deploy/digitalocean.md` |
| CI | `.github/workflows/ci.yml` — autopep8, mypy, unit tests, Bruno smoke integration tests |
| Unit tests | Passing via `./run.sh unit-tests` |
| Auth, monitoring | Not implemented |

---

## Phase 1 — End-to-end works (private beta)

Goal: you and a few friends can use Skipr against a stable HTTPS API.

### 1.1 Update skipr-plugin for v2

skipr-plugin lives in a **separate repo**. The last in-repo version (`d75689a`) predates v2 polling.

- [ ] **Poll on `pending`** — first request returns `202` + `{"status": "pending"}`; retry until `ready` or `failed`
- [ ] **Parse v2 response** — use `intervals`, not the whole response object
- [ ] **Handle `failed`** — show/log `error`; optionally offer retry with `?retry=1`
- [ ] **Fix skip loop** — remove `timestamps.length - 1` off-by-one (last interval was skipped)
- [ ] **URL parsing** — support `youtu.be`, `/shorts/`, `/embed/` (server already does via `youtube_url.py`)
- [ ] **Tighter skip check** — reduce 5s interval or use `timeupdate` / `requestAnimationFrame` so short ad windows aren't missed
- [ ] **Point skipr-plugin at production URL** — stable HTTPS host

**v2 contract reference**

| Status | HTTP | Body |
|--------|------|------|
| `pending` | 202 | `{"status": "pending"}` |
| `ready` | 200 | `{"status": "ready", "intervals": [{id, start_time, end_time, orgs}]}` |
| `failed` | 200 | `{"status": "failed", "error": "..."}` |
| Bad URL | 400 | `{"error": "..."}` |

### 1.2 Deploy the server for real

**Host: DigitalOcean Droplet** — see `deploy/digitalocean.md`

- [x] Pick a host — **DigitalOcean Droplet** (8 GB RAM recommended; skip App Platform)
- [x] Replace `flask run` in `entrypoint.sh` with **gunicorn** (1 worker, 4 threads)
- [x] Add reverse proxy (**Caddy**) for TLS termination (`Caddyfile`, `docker-compose.prod.yml`)
- [x] Remove hardcoded credentials from `docker-compose.yml` — use `.env`
- [x] Inject secrets via `.env` (gitignored); see `.env.example`
- [x] Add `.env.example` documenting: `DB_*`, `HUGGINGFACE_MODEL`, `CORS_ORIGINS`, `CLASSIFIER_BATCH_SIZE`, `DOMAIN`
- [x] Restrict MySQL port — localhost only in dev; no public port in prod overlay (compose MySQL on same machine)
- [x] Repo entrypoint: `./run.sh api-dev` / `api-prod`
- [ ] Provision Droplet, domain DNS, firewall, and run `./run.sh api-prod` on the server

### 1.3 Harden job lifecycle (single-server beta)

`analysis_runner.py` uses in-process daemon threads + in-memory `_active_jobs`.

- [ ] Run **one worker process** initially (multi-worker breaks in-memory dedup)
- [ ] Add **stale `pending` recovery** — if a job has been `pending` too long with no active thread, allow re-queue (or auto-retry)
- [ ] Document restart behavior: jobs in flight are lost on deploy/restart

*Defer a proper job queue (Redis/RQ, Celery) until you need horizontal scaling.*

### 1.4 Basic abuse protection

API is fully public today.

- [ ] Per-IP rate limiting on `/api/v2/timestamps`
- [ ] Optional shared API key header from skipr-plugin
- [ ] Timeouts on YouTube transcript fetch and model inference

### 1.5 Health checks

- [x] Add `/health` — DB connectivity check
- [x] Wire Docker `healthcheck` to `/health` (app) and `mysqladmin ping` (db)
- [x] Add DB `healthcheck` in `docker-compose.yml` so app doesn't race cold-start MySQL
- [ ] Optional: extend `/health` to verify models loaded

### 1.6 Tests and CI

- [x] Unit tests under `tests/` — `./run.sh unit-tests`
- [x] Bruno integration smoke tests — `integration_tests/` via `./run.sh integration-tests`
- [x] Static checks — `./run.sh mypy`, `./run.sh autopep8-check`
- [x] GitHub Actions — `.github/workflows/ci.yml`
- [ ] Add Flask unit tests for `/api/v2/timestamps` (`202`/`200`/`400`, response shape, CORS)
- [ ] Decide production `min_duration` for `compute_intervals` vs test expectations (tests use `min_duration=0`; production default is 45)

**Phase 1 done when:** skipr-plugin polls v2, skips ads on real videos, server runs on HTTPS with gunicorn, health check passes, CI green.

---

## Phase 2 — Public launch

Goal: strangers can install and use Skipr without you hand-holding.

### 2.1 Browser extension distribution

- [ ] AMO / Chrome Web Store listing (or documented sideload path)
- [ ] Privacy policy (video URLs sent to your server; what you store/cache)
- [ ] Evaluate Manifest V2 → MV3 migration

### 2.2 Observability

- [ ] Structured logging (request ID, video_id, analysis duration, failures)
- [ ] Error tracking (Sentry or similar) on analysis failures and 500s
- [ ] Uptime monitoring on `/health`

### 2.3 Model and image optimization

- [ ] Bake Hugging Face models into Docker image or persistent volume (avoid cold-start downloads)
- [ ] Decide CPU vs GPU for cost/latency; enable GPU compose profile if needed
- [ ] Multi-stage Docker build to trim image size where possible
- [ ] Split runtime vs dev dependencies further (`onnx` / `pytorch` extras for lean prod images)

### 2.4 Scaling (when single-server isn't enough)

- [ ] Replace in-process threads with a job queue
- [ ] Move `_active_jobs` dedup to DB or Redis
- [ ] Multiple replicas behind load balancer (only after queue is in place)

**Phase 2 done when:** store-listed extension, monitoring in place, abuse protection tested under load.

---

## Deferred / nice-to-have

Not blockers for beta or initial launch.

- [ ] Use `transcript_hash` for cache invalidation when YouTube transcript changes (model/pipeline version already triggers recompute)
- [ ] OpenAPI / formal API docs for client implementers
- [x] Remove unused `Authlib` from dependencies (`pyproject.toml`)
- [ ] Global `@app.errorhandler` for JSON 500s instead of Flask HTML
- [ ] Remove debug `/api/test` route if no longer needed

---

## Suggested order of work

```
skipr-plugin v2 integration
    → Deploy (./run.sh api-prod on Droplet)
        → Single worker + stale pending recovery
            → Rate limit + /health
                → API route unit tests
                    → [beta] share extension with prod URL
                        → [public] store listing + monitoring + model bake-in
```

---

## Quick reference — files to touch

| Task | Primary files |
|------|----------------|
| skipr-plugin v2 | [skipr-plugin-browser](https://github.com/dkayaa/skipr-plugin-browser) repo |
| Local / prod stacks | `run.sh`, `server/docker-compose*.yml` |
| Production server | `server/entrypoint.sh`, `server/Dockerfile`, `deploy/digitalocean.md` |
| Job lifecycle | `server/backend/analysis_runner.py`, `server/backend/interval_store.py` |
| Health | `server/app.py` |
| Rate limiting | `server/app.py` (or middleware) |
| Config docs | `server/.env.example`, `README.md` |
| Unit tests | `tests/` |
| Integration tests | `integration_tests/` |
| CI | `.github/workflows/ci.yml` |
