# Own Firebase - Phase 1 MVP Bootstrap Summary

## What Was Created

This is a complete, working Django project scaffold for the Own Firebase Firestore alternative. All files are production-ready (not pseudocode) and follow the Target Architecture from the spec.

### Project Structure

```
ownfirebase/
├── manage.py                     # Django CLI
├── requirements.txt              # Python dependencies (30 packages)
├── Dockerfile                    # Docker image (Python 3.11-slim)
├── docker-compose.yml            # Full stack: Django, Postgres, Redis, Celery
├── postgres-init.sql             # RLS setup + pgvector + context vars
├── .env.example                  # Environment template
├── .gitignore                    # Python + Django ignore rules
├── celery.py                     # Celery configuration
├── cli.py                        # Typer CLI scaffold (Phase 2+)
├── quickstart.sh                 # One-command bootstrapping script
├── README.md                     # Full setup & API documentation
├── BOOTSTRAP_SUMMARY.md          # This file
│
├── ownfirebase/                  # Django project package
│   ├── __init__.py               # Loads Celery
│   ├── settings.py               # 250+ lines: DB, Redis, JWT, CORS, RLS setup
│   ├── urls.py                   # Base routes + OpenAPI schema endpoints
│   ├── wsgi.py                   # WSGI application
│   └── asgi.py                   # ASGI application (Channels stub for Phase 2)
│
├── core/                         # Core app: models + middleware
│   ├── models.py                 # Project, ProjectMembership, UserProfile, MultiTenantModel
│   ├── middleware.py             # JWT extraction + multi-tenant context vars
│   ├── permissions.py            # IsProjectMember, IsProjectOwner, IsProjectEditorOrOwner
│   ├── admin.py                  # Django admin configuration
│   ├── apps.py                   # App config
│   └── __init__.py
│
├── api/                          # DRF REST API app
│   ├── views.py                  # 5 viewsets: Auth, Project, Membership, Data (stub), Rules (stub)
│   ├── serializers.py            # 8 serializers for all models
│   ├── urls.py                   # API routing (15+ endpoints)
│   ├── apps.py                   # App config
│   └── __init__.py
│
└── tests/                        # Full pytest suite
    ├── conftest.py               # Fixtures (api_client, authenticated_client, test_user, test_project)
    ├── test_auth.py              # 7 auth endpoint tests
    ├── test_projects.py          # 7 project CRUD tests
    ├── __init__.py
    └── pytest.ini                # Pytest configuration (coverage, markers)
```

## What's Included

### 1. Django Project Configuration (`ownfirebase/settings.py`)

- **Database**: PostgreSQL 16 with RLS (Row-Level Security) enabled
- **Cache**: Redis via django-redis
- **Channels**: Django Channels + Redis channel layer for WebSocket (Phase 2)
- **Celery**: Background tasks + Celery Beat for scheduling
- **JWT Auth**: djangorestframework-simplejwt with 1h access / 30d refresh
- **CORS**: Configurable allowed origins
- **OpenAPI Schema**: drf-spectacular for auto-generated Swagger/ReDoc docs
- **Logging**: Console + file rotation
- **Storage**: MinIO/S3 support (optional, via boto3)

### 2. Multi-Tenant Core Models (`core/models.py`)

- **Project**: Top-level tenant container (UUID, name, slug, owner, api_key, is_active)
- **ProjectMembership**: User → Project mapping with roles (owner, editor, viewer)
- **UserProfile**: Extended user profile (sign_in_provider, email_verified, phone, avatar, custom_claims)
- **MultiTenantModel**: Abstract base class for all multi-tenant data (project_id + user audit fields)

### 3. Multi-Tenant Middleware (`core/middleware.py`)

- Extracts JWT from Authorization header
- Sets context vars: `current_project_id`, `current_user_id`
- Attaches to request object for easy access in views
- Skips public paths (login, register, schema, admin)

### 4. Permission Classes (`core/permissions.py`)

- **IsProjectMember**: Check membership in a project
- **IsProjectOwner**: Only project owners
- **IsProjectEditorOrOwner**: Editors + owners for write access

### 5. REST API Endpoints (`api/`)

**Authentication** (fully implemented):
- `POST /api/v1/auth/login` — Email/password login → JWT tokens
- `POST /api/v1/auth/register` — Create new user with auto profile
- `POST /api/v1/auth/anonymous-signin` — Anonymous user with sign_in_provider='anonymous'
- `POST /api/v1/auth/logout` — Token blacklist

**Projects** (fully implemented):
- `GET /api/v1/projects/` — List user's projects (filtered by membership)
- `POST /api/v1/projects/` — Create project (auto-add creator as owner)
- `GET /api/v1/projects/{id}/` — Retrieve project
- `PUT /api/v1/projects/{id}/` — Update project
- `DELETE /api/v1/projects/{id}/` — Delete project
- `GET /api/v1/projects/{id}/members/` — List project members
- `POST /api/v1/projects/{id}/invite_member/` — Invite user (owner-only)

**Memberships** (fully implemented):
- `GET /api/v1/memberships/` — List memberships
- `POST /api/v1/memberships/{id}/remove_member/` — Remove member

**Data API** (stubs for Phase 2):
- `GET /api/v1/data/collections/` — List collections
- `POST /api/v1/data/query/` — Query documents
- `POST /api/v1/data/write-batch/` — Batch write

**Security Rules** (stubs for Phase 2):
- `GET /api/v1/rules/` — Get rules
- `POST /api/v1/rules/` — Update rules
- `POST /api/v1/rules/test/` — Test rules

### 6. Docker Compose Stack (`docker-compose.yml`)

