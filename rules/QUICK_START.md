# Security Rules Quick Start

## 30-Second Overview

Security Rules control who can read/write/delete documents. They're evaluated automatically on every request.

**Default behavior:**
- ✅ Authenticated users can READ any document
- ✅ Only owners can WRITE/DELETE their own documents
- ✅ Admins (is_staff=True) bypass all rules

## Setup (5 minutes)

### 1. Run Migrations
```bash
python manage.py migrate
```

This creates:
- `rules_security_policy` table (stores rules)
- `rules_policy_audit_log` table (logs evaluations)
- `core_document` table (documents)
- Default policies for each project

### 2. Create a Test Project
```bash
# Via API
curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project", "slug": "my-project"}'
```

### 3. Create a Document
```bash
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "<project-uuid>",
    "collection": "documents",
    "data": {"title": "Hello World"}
  }'
```

### 4. Test Access Control
```bash
# This user can read (authenticated)
curl -X GET http://localhost:8000/api/v1/documents/<doc-id>/ \
  -H "Authorization: Bearer <user1-token>"
# → 200 OK

# This user cannot write (not owner)
curl -X PATCH http://localhost:8000/api/v1/documents/<doc-id>/ \
  -H "Authorization: Bearer <user2-token>" \
  -d '{"data": {"title": "Hacked"}}'
# → 403 Forbidden
```

## Creating Custom Rules

### Via Django Admin

1. Go to `/admin/rules/securitypolicy/`
2. Click "Add Security Policy"
3. Fill in:
   - **Project**: Select project
   - **Collection**: "documents"
   - **Rule Type**: "read", "write", or "delete"
   - **Condition JSON**: (see examples below)
   - **Active**: ✓ Enable
   - **Priority**: 100 (default)

### Via Python

```python
from rules.models import SecurityPolicy
from core.models import Project

project = Project.objects.get(slug='my-project')

# Allow read if document is marked public
SecurityPolicy.objects.create(
    project=project,
    collection='documents',
    rule_type='read',
    condition_json={
        'operator': 'and',
        'conditions': [
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
    priority=50,
    description='Allow read if public'
)
```

## Common Condition Examples

### "Owner Only"
```json
{
  "operator": "and",
  "conditions": [
    {"type": "auth_check", "value": {"op": "!=", "rhs": "null"}},
    {"type": "owner_check", "value": {"field": "owner_id"}}
  ]
}
```

### "Authenticated Users Only"
```json
{
  "operator": "and",
  "conditions": [
    {"type": "auth_check", "value": {"op": "!=", "rhs": "null"}}
  ]
}
```

### "Public or Owner"
```json
{
  "operator": "or",
  "conditions": [
    {
      "type": "field_check",
      "value": {"path": "data.is_public", "op": "==", "rhs": "true"}
    },
    {
      "type": "owner_check",
      "value": {"field": "owner_id"}
    }
  ]
}
```

### "Owner Can Modify, Group Members Can Read"
```json
{
  "operator": "or",
  "conditions": [
    {
      "type": "owner_check",
      "value": {"field": "owner_id"}
    },
    {
      "type": "field_check",
      "value": {
        "path": "data.group_members",
        "op": "contains",
        "rhs_field": "request.auth.uid"
      }
    }
  ]
}
```

### "Size Limit (Write Only for Small Files)"
```json
{
  "operator": "and",
  "conditions": [
    {"type": "auth_check", "value": {"op": "!=", "rhs": "null"}},
    {
      "type": "field_check",
      "value": {
        "path": "data.size",
        "op": "<",
        "rhs": "10000000"  # 10 MB
      }
    }
  ]
}
```

## Testing in Django Shell

```python
python manage.py shell

from rules.dsl import RuleEngine, RequestContext, Document as DSLDocument
from django.contrib.auth.models import User
from rules.models import SecurityPolicy

# Get a user and policy
user = User.objects.get(email='alice@example.com')
policy = SecurityPolicy.objects.first()

# Create request context
request_ctx = RequestContext(
    auth_user=user,
    auth_uid=str(user.id),
    operation='read',
    is_admin=False,
)

# Create document context
doc = DSLDocument(
    id='doc-1',
    data={'title': 'Test', 'owner': str(user.id)},
    owner_id=str(user.id),
)

# Evaluate rule
engine = RuleEngine()
result = engine.check(policy.condition_json, request_ctx, doc)
print(f"Access allowed: {result}")
```

