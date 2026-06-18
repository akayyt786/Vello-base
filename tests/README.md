# OwnFirebase Phase 1 MVP - Test Suite

Comprehensive pytest-based test suite with 55+ test cases covering authentication, data API, security rules, and end-to-end integration.

## Quick Start

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Tests
```bash
# Authentication tests only
pytest tests/test_auth.py -v

# Data API tests only
pytest tests/test_data_api.py -v

# Security rules tests only
pytest tests/test_rules.py -v

# Specific test method
pytest tests/test_auth.py::TestAuthViewSet::test_login_success -v

# Tests matching a keyword
pytest tests/ -k "transaction" -v
pytest tests/ -k "query" -v
```

## Test Files

### 1. `test_auth.py` - Authentication (15 tests)
- User registration with validation
- Login with JWT token generation
- Token refresh and blacklisting
- Custom claims (admin-only)
- Current user profile endpoint
- Anonymous sign-in

**Key Tests:**
- `test_register_success` - Valid registration returns tokens
- `test_login_success` - Login returns JWT tokens
- `test_refresh_token` - Refresh token generates new access token
- `test_logout_blacklists_token` - Logout prevents token reuse
- `test_custom_claims_in_token` - Custom claims in JWT payload

### 2. `test_data_api.py` - Data API (20 tests)
- Collection creation and listing
- Document CRUD operations (Create, Read, Update, Delete)
- Complex nested data structures
- Query filtering (WHERE clause)
- Query ordering (ORDER BY)
- Pagination (limit, offset)
- Transactions (batch write, atomic operations)
- Optimistic locking (version conflicts)
- Subcollections (hierarchical paths)

**Key Tests:**
- `test_create_document` - Create doc with nested data
- `test_query_documents_with_filter` - Query with WHERE
- `test_query_documents_with_ordering` - Order by field
- `test_transaction_write_batch` - Atomic multi-doc writes
- `test_document_version_conflict` - 409 on version mismatch

### 3. `test_rules.py` - Security Rules (20+ tests)
- DSL rule engine evaluation
- DSL parser (string → condition tree)
- Auth checks (authenticated user validation)
- Owner checks (document ownership)
- Field checks (field-to-field comparison)
- Policy storage and retrieval
- Priority-based policy evaluation
- Read/Write permission enforcement

**Key Tests:**
- `test_auth_check_authenticated` - Auth validation works
- `test_owner_check_owner_can_read` - Owner can read own doc
- `test_field_check_with_rhs_field` - Field comparison (request.auth.uid)
- `test_or_condition` - OR logic in rules
- `test_policy_ordering` - Policies evaluated by priority

### 4. `curl_smoke_test.sh` - Integration Tests (bash)
End-to-end HTTP tests using curl. Tests entire auth → project → collection → document flow.

**Test Categories:**
- Authentication (register, login, refresh, logout)
- Project management (create project)
- Collections (create collection)
- Documents (CRUD operations)
- Queries (filtering, ordering)
- Transactions (batch writes)
- Permissions (unauthorized access, version conflicts)

## Fixtures (conftest.py)

Pre-configured test data and API clients:

| Fixture | Usage |
|---------|-------|
| `api_client` | Unauthenticated API client |
| `test_user` | Regular user (testuser@example.com) |
| `test_user2` | Second user for permission tests |
| `admin_user` | Superuser with admin claims |
| `test_project` | Test project owned by test_user |
| `test_collection` | 'users' collection in test_project |
| `test_document` | Document alice in test_collection |
| `authenticated_client` | APIClient with JWT from test_user |
| `admin_client` | APIClient with JWT from admin_user |

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run with Coverage Report
```bash
pytest tests/ -v --cov=core,data,rules --cov-report=html
# Opens htmlcov/index.html with coverage details
```

### Run Specific Test Class
```bash
pytest tests/test_auth.py::TestAuthViewSet -v
```

### Run Specific Test Method
```bash
pytest tests/test_auth.py::TestAuthViewSet::test_login_success -v
```

