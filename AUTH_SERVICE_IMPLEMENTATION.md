# Auth Service Implementation — Phase 1 MVP

Complete JWT-based authentication service for Own Firebase, mirroring Firebase Authentication API.

## Features

- **Email/Password Registration & Login** — Create accounts and authenticate users
- **JWT Tokens** — Access tokens (15 min) and refresh tokens (7 days)
- **Custom Claims** — Store user roles, permissions, and metadata in JWT
- **Token Blacklist** — Revoke tokens on logout
- **Anonymous Sign-in** — Create temporary sessions before account creation
- **User Profiles** — Email verification status, sign-in provider, custom claims
- **Admin API** — Set custom claims for users (admin only)

## Architecture

```
Authentication Flow:
┌─────────────┐
│ Client App  │
└────┬────────┘
     │ POST /api/auth/register + password
     │ POST /api/auth/login + credentials
     ├──────────────────────────────────────┐
     │                                      │
  ┌──▼─────────────────────────────────────▼──┐
  │ DRF ViewSet (api/views.py)                │
  │  - RegisterView                           │
  │  - LoginView                              │
  │  - RefreshView                            │
  │  - MeView (profile)                       │
  │  - LogoutView (blacklist)                 │
  └──┬─────────────────────────────────────┬──┘
     │                                     │
     ├─────────────────────────────────────┤
     │                                     │
  ┌──▼────────────────┐         ┌─────────▼──────────┐
  │ CustomJWTAuth     │         │ User Model         │
  │ Backend           │         │ UserProfile        │
  │ (core/backends)   │         │ RefreshTokenBL     │
  └──┬────────────────┘         └─────────┬──────────┘
     │ Verify signature                   │ Store custom claims
     │ Check blacklist                    │ Track sign-in provider
     │ Decode claims                      │ Manage tokens
     │                                    │
  ┌──▴────────────────────────────────────▴──┐
  │ PostgreSQL Database                       │
  │  - django_auth_user                       │
  │  - core_user_profile (custom_claims)      │
  │  - core_refresh_token_blacklist           │
  └──────────────────────────────────────────┘
```

## Database Models

### 1. User (Django's built-in)
Standard Django User model extended by UserProfile.

### 2. UserProfile (core/models.py)
```python
class UserProfile(models.Model):
    user = OneToOneField(User, on_delete=CASCADE)
    sign_in_provider = CharField()  # 'password', 'google', 'github', 'anonymous'
    email_verified = BooleanField()
    email_verified_at = DateTimeField()
    phone_number = CharField()
    phone_verified = BooleanField()
    avatar_url = URLField()
    bio = TextField()
    custom_claims = JSONField()  # Store custom claims (max 1000 bytes)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### 3. RefreshTokenBlacklist (core/models.py)
```python
class RefreshTokenBlacklist(models.Model):
    jti = TextField(unique=True)  # JWT ID (from token payload)
    user = ForeignKey(User, on_delete=CASCADE)
    created_at = DateTimeField(auto_now_add=True)
    expires_at = DateTimeField()  # When to prune this entry
```

## API Endpoints

### POST `/api/auth/register/`
Register a new user with email and password.

**Request:**
```json
{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
}
```

**Response (201 Created):**
```json
{
    "access": "<JWT access token>",
    "refresh": "<JWT refresh token>",
    "user": {
        "id": 1,
        "username": "user@example.com",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe"
    }
}
```

**Validations:**
- Email must be unique
- Password must match password_confirm
- Password must pass Django's validators (min length 8, not numeric-only, etc.)

---

### POST `/api/auth/login/`
Authenticate with email and password, receive JWT tokens.

**Request:**
```json
{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "project_id": "uuid-optional"
}
```

**Response (200 OK):**
```json
{
    "access": "<JWT access token>",
    "refresh": "<JWT refresh token>",
    "user": { ... }
}
```

**Validations:**
- Email and password must match a user
- Returns 401 Unauthorized if credentials are invalid

---

### POST `/api/auth/refresh/`
Refresh an expired access token.

**Request:**
```json
{
    "refresh": "<JWT refresh token>"
}
```

**Response (200 OK):**
```json
{
    "access": "<new JWT access token>",
    "refresh": "<new JWT refresh token (if rotated)>"
}
```

**Behavior:**
- ROTATE_REFRESH_TOKENS = True: Returns a new refresh token on each call
- BLACKLIST_AFTER_ROTATION = True: Blacklists the old refresh token
- Returns 401 if refresh token is blacklisted or expired

---

### GET `/api/auth/me/`
Get the current authenticated user's profile and custom claims.

**Request:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
    "user": {
        "id": 1,
        "username": "user@example.com",
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe"
    },
    "profile": {
        "user": { ... },
        "sign_in_provider": "password",
        "email_verified": false,
        "phone_number": "",
        "avatar_url": "",
        "bio": "",
        "custom_claims": {
            "admin": false,
            "role": "editor",
            "tier": "premium"
        }
    },
    "email_verified": false,
    "sign_in_provider": "password",
    "custom_claims": { ... }
}
```

