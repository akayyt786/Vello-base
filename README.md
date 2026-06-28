# OwnFirebase

A complete, self-hosted Firebase replacement built on Django + PostgreSQL + Redis + Rust. Own your data, control your costs, and get the full Firebase feature set without vendor lock-in.

---

## What Is This?

Firebase is ~25 tightly integrated managed services. This project rebuilds every one of them using open-source tools you can run anywhere — a VPS, Kubernetes, bare metal, or your laptop.

| Firebase Service | This Project | Stack |
|---|---|---|
| Authentication | JWT auth, anonymous, social OAuth | djangorestframework-simplejwt, django-allauth |
| Cloud Firestore | Document + collection API with JSONB | Django + PostgreSQL JSONB + GIN indexes |
| Realtime Database | WebSocket listeners | Django Channels + Redis + Postgres LISTEN/NOTIFY |
| Cloud Storage | Object storage API | django-storages + MinIO (S3-compatible) |
| Cloud Functions | HTTP + background triggers | Celery tasks + DRF endpoints |
| Security Rules | DSL evaluator | **Rust (PyO3)** — 3-10x faster than Python |
| Push Notifications | FCM + APNs + Web Push | Django + **Rust push-worker** (tokio async) |
| Analytics | Event tracking, user properties, funnels | Django + PostgreSQL aggregations |
| Remote Config | Key-value config with conditions | Django + condition evaluator |
| A/B Testing | Experiments + variant assignment | Deterministic MD5 hash bucketing |
| Crashlytics | Crash grouping, error reports | Django + sha256 signature deduplication |
| Performance Monitoring | Traces + network requests | Django + batch ingest |

---

## Architecture

```
                        ┌─────────────────────────────────────────┐
                        │              Django (ASGI/Daphne)        │
                        │                                          │
  REST clients ────────►│  Auth · Data · Storage · Functions       │
  WebSocket clients ───►│  Push · Analytics · Config · Crashlytics │
                        └─────────┬───────────────────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
       PostgreSQL 16          Redis 7            MinIO
       (JSONB, RLS,        (Channels,         (S3-compatible
        pgvector)          Celery, Cache,      object storage)
                           Push queue)
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Rust Push Worker        │
                    │  (tokio, BLPOP queue)    │
                    │  FCM · APNs · Web Push   │
                    └─────────────────────────┘

  Rust rules-engine (PyO3 .so) ── imported by Django in-process
```

**Why Rust?**
- `rust/rules-engine` — security rules DSL evaluator compiled as a Python extension (PyO3). Runs in Django's process with zero IPC overhead.
- `rust/push-worker` — standalone tokio async service. BLPOP from Redis, delivers to FCM/APNs/Web Push concurrently, writes delivery status back to Postgres via sqlx.

---

## Project Structure

```
own firebase/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml          # Full local stack
├── postgres-init.sql           # RLS + pgvector setup
│
├── ownfirebase/                # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py                 # WebSocket (Channels)
│   └── wsgi.py
│
├── core/                       # Multi-tenant foundation
│   ├── models.py               # Project, ProjectMembership
│   ├── middleware.py           # JWT + project context injection
│   └── permissions.py
│
├── api/                        # Auth + Project management
│   ├── views.py                # register, login, projects, members
│   ├── serializers.py
│   └── urls.py
│
├── data/                       # Firestore-like Document API
├── realtime/                   # WebSocket consumers
├── storage/                    # Object storage (MinIO/S3)
├── functions/                  # Cloud Functions (HTTP + Celery)
├── rules/                      # Security Rules DSL
├── push/                       # Push Notifications
├── analytics/                  # Analytics + event tracking
├── config/                     # Remote Config + A/B Testing
├── crashlytics/                # Crashlytics + Performance
│
├── rust/
│   ├── rules-engine/           # PyO3 extension (security rules)
│   │   └── src/lib.rs          # evaluate() callable from Python
│   └── push-worker/            # tokio async push delivery
│       ├── src/main.rs
│       ├── src/fcm.rs
│       ├── src/apns.rs
│       ├── src/webpush.rs
│       └── Dockerfile
│
└── tests/
    ├── conftest.py
    ├── test_auth.py
    ├── test_data_api.py
    ├── test_projects.py
    ├── test_rules.py
    ├── test_storage.py
    ├── test_functions.py
    ├── test_realtime.py
    ├── test_push.py
    └── test_phase4.py          # Analytics + Config + Crashlytics
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### 1. Clone

```bash
git clone https://github.com/akayyt786/Vello-base.git
cd Vello-base
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — see Environment Variables section below
```

### 3. Start the full stack

```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| Django API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/api/docs/ |
| ReDoc | http://localhost:8000/api/redoc/ |
| Django Admin | http://localhost:8000/admin/ |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| MinIO Console | http://localhost:9001 |

