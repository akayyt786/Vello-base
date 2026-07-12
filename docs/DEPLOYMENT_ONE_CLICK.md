# Deploying OwnFirebase

Three ways to run OwnFirebase, from fastest/local to production Kubernetes. All commands below
were checked against the actual files in this repo (`docker-compose.yml`, `docker-compose.prod.yml`,
`Dockerfile`, `Makefile`, `cli.py`, `requirements.txt`) — nothing here is aspirational.

1. [Docker Compose](#1-docker-compose-quickest-start) — quickest start, single machine.
2. [Kubernetes (Helm + Terraform)](#2-kubernetes-helm-chart--terraform-module) — production, multi-node.
3. [One-click cloud deploy (Render)](#3-one-click-cloud-deploy) — hosted, no server to manage.

---

## 1. Docker Compose (quickest start)

This is the path the repo is actually built and tested around — `docker-compose.yml` defines 7
services (`postgres`, `minio`, `redis`, `django`, `celery`, `celery_beat`, plus an optional
`migrations`/`tests` profile pair and a Rust `push-worker`), and `docker-compose.prod.yml` is a
small overlay for production process management.

### 1.1 Bring the stack up

```bash
git clone <this-repo>
cd own-firebase
cp .env.example .env
# Edit .env: set a real DJANGO_SECRET_KEY, DATABASE_PASSWORD, etc. — the example file ships with
# placeholder values that are fine for local dev only.

docker-compose up -d --build
```
This builds the app image from the repo-root `Dockerfile` (`python:3.11-slim`, installs
`requirements.txt`, copies the project in) and starts:
- `postgres` (16-alpine, with `pgvector`/`pg_trgm`/RLS enabled via `postgres-init.sql`, mounted at
  `/docker-entrypoint-initdb.d/01-init.sql`)
- `minio` (S3-compatible storage, console on `:9001`, API on `:9000`)
- `redis` (Celery broker/result backend, Channels layer, cache)
- `django` (runs `python manage.py migrate && python manage.py createcachetable && daphne -b 0.0.0.0 -p 8000 ownfirebase.asgi:application` — Daphne serves both HTTP and the realtime WebSocket route from one process)
- `celery` (`celery -A ownfirebase worker -l info`)
- `celery_beat` (`celery -A ownfirebase beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`)
- `push-worker` (Rust binary, `rust/push-worker`, FCM/APNs/Web Push delivery — configured via
  `FCM_SERVER_KEY`/`APNS_*`/`VAPID_*` env vars, all optional/blank by default)

Each of `django`/`celery`/`celery_beat`/`migrations`/`tests` has its own healthcheck or
`depends_on: condition: service_healthy` gate on `postgres`/`redis`, so `docker-compose up -d` will
wait for the DB and broker to actually be ready before starting the app.

### 1.2 Everyday commands

Either the `Makefile` or the bundled `cli.py` (`own` command) wrap the same `docker-compose`
invocations:
```bash
make up            # docker-compose up --build (foreground)
make up-d           # detached
make logs-django    # docker-compose logs -f django
make migrate        # docker-compose exec django python manage.py migrate
make shell          # docker-compose exec django python manage.py shell
make test           # docker-compose exec django pytest -v
make down-v         # stop + wipe volumes (reset DB)

# equivalently, via the CLI (cli.py, installed as `own` per its Typer app name):
python cli.py up
python cli.py shell
python cli.py deploy   # see 1.3 below
```
`quickstart.sh` is an interactive bootstrap that offers Docker Compose or a local
venv+PostgreSQL+Redis setup and runs migrations/`createsuperuser` for you.

Once up: API at `http://localhost:8000`, Swagger UI at `http://localhost:8000/api/docs/` (DEBUG
only — gated behind `if settings.DEBUG` in `ownfirebase/urls.py`), Django admin at
`http://localhost:8000/admin/`, MinIO console at `http://localhost:9001`.

### 1.3 Production overlay (still Docker Compose, single machine)

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# or: python cli.py deploy
```
`docker-compose.prod.yml` overrides the `django` service to run
`gunicorn ownfirebase.wsgi:application -b 0.0.0.0:8000 -w 4 --timeout 120` instead of Daphne, and
sets `DEBUG=false`. **Read the comment in that file carefully**: switching to gunicorn/WSGI means
the realtime WebSocket route is no longer served by this process — the file explicitly notes
"WebSocket / ASGI routes should be handled by a separate Daphne process or an ASGI gateway... placed
behind the load balancer." As shipped, this overlay does not stand up that separate ASGI process
for you; if you need realtime subscriptions in this production mode, you must add that piece
yourself (or keep using Daphne behind your reverse proxy instead of switching to gunicorn).
`cli.py`'s `deploy` command additionally refuses to run if `.env` still has the default
`DJANGO_SECRET_KEY=dev-secret-key...` placeholder — a real safety check, not just documentation.

This is still a single-host deployment (no autoscaling, no multi-node failover) — for that, see §2.

---

## 2. Kubernetes: Helm chart + Terraform module

For multi-node/production Kubernetes deployment, two parallel efforts exist in this repo (owned
and maintained separately from this doc):

- **Helm chart:** `deploy/helm/ownfirebase/` — see that directory's own `README.md` for exact
  install commands, values, and template layout. Do not assume specific template filenames or
  `values.yaml` keys beyond what that README documents; this doc intentionally does not restate
  chart internals that live (and may still be evolving) in that directory.
- **Terraform module:** `deploy/terraform/` — provisions the underlying cloud infrastructure (VPC,
  managed Postgres, managed Redis/cache, object storage, Kubernetes cluster, etc., depending on
  what that module targets). Again, see that directory's own documentation for exact variables,
  outputs, and supported cloud providers rather than relying on this doc for specifics.

At a high level, the expected flow is: `terraform apply` (or your existing cluster) to get a
Kubernetes cluster + managed Postgres/Redis, then `helm install ownfirebase deploy/helm/ownfirebase/`
pointed at those endpoints — mirroring the same services `docker-compose.yml` runs locally
(Django/Daphne, Celery worker, Celery Beat, Postgres, Redis, object storage), just orchestrated by
Kubernetes instead of Compose. Confirm the exact commands against each directory's own README
before running them; those charts/modules are actively being built in this repo and this doc does
not duplicate (and could drift from) their real contents.

---

## 3. One-click cloud deploy

### 3.1 What a "Deploy to Render/Railway" button actually needs (general background)

A "Deploy to X" badge is just a link to that provider's UI with a `repo` query parameter; the
provider then reads a manifest file it expects to find at the repo root to know what to build and
run:
- **Render** reads `render.yaml` (a "Blueprint") — it can declare **multiple services** (web
  services, background workers, cron jobs, static sites, key-value/Redis instances) plus managed
  Postgres databases in one file, each with its own build/start command and env vars, with
  `fromDatabase`/`fromService` references to wire connection strings between them automatically.
- **Railway** reads `railway.json`/`railway.toml`, but that format configures **one service's**
  build/deploy settings — it is not a multi-service orchestrator the way `render.yaml` or
  `docker-compose.yml` are. Railway's actual multi-service story for an existing Compose project is
  to drag-and-drop your `docker-compose.yml` onto a project canvas in their dashboard, which
  auto-creates one Railway service (with volumes) per Compose service as a reviewable, editable set
  of staged changes — this is a one-time interactive import, not a static file a "Deploy" badge can
  drive unattended the way Render's Blueprint can.

**Given that**, this repo now ships a real `render.yaml` at the repo root (multi-service, matches
Render's actual Blueprint schema), and for Railway the practical path is the dashboard's
docker-compose import rather than a fabricated `railway.json` that would silently under-represent
this app's multi-service shape (Postgres + Redis + Django + Celery worker + Celery Beat).

### 3.2 Render — `render.yaml` at repo root

The `render.yaml` in this repo declares:

| Service | Type | Command | Plan used |
|---|---|---|---|
| `ownfirebase-db` | Postgres | — | `starter` |
| `ownfirebase-redis` | Key Value | — | `starter` |
| `ownfirebase-web` | web (`runtime: docker`) | `migrate && createcachetable && daphne -p 8000 …` | `free` |
| `ownfirebase-worker` | background worker (`runtime: docker`) | `celery -A ownfirebase worker -l info` | `starter` |
| `ownfirebase-beat` | background worker (`runtime: docker`) | `celery -A ownfirebase beat -l info --scheduler …` | `starter` |

To deploy: push this repo to your own GitHub/GitLab, then in Render choose **New → Blueprint** and
point it at your repo (or use a `https://render.com/deploy?repo=<your-repo-url>` badge once the repo
is public) — Render will read `render.yaml` and propose all five resources above for you to
confirm before creating them.

**Read before you click deploy:**

- **This is genuinely not free end-to-end.** Render's free tier only covers a single web service
  (with cold starts after ~15 minutes idle) and does not offer free background workers or
  time-unlimited free Postgres. The Celery worker, Celery Beat, and Postgres in this blueprint are
  set to Render's `starter` plan, which has a real monthly cost per service. If you only want to
  poke at the HTTP API without background jobs (no async Cloud Functions dispatch, no scheduled
  triggers, no async push delivery), you can delete the `ownfirebase-worker` and `ownfirebase-beat`
  blocks from `render.yaml` before deploying and stay on cheaper plans — but Cloud Functions
  invocation and scheduled triggers genuinely will not run without at least the worker.
- **`postgres-init.sql` does not run automatically on Render.** That script (repo root) enables
  the `pgvector`/`pg_trgm`/`uuid-ossp` extensions and sets up RLS session-variable helper functions,
  via Postgres's `docker-entrypoint-initdb.d` mechanism — which only exists for the containerized
  Postgres in `docker-compose.yml`, not Render's managed Postgres. After Render provisions
  `ownfirebase-db`, connect with `psql` (Render gives you a connection string in its dashboard) and
  run the `CREATE EXTENSION`/`CREATE SCHEMA`/`ALTER DATABASE` statements from `postgres-init.sql`
  by hand once (substituting Render's actual generated database name for the hardcoded
  `ownfirebase` in that file) before relying on pgvector-backed features (`rag/` app) or RLS.
- **Object storage (MinIO in Compose) has no Render equivalent in this blueprint.** Render does not
  offer a managed S3-compatible bucket product comparable to the `minio` Compose service, so
  `render.yaml` does not attempt to stand one up. To use the Storage API (§3 of
  `docs/FIREBASE_MIGRATION_GUIDE.md`) on Render, point `AWS_S3_ENDPOINT_URL`/`AWS_ACCESS_KEY_ID`/
  `AWS_SECRET_ACCESS_KEY`/`AWS_STORAGE_BUCKET_NAME` (see `.env.example`) at a real S3-compatible
  bucket you provision elsewhere (AWS S3, Cloudflare R2, Backblaze B2, or your own MinIO instance),
  and set `USE_S3=True`.
- **The Rust `push-worker` service is intentionally omitted** from `render.yaml` to keep the
  Blueprint's cost/complexity down — push notification *registration* and the REST API still work
  without it, but actual FCM/APNs/Web Push delivery (`rust/push-worker`) will not run. Add it as its
  own `runtime: docker` service (`dockerfilePath: ./rust/push-worker/Dockerfile`) if you need it.
- **Migration race on first boot.** All three app services (`web`, `worker`, `beat`) start
  concurrently; only `ownfirebase-web`'s start command runs `migrate`. On a fresh deploy the worker
  and beat services may briefly start before tables exist. Render's `preDeployCommand` field can
  centralize this on paid plans, but as configured here it relies on the same idempotent
  `python manage.py migrate` embedded in the web service's command, matching what
  `docker-compose.yml` already does — expect the worker/beat logs to show transient connection
  errors on the very first boot only.
- **Validate before trusting this file end-to-end.** Render's exact plan names,
  `fromDatabase`/`fromService` property names, and free-tier availability are controlled by Render
  and can change. Run Render's Blueprint preview (`New → Blueprint`, or `render blueprint sync
  --dry-run` via the Render CLI) and review the proposed resources before confirming, and treat the
  cost figures above as "verify current pricing on Render," not a locked-in quote.

### 3.3 Railway — no `railway.json` shipped here, by design

A single-service `railway.json`/`railway.toml` cannot honestly represent "Postgres + Redis + Django
+ Celery worker + Celery Beat" the way `render.yaml` can — shipping one anyway would either silently
drop the worker/beat processes (breaking Cloud Functions and scheduled triggers) or require Railway
IaC/CLI-managed multi-service config that doesn't reduce to a single static file a "Deploy" badge
reads. The accurate, supported path on Railway today is:

```bash
railway login
railway init
# From the Railway dashboard: drag-and-drop docker-compose.yml onto your project canvas.
# Railway stages one service per Compose service (postgres, minio, redis, django, celery,
# celery_beat, push-worker) plus their volumes for you to review, then "Deploy" to provision them.
```
Set the same environment variables `docker-compose.yml` already defines (`DATABASE_*`, `REDIS_URL`,
`DJANGO_SECRET_KEY`, etc. — see `.env.example`) on the imported `django`/`celery`/`celery_beat`
services via the Railway dashboard, since Compose `environment:` blocks that reference `${VAR}`
interpolation are not automatically backed by a `.env` file in Railway's environment.
