# Own Firebase - Phase 1 MVP

A Firestore alternative built on Django, PostgreSQL, and Redis. Multi-tenant by project with security rules, realtime updates, and developer-friendly APIs.

## Project Structure

```
ownfirebase/
├── manage.py                 # Django management CLI
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker image
├── docker-compose.yml        # Local dev stack (Postgres, Redis, Django, Celery)
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
├── postgres-init.sql         # PostgreSQL initialization (RLS, pgvector)
├── celery.py                 # Celery configuration
├── ownfirebase/              # Django project package
│   ├── __init__.py
│   ├── settings.py           # Django settings (DB, Redis, JWT, CORS)
│   ├── urls.py               # Base URL routes
│   ├── wsgi.py               # WSGI application
│   └── asgi.py               # ASGI application (Channels/WebSocket)
├── core/                     # Core app: multi-tenant models & middleware
│   ├── models.py             # Project, ProjectMembership, UserProfile, MultiTenantModel
│   ├── middleware.py         # JWT extraction + multi-tenant context
│   ├── permissions.py        # IsProjectMember, IsProjectOwner, etc.
│   ├── admin.py              # Django admin configuration
│   └── apps.py
├── api/                      # REST API app
│   ├── views.py              # AuthViewSet, ProjectViewSet, DataViewSet, RulesViewSet (stubs)
│   ├── serializers.py        # DRF serializers
│   ├── urls.py               # API routing
│   └── apps.py
├── tests/                    # Test suite
│   ├── conftest.py           # Pytest fixtures
│   ├── test_auth.py          # Auth endpoint tests
│   ├── test_projects.py      # Project CRUD tests
│   └── pytest.ini            # Pytest configuration
└── README.md                 # This file
```

## Quick Start (Docker Compose — Full Local Emulator)

### Prerequisites
- Docker & Docker Compose installed
- Python 3.11+ (for local development without Docker)

### 1. Clone & Setup

```bash
cd "own firebase"
cp .env.example .env  # or use the already-provided .env
```

### 2. Start the Full Stack

```bash
docker-compose up --build
```

**Services start at:**
- **Django API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/api/docs/
- **API Docs (ReDoc)**: http://localhost:8000/api/redoc/
- **Django Admin**: http://localhost:8000/admin/
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

Migrations run automatically on `django` service startup.

### 3. Create Superuser (Admin)

```bash
docker-compose exec django python manage.py createsuperuser
```

Then visit http://localhost:8000/admin/ and login.

### 4. Test

```bash
# Run pytest in the django container
docker-compose exec django pytest

# Or run the dedicated tests service (CI mode)
docker-compose --profile tests up tests
```

### 5. Stop Services

```bash
docker-compose down          # Stop and remove containers
docker-compose down -v       # Also remove volumes (reset DB)
```

## API Quick Examples

### Register a New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'
```

### Create a Project

```bash
curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "My App",
    "description": "A test project"
  }'
```

### List Projects

```bash
curl -X GET http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Local Development (Without Docker)

### 1. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Database & Redis

```bash
# Option A: Use system PostgreSQL & Redis
export DATABASE_HOST=localhost DATABASE_USER=postgres DATABASE_PASSWORD=postgres
export REDIS_URL=redis://localhost:6379/0

# Option B: Use docker-compose for services only
docker-compose up postgres redis -d
```

### 4. Run Migrations & Start Server

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit http://localhost:8000

## API Endpoints (Phase 1 MVP)

### Authentication
- `POST /api/v1/auth/login` — Email/password login
- `POST /api/v1/auth/register` — Register new user
- `POST /api/v1/auth/anonymous-signin` — Anonymous login
- `POST /api/v1/auth/logout` — Logout (token blacklist)

### Projects
- `GET /api/v1/projects/` — List user's projects
- `POST /api/v1/projects/` — Create project
- `GET /api/v1/projects/{id}/` — Get project
- `PUT /api/v1/projects/{id}/` — Update project
- `DELETE /api/v1/projects/{id}/` — Delete project
- `GET /api/v1/projects/{id}/members/` — List project members
- `POST /api/v1/projects/{id}/invite_member/` — Invite member

