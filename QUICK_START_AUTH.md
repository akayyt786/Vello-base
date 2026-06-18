# Quick Start: Auth Service

## Running the Server

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Update DATABASE_* and REDIS_URL if needed

# 3. Run migrations
python manage.py migrate

# 4. Create admin user
python manage.py createsuperuser

# 5. Start development server
python manage.py runserver
```

## API Endpoints

### Register a new user
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@test.com",
    "password":"SecurePass123!",
    "password_confirm":"SecurePass123!"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@test.com",
    "password":"SecurePass123!"
  }'

# Response:
# {
#   "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
#   "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
#   "user": { ... }
# }
```

### Get current user profile
```bash
curl -X GET http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Refresh access token
```bash
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<REFRESH_TOKEN>"}'
```

### Logout
```bash
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<REFRESH_TOKEN>"}'
```

### Anonymous sign-in
```bash
curl -X POST http://localhost:8000/api/auth/anonymous-signin/
```

### Set custom claims (admin only)
```bash
curl -X POST http://localhost:8000/api/auth/set-custom-claims/ \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2,
    "claims": {
      "admin": false,
      "role": "editor",
      "tier": "premium"
    }
  }'
```

## Running Tests

```bash
# All tests
pytest tests/test_auth.py -v

# Specific test
pytest tests/test_auth.py::TestAuthViewSet::test_register_success -v

# With coverage
pytest tests/test_auth.py --cov=api --cov=core
```

## File Locations

- **Models**: `/core/models.py`
- **Views**: `/api/views.py` (AuthViewSet)
- **Serializers**: `/api/serializers.py`
- **Authentication Backend**: `/core/backends.py`
- **URL Routes**: `/api/urls.py`
- **Settings**: `/ownfirebase/settings.py` (SIMPLE_JWT config)
- **Tests**: `/tests/test_auth.py`
- **Documentation**: `/AUTH_SERVICE_IMPLEMENTATION.md`

## Token Format

Access token contains:
```json
{
  "user_id": 1,
  "email": "user@example.com",
  "email_verified": false,
  "sign_in_provider": "password",
  "custom_claims": {
    "role": "editor",
    "admin": false
  },
  "firebase": {
    "sign_in_provider": "password",
    "identities": {}
  }
}
```

## Common Issues

### 401 Unauthorized
- Token expired? Use `/refresh/` to get new access token
- Token blacklisted after logout? Need to login again
- Missing Authorization header? Add: `Authorization: Bearer <TOKEN>`

### 400 Bad Request
- Email already registered? Choose different email
- Password too weak? Use min 8 chars, avoid all numbers
- Passwords don't match? Ensure password and password_confirm are identical

### 403 Forbidden
- Not an admin? Only admins can set custom claims
- Not a project member? Only project members can access data

## Next Steps

1. Read `/AUTH_SERVICE_IMPLEMENTATION.md` for comprehensive guide
2. Check `/tests/test_auth.py` for usage examples
3. Review `/core/models.py` and `/api/serializers.py` for data structures
4. Explore `/core/backends.py` to understand JWT validation