Migrations run automatically on startup.

### 4. Create a superuser

```bash
docker-compose exec django python manage.py createsuperuser
```

### 5. Run tests

```bash
docker-compose exec django pytest
# or
docker-compose --profile tests up tests
```

### 6. Stop

```bash
docker-compose down        # stop containers
docker-compose down -v     # also wipe volumes (reset DB)
```

---

## Local Development (Without Docker)

```bash
# 1. Services (Postgres + Redis + MinIO)
docker-compose up postgres redis minio -d

# 2. Python env
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Migrate + run
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## API Reference

### Authentication

```
POST /api/v1/auth/register/          Register with email + password
POST /api/v1/auth/login/             Login → access + refresh JWT
POST /api/v1/auth/token/refresh/     Refresh access token
POST /api/v1/auth/logout/            Blacklist refresh token
POST /api/v1/auth/anonymous-signin/  Create anonymous session
```

### Projects & Members

```
GET    /api/v1/projects/                    List your projects
POST   /api/v1/projects/                    Create project
GET    /api/v1/projects/{id}/               Project detail
PUT    /api/v1/projects/{id}/               Update project
DELETE /api/v1/projects/{id}/               Delete project
GET    /api/v1/projects/{id}/members/       List members
POST   /api/v1/projects/{id}/invite_member/ Invite member (owner only)
GET    /api/v1/memberships/                 List memberships
POST   /api/v1/memberships/{id}/remove_member/ Remove member
```

### Data API (Firestore-like)

```
GET    /api/projects/{id}/data/{collection}/         List documents
POST   /api/projects/{id}/data/{collection}/         Create document
GET    /api/projects/{id}/data/{collection}/{doc}/   Get document
PUT    /api/projects/{id}/data/{collection}/{doc}/   Update document
DELETE /api/projects/{id}/data/{collection}/{doc}/   Delete document
POST   /api/projects/{id}/data/query/                Filtered query
POST   /api/projects/{id}/data/batch/                Batch write
```

### Storage

```
GET    /api/projects/{id}/storage/files/                  List files
POST   /api/projects/{id}/storage/files/                  Upload file
GET    /api/projects/{id}/storage/files/{pk}/             File detail
DELETE /api/projects/{id}/storage/files/{pk}/             Delete file
GET    /api/projects/{id}/storage/files/{pk}/download/    Download file
POST   /api/projects/{id}/storage/files/{pk}/presigned/   Presigned URL
```

### Cloud Functions

```
GET    /api/projects/{id}/functions/              List functions
POST   /api/projects/{id}/functions/              Register function
POST   /api/projects/{id}/functions/{pk}/invoke/  Invoke (HTTP trigger)
GET    /api/projects/{id}/functions/{pk}/logs/    Function logs
```

### Push Notifications

```
POST   /api/projects/{id}/push/tokens/register/            Register device token (FCM/APNs/Web)
POST   /api/projects/{id}/push/tokens/{pk}/unregister/     Deactivate token
GET    /api/projects/{id}/push/topics/                     List topics
POST   /api/projects/{id}/push/topics/                     Create topic (editor)
POST   /api/projects/{id}/push/topics/{pk}/subscribe/      Subscribe device to topic
POST   /api/projects/{id}/push/topics/{pk}/unsubscribe/    Unsubscribe
POST   /api/projects/{id}/push/notifications/              Send notification (queues to Rust worker)
GET    /api/projects/{id}/push/campaigns/                  List campaigns
POST   /api/projects/{id}/push/campaigns/                  Create campaign (editor)
POST   /api/projects/{id}/push/campaigns/{pk}/send/        Fire campaign immediately
```

### Analytics

```
POST   /api/projects/{id}/analytics/events/                Log event
POST   /api/projects/{id}/analytics/events/batch/          Batch log (up to 500)
GET    /api/projects/{id}/analytics/events/                List events
POST   /api/projects/{id}/analytics/user-properties/set/   Set user properties (bulk upsert)
GET    /api/projects/{id}/analytics/user-properties/       List user properties
POST   /api/projects/{id}/analytics/conversion-events/     Mark conversion event (editor)
GET    /api/projects/{id}/analytics/query/                 Aggregated query
  ?metric=event_count|unique_users|session_count
  &event_name=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  &group_by=day|week|month|event_name|platform
