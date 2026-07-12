# OwnFirebase Helm chart

Deploys OwnFirebase (self-hosted Firebase alternative — Django + Celery +
Django Channels) to Kubernetes. This chart has no external chart
dependencies (no Bitnami subcharts) — Postgres, Redis and MinIO are lean,
single-replica templates owned by this chart, proportionate for a
self-hosted app's own bundled datastores rather than enterprise HA infra.

## What it deploys

| Component        | Kind         | Replicas             | Notes |
|-------------------|--------------|-----------------------|-------|
| `web`             | Deployment   | 2 (default)           | `gunicorn ownfirebase.wsgi:application` — REST API only |
| `websocket`       | Deployment   | 2 (default)           | `daphne ownfirebase.asgi:application` — realtime/WebSocket API |
| `celery-worker`   | Deployment   | 2 (default)           | `celery -A ownfirebase worker` |
| `celery-beat`     | Deployment   | **1, always**         | `celery -A ownfirebase beat --scheduler django_celery_beat.schedulers:DatabaseScheduler` |
| `push-worker`     | Deployment   | 1 (default), disabled | Rust FCM/APNs/WebPush worker (`rust/push-worker`) — opt-in |
| `postgres`        | Deployment   | 1                     | `pgvector/pgvector:pg16`, PVC-backed |
| `redis`           | Deployment   | 1                     | `redis:7-alpine`, ephemeral (no PVC) |
| `minio`           | Deployment   | 1                     | `minio/minio:latest`, PVC-backed |
| migration Job     | Job (Helm hook) | n/a                | Runs `migrate` / `createcachetable` / `collectstatic` once per install/upgrade |
| Ingress           | Ingress      | n/a                   | Routes `/ws/` → websocket Service, `/` → web Service |

## Why web and websocket are split

`docker-compose.prod.yml` swaps the `django` service from `daphne` (ASGI) to
`gunicorn` (WSGI) for production, but its own comment says WebSocket/ASGI
routes "should be handled by a separate Daphne process ... placed behind the
load balancer" — and then never actually adds that second process. So a
compose-based prod deploy silently has **no working WebSocket/realtime
feature**. This chart fixes that for real: `web` and `websocket` are two
separate Deployments built from the *same* image, running different
commands, each with its own Service. The Ingress (`templates/ingress.yaml`)
sends the `/ws/` path prefix to the websocket Service and everything else to
the web Service — matching the real WS path in `realtime/routing.py`
(`/ws/v1/projects/{project_id}/listen/`).

## Install

```bash
# 1. Build and load the app image (kind has no registry access by default)
docker build -t ownfirebase/api:latest .
kind load docker-image ownfirebase/api:latest

# 2. Install (django secret key is required — no insecure default is shipped
#    for it since it's used for session/CSRF/JWT signing, not just container
#    bootstrapping)
helm install ownfirebase deploy/helm/ownfirebase \
  --set secrets.djangoSecretKey="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"

# Or, for anything beyond a quick local smoke test, use a values file you
# don't commit:
helm install ownfirebase deploy/helm/ownfirebase -f my-values.yaml
```

`helm upgrade --install` re-runs the migration hook automatically; nothing
extra to do on redeploys.

## What MUST be overridden for a real (non-local-kind) deployment

