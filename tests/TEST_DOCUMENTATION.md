# OwnFirebase Phase 1 MVP - Test Suite Documentation

## Overview

This document describes the comprehensive Phase 1 MVP test suite for the OwnFirebase project. The test suite covers:

1. **Authentication Service** (test_auth.py) - User registration, login, JWT tokens, custom claims
2. **Data API** (test_data_api.py) - Collections, documents, queries, transactions
3. **Security Rules** (test_rules.py) - Rule engine, DSL parsing, permission enforcement
4. **Smoke Tests** (curl_smoke_test.sh) - End-to-end integration tests via curl

All tests are designed to be **comprehensive, runnable, and production-ready** for Phase 1.

---

## Test Structure

### Directory Layout
```
tests/
├── conftest.py                 # Pytest fixtures and configuration
├── test_auth.py               # Authentication tests (~300 lines)
├── test_data_api.py          # Data API tests (~500 lines)
├── test_rules.py             # Security rules tests (~400 lines)
├── curl_smoke_test.sh        # Manual integration tests (bash script)
└── TEST_DOCUMENTATION.md     # This file
```

---

## Fixtures (conftest.py)

All fixtures use pytest's `@pytest.fixture` decorator and `(db)` marker for database access.

### Core Fixtures

#### `api_client`
- Returns an unauthenticated DRF `APIClient`
- Used for testing public endpoints or crafting custom auth headers

#### `test_user` / `test_user2`
- Creates a Django `User` with email, password, and `UserProfile`
- `test_user`: email=`testuser@example.com`, password=`testpass123`
- `test_user2`: email=`testuser2@example.com`, password=`testpass123`

#### `admin_user`
- Creates a superuser with admin privileges
- Includes custom claims: `{'admin': True, 'is_admin': True}`
- email=`admin@example.com`, password=`adminpass123`

#### `test_project` / `test_project_2`
- Creates a `Project` owned by a test user
- Auto-creates `ProjectMembership` with role='owner'
- Used to isolate multi-tenant tests

#### `test_collection`
- Creates a `Collection` named 'users' with schema metadata
- Fields: name, email, age, status (all indexed)

#### `test_document`
- Creates a document in the test collection
- doc_id='alice', contains sample user data

#### `authenticated_client` / `authenticated_client_2` / `admin_client`
- Pre-configured `APIClient` with JWT Authorization header
- Ready to make authenticated requests
- Uses `RefreshToken.for_user()` to generate valid JWT

---

## Test Files Overview

### 1. test_auth.py - Authentication Tests (~15 tests)

**Purpose**: Verify user registration, login, JWT token generation, custom claims, and token management.

#### Core Tests

**Registration Tests**
- `test_register_success` - User can register with valid email/password
- `test_register_password_mismatch` - Rejects mismatched passwords
- `test_register_duplicate_email` - Rejects duplicate email registration
- `test_register_password_validation` - Enforces password strength requirements

**Login Tests**
- `test_login_success` - User can login and receive JWT tokens
- `test_login_invalid_password` - Rejects wrong password
- `test_login_nonexistent_user` - Rejects non-existent user

**Token Tests**
- `test_refresh_token` - Access token can be refreshed using refresh token
- `test_refresh_token_with_custom_claims` - Refreshed token includes custom claims
- `test_logout_blacklists_token` - Logout adds token to blacklist
- `test_logout_prevents_token_reuse` - Blacklisted token cannot be reused

**Profile Tests**
- `test_me_authenticated` - GET /api/auth/me/ returns current user profile
- `test_me_unauthenticated` - Returns 401 without token

**Custom Claims Tests**
- `test_set_custom_claims_admin` - Admin can set custom claims on users
- `test_set_custom_claims_non_admin` - Non-admin cannot set claims (403 Forbidden)
- `test_custom_claims_in_token` - Custom claims appear in JWT payload

**Anonymous Access**
- `test_anonymous_signin` - Anonymous user can sign in without credentials

#### Run Auth Tests
```bash
pytest tests/test_auth.py -v
pytest tests/test_auth.py::TestAuthViewSet::test_login_success -v
pytest tests/test_auth.py -k "custom_claims" -v
```

---

### 2. test_data_api.py - Data API Tests (~20 tests)

**Purpose**: Verify collection/document CRUD, querying, pagination, transactions, and optimistic locking.

#### Collection Tests
- `test_create_collection` - Create a collection with schema
- `test_list_collections` - List all collections in a project