```

### Remote Config

```
GET    /api/projects/{id}/config/parameters/               List config params
POST   /api/projects/{id}/config/parameters/               Create param (editor)
GET    /api/projects/{id}/config/parameters/fetch/         Evaluate config for client
  ?platform=web|android|ios&app_version=1.2.3&user_id=...
POST   /api/projects/{id}/config/parameters/publish/       Publish version snapshot (editor)
GET    /api/projects/{id}/config/parameters/{pk}/conditions/    List conditions
POST   /api/projects/{id}/config/parameters/{pk}/conditions/    Add condition (editor)
```

### A/B Testing

```
GET    /api/projects/{id}/config/experiments/                   List experiments
POST   /api/projects/{id}/config/experiments/                   Create experiment (editor)
POST   /api/projects/{id}/config/experiments/{pk}/start/        Start experiment
POST   /api/projects/{id}/config/experiments/{pk}/pause/        Pause experiment
POST   /api/projects/{id}/config/experiments/{pk}/complete/     Mark complete
POST   /api/projects/{id}/config/experiments/{pk}/assign/       Assign user to variant
  body: {"user_id": "uid_123"}  → returns variant + config_overrides
GET    /api/projects/{id}/config/experiments/{pk}/variants/     List variants
POST   /api/projects/{id}/config/experiments/{pk}/variants/     Add variant (editor)
```

### Crashlytics + Performance

```
POST   /api/projects/{id}/crashlytics/reports/                Submit crash report
GET    /api/projects/{id}/crashlytics/reports/                List crash reports
GET    /api/projects/{id}/crashlytics/groups/                 List crash groups (deduplicated)
PATCH  /api/projects/{id}/crashlytics/groups/{pk}/            Update notes (editor)
POST   /api/projects/{id}/crashlytics/groups/{pk}/resolve/    Mark resolved (editor)
POST   /api/projects/{id}/crashlytics/groups/{pk}/unresolve/  Reopen (editor)
GET    /api/projects/{id}/crashlytics/summary/                Dashboard summary stats
POST   /api/projects/{id}/crashlytics/traces/                 Submit performance trace
POST   /api/projects/{id}/crashlytics/traces/batch/           Batch traces (up to 500)
POST   /api/projects/{id}/crashlytics/network-requests/       Submit network request
POST   /api/projects/{id}/crashlytics/network-requests/batch/ Batch (up to 500)
```

---

## API Examples

### Register + get token

```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123","first_name":"John","last_name":"Doe"}'
```

```json
{
  "access": "eyJ0eXAiOiJKV1Qi...",
  "refresh": "eyJ0eXAiOiJKV1Qi...",
  "user": {"id": 1, "email": "user@example.com"}
}
```

### Create a project

```bash
curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"My App","description":"Test project"}'
```

### Write a document

```bash
curl -X POST http://localhost:8000/api/projects/PROJECT_ID/data/users/ \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"name":"Alice","plan":"pro","score":42}}'
```

### Log an analytics event

```bash
curl -X POST http://localhost:8000/api/projects/PROJECT_ID/analytics/events/ \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_name":"purchase","event_params":{"item_id":"sku_99","revenue":9.99},"platform":"web"}'
```

### Fetch evaluated Remote Config

```bash
curl "http://localhost:8000/api/projects/PROJECT_ID/config/parameters/fetch/?platform=android&app_version=2.1.0" \
  -H "Authorization: Bearer ACCESS_TOKEN"