**Auth Required:** Yes (Bearer token)

---

### POST `/api/auth/set-custom-claims/`
Set custom claims for a user (admin only, like Firebase Admin SDK).

**Request:**
```json
{
    "user_id": 123,
    "claims": {
        "admin": false,
        "role": "editor",
        "tier": "premium"
    }
}
```

**Response (200 OK):**
```json
{
    "user_id": 123,
    "custom_claims": {
        "admin": false,
        "role": "editor",
        "tier": "premium"
    }
}
```

**Validations:**
- Claims must not exceed 1000 bytes (JSON encoded)
- Only admin/staff users can set claims
- Returns 403 Forbidden if not admin
- Returns 404 Not Found if user doesn't exist

**Important:** Custom claims appear in the JWT on the next login. The claims are automatically injected into the access token by `CustomTokenObtainPairSerializer.get_token()`.

---

### POST `/api/auth/logout/`
Logout by blacklisting the refresh token.

**Request:**
```json
{
    "refresh": "<JWT refresh token>"
}
```

**Response (204 No Content)**

**Behavior:**
- Extracts the `jti` (JWT ID) from the refresh token
- Creates a RefreshTokenBlacklist entry
- The `CustomJWTAuthentication` backend checks the blacklist on every request
- Prevents token reuse after logout

---

### POST `/api/auth/anonymous-signin/`
Create an anonymous user session (useful for guest users accumulating data).

**Request:**
```
POST /api/auth/anonymous-signin/
```

**Response (201 Created):**
```json
{
    "access": "<JWT access token>",
    "refresh": "<JWT refresh token>",
    "user": {
        "id": 2,
        "username": "anon_abc123def456",
        "email": "anon_abc123def456@anonymous.local",
        "first_name": "",
        "last_name": ""
    }
}
```

**Behavior:**
- Creates a user with a unique anonymous username
- Sets `sign_in_provider` to 'anonymous' in profile
- No authentication required
- Can be upgraded to a full account later (Phase 2 feature)

---

## JWT Token Structure

### Access Token (15 min TTL)
```json
{
    "user_id": 1,
    "email": "user@example.com",
    "email_verified": false,
    "sign_in_provider": "password",
    "role": "editor",           // Custom claim
    "admin": false,             // Custom claim
    "firebase": {
        "sign_in_provider": "password",
        "identities": {}
    },
    "iat": 1716995000,
    "exp": 1716995900,
    "jti": "abc123..."
}
```

### Refresh Token (7 day TTL)
```json
{
    "user_id": 1,
    "iat": 1716995000,
    "exp": 1717600000,
    "jti": "def456..."
}
```

**Signing:** HMAC-SHA256 with settings.SECRET_KEY

---

## Custom Claims

Custom claims are stored in `UserProfile.custom_claims` as a JSON field. They:

1. **Are automatically injected into the JWT** when a user logs in or when a token is refreshed
2. **Appear immediately** (no propagation delay like Firebase's up-to-1-hour delay)
3. **Are set via `/api/auth/set-custom-claims/`** by admins
4. **Are limited to 1000 bytes** (JSON encoded) like Firebase
5. **Can include any JSON-serializable data:** booleans, strings, numbers, objects, arrays

### Example Custom Claims
```python
{
    "admin": true,
    "role": "editor",
    "tier": "premium",
    "permissions": ["read", "write", "delete"],
    "workspace_ids": ["uuid1", "uuid2"],
    "quota_gb": 100,
    "features_enabled": {
        "collaboration": true,
        "advanced_search": false
    }
}
```

---

## Authentication Backend (core/backends.py)

The `CustomJWTAuthentication` backend:

1. **Verifies JWT signature** using settings.SIMPLE_JWT['SIGNING_KEY']
2. **Decodes the token payload** and extracts claims
3. **Checks token blacklist** — raises 401 if token is revoked
4. **Attaches claims to request.token_claims** for views to access
5. **Returns (user, token)** tuple to DRF

### Usage in Views
```python
@permission_classes([IsAuthenticated])
def my_view(request):
    # request.user is the authenticated User
    # request.token_claims contains the decoded JWT payload
    claims = request.token_claims
    role = claims.get('role')
    admin = claims.get('admin')
```

---

## Configuration (settings.py)

### INSTALLED_APPS
```python
INSTALLED_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    # ... others
]
```

### REST_FRAMEWORK
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'core.backends.CustomJWTAuthentication',  # Custom backend with blacklist
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}
```

### SIMPLE_JWT
```python
SIMPLE_JWT = {
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('JWT_SIGNING_KEY', SECRET_KEY),
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # 15 min
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # 7 days
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'JTI_CLAIM': 'jti',
    'TOKEN_OBTAIN_SERIALIZER': 'api.serializers.CustomTokenObtainPairSerializer',
    'TOKEN_REFRESH_SERIALIZER': 'api.serializers.RefreshTokenSerializer',
}
```

---

## Testing

Run tests with pytest:

```bash
# All auth tests
pytest tests/test_auth.py -v

# Specific test
pytest tests/test_auth.py::TestAuthViewSet::test_register_success -v

# With coverage
pytest tests/test_auth.py --cov=api --cov=core
```

### Test Coverage
- ✓ User registration (success, validation, duplicate email)
- ✓ User login (success, invalid credentials, nonexistent user)
- ✓ Token refresh (new access token)
- ✓ Get current user profile (/api/auth/me/)
- ✓ Set custom claims (admin only, size validation)
- ✓ Custom claims in JWT
- ✓ Logout (token blacklist)
- ✓ Anonymous sign-in
- ✓ Password validation (weak passwords rejected)

---

## Usage Examples

### 1. Register and Login Flow
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email":"user@example.com",
    "password":"SecurePass123!",
    "password_confirm":"SecurePass123!"
  }'

# Response
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": { "id": 1, "email": "user@example.com", ... }
}

# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email":"user@example.com",
    "password":"SecurePass123!"
  }'
```

### 2. Use Access Token to Call Protected Endpoint
```bash
curl -X GET http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# Response
{
  "user": { ... },
  "profile": { ... },
  "custom_claims": {}
}
```

### 3. Refresh Expired Access Token
```bash
curl -X POST http://localhost:8000/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'

# Response
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 4. Set Custom Claims (Admin)
```bash
curl -X POST http://localhost:8000/api/auth/set-custom-claims/ \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2,
    "claims": {
      "admin": false,
      "role": "editor",
      "tier": "premium"
    }
  }'

# Response
{
  "user_id": 2,
  "custom_claims": {
    "admin": false,
    "role": "editor",
    "tier": "premium"
  }
}
```

### 5. Logout
```bash
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}'