### Memberships
- `GET /api/v1/memberships/` — List memberships
- `POST /api/v1/memberships/{id}/remove_member/` — Remove member

### Data API (Stubs - Phase 2+)
- `GET /api/v1/data/collections/` — List collections
- `POST /api/v1/data/query/` — Query documents
- `POST /api/v1/data/write-batch/` — Batch write

### Security Rules (Stubs - Phase 2+)
- `GET /api/v1/rules/` — Get rules
- `POST /api/v1/rules/` — Update rules
- `POST /api/v1/rules/test/` — Test rules

## Key Architecture Decisions

### Multi-Tenant by Project
- Every table has a `project_id` foreign key.
- Row-Level Security (RLS) enforced at the database level via Postgres policies.
- Middleware extracts JWT and sets `app.current_project`, enabling RLS enforcement.

### Base MultiTenantModel
All data models inherit from `MultiTenantModel`:
```python
class MyDocument(MultiTenantModel):
    project = ForeignKey(Project)  # Inherited
    name = CharField()
```

### JWT Authentication
- `djangorestframework-simplejwt` for token generation/refresh.
- Custom `CustomTokenSerializer` adds project-level claims.
- Tokens live 1 hour (access) / 30 days (refresh).

### Celery & Celery Beat
- Background tasks via Celery + Redis broker.
- Scheduled jobs via Celery Beat (e.g., cleanup, notifications).
- Configuration: `celery.py` + Django settings.

### PostgreSQL RLS
- Postgres context variables: `app.current_project`, `app.current_user`.
- Helper functions: `app_funcs.current_project()`, `app_funcs.current_user()`.
- RLS policies evaluate `current_project()` to isolate data per tenant.
- Full example in Phase 2 (Document model + policies).

### WebSocket & Realtime (Phase 2+)
- Django Channels + Redis channel layer for WebSocket subscriptions.
- `ASGI` app in `ownfirebase/asgi.py`.
- Postgres `LISTEN/NOTIFY` → Channels consumer → WebSocket broadcast.

## Testing

Run pytest:
```bash
pytest                # All tests
pytest tests/test_auth.py  # Auth tests only
pytest -v             # Verbose
pytest --cov          # Coverage report
```

Fixtures (in `tests/conftest.py`):
- `api_client` — Unauthenticated API client
- `authenticated_client` — Authenticated client (test_user)
- `test_user` — User with profile
- `test_project` — Project owned by test_user

## Environment Variables

See `.env.example`. Key ones:
- `DEBUG` — Enable debug mode (development only)
- `DJANGO_SECRET_KEY` — Django secret
- `DATABASE_*` — PostgreSQL connection
- `REDIS_URL` — Redis connection
- `CORS_ALLOWED_ORIGINS` — Allowed client origins
- `JWT_SIGNING_KEY` — JWT signing key

## Deployment (Phase 2+)

### Docker / Kubernetes
```bash
docker build -t ownfirebase:latest .
docker run -p 8000:8000 -e DATABASE_HOST=postgres ... ownfirebase:latest
```

### Gunicorn (Production)
```bash
gunicorn ownfirebase.wsgi -b 0.0.0.0:8000 -w 4
```

### Daphne (ASGI + WebSocket)
```bash
daphne -b 0.0.0.0 -p 8000 ownfirebase.asgi:application
```

## Next Steps (Phase 2 MVP)

1. **Document Model** — JSONB data + GIN indexes + collection queries
2. **Security Rules DSL** — Firebase-style rules compiler to RLS policies
3. **Realtime Listeners** — Channels consumers + Postgres LISTEN/NOTIFY
4. **Change Data Capture** — Postgres triggers → WebSocket broadcasts
5. **Cloud Functions** — Celery tasks + HTTP triggers
6. **Admin Console** — React UI for project/rules management
7. **Client SDKs** — Auto-generated JS/Dart/Swift from OpenAPI schema

## License

MIT