# → {"dark_mode": "true", "max_retries": "3", "feature_x": "false"}
```

### Submit a crash report

```bash
curl -X POST http://localhost:8000/api/projects/PROJECT_ID/crashlytics/reports/ \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "exception_type": "NullPointerException",
    "exception_message": "Attempt to invoke method on null object",
    "stack_trace": "at com.myapp.MainActivity.onCreate(MainActivity.java:42)\n...",
    "platform": "android",
    "app_version": "2.1.0",
    "fatal": true,
    "occurred_at": "2026-06-28T10:30:00Z"
  }'
```

---

## Security Model

### Role-based access

Every project membership has a role:

| Role | Permissions |
|---|---|
| `owner` | Full access including delete project, manage members |
| `editor` | Create/update/delete data, send push, manage config |
| `viewer` | Read-only access |

### Security Rules

Write Firebase-style rules for your Data API:

```json
{
  "rules": {
    "users": {
      ".read": "auth.uid != null",
      ".write": "auth.uid == owner_id"
    },
    "public": {
      ".read": true,
      ".write": "auth.uid != null"
    }
  }
}
```

Rules are evaluated by the Rust `rules-engine` PyO3 extension — compiled native code, no interpreter overhead.

### Multi-tenancy

Every table carries a `project_id` FK. PostgreSQL Row-Level Security policies enforce tenant isolation at the database level — no cross-project data leaks even if application code has a bug.

---

## Rust Components

### rules-engine (PyO3)

```bash
cd rust/rules-engine
maturin develop --release    # compiles .so, installs into .venv
```

Called from Django as a regular Python import:

```python
from rules_engine import evaluate
allowed = evaluate(condition_json, auth_uid, is_authenticated, doc_data_json, doc_owner_id, operation)
```

### push-worker (tokio)

```bash
# Run standalone
cd rust/push-worker
cargo run --release

# Or via Docker Compose (included by default)
docker-compose up push-worker
```

Environment variables for the worker:

```
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ownfirebase
FCM_SERVER_KEY=...
APNS_KEY_ID=...   APNS_TEAM_ID=...   APNS_BUNDLE_ID=...
VAPID_PRIVATE_KEY=...   VAPID_SUBJECT=mailto:admin@example.com
PUSH_WORKER_CONCURRENCY=8
```

---

## Environment Variables

```bash
# Django
DEBUG=False
DJANGO_SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_NAME=ownfirebase
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage (MinIO / S3)
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_STORAGE_BUCKET_NAME=ownfirebase
AWS_S3_ENDPOINT_URL=http://localhost:9000

# JWT
JWT_SIGNING_KEY=your-jwt-signing-key

# Push (optional — only needed if using push notifications)
FCM_SERVER_KEY=
APNS_KEY_ID=
APNS_TEAM_ID=
APNS_BUNDLE_ID=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=mailto:admin@example.com

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## Testing

293 tests, 0 failures.

```bash
# Run all tests
pytest tests/ -q

# Specific module
pytest tests/test_push.py -v
pytest tests/test_phase4.py -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

Fixtures (in `tests/conftest.py`):
- `api_client` — unauthenticated DRF client
- `authenticated_client` — client with JWT for `test_user`
- `test_user` — User + UserProfile
- `test_project` — Project owned by `test_user`

---

## Production Deployment

### Docker Compose (single server)

```bash
cp .env.example .env
# fill in production values

docker-compose up -d --build
```

### Behind nginx (reverse proxy + WebSocket)

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Daphne (ASGI + WebSocket)

```bash
daphne -b 0.0.0.0 -p 8000 ownfirebase.asgi:application
```

### Kubernetes

```bash
docker build -t yourregistry/ownfirebase:latest .
docker push yourregistry/ownfirebase:latest
# rust push-worker has its own Dockerfile at rust/push-worker/Dockerfile
```

---

## Roadmap

- [ ] Phase 5: Enhanced Auth — Phone OTP, Anonymous auth, MFA (TOTP + SMS), Passwordless email link, App Check
- [ ] Phase 6: AI/ML — pgvector embeddings, LLM API wrapper, semantic search
- [ ] Phase 7: Dynamic Links, In-App Messaging, CLI (`ownfb`), Admin Console UI

---

## License

MIT