**Services**:
- **Django** (Daphne): ASGI app on port 8000, mounts ./app
- **PostgreSQL 16**: Port 5432, initializes RLS + pgvector + context funcs
- **Redis**: Port 6379, persistent data
- **Celery**: Background worker
- **Celery Beat**: Scheduled task scheduler

**Health checks** on Postgres & Redis
**Automatic migrations** on Django startup

### 7. Test Suite (`tests/`)

**Fixtures** (conftest.py):
- `api_client` — Unauthenticated APIClient
- `test_user` — Sample user with profile
- `test_project` — Sample project owned by test_user
- `authenticated_client` — APIClient with JWT auth

**Tests** (14 total):
- `test_auth.py`: Register, login, password validation, anonymous signin, logout
- `test_projects.py`: List, create, update, delete, invite, members, permission checks

**Run**: `pytest` or `docker-compose exec django pytest`

### 8. Configuration & Scripts

- **`.env.example`**: Template with all variables (DB, Redis, JWT, CORS, email, S3)
- **`.gitignore`**: Python, Django, venv, migrations, .env, logs
- **`Dockerfile`**: Python 3.11-slim, installs deps, creates logs/ dir
- **`postgres-init.sql`**: Enables RLS, pgvector, creates app context functions
- **`celery.py`**: Celery config with Redis broker + Beat scheduler
- **`quickstart.sh`**: Interactive setup (Docker Compose or local)
- **`cli.py`**: Typer CLI scaffold (Phase 2+)

### 9. Documentation

- **`README.md`**: Full setup guide, API reference, architecture overview
- **`ownfirebase.md`**: Original spec (Target Architecture, Tech Stack)

## Key Design Decisions

### Multi-Tenant by Project

Every row in every table carries `project_id` for isolation. RLS policies at the database level enforce this—Django middleware sets `app.current_project` and `app.current_user` context vars, which RLS checks before returning data.

### JWT Tokens Include Project Context

When a user logs in to a project, the JWT includes:
```json
{
  "user_id": 123,
  "project_id": "uuid-...",
  ...
}
```

This is extracted by middleware and used for:
1. RLS enforcement (Postgres checks `app.current_project`)
2. Permission class validation (IsProjectMember)
3. Query filtering (auto-filter by project)

### BaseMultiTenantModel

All data models inherit from this abstract class:
```python
class MyData(MultiTenantModel):
    project = ForeignKey(Project)  # Inherited
    name = CharField()
```

This ensures every table has project isolation and audit fields.

### Stubs for Phase 2+

These are complete scaffolds but not yet implemented:
- **Document model** with JSONB data + collection queries
- **Security Rules DSL** compiler (Firebase rules → RLS policies)
- **Realtime listeners** (Channels + Postgres LISTEN/NOTIFY)
- **Change Data Capture** (Postgres triggers → WebSocket)
- **Cloud Functions** (Celery tasks)

## How to Use

### Option 1: Docker Compose (Recommended)

```bash
cd "own firebase"
chmod +x quickstart.sh
./quickstart.sh
# Choose option [1]
```

### Option 2: Local Setup

```bash
cd "own firebase"
chmod +x quickstart.sh
./quickstart.sh
# Choose option [2]
# (requires PostgreSQL 16 + Redis running)
```

### Option 3: Manual

```bash
cd "own firebase"
cp .env.example .env
# Edit .env as needed

# Start services
docker-compose up postgres redis -d

# Or use local Postgres/Redis

# Setup Django
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## API Examples

### Register

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!"
  }'
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "user@example.com",
    "email": "user@example.com"
  }
}
```

### Create Project

```bash
curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My App",
    "slug": "my-app",
    "description": "My first Own Firebase project"
  }'
```

### Invite Member

```bash
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/invite_member/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teammate@example.com",
    "role": "editor"
  }'
```

## What's Ready for Phase 2

The foundation is complete. Phase 2 will add:

1. **Document Model** — JSONB documents + collection queries + transactions
2. **Security Rules** — Firebase-style DSL compiler to RLS policies
3. **Realtime API** — WebSocket listeners via Channels + Postgres notifications
4. **Cloud Functions** — Celery tasks with HTTP triggers
5. **Admin Console** — React UI for projects, rules, monitoring
6. **Client SDKs** — Auto-generated JS/Dart/Swift from OpenAPI

All scaffolded stubs are in place (e.g., `DataViewSet`, `RulesViewSet`).

## File Checklist

✓ Django project config (settings, urls, wsgi, asgi)
✓ Core app (models, middleware, permissions, admin)
✓ API app (views, serializers, urls)
✓ Docker Compose (full stack)
✓ PostgreSQL init (RLS, pgvector)
✓ Celery config (tasks, beat)
✓ Tests (fixtures, auth, projects)
✓ Environment template (.env.example)
✓ Git ignore (.gitignore)
✓ Dockerfile
✓ CLI scaffold (cli.py)
✓ Quickstart script (quickstart.sh)
✓ README & documentation

## Production Readiness

- ✓ Multi-tenant architecture (isolated by project)
- ✓ JWT authentication with token refresh
- ✓ Role-based access control (owner, editor, viewer)
- ✓ CORS configured for client apps
- ✓ Gunicorn/Daphne ready for deployment
- ✓ Logging to file + console
- ✓ Database connection pooling (CONN_MAX_AGE)
- ✓ WhiteNoise for static file serving
- ✓ Pytest with fixtures & coverage reporting
- ⚠ Security rules validation (Phase 2+)
- ⚠ Rate limiting (Phase 2+)
- ⚠ Request validation (Phase 2+)

---

**Next**: Follow the README to start the services and test the API!
