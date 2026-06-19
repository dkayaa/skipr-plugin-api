# skipr-plugin Backend

## What ?
Skipr-plugin is a browser extension that uses AI text classification to detect and scrub content from Youtube videos in real-time. 
## Why ? 
Improve the Youtube user experience by automatically skipping those in-video ad reads that were going to be skipped anyway. 
## How ? 
When a user navigates to a Youtube video URL, a request is sent to the backend server to execute the following; the back-end first retrieves the relevant audio transcript and timestamps, leveraging the python's `youtube-transcript-api` library. The transcript undergoes a preprocessing step whereby it is split into overlapping text chunks. Each chunk is then processed by a text-classification model. Specifically, we leverage the pretrained `distilbert-base-uncased` model, fine tuned on a manually curated dataset of 3K+ labelled samples, to employ binary classification for each text chunk as either an advertisement or not. The finetuned model is a binary classification model, classifying advertisement text segments.

## Prerequisites

Local development needs the following:

| Requirement | Used for |
|-------------|----------|
| **Docker** + **Docker Compose v2** (`docker compose`) | Dev/prod stacks (`./run.sh api-dev`, `api-prod`) |
| **Python 3.11** | `./run.sh unit-tests` only (creates `server/.venv`) |

Install Docker from [docker.com](https://docs.docker.com/get-docker/) or your package manager. Verify Compose v2 with `docker compose version` (not the legacy `docker-compose` hyphenated command).

Clone the repo and copy `server/.env.example` to `server/.env` before either setup path below.

## Local Setup

Copy `server/.env.example` to `server/.env`, then use `./run.sh`:

| Command | Description |
|---------|-------------|
| `./run.sh api-dev` | Dev stack in Docker (db + app on http://127.0.0.1:8090) |
| `./run.sh api-dev --clear-volumes` | Dev stack with fresh DB volume |
| `./run.sh api-prod` | Prod stack in Docker (db + app + caddy) |
| `./run.sh unit-tests` | Python unit tests (`tests/`) |
| `./run.sh integration-tests` | Bruno smoke tests (API must be running) |

`./run.sh --help` for all options.

For the browser extension, see the [skipr-plugin](https://github.com/dkayaa/skipr-plugin-browser) repo.

## Production deployment

See [deploy/digitalocean.md](deploy/digitalocean.md) for DigitalOcean Droplet setup (gunicorn, Caddy TLS, managed or compose MySQL).

## Training Data
An indicative training sample is provided below 
```
 {
        "text": "very high quality protein with just 150 calories if you would like to try David you can go to david.com huberman again the link is david.com huberman today's episode is also brought To Us by eight sleep eight sleep makes Smart mattress covers with cooling Heating and sleep tracking capacity now I've spoken before on this podcast about the critical need for us to get adequate amounts of quality sleep each night now one of the best ways to ensure a great night's sleep is to ensure that the temperature of your sleeping environment is correct and that's because in order to fall and stay deeply asleep your body temperature actually has to drop by about 1 to 3° and in order to wake up feeling refreshed and energized your body",
        
        "start": 236.799,
        
        "label": 1
}
```