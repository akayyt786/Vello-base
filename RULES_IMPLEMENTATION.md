# Security Rules / RLS Implementation — Phase 1 MVP

## Summary

Implemented a complete **declarative Security Rules system** for Phase 1 MVP of Own Firebase, enabling document-level access control via:

1. **Application-level rule evaluation** (RuleEngine in Python)
2. **Postgres Row-Level Security** (SQL policies, optional)
3. **DRF integration** (automatic permission enforcement on every request)
4. **Default policies** (seeded on project creation)
5. **Audit logging** (tracks all rule evaluations for debugging)

This mirrors Firebase Security Rules behavior while providing more flexibility and transparency through Python-evaluated conditions + Postgres RLS.

---

## Files Created

### Core Implementation

```
rules/
├── __init__.py                    # Package init
├── apps.py                         # Django app config
├── models.py                       # SecurityPolicy & PolicyAuditLog models
├── dsl.py                         # RuleEngine, RequestContext, DSLParser
├── postgres.py                    # Postgres RLS builder & helpers
├── permissions.py                 # DocumentRules DRF permission class
├── admin.py                       # Django admin interface
├── migrations/
│   ├── __init__.py
│   ├── 0001_initial.py           # Create SecurityPolicy & PolicyAuditLog tables
│   └── 0002_default_policies.py  # Seed default policies
└── README.md                      # Comprehensive usage guide

core/
├── models.py                      # Added Document model (Firestore-like)
└── migrations/
    └── 0002_document.py           # Migration for Document model

api/
├── views.py                       # Added DocumentViewSet with rule enforcement
├── serializers.py                 # Added DocumentSerializer
└── urls.py                        # Registered documents router

ownfirebase/
└── settings.py                    # Added 'rules' to INSTALLED_APPS

tests/
└── test_rules.py                  # Comprehensive test suite
```

---

## Architecture Overview

### 1. Models (rules/models.py)

#### SecurityPolicy
Stores declarative access control rules per (project, collection, operation).

```python
class SecurityPolicy(MultiTenantModel):
    id: UUID
    project: ForeignKey(Project)
    collection: str                    # "documents", "posts", "comments"
    rule_type: str                     # "read", "write", "delete"
    condition_json: JSONField          # Structured condition tree
    active: bool                       # Enable/disable rule
    priority: int                      # Evaluation order (higher first)
    description: str                   # Human-readable
```

**Example:**
```json
{
  "collection": "documents",
  "rule_type": "write",
  "condition_json": {
    "operator": "and",
    "conditions": [
      {"type": "auth_check", "value": {"op": "!=", "rhs": "null"}},
      {"type": "owner_check", "value": {"field": "owner_id"}}
    ]
  },
  "active": true,
  "priority": 100
}
```

#### PolicyAuditLog
Logs every rule evaluation for debugging & compliance.

```python
class PolicyAuditLog(models.Model):
    id: UUID
    project: ForeignKey(Project)
    user: ForeignKey(User)
    collection: str
    operation: str                     # "read", "write", "delete"
    document_id: str
    allowed: bool                      # Whether rule allowed the operation
    reason: str                        # Why allowed/denied
    matched_policies: JSON             # Which policies were evaluated
    created_at: DateTime
```

### 2. DSL Parser & Evaluator (rules/dsl.py)

#### RuleEngine
Evaluates condition trees against (request_user, document) context.

**Key Classes:**
- `RequestContext` — Wraps request metadata (auth_user, auth_uid, operation, is_admin)
- `Document` — Represents a document being evaluated (id, data, owner_id)
- `RuleEngine` — Evaluates conditions recursively

**Algorithm:**
1. Load rules for (project, collection, operation), sorted by priority
2. For each rule:
   - Evaluate condition tree recursively (AND/OR logic)
   - First rule to allow wins → return True
3. If no rule allowed → return False (fail-safe)

**Condition Types:**

| Type | Example | Evaluates |
|------|---------|-----------|
| `auth_check` | `request.auth != null` | User is authenticated |
| `field_check` | `data.owner == request.auth.uid` | Document field comparison |
| `owner_check` | (implicit) | `doc.owner_id == request.user.id` |
| `role_check` | `role in ["admin", "editor"]` | User's project role (Phase 2) |

#### DSLParser (Optional)
Parses Firebase-like rule syntax into condition JSON:

```
Input:  "allow write if request.auth != null && data.owner == request.auth.uid"
Output: {
  "operator": "and",
  "conditions": [
    {"type": "auth_check", ...},
    {"type": "field_check", ...}
  ]
}
```