## Viewing Audit Logs

### Django Admin
Go to `/admin/rules/policyauditlog/` to see all evaluations.

### Python
```python
from rules.models import PolicyAuditLog

# Recent denials
denials = PolicyAuditLog.objects.filter(
    allowed=False
).order_by('-created_at')[:10]

for log in denials:
    print(f"{log.user.email} {log.operation} {log.collection}/{log.document_id}: {log.reason}")
```

### SQL
```sql
SELECT user_id, operation, collection, allowed, COUNT(*) as count
FROM rules_policy_audit_log
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY user_id, operation, collection, allowed
ORDER BY count DESC;
```

## Debugging Rules Not Working

### Check 1: Is the rule active?
```python
from rules.models import SecurityPolicy
policy = SecurityPolicy.objects.get(id='...')
print(f"Active: {policy.active}")  # Should be True
```

### Check 2: Is DocumentRules in permissions?
```python
# In your viewset
class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, DocumentRules]  # ← Required
```

### Check 3: Check audit logs
```python
from rules.models import PolicyAuditLog
logs = PolicyAuditLog.objects.filter(
    user__email='bob@example.com'
).order_by('-created_at')[:5]

for log in logs:
    print(f"Allowed: {log.allowed}, Reason: {log.reason}")
```

### Check 4: Manual evaluation
```python
from rules.permissions import DocumentRules
from rest_framework.test import APIRequestFactory

factory = APIRequestFactory()
request = factory.get('/documents/doc-id/')
request.user = user  # Attach user

permission = DocumentRules()
obj = document

# Manually check
allowed = permission.has_object_permission(request, None, obj)
print(f"Permission granted: {allowed}")
```

## Performance Tips

### High-Volume Scenarios
Use `DocumentRulesNoAudit` to skip audit logging:
```python
class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, DocumentRulesNoAudit]
```

### Rule Caching (Phase 2)
Future enhancement: cache frequently evaluated rules.

### Postgres RLS (Optional Hardening)
Enable database-level enforcement:
```python
from rules.postgres import enable_rls_on_table
enable_rls_on_table(table_name='core_document')
```

## Common Mistakes

❌ **Mistake 1**: Forgetting `auth_check` in conditions
```json
// Wrong: will allow unauthenticated access
{"operator": "and", "conditions": [{"type": "owner_check", ...}]}

// Right: check auth first
{"operator": "and", "conditions": [
  {"type": "auth_check", "value": {"op": "!=", "rhs": "null"}},
  {"type": "owner_check", ...}
]}
```

❌ **Mistake 2**: Using `==` instead of `!=` for auth check
```json
// Wrong: allows only if NOT authenticated
{"type": "auth_check", "value": {"op": "==", "rhs": "null"}}

// Right: allows if authenticated
{"type": "auth_check", "value": {"op": "!=", "rhs": "null"}}
```

❌ **Mistake 3**: Forgetting to set `active=True`
```python
# Rule won't be evaluated if active=False
policy.active = True
policy.save()
```

## FAQ

**Q: Can users see documents they can't access?**
A: No. The `DocumentViewSet.get_queryset()` respects permissions, so unauthorized documents are filtered out.

**Q: How fast are rule evaluations?**
A: Very fast (~1-5ms for typical rules). Complex rules with many conditions take longer. Use audit logs to profile.

**Q: Can I use rules across multiple collections?**
A: Phase 1 only supports per-collection rules. Phase 2 will add wildcard/collection-group rules.

**Q: What if a rule has a syntax error?**
A: The rule will fail to save (validation in `SecurityPolicy.clean()`). Check the error message in the admin.

**Q: Can rules call external APIs?**
A: No, Phase 1 rules are pure logic only. Phase 2 will add external data source queries.

**Q: How do I test rules before deploying?**
A: Use the Django shell to manually evaluate, or set `active=False` and toggle it later.

## Next Steps

1. ✅ Read: `rules/README.md` (comprehensive guide)
2. ✅ Create a custom rule via Django admin
3. ✅ Test access control via API
4. ✅ Check audit logs
5. ✅ Phase 2: Add cross-document rules, full DSL parser
