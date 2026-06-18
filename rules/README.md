# Security Rules / Row-Level Security (RLS) — Phase 1 MVP

This module implements declarative security rules for document access control, mirroring Firebase Security Rules while evaluating policies at the application level and in Postgres.

## Architecture

### Components

1. **rules/models.py** — Database models
   - `SecurityPolicy`: Stores rules per (project, collection, operation)
   - `PolicyAuditLog`: Logs all rule evaluations for debugging

2. **rules/dsl.py** — DSL parser & evaluation engine
   - `RuleEngine`: Evaluates condition trees against (request_user, document)
   - `RequestContext`: Request metadata (auth info, operation type)
   - `Document`: Represents a document being evaluated
   - `DSLParser`: Parses Firebase-like rule syntax into JSON (future enhancement)

3. **rules/postgres.py** — Postgres RLS helpers
   - `RLSPolicyBuilder`: Converts condition JSON to SQL RLS policies
   - `apply_rls_policy()`: Creates Postgres policies via SQL
   - `enable_rls_on_table()`: Enables RLS for a table

4. **rules/permissions.py** — DRF integration
   - `DocumentRules`: Permission class that evaluates rules on every request
   - Integrates with DRF viewsets for automatic enforcement

5. **rules/migrations/** — Database migrations
   - `0001_initial.py`: Create SecurityPolicy & PolicyAuditLog tables
   - `0002_default_policies.py`: Seed default policies per project

## Default Policies (Phase 1)

When a project is created, three default policies are created for the `documents` collection:

### Read Policy
- **Rule**: Allow if user is authenticated
- **Condition**: `request.auth != null`
- **Effect**: Any logged-in user can read any document (no ownership check)

### Write Policy
- **Rule**: Allow if user is authenticated AND is the document owner
- **Condition**: `request.auth != null && resource.data.owner == request.auth.uid`
- **Effect**: Only the document owner can modify it

### Delete Policy
- **Rule**: Allow if user is authenticated AND is the document owner
- **Condition**: `request.auth != null && resource.data.owner == request.auth.uid`
- **Effect**: Only the document owner can delete it

**Admin Override**: Users with `is_staff=True` bypass all rule checks (configurable).

## Usage

### 1. Creating a Document with Automatic Rule Enforcement

```python
from django.contrib.auth.models import User
from core.models import Project, Document

user = User.objects.get(email='alice@example.com')
project = Project.objects.get(slug='my-project')

# Create a document; user is automatically the owner
doc = Document.objects.create(
    project=project,
    collection='articles',
    data={'title': 'My Article', 'content': '...'},
    owner=user,
    created_by=user,
)
# Only `user` can modify or delete this document (enforced by rules)
```

### 2. Reading Documents via API

```bash
# Authenticate
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "password123"}'

# Response includes access token
# {
#   "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "refresh": "...",
#   "user": {...},
#   "project_id": "..."
# }

# Read a document (rules enforced by DocumentRules permission class)
curl -X GET http://localhost:8000/api/v1/documents/doc-uuid/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# If user is authenticated and owns the document → 200 OK
# If user doesn't own the document → 403 Forbidden
# If user is not authenticated → 401 Unauthorized
```

### 3. DRF ViewSet Integration

```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rules.permissions import DocumentRules
from core.models import Document
from api.serializers import DocumentSerializer

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, DocumentRules]
    
    # Rules are checked automatically on every request:
    # - GET /documents/ — user can list documents (auth check)
    # - GET /documents/{id}/ — user can read if owner (owner check)
    # - PATCH /documents/{id}/ — user can update if owner (owner check)
    # - DELETE /documents/{id}/ — user can delete if owner (owner check)
```

### 4. Creating Custom Security Rules

#### Via Django Admin

1. Navigate to `/admin/rules/securitypolicy/`
2. Click "Add Security Policy"
3. Fill in:
   - **Project**: Select project
   - **Collection**: "documents" (or your collection name)
   - **Rule Type**: "read", "write", or "delete"
   - **Condition JSON**: Structured condition tree (see examples below)
   - **Active**: Check to enable
   - **Priority**: Higher numbers evaluated first
   - **Description**: "Allow read if user is group member" (optional)

#### Via Python/Django ORM

```python
from rules.models import SecurityPolicy
from core.models import Project

project = Project.objects.get(slug='my-project')

# Custom rule: allow read if document is public
policy = SecurityPolicy.objects.create(
    project=project,
    collection='documents',
    rule_type='read',
    condition_json={
        'operator': 'or',
        'conditions': [
            # Default owner check
            {
                'type': 'auth_check',
                'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
            },
            {
                'type': 'owner_check',
                'value': {'field': 'owner_id'}
            },
            # OR allow if marked public
            {
                'type': 'field_check',
                'value': {
                    'path': 'data.is_public',
                    'op': '==',
                    'rhs': 'true'
                }
            }
        ]
    },
    active=True,
    priority=50,  # Lower than default (100), evaluated later
    description='Allow read if owner OR document is public',
)
```

## Condition JSON Structure

Rules are stored as JSON condition trees evaluated by `RuleEngine`.

### Schema

```json
{
  "operator": "and" | "or",
  "conditions": [
    {
      "type": "auth_check" | "field_check" | "owner_check" | "role_check",
      "value": { /* type-specific fields */ }
    },
    ...
  ]
}
```

### Condition Types

#### 1. `auth_check` — Check authentication status

```json
{
  "type": "auth_check",
  "value": {
    "field": "request.auth",
    "op": "!=" | "==",
    "rhs": "null"
  }
}
```

**Examples:**
- `request.auth != null` → User is authenticated
- `request.auth == null` → User is not authenticated

#### 2. `field_check` — Compare document fields

```json
{
  "type": "field_check",
  "value": {
    "path": "data.owner" | "data.group_id" | "data.is_public",
    "op": "==" | "!=" | "<" | "<=" | ">" | ">=" | "in" | "contains" | "matches",
    "rhs": "literal_value" | null,
    "rhs_field": "request.auth.uid" | "data.other_field" | null
  }
}
```

**Examples:**
- Owner comparison: `{"path": "data.owner", "op": "==", "rhs_field": "request.auth.uid"}`
- Public check: `{"path": "data.is_public", "op": "==", "rhs": "true"}`
- Visibility check: `{"path": "data.visibility", "op": "==", "rhs": "public"}`

#### 3. `owner_check` — Check if user owns the document

```json
{
  "type": "owner_check",
  "value": {
    "field": "owner_id"  // Document field to check against request.auth.uid
  }
}
```

**Example:**
- `{"type": "owner_check", "value": {"field": "owner_id"}}` → True if `doc.owner_id == request.user.id`

#### 4. `role_check` — Check user's project role (Phase 2)

```json
{
  "type": "role_check",
  "value": {
    "role": "admin" | "editor" | "viewer"
  }
}
```

**Note**: Phase 1 only checks `is_staff` flag. Phase 2 will integrate with `ProjectMembership.role`.

## Postgres RLS Integration (Optional)

Rules can also be enforced at the database level via Postgres Row-Level Security.

### Enable RLS on a Table

```python
from rules.postgres import enable_rls_on_table