- `secrets.djangoSecretKey` — **required**, no default. Django hard-crashes
  without it (`settings.py`: `SECRET_KEY = os.environ['DJANGO_SECRET_KEY']`).
  `templates/secret.yaml` uses Helm's `required` function so `helm
  install`/`template` fails fast with a clear message instead of shipping a
  crash-looping pod.
- `postgresql.auth.password` / `minio.auth.rootPassword` — shipped with the
  exact same insecure defaults (`postgres` / `minioadmin`+`minioadmin`)
  Django's own `settings.py` already falls back to, purely so `helm install`
  works out of the box on a fresh local kind cluster with zero flags.
  **Change both for anything that isn't a throwaway local cluster.**
- `config.allowedHosts` / `ingress.host` — keep these in sync (Django
  rejects requests whose `Host` header isn't in `ALLOWED_HOSTS`).
- `ingress.tls.*` — no TLS by default. See "Known gaps" below — this
  actually matters more than usual for this app.
- Any of the optional integration secrets you actually use: `stripeSecretKey`,
  `stripeWebhookSecret`, `twilioAccountSid`/`twilioAuthToken`,
  `githubClientSecret`, `fcmServerKey`, `vapidPrivateKey`, `aiProviderKek`,
  `sentryDsn`, `emailHostPassword`. All default to `""`, which each
  corresponding app module treats as "feature disabled" (verified in source,
  not assumed) — safe to leave blank if you don't use that integration.

## Secret vs. non-secret split (judgment calls)

Every `os.environ.get`/`os.getenv()` read in `ownfirebase/settings.py`,
`core/observability.py` and `ai/encryption.py` was enumerated and placed in
either `templates/configmap.yaml` (non-secret) or `templates/secret.yaml`
(secret-shaped). A few borderline calls worth knowing about:

- **`AWS_ACCESS_KEY_ID`** was treated as secret-shaped (paired 1:1 with
  `AWS_SECRET_ACCESS_KEY` and mirrors MinIO's own root user), even though an
  access-key-ID alone is sometimes treated as semi-public elsewhere.
- **`TWILIO_ACCOUNT_SID`** was treated as secret-shaped for the same
  reason (always used together with `TWILIO_AUTH_TOKEN`), while
  `TWILIO_PHONE_NUMBER` (a real phone number, already visible to every SMS
  recipient) was treated as non-secret config.
- **`SENTRY_DSN`** was treated as secret-shaped out of caution, even though
  Sentry DSNs are not bearer credentials in the traditional sense.
- **`EMAIL_HOST_USER`** was treated as non-secret (mirrors the
  `DATABASE_USER`/`DATABASE_PASSWORD` split — the *user* is config, the
  *password* is the secret).
- **`APNS_KEY_ID`/`APNS_TEAM_ID`/`APNS_BUNDLE_ID`** are Apple-issued
  identifiers, not the actual `.p8` private key material (which isn't
  modeled as an env var anywhere in this codebase), so they're non-secret
  config.

## `postgresql.enabled` / `redis.enabled` / `minio.enabled`

Each defaults to `true` (bundled). Set to `false` to point at an external
managed service instead:

```yaml
postgresql:
  enabled: false
externalDatabase:
  host: my-managed-postgres.example.com
  port: "5432"
  database: ownfirebase
  username: ownfirebase
secrets:
  databasePassword: "..."   # required when postgresql.enabled=false

redis:
  enabled: false
externalRedis:
  url: "redis://:password@my-managed-redis.example.com:6379/0"

minio:
  enabled: false
config:
  awsS3EndpointUrl: "https://s3.amazonaws.com"
  awsS3RegionName: "us-east-1"
  awsS3UseSSL: "True"
secrets:
  awsAccessKeyId: "..."       # required when minio.enabled=false
  awsSecretAccessKey: "..."