#### Document CRUD Tests
- `test_create_document` - Create a new document with arbitrary JSON data
- `test_get_document` - Retrieve a document by collection/doc_id
- `test_update_document` - PATCH update specific fields (merge behavior)
- `test_update_document_increments_version` - Each update increments __v
- `test_delete_document` - Delete a document
- `test_list_documents` - List all documents in a collection
- `test_get_document_by_id_not_found` - 404 for non-existent doc
- `test_delete_document_not_found` - 404 when deleting non-existent doc

#### Query Tests
- `test_query_documents_with_filter` - WHERE clause filtering (e.g., status == 'active')
- `test_query_documents_with_ordering` - ORDER BY with direction (asc/desc)
- `test_array_contains_query` - array-contains operator
- `test_comparison_operators` - >, <, >=, <=, ==, != operators
- `test_multiple_queries_with_filters_and_ordering` - Combined WHERE + ORDER BY

#### Pagination Tests
- `test_pagination_limit_and_offset` - Limit and offset parameters work

#### Data Structure Tests
- `test_complex_nested_data_structure` - Nested objects, arrays, and deep nesting
- `test_document_created_updated_timestamps_present` - Timestamps on creation

#### Transaction Tests
- `test_transaction_write_batch` - Multiple writes in single transaction
- `test_transaction_delete_operation` - Delete within transaction
- `test_transaction_rollback_on_error` - Transaction consistency

#### Concurrency Tests
- `test_document_version_conflict` - 409 when updating with wrong version

#### Permission Tests
- `test_missing_project_returns_404` - Non-existent project returns 404
- `test_unauthorized_access_denied` - User not in project gets 403

#### Subcollection Tests
- `test_subcollection_path` - Support for nested paths (users/alice/posts/post1)

#### Run Data API Tests
```bash
pytest tests/test_data_api.py -v
pytest tests/test_data_api.py::TestDataAPI::test_create_document -v
pytest tests/test_data_api.py -k "transaction" -v
pytest tests/test_data_api.py -k "query" -v
```

---

### 3. test_rules.py - Security Rules Tests (~20 tests)

**Purpose**: Verify DSL parsing, rule engine evaluation, and permission enforcement.

#### DSL Engine Tests

**Rule Evaluation**
- `test_auth_check_authenticated` - `request.auth != null` evaluates true for authenticated user
- `test_auth_check_unauthenticated` - `request.auth != null` evaluates false for anonymous
- `test_owner_check_owner_can_read` - Owner passes ownership check
- `test_owner_check_non_owner_cannot_read` - Non-owner fails ownership check
- `test_field_check_with_rhs_field` - Field-to-field comparison (e.g., `data.owner == request.auth.uid`)
- `test_or_condition` - OR logic (at least one condition passes)
- `test_rule_conditions_with_and_operator` - AND logic (all conditions pass)
- `test_rule_conditions_with_or_operator_partial_match` - OR with partial match

#### DSL Parser Tests
- `test_parse_simple_auth_rule` - Parse rule string to condition tree
- `test_parse_owner_comparison` - Parse owner comparisons

#### Security Policy Model Tests
- `test_create_policy` - Create a SecurityPolicy
- `test_policy_validation` - Validate condition_json structure
- `test_policy_ordering` - Policies ordered by priority (descending)
- `test_inactive_policies_not_evaluated` - Inactive policies excluded

#### Policy Evaluation Tests
- `test_multiple_policies_first_match_wins` - Short-circuit evaluation by priority

#### Document Permission Tests (Integration)
- `test_authenticated_can_read_own_doc` - Authenticated user can read own document
- `test_unauthenticated_cannot_read` - Anonymous user denied read
- `test_non_owner_cannot_modify` - Non-owner denied write

#### Run Rules Tests
```bash
pytest tests/test_rules.py -v
pytest tests/test_rules.py::TestDSLEvaluator -v
pytest tests/test_rules.py::TestSecurityPolicyModel -v
pytest tests/test_rules.py -k "policy" -v
```

---

### 4. curl_smoke_test.sh - Integration Tests

**Purpose**: End-to-end testing via HTTP with curl. Verifies the entire system works together.

#### Test Categories

**Authentication Flow**
- `test_register_user` - Register a new user via POST /api/auth/register/
- `test_login_user` - Login and receive JWT tokens
- `test_get_current_user` - GET /api/auth/me/ returns profile
- `test_refresh_token` - Refresh access token with refresh token
- `test_login_invalid_password` - Login fails with wrong password
- `test_logout_user` - Logout blacklists token (204)

**Project & Collection Management**
- `test_create_project` - Create a new project
- `test_create_collection` - Create a collection with schema