### 3. Postgres RLS Integration (rules/postgres.py)

Optional database-level enforcement. When a rule is created:

```sql
CREATE POLICY "documents_write_abc123" ON core_document
FOR INSERT
WITH CHECK (
  auth.uid() IS NOT NULL AND
  (data->>'owner') = auth.uid()::TEXT
);
```

**Benefits:**
- Database-enforced: rules apply even if app is compromised
- Faster: evaluated by Postgres before data returned
- Transactions: respects ACID guarantees

**Limitations:**
- Simple rules only (SQL doesn't support complex logic)
- Custom claims not available
- Admin bypass needs role separation

### 4. DRF Permission Class (rules/permissions.py)

#### DocumentRules
Integrates rule engine with Django REST Framework.

```python
class DocumentRules(BasePermission):
    def has_permission(self, request, view):
        # List permissions: check authenticated
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Detail permissions: evaluate rules
        operation = self._get_operation(request)  # read/write/delete
        collection = self._get_collection_name(obj)
        document = self._object_to_document(obj)
        project_id = self._get_project_id(request, obj)
        
        allowed = self._check_rules(
            request.user, project_id, collection, operation, document
        )
        
        self._log_decision(...)  # Audit log
        return allowed
```

**Usage in ViewSet:**
```python
class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, DocumentRules]
    # Rules automatically enforced on every request
```

### 5. Document Model (core/models.py)

Added a Firestore-like document model:

```python
class Document(MultiTenantModel):
    id: UUID
    project: ForeignKey(Project)        # Multi-tenant
    collection: str                     # "documents", "posts"
    data: JSONField                     # Arbitrary document data
    owner: ForeignKey(User)             # Document owner
    created_by: ForeignKey(User)        # Who created
    updated_by: ForeignKey(User)        # Who last updated
    created_at: DateTime
    updated_at: DateTime
```

---

## Default Policies (Seeded on Project Creation)

When a project is created, three default policies are auto-created for the `documents` collection:

### 1. Read Policy
- **Name**: "Default: allow read if authenticated"
- **Collection**: `documents`
- **Operation**: `read`
- **Rule**: `request.auth != null`
- **Effect**: Any logged-in user can read any document
- **Priority**: 100

### 2. Write Policy
- **Name**: "Default: allow write if owner"
- **Collection**: `documents`
- **Operation**: `write`
- **Rule**: `request.auth != null && data.owner == request.auth.uid`
- **Effect**: Only document owner can modify
- **Priority**: 100

### 3. Delete Policy
- **Name**: "Default: allow delete if owner"
- **Collection**: `documents`
- **Operation**: `delete`
- **Rule**: `request.auth != null && data.owner == request.auth.uid`
- **Effect**: Only document owner can delete
- **Priority**: 100

**Admin Override**: Users with `is_staff=True` always bypass all checks (configurable).

---

## Workflow: Testing Rule Enforcement

### Scenario: Try to read a document owned by another user

**Step 1: Create Users**
```bash
# User A
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "SecurePassword123",
    "password_confirm": "SecurePassword123"
  }'

# User B
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bob@example.com",
    "password": "SecurePassword123",
    "password_confirm": "SecurePassword123"
  }'
```

**Step 2: Create Project & Add Users**
```bash
# Login as Alice and create project
TOKEN_A=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "SecurePassword123"}' \
  | jq -r '.access')

PROJECT=$(curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "slug": "test-project"}' \
  | jq -r '.id')

# Add Bob to project
curl -X POST http://localhost:8000/api/v1/projects/$PROJECT/invite_member/ \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "role": "viewer"}'
```

**Step 3: Alice Creates a Document**
```bash
DOC=$(curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "'$PROJECT'",
    "collection": "documents",
    "data": {"title": "Alice Secret"}
  }' \
  | jq -r '.id')

echo "Created document: $DOC (owned by Alice)"
```

**Step 4: Bob Tries to Modify Document**
```bash
TOKEN_B=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "password": "SecurePassword123"}' \
  | jq -r '.access')

curl -X PATCH http://localhost:8000/api/v1/documents/$DOC/ \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{"data": {"title": "Bob Hacked It"}}'

# Response: 403 Forbidden
# {
#   "detail": "You do not have permission to perform this action."
# }
```

**Step 5: Check Audit Log**
```python
from rules.models import PolicyAuditLog

# In Django shell:
logs = PolicyAuditLog.objects.filter(document_id='<doc-id>').order_by('-created_at')
for log in logs:
    print(f"{log.user.email} {log.operation} {log.collection}/{log.document_id}: {log.allowed}")

# Output:
# bob@example.com write documents/<doc-id>: False
# alice@example.com read documents/<doc-id>: True
```

---

## Condition JSON Examples

### 1. Public Documents (Anyone Can Read)

```json
{
  "operator": "or",
  "conditions": [
    {
      "type": "field_check",
      "value": {
        "path": "data.is_public",
        "op": "==",
        "rhs": "true"
      }
    },
    {
      "type": "auth_check",
      "value": {"op": "!=", "rhs": "null"}
    }
  ]
}
```

**Effect**: Allow read if `is_public=true` OR user is authenticated.

### 2. Group-Based Access (Editor Group Members Only)

```json
{
  "operator": "and",
  "conditions": [
    {
      "type": "auth_check",
      "value": {"op": "!=", "rhs": "null"}
    },
    {
      "type": "field_check",
      "value": {
        "path": "data.group_editors",
        "op": "contains",
        "rhs_field": "request.auth.uid"
      }
    }
  ]
}
```

**Effect**: Allow write if authenticated AND user ID is in `data.group_editors` array.

### 3. Admin Can Do Anything, Owner Can Modify

```json
{
  "operator": "or",
  "conditions": [
    {
      "type": "role_check",
      "value": {"role": "admin"}
    },
    {
      "type": "owner_check",
      "value": {"field": "owner_id"}
    }
  ]
}
```

**Effect**: Allow if user is admin OR is document owner.

---

## Running Tests

```bash
# All rule tests
pytest tests/test_rules.py -v

# Specific test class
pytest tests/test_rules.py::TestDSLEvaluator -v

# Test with coverage
pytest tests/test_rules.py --cov=rules --cov-report=html
```

**Test Coverage:**
- DSL evaluation (auth_check, field_check, owner_check, role_check)
- AND/OR logic
- Document permission checks
- SecurityPolicy model validation
- Policy ordering by priority
- Audit logging

---

## Phase 1 to Phase 2 Migration Path

### Phase 1 MVP (Now)
- [x] SecurityPolicy model + migrations
- [x] RuleEngine evaluator (JSON condition trees)
- [x] DRF permission class (DocumentRules)
- [x] Default policies (per collection)
- [x] Audit logging
- [x] Basic Postgres RLS helpers
- [x] Django admin interface
- [x] Comprehensive tests

### Phase 2 Enhancements (Ready to Implement)
- [ ] Full DSL parser (Firebase-compatible syntax)
- [ ] Custom claims in conditions (`request.auth.custom_claim`)
- [ ] Cross-document checks (`get()`, `exists()`)
- [ ] Full role-based access control integration
- [ ] Rule versioning & deployment
- [ ] OPA integration (complex policies)
- [ ] Performance: rule caching, compiled SQL
- [ ] Batch write/delete with atomicity
- [ ] Real-time rule update notifications

### Phase 3+ (Future)
- [ ] Multi-collection rules (wildcards)
- [ ] Subcollection rules
- [ ] Transaction-level rules
- [ ] Index-based optimization
- [ ] Rule profiling & performance insights
- [ ] UI rule builder / rule playground

---

## Integration Checklist

### 1. Database Setup
```bash
# Run migrations
python manage.py migrate rules
python manage.py migrate core

# Verify tables created
python manage.py dbshell
SELECT * FROM rules_security_policy LIMIT 1;
SELECT * FROM rules_policy_audit_log LIMIT 1;
SELECT * FROM core_document LIMIT 1;
```

### 2. Document ViewSet Registration
✅ Added `DocumentViewSet` to `api/views.py`
✅ Registered in `api/urls.py`
✅ Added `DocumentSerializer` to `api/serializers.py`

### 3. Rules App Installation
✅ Added `'rules'` to `INSTALLED_APPS` in `ownfirebase/settings.py`
✅ Created `rules/apps.py`

### 4. Default Rules Seeding
✅ Created `0002_default_policies.py` data migration
- Automatically creates default read/write/delete policies on migrate

### 5. Admin Interface
✅ Created `rules/admin.py`
- Full CRUD for `SecurityPolicy` in Django admin
- Read-only audit log viewer

---

## Key Design Decisions

### 1. JSON Condition Trees (vs Text DSL)
**Chosen**: Structured JSON for Phase 1, optional text DSL parser for Phase 2.

**Rationale**: 
- Easier to validate & store in DB
- Type-safe evaluation
- Can add DSL parser later without breaking existing rules
- Better for programmatic generation

### 2. Application-Level Evaluation (vs Database-Only)
**Chosen**: Primary evaluation in Python, optional Postgres RLS.

**Rationale**:
- More flexible: custom claims, complex logic, cross-service calls
- Easier to debug: audit logs, testing
- Language-native: Python expressions easier to reason about
- Postgres RLS as optional hardening

### 3. Fail-Safe Default (vs Fail-Open)
**Chosen**: If no rules match → DENY (fail-safe).

**Rationale**:
- Security: default is "no access"
- Requires explicit rule to allow
- Prevents accidental exposure

### 4. Priority-Based Rule Ordering
**Chosen**: Rules evaluated by `-priority` (higher first), first match wins.

**Rationale**:
- Clear precedence: no ambiguity
- Performance: can short-circuit on first allow
- Familiar: same as middleware/permission chains

---

## Known Limitations & Future Work

### Phase 1 Limitations
1. **No Cross-Document Checks**: Can't query other documents to make decisions (Firebase's `get()`/`exists()`)
2. **No Custom Claims in Conditions**: Would need to parse JWT in condition evaluator
3. **Simple DSL Parser**: Basic text parsing, not full Firebase CEL syntax
4. **Role Check Incomplete**: Only checks `is_staff`, not `ProjectMembership.role`
5. **No Rule Versioning**: Can't deploy/rollback rule versions
6. **Postgres RLS Optional**: Not all rules convert to SQL