# Enable RLS for the documents table
enable_rls_on_table(table_name='core_document')
```

### Apply a Policy

When a `SecurityPolicy` is created/updated via the admin, RLS policies are automatically generated and applied:

```sql
-- Generated SQL for read rule:
CREATE POLICY "documents_read_<id>" ON core_document
FOR SELECT
USING (
  auth.uid() IS NOT NULL AND
  (data->>'owner') = auth.uid()::TEXT
);
```

**Benefits:**
- Database-enforced: rules apply even if application is compromised
- Faster: evaluated at Postgres level before data is returned
- Transactions: RLS respects database transaction isolation

**Limitations:**
- SQL-only policies: complex rules may not translate
- Custom claims: would need to query JWT metadata via Postgres function
- Admin bypass: requires Postgres role separation (not implemented in Phase 1)

## Testing Rules

### Unit Tests

```bash
# Run rule evaluation tests
pytest tests/test_rules.py::TestDSLEvaluator -v

# Run permission class tests
pytest tests/test_rules.py::TestDocumentRulesPermission -v

# Run model tests
pytest tests/test_rules.py::TestSecurityPolicyModel -v
```

### Manual Testing via API

**Scenario: Try to read a document owned by another user**

```bash
# 1. Create User A and User B
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "SecurePassword123"}'

curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "password": "SecurePassword123"}'

# 2. Create a project and add both users
# (via Django admin or API)

# 3. User A creates a document
TOKEN_A=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "SecurePassword123"}' \
  | jq -r '.access')

DOC_ID=$(curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"collection": "documents", "data": {"title": "Alice'\''s Secret"}}' \
  | jq -r '.id')

# 4. User B tries to modify the document
TOKEN_B=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "password": "SecurePassword123"}' \
  | jq -r '.access')