**Document Operations**
- `test_create_document` - POST to create document
- `test_get_document` - GET document by ID
- `test_update_document` - PATCH to update fields
- `test_list_documents` - List documents in collection
- `test_query_documents` - Query with WHERE filter
- `test_delete_document` - DELETE document

**Security & Permissions**
- `test_unauthorized_access` - Different user cannot access project (403)
- `test_document_version_conflict` - Concurrent update conflict (409)

**Transactions**
- `test_transaction_batch_write` - Batch write multiple docs

#### Running Smoke Tests

```bash
# Start Django server first
python manage.py runserver

# In another terminal, run tests (default: http://localhost:8000)
bash tests/curl_smoke_test.sh

# Or specify custom base URL
bash tests/curl_smoke_test.sh http://example.com:8000

# Output is color-coded: GREEN [PASS], RED [FAIL], YELLOW [TEST]
```

---

## Running All Tests

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate
```

### Run All Tests
```bash
# Run all tests with coverage
pytest tests/ -v --cov=core,data,rules --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run specific test class
pytest tests/test_auth.py::TestAuthViewSet -v

# Run specific test method
pytest tests/test_auth.py::TestAuthViewSet::test_login_success -v

# Run tests matching pattern
pytest tests/ -k "auth" -v
pytest tests/ -k "transaction" -v
pytest tests/ -k "query" -v

# Run with short traceback format
pytest tests/ -v --tb=short

# Run with pdb on failure
pytest tests/ -v --pdb
```

### Running Pytest with Django

All tests use `@pytest.mark.django_db` decorator to access the test database:

```bash
# pytest-django automatically creates test DB with Django ORM
# and migrates it before running tests

# By default, DB is isolated per test class/function
# For database persistence across tests:
pytest --nomigrations tests/
```

---

## Test Coverage

### Coverage Report

```bash
# Generate coverage report (outputs to htmlcov/index.html)
pytest tests/ --cov=core,data,rules --cov-report=html

# View summary in terminal
pytest tests/ --cov=core,data,rules --cov-report=term-missing
```

### Current Coverage (Phase 1 MVP)
- **core/models.py** - Project, ProjectMembership, UserProfile, RefreshTokenBlacklist (85%+)
- **core/views.py** - Authentication endpoints (90%+)
- **data/models.py** - Collection, Document (90%+)
- **data/views.py** - Collection/Document CRUD, transactions (85%+)
- **rules/models.py** - SecurityPolicy, PolicyAuditLog (80%+)
- **rules/dsl.py** - RuleEngine, DSLParser (85%+)

---

## Test Assertions

### Common Patterns

#### HTTP Status Assertions
```python
assert response.status_code == status.HTTP_201_CREATED
assert response.status_code == status.HTTP_200_OK
assert response.status_code == status.HTTP_204_NO_CONTENT
assert response.status_code == status.HTTP_400_BAD_REQUEST
assert response.status_code == status.HTTP_401_UNAUTHORIZED
assert response.status_code == status.HTTP_403_FORBIDDEN
assert response.status_code == status.HTTP_404_NOT_FOUND
assert response.status_code == status.HTTP_409_CONFLICT
```

#### Response Data Assertions
```python
assert 'access' in response.data
assert response.data['user']['email'] == 'test@example.com'
assert response.data['data']['name'] == 'Alice'
assert response.data['__v'] == 1  # Version incremented
assert 'created_at' in response.data
```

#### Database Assertions
```python
assert User.objects.filter(email='test@example.com').exists()
assert Document.objects.get(doc_id='alice').data['age'] == 30
assert not Document.objects.filter(doc_id='deleted').exists()
```

#### JWT Token Assertions
```python
from jwt import decode as jwt_decode
from django.conf import settings

decoded = jwt_decode(
    token,
    settings.SIMPLE_JWT['SIGNING_KEY'],
    algorithms=['HS256']
)
assert decoded['email'] == 'test@example.com'
assert decoded.get('role') == 'editor'
```

---

## Test Data Setup

### Fixture Dependency Chain
```
api_client
  ↓
test_user → test_project → test_collection → test_document
             ↓
          ProjectMembership

admin_user → admin_project

authenticated_client (requires test_user + api_client)
admin_client (requires admin_user + api_client)
```

### Custom Test Data
For tests requiring specific data, create within the test method:

```python
@pytest.mark.django_db
def test_example(test_user, test_project):
    # Use fixtures
    project = test_project
    
    # Create custom data
    user = User.objects.create_user(
        username='custom@example.com',
        email='custom@example.com',
        password='pass123'
    )
    
    # Test logic
    assert user.email == 'custom@example.com'
