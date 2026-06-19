# Skipr API integration tests (Bruno)

Black-box HTTP tests against a running Skipr stack. Uses [Bruno](https://www.usebruno.com/) collections stored as plain-text `.bru` files.

## Prerequisites

- A running API — from repo root:
  ```bash
  ./run.sh api-dev
  ```
- [Bruno CLI](https://docs.usebruno.com/bru-cli/overview) for command-line runs, or the Bruno desktop app to explore requests interactively.

Install the CLI:

```bash
npm install -g @usebruno/cli
```

## Environments

| File | Purpose |
|------|---------|
| `environments/local.bru` | Default — `http://127.0.0.1:8090` |

Variables:

- `baseUrl` — API origin
- `testVideoUrl` — stable YouTube URL used for E2E analysis
- `pollMaxAttempts` / `pollDelayMs` — async poll limits (default 60 × 5s ≈ 5 min)

## Test tiers

| Tag | Requests | When to run |
|-----|----------|-------------|
| `smoke` | Health, invalid link → 400 | Every PR / after deploy |
| `e2e` | Start analysis → poll until `ready`/`failed` | Nightly or pre-release (slow; hits YouTube + ML) |

## Run

From repo root (waits for `/health`, then runs smoke tests by default):

```bash
./run.sh integration-tests
./run.sh integration-tests --tags e2e
```

Or from this directory with Bruno directly:

```bash
cd integration_tests
bru run --env local --tags smoke
bru run --env local --tags e2e
bru run --env local
```

## Async flow

`/api/v2/timestamps` returns `202 pending` on first request, then `200 ready` or `200 failed` after background analysis.

- **Start timestamps analysis** — kicks off or hits cache; chains to poll on `pending`
- **Poll timestamps** — loops until `ready`/`failed` or timeout

If the video is already cached in MySQL, the start request returns `200 ready` immediately and polling is skipped.

## Notes

- E2E tests depend on YouTube transcript availability and Hugging Face model load — failures may be flaky.
- No auth on the API today; CORS does not affect Bruno.
- Do not point destructive or high-volume tests at production.