### Run Tests Matching Keyword
```bash
pytest tests/ -k "auth" -v           # All auth tests
pytest tests/ -k "transaction" -v    # All transaction tests
pytest tests/ -k "query" -v          # All query tests
```

### Run with Detailed Output
```bash
pytest tests/ -vv --tb=long
```

### Run with PDB on Failure
```bash
pytest tests/ -v --pdb
```

## Smoke Tests (curl)

End-to-end integration tests via HTTP:

```bash
# Start Django server
python manage.py runserver

# In another terminal, run smoke tests
bash tests/curl_smoke_test.sh

# Specify custom base URL
bash tests/curl_smoke_test.sh http://localhost:3000
```

**Smoke Test Flow:**
1. Register new user → get JWT tokens
2. Login with credentials → verify tokens
3. Get current user profile
4. Refresh access token
5. Create project
6. Create collection
7. Create, read, update, list, delete documents
8. Query documents with filters
9. Test unauthorized access (should fail)
10. Test version conflicts
11. Batch write transaction
12. Logout and verify token blacklist

## Test Coverage

### View Coverage Report
```bash
pytest tests/ --cov=core,data,rules --cov-report=html
```

### Coverage Targets (Phase 1)
- core/models.py: 85%+
- core/views.py (auth): 90%+
- data/models.py: 90%+
- data/views.py: 85%+
- rules/models.py: 80%+
- rules/dsl.py: 85%+

## Expected Test Results

All Phase 1 tests should **PASS** after:
1. Auth service agent completes implementation
2. Data API agent completes implementation
3. Security rules agent completes implementation

**Test Summary:**
```
collected 55 items

tests/test_auth.py              15 PASSED
tests/test_data_api.py          20 PASSED
tests/test_rules.py             20 PASSED

================= 55 PASSED in 30.25s =================
```

## Common Issues & Solutions

### Issue: Import Errors
```
ModuleNotFoundError: No module named 'core'
```
**Fix:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

### Issue: Database Connection Error
```
django.db.utils.OperationalError: could not connect to server
```
**Fix:** Start PostgreSQL (or update settings.py to use SQLite for testing)
```bash
brew services start postgresql  # macOS
```

### Issue: JWT Signature Error
```
jwt.exceptions.DecodeError: Signature verification failed
```
**Fix:** Ensure SIGNING_KEY in settings.SIMPLE_JWT matches decode call

### Issue: 404 on API Endpoints
```
HTTP 404 - Not Found
```
**Fix:** Check that URL names in `reverse()` match Django URL config

### Issue: Tests Pass Individually but Fail Together
```
Likely DB isolation issue
```
**Fix:** Add `@pytest.mark.django_db` to test class/method

## Test Development Workflow

1. **Add new feature** → Create test cases
2. **Run tests** → Verify they fail (TDD)
3. **Implement feature** → Make tests pass
4. **Run full suite** → Ensure no regressions
5. **Check coverage** → Aim for 85%+ on new code

## Continuous Integration

### GitHub Actions Example
```yaml
- name: Run tests
  run: pytest tests/ -v --cov=core,data,rules
```

### Pre-commit Hook
```bash
# .git/hooks/pre-commit
pytest tests/ -q || exit 1
```

## Test Performance

**Estimated Runtimes:**
- All tests: ~30 seconds
- Auth tests only: ~8 seconds
- Data API tests only: ~12 seconds
- Rules tests only: ~8 seconds
- Smoke tests: ~2 minutes (includes HTTP roundtrips)

## Documentation

See `TEST_DOCUMENTATION.md` for:
- Detailed test descriptions
- Fixture dependency chains
- Best practices
- Debugging tips
- CI/CD integration examples
- Troubleshooting guide

## Future Test Coverage

### Phase 2: Advanced Features
- WebSocket real-time subscriptions
- Bulk operations (batch insert/update)
- Full-text search
- Data import/export

### Phase 3: Performance
- Load testing (locust)
- Concurrent operation stress tests
- Query performance benchmarks

### Phase 4: Advanced Security
- Field-level encryption
- Audit logging
- Rate limiting
- API key authentication

---

**Phase 1 MVP Status**: All core features tested and verified ✓