```

## The migration Job: `post-install,pre-upgrade`, not `pre-install,pre-upgrade`

The task this chart was built against asked for
`helm.sh/hook: pre-install,pre-upgrade`. This chart deliberately uses
`post-install,pre-upgrade` instead — **this is a considered deviation, not
an oversight**:

Postgres and Redis are bundled inside *this same chart*. Helm's
`pre-install` hooks run **before any of the chart's own normal templates are
even created** — including the bundled `postgres`/`redis` Deployments. A
`pre-install` migration Job would therefore always fail on a first install:
there is nothing for it to connect to, and nothing will ever create it
while that hook is running (the Deployment that would create it hasn't been
submitted to the API server yet). `post-install` runs after the chart's
normal resources have been created, and `templates/migration-job.yaml`'s
`initContainers` additionally poll `pg_isready` / a TCP check against Redis
before running `migrate`, so it waits for those pods to actually be ready,
not just "created". `pre-upgrade` is kept exactly as requested for upgrades,
since on an upgrade the datastores already exist from the previous release.

**Known trade-off:** on a brand-new install there's a short window (Postgres
starting for the first time, running `postgres-init.sql`, can take a few
seconds beyond simple pod-ready) where `web`/`websocket` pods may already be
serving before migrations finish. Requests touching un-migrated tables will
500 until the migration Job completes, then resolve on their own with no
action needed. `web`/`websocket`/`celery-worker`/`celery-beat` pods also get
their own `wait-for-postgres`/`wait-for-redis` initContainers (see
`_helpers.tpl`'s `ownfirebase.waitForDeps`) so they don't crash-loop while
the bundled datastores are still starting.

## Known gaps carried over from the app itself (not fixable within `deploy/helm/`)

- **`SECURE_SSL_REDIRECT`/`SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE`**:
  `ownfirebase/settings.py` computes these as `not DEBUG` in Python — they
  are **not** read from the environment at all, so
  `docker-compose.prod.yml`'s `SECURE_SSL_REDIRECT: "false"` override is
  already dead configuration upstream of this chart. With this chart's
  default `config.debug: "False"`, Django will force HTTPS redirects and
  secure-only cookies. On a local kind cluster with a plain-HTTP ingress
  (the default here — `ingress.tls.enabled: false`) this **will** break
  login/admin/CSRF-protected requests. For local kind verification, either:
  - `--set config.debug=true` (also exposes `/api/docs/` Swagger/Redoc and
    Django's debug error pages — fine for local testing, not for real prod), or
  - set `ingress.tls.enabled: true` with a real or self-signed cert so the
    HTTPS/secure-cookie requirements are actually satisfied.
  This can't be fixed from `deploy/helm/` alone since it requires a code
  change to `ownfirebase/settings.py`, which is out of scope for this task.
- **Health-check endpoint choice**: `docker-compose.yml`'s own healthcheck
  hits `/api/docs/`, but that route is only registered `if settings.DEBUG:`
  in `ownfirebase/urls.py` — it 404s whenever `DEBUG=False`, which is
  exactly the default for a production-shaped deployment. This chart uses
  `core/health.py`'s dedicated `/health/` (liveness) and `/ready/`
  (readiness — checks DB + cache connectivity) views instead, which are
  registered unconditionally for exactly this purpose.
- **`postgres-init.sql`'s hardcoded database name**: the file is copied
  byte-for-byte into `files/postgres-init.sql` (never retyped, to avoid
  drift) and it contains `ALTER DATABASE ownfirebase SET app.current_project
  = '';` with the name `ownfirebase` hardcoded rather than parameterized.
  This chart's default `postgresql.auth.database` is also `ownfirebase`, so
  it works out of the box — but if you override `postgresql.auth.database`
  to something else, first-time cluster initialization will fail on that
  line. Either keep the default database name, or edit
  `files/postgres-init.sql` yourself.
- **`rust/push-worker` build context**: `docker-compose.yml` builds it with
  `context: ./rust/push-worker`, but `rust/push-worker/Dockerfile` `COPY`s
  `Cargo.toml` (the *workspace* root manifest) and
  `../rules-engine/Cargo.toml` — paths that don't exist relative to
  `rust/push-worker/` alone. You'll need to build it yourself with the
  workspace root as context, e.g.:
  ```bash
  docker build -f rust/push-worker/Dockerfile -t ownfirebase/push-worker:latest rust/
  kind load docker-image ownfirebase/push-worker:latest
  ```
  before setting `pushWorker.enabled=true`.

## Resource sizing (judgment call)

Defaults are sized for a resource-constrained local kind cluster, not
production capacity planning: `128Mi`/`100m` requests and modest limits
(`256Mi`/`500m`) for the Django/Celery pods, slightly less for `celery-beat`
and `push-worker` (lighter processes), and slightly more for bundled
Postgres (`256Mi`/`250m` requests, `512Mi`/`500m` limits) since it's a real
database process. Override all of these under `web.resources`,
`websocket.resources`, `celeryWorker.resources`, `celeryBeat.resources`,
`pushWorker.resources`, `postgresql.resources`, `redis.resources`,
`minio.resources` for real workloads.

## Linting

`helm lint` / `helm template` were **not runnable in the environment this
chart was authored in** (`helm` is not installed there — verified with
`which helm` / `helm version`). Run both yourself before/after your kind
deploy:

```bash
helm lint deploy/helm/ownfirebase
helm template deploy/helm/ownfirebase --set secrets.djangoSecretKey=test-key-only
```