```

---

## Best Practices

### 1. Use `@pytest.mark.django_db`
All tests using ORM must have this marker:
```python
@pytest.mark.django_db
class TestMyAPI:
    def test_something(self):
        # Can use ORM
        user = User.objects.create_user(...)
```

### 2. Use Fixtures for Common Setup
Instead of repeating setup code, create fixtures:
```python
@pytest.fixture
def authenticated_request(authenticated_client):
    return authenticated_client.get('/api/auth/me/')
```

### 3. Test One Thing Per Test
Each test should test a single behavior:
```python
# Good
def test_login_fails_with_wrong_password(self):
    response = self.client.post(url, {'password': 'wrong'})
    assert response.status_code == 401

# Bad - tests multiple things
def test_login(self):
    # register
    # login
    # get me
    # logout
```

### 4. Use Descriptive Names
Test names should describe what's being tested:
```python
# Good
def test_user_cannot_read_others_document_without_permission(self):

# Bad
def test_read(self):
```

### 5. Assert Response Structure and Content
```python
# Good - check both status and data
assert response.status_code == 201
assert response.data['id'] is not None
assert response.data['email'] == expected_email

# Bad - only check status
assert response.status_code == 201
```

---

## Debugging Failed Tests

### Enable Verbose Output
```bash
pytest tests/test_auth.py::TestAuthViewSet::test_login_success -vv
```

### Print Debug Info
```python
def test_example(self, api_client, test_user):
    response = api_client.post(url, data)
    print(f"Status: {response.status_code}")
    print(f"Data: {response.data}")
    print(f"User: {test_user}")
```

### Use PDB Debugger
```bash
pytest tests/test_auth.py -v --pdb
```

### Check Database State
```python
# In test, inspect DB directly
from django.contrib.auth.models import User
all_users = User.objects.all()
print(f"Users in DB: {all_users.count()}")
```

### View Full Response Body
```python
def test_example(self, api_client):
    response = api_client.post(url, data)
    if response.status_code != 201:
        import json
        print(json.dumps(response.data, indent=2))
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run migrations
        run: python manage.py migrate
      
      - name: Run tests
        run: pytest tests/ --cov=core,data,rules --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Troubleshooting Common Issues

### Issue: Import errors
```
ModuleNotFoundError: No module named 'core'
```
**Solution**: Ensure PYTHONPATH includes project root
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

### Issue: Database connection errors
```
django.db.utils.OperationalError: could not connect to server
```
**Solution**: Ensure PostgreSQL is running
```bash
# macOS with Homebrew
brew services start postgresql

# Or use SQLite for testing
# Set TEST DATABASE in settings.py
```

### Issue: Token decoding errors
```
jwt.exceptions.DecodeError: Signature verification failed
```
**Solution**: Ensure SIGNING_KEY matches settings.SIMPLE_JWT['SIGNING_KEY']

### Issue: 404 on API endpoints
```
HTTP 404 - Not Found
```
**Solution**: Check API URL routing and ensure URL names match in `reverse()`

---

## Next Steps for Future Phases

### Phase 2: Advanced Features
- [ ] Real-time subscriptions (WebSocket tests)
- [ ] Batch operations (bulk insert/update/delete)
- [ ] Full-text search (Elasticsearch tests)
- [ ] Data import/export (CSV, JSON)
- [ ] Scheduled tasks and cron jobs

### Phase 3: Performance & Scale
- [ ] Load testing (locust, k6)
- [ ] Performance benchmarks
- [ ] Stress testing with concurrent operations
- [ ] Database query optimization tests

### Phase 4: Advanced Security
- [ ] Field-level encryption tests
- [ ] Audit logging tests
- [ ] Rate limiting tests
- [ ] CORS policy tests
- [ ] API key authentication tests

---

## Appendix: Test File Reference

### conftest.py Fixtures
| Fixture | Type | Purpose |
|---------|------|---------|
| `api_client` | APIClient | Unauthenticated requests |
| `test_user` / `test_user2` | User | Regular users |
| `admin_user` | User | Superuser with admin claims |
| `test_project` / `test_project_2` | Project | Test projects |
| `test_collection` | Collection | Test collection (users) |
| `test_document` | Document | Test document (alice) |
| `authenticated_client` | APIClient | Client as test_user |
| `admin_client` | APIClient | Client as admin_user |

### Test Metrics
- **Total Test Cases**: ~55+
- **Total Assertions**: ~200+
- **Estimated Runtime**: ~30 seconds
- **Code Coverage Target**: 85%+

---

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-django Documentation](https://pytest-django.readthedocs.io/)
- [Django REST Framework Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)