### Phase 2 Priority Enhancements
1. Implement full DSL parser (Firebase-compatible)
2. Add cross-document rule evaluation via DB queries
3. Full role-based access control
4. Rule versioning & deployment
5. Performance: rule result caching, compiled SQL policies
6. OPA sidecar for complex policy evaluation

---

## Troubleshooting Guide

### Rule Not Being Enforced

**Checklist:**
1. Is the rule `active=True`?
2. Is `DocumentRules` in the viewset's `permission_classes`?
3. Check `PolicyAuditLog` for evaluation results
4. Verify rule `priority` (higher = evaluated first)
5. Test rule in Django shell:
   ```python
   from rules.dsl import RuleEngine, RequestContext, Document as DSLDocument
   engine = RuleEngine()
   result = engine.check(policy.condition_json, request_ctx, doc)
   print(f"Allowed: {result}")
   ```

### Audit Log Growing Too Large

**Solution:**
```python
# Create management command or Celery task:
from django.utils import timezone
from datetime import timedelta
from rules.models import PolicyAuditLog

cutoff = timezone.now() - timedelta(days=30)
deleted_count, _ = PolicyAuditLog.objects.filter(created_at__lt=cutoff).delete()
print(f"Deleted {deleted_count} audit logs")
```

### Postgres RLS Policy Not Applied