# Response: 204 No Content
```

---

## Comparison with Firebase Authentication

| Feature | Firebase | Own Firebase (Phase 1) |
|---------|----------|----------------------|
| Email/Password Auth | ✓ REST API | ✓ /api/auth/register, /login |
| JWT Tokens | ID Token (1h) + Refresh | Access (15m) + Refresh (7d) |
| Token Signing | RS256 (public key rotation) | HS256 (single shared key) |
| Custom Claims | Via Admin SDK only, 1-hour delay | Via /set-custom-claims, immediate |
| Token Revocation | No native blacklist (session-based) | ✓ Token blacklist on logout |
| Anonymous Auth | ✓ Builtin | ✓ /api/auth/anonymous-signin |
| Verifying Tokens | `admin.auth().verifyIdToken()` | Built-in JWTAuthentication |
| Refresh Tokens | Opaque, long-lived | JWT with standard claims |

---

## Security Considerations

### 1. Secret Key
- Store `DJANGO_SECRET_KEY` in environment variables
- Never commit `.env` files to git
- Rotate keys periodically in production

### 2. Token TTL
- Access tokens (15 min): Short-lived to limit exposure
- Refresh tokens (7 days): Longer-lived for convenience
- Adjust based on security requirements

### 3. HTTPS Enforcement
- Always use HTTPS in production
- Tokens should only be sent over TLS
- Set `SECURE_SSL_REDIRECT = True` in production settings

### 4. Token Storage (Client-side)
- Store access tokens in memory or sessionStorage (not localStorage)
- Store refresh tokens in httpOnly cookies when possible
- Never expose tokens in URLs or logs

### 5. Custom Claims Size
- Limited to 1000 bytes (same as Firebase)
- Use efficient JSON structures
- Avoid storing sensitive data in claims (readable in token)

### 6. Password Security
- Passwords hashed with PBKDF2 (Django default)
- Consider upgrading to Scrypt via PASSWORD_HASHERS
- Enforce strong password policies

### 7. Rate Limiting
- Add rate limiting to /register and /login endpoints
- Prevent brute-force attacks
- Consider using `django-ratelimit` or similar

---

## Migration Guide

### From Unauthenticated API
1. Update client to call `/api/auth/register/`
2. Store `access` and `refresh` tokens
3. Include `Authorization: Bearer {access}` on subsequent requests
4. Handle 401 responses by refreshing token with `/api/auth/refresh/`

### From Firebase
1. Export Firebase users (see Firebase documentation)
2. Create Django users with matching emails
3. Update client to call `/api/auth/login/` instead of Firebase SDK
4. Migrate custom claims via `/api/auth/set-custom-claims/`

---

## Future Enhancements (Phase 2+)

- [ ] Multi-factor authentication (MFA)
- [ ] Email verification workflows
- [ ] Password reset flows
- [ ] OAuth2 / Social login (Google, GitHub)
- [ ] Account linking (upgrade anonymous → email)
- [ ] Session management (list active sessions, revoke by device)
- [ ] Security events (login attempts, claim changes)
- [ ] Rate limiting on auth endpoints
- [ ] RS256 signing with key rotation
- [ ] Account recovery codes

---

## File Structure

```
ownfirebase/
├── core/
│   ├── models.py              # User, UserProfile, RefreshTokenBlacklist
│   ├── backends.py            # CustomJWTAuthentication
│   ├── permissions.py         # IsProjectMember, etc.
│   ├── middleware.py          # MultiTenantMiddleware
│   └── migrations/
│       └── 0001_initial.py    # Initial migration
├── api/
│   ├── views.py               # AuthViewSet (register, login, refresh, me, etc.)
│   ├── serializers.py         # Auth serializers + CustomTokenObtainPairSerializer
│   ├── urls.py                # /api/auth/* routes
│   └── migrations/
└── ownfirebase/
    ├── settings.py            # JWT config, SIMPLE_JWT, REST_FRAMEWORK
    └── urls.py                # Include api.urls
```

---

## Quick Start

1. **Install dependencies** (already in requirements.txt)
2. **Run migrations:** `python manage.py migrate`
3. **Create superuser:** `python manage.py createsuperuser`
4. **Start server:** `python manage.py runserver`
5. **Test register:** `curl -X POST http://localhost:8000/api/auth/register/ ...`

---

## References

- Django REST Framework: https://www.django-rest-framework.org/
- djangorestframework-simplejwt: https://django-rest-framework-simplejwt.readthedocs.io/
- Firebase Authentication docs: https://firebase.google.com/docs/auth
- JWT.io: https://jwt.io/
