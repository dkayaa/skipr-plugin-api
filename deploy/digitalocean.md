# Deploy Skipr on DigitalOcean

Use a **Droplet + Docker Compose** (app, MySQL, Caddy on one machine). Skip App Platform — PyTorch and Hugging Face models need several GB of RAM.

## Architecture

| Component | Setup |
|-----------|--------|
| Compute | Droplet 8 GB RAM / 4 vCPU |
| Database | **Compose MySQL** (`db` service) on same droplet — not exposed publicly |
| TLS | Caddy in `docker-compose.prod.yml` — automatic Let's Encrypt |
| DNS | A record → Droplet IP (or floating IP) |

```
Internet → Caddy :443 → app (gunicorn :8090) → db (MySQL, internal only)
```

**Skip App Platform** — image size, memory limits, and cold starts work against you.

## 1. Create infrastructure

### Droplet

1. Create Droplet: **Ubuntu 24.04**, **8 GB RAM** (4 GB may OOM on first model load).
2. Enable monitoring and add your SSH key.
3. Assign floating IP if you use one; note the public IP for DNS.

### Domain

1. Add an **A record**: `api.yourdomain.com` → Droplet IP (or floating IP).
2. Set `DOMAIN=api.yourdomain.com` in `.env`.

### Firewall

Allow only:

- `22` — SSH (restrict to your IP if possible)
- `80` — HTTP (Caddy ACME challenge)
- `443` — HTTPS

Do **not** open `3306` or `8090`. MySQL is only reachable inside the Docker network.

### Database

No separate DBaaS needed. The `db` service in `docker-compose.yml` runs MySQL in a container with a persistent `db_data` volume. Prod overlay sets `ports: []` so MySQL is never published to the host.

If you already created DigitalOcean Managed MySQL, you can **delete it** to save ~$15/mo — this stack does not use it.

## 2. Prepare the server

```bash
ssh root@<droplet-ip>

apt-get update && apt-get install -y docker.io docker-compose-v2 git
systemctl enable --now docker

git clone <your-repo-url> /opt/skipr
cd /opt/skipr/server
```

## 3. Configure secrets

```bash
cp .env.example .env
nano .env
```

Generate passwords:

```bash
openssl rand -base64 24
```

Required values:

```env
DOMAIN=api.yourdomain.com
CORS_ORIGINS=https://www.youtube.com
HUGGINGFACE_MODEL=kayaaaa/ad-classifier
CLASSIFIER_BATCH_SIZE=32

DB_USER=skipr
DB_PASSWORD=<strong-password>
DB_NAME=skipr_db
MYSQL_ROOT_PASSWORD=<strong-root-password>
```

Do **not** set `DB_HOST` or `DB_PORT` in `.env` — compose pins `DB_HOST=db` and `DB_PORT=3306` for the app container.

## 4. Start production stack

From repo root:

```bash
./run.sh api-prod
```

This starts all three services: **db**, **app**, **caddy**.

First boot downloads ML models and can take several minutes:

```bash
cd server
docker compose -f docker-compose.db.yml -f docker-compose.yml -f docker-compose.prod.yml logs -f app
```

Wait until you see gunicorn listening before testing HTTPS.

## 5. Verify

```bash
curl -s https://api.yourdomain.com/health
# {"status":"ok"}

curl -s "https://api.yourdomain.com/api/v2/timestamps?link=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
# {"status":"pending"}  (202) then poll until ready
```

Point skipr-plugin at `https://api.yourdomain.com` (no trailing slash).

## 6. Updates

```bash
cd /opt/skipr
git pull
./run.sh api-prod
```

Migrations run automatically via `entrypoint.sh` on container start.

## Cost estimate

| Item | ~Monthly |
|------|----------|
| Droplet 8 GB | ~$48 |
| Domain | ~$1–2 |
| **Total** | **~$50** |

Cheaper alternatives: Hetzner CPX31 (8 GB) ~€15/mo with the same compose setup.

## Local dev

From repo root:

```bash
cp server/.env.example server/.env
./run.sh api-dev
# App: http://127.0.0.1:8090
# MySQL: 127.0.0.1:3306 (localhost only, via docker-compose.db.dev.yml)
```

```bash
cd server
docker compose -f docker-compose.db.yml exec db mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" skipr_db > backup.sql
```