**Troubleshooting:**
1. RLS is optional; app-level checks are primary
2. Enable RLS: `from rules.postgres import enable_rls_on_table; enable_rls_on_table()`
3. Check Postgres logs for SQL errors
4. Complex rules may not translate to SQL (limitations of PostgreSQL)

---

## Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `rules/models.py` | ~180 | SecurityPolicy, PolicyAuditLog models |
| `rules/dsl.py` | ~450 | RuleEngine, RequestContext, DSLParser |
| `rules/postgres.py` | ~280 | Postgres RLS builder, SQL generation |
| `rules/permissions.py` | ~180 | DocumentRules DRF permission class |
| `rules/admin.py` | ~80 | Django admin interface |
| `rules/apps.py` | ~10 | App config |
| `rules/migrations/0001_initial.py` | ~110 | Create tables |
| `rules/migrations/0002_default_policies.py` | ~90 | Seed default rules |
| `core/models.py` | +60 | Added Document model |
| `api/views.py` | +50 | Added DocumentViewSet |
| `api/serializers.py` | +30 | Added DocumentSerializer |
| `tests/test_rules.py` | ~350 | Comprehensive test suite |
| `rules/README.md` | ~500 | Full usage documentation |
| **Total** | **~2,400** | **Complete implementation** |

---

## Next Steps

1. **Run Migrations**: `python manage.py migrate`
2. **Create Test Project**: Via admin or API
3. **Test Rules**: Follow "Testing Rule Enforcement" scenario above
4. **View Audit Logs**: In admin at `/admin/rules/policyauditlog/`
5. **Create Custom Rules**: Add via admin or Python ORM
6. **Monitor Performance**: Check audit logs for rule evaluation times (Phase 2)