curl -X PATCH http://localhost:8000/api/v1/documents/$DOC_ID/ \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{"data": {"title": "Bob Hacked It"}}'

# Expected: 403 Forbidden (rule evaluation denied the write)
```

## Audit Logging

Every rule evaluation is logged to `PolicyAuditLog` for debugging:

```python
from rules.models import PolicyAuditLog

# View recent audit log
logs = PolicyAuditLog.objects.filter(
    project__slug='my-project'
).order_by('-created_at')[:10]

for log in logs:
    print(f"{log.user.email} {log.operation} {log.collection}/{log.document_id}: {log.allowed} ({log.reason})")
```

**Example output:**
```
alice@example.com read documents/doc-123: True (Rule 1 ALLOWED read documents/doc-123)
bob@example.com write documents/doc-123: False (No rules allowed write documents/doc-123. Denying.)
```

View audit logs in the Django admin at `/admin/rules/policyauditlog/`.

## Phase 2+ Enhancements

- **DSL Parser**: Full Firebase Security Rules syntax parser (currently basic)
- **Custom Claims**: Support `request.auth.custom_claim` in rules
- **Cross-Document Checks**: Equivalent to Firebase's `get()` and `exists()`
- **Role-Based Checks**: Full integration with `ProjectMembership.role`
- **Performance**: Caching frequently evaluated rules, compiled SQL policies
- **OPA Integration**: Complex policy evaluation via Open Policy Agent sidecar
- **Rule Versioning**: Deploy/rollback rule versions like Firestore does
- **Real-Time Updates**: Notify clients when rules change
- **Batch Operations**: Batch write/delete with atomicity guarantees

## Troubleshooting

### Q: Rule was created but doesn't seem to be enforced

**A:**
1. Verify rule is `active=True`
2. Check `PolicyAuditLog` for evaluations
3. Ensure `DocumentRules` permission is on your viewset
4. Check rule priority (`-priority` ordering means higher numbers evaluated first)

### Q: Postgres RLS policy not being applied

**A:**
1. RLS is optional in Phase 1; application-level checks are the primary enforcement
2. To enable: call `enable_rls_on_table()` first
3. Check logs for conversion errors (complex rules may not translate to SQL)
4. Manually write SQL if needed

### Q: Audit log growing too large

**A:**
1. Set up a management command to prune old logs:
   ```python
   from django.utils import timezone
   from datetime import timedelta
   from rules.models import PolicyAuditLog
   
   cutoff = timezone.now() - timedelta(days=30)
   PolicyAuditLog.objects.filter(created_at__lt=cutoff).delete()
   ```
2. Add to a Celery beat task for automatic cleanup

### Q: How do I test if a rule blocks access?

**A:**
```python
from rules.dsl import RuleEngine, RequestContext, Document
from rules.models import SecurityPolicy

policy = SecurityPolicy.objects.get(id='...')
engine = RuleEngine()

request = RequestContext(
    auth_user=request.user,
    auth_uid=str(request.user.id),
    operation='write',
    is_admin=False,
)

doc = Document(id='...', data={...}, owner_id='...')

result = engine.check(policy.condition_json, request, doc)
print(f"Access allowed: {result}")
```

## API Reference

### SecurityPolicy Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `project` | ForeignKey(Project) | Project this rule belongs to |
| `collection` | CharField | Collection name ("documents", "posts", etc.) |
| `rule_type` | CharField | "read", "write", or "delete" |
| `condition_json` | JSONField | Condition tree (see schema above) |
| `active` | Boolean | Enable/disable the rule |
| `description` | TextField | Human-readable description |
| `priority` | Integer | Evaluation order (higher = first) |
| `created_at` | DateTime | Created timestamp |
| `updated_at` | DateTime | Last updated timestamp |

### RuleEngine Methods

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `check()` | condition_json, request, doc | bool | Evaluate rule against request + document |
| `_evaluate_condition()` | condition, request, doc | bool | Recursively evaluate condition tree |
| `_evaluate_atomic()` | condition, request, doc | bool | Evaluate single condition |

### DocumentRules Permission Class

| Method | Returns | Description |
|--------|---------|-------------|
| `has_permission()` | bool | Check list-level permissions |
| `has_object_permission()` | bool | Check object-level permissions (calls rule engine) |

## References

- Firebase Security Rules: https://firebase.google.com/docs/rules
- Postgres RLS: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Django RLS: https://django-rls.readthedocs.io/
