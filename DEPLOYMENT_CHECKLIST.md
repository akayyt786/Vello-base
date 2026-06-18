# Security Rules Implementation — Deployment Checklist

## Pre-Deployment

- [ ] All Python files compile without syntax errors
  ```bash
  python3 -m py_compile rules/*.py
  ```

- [ ] Settings.py has 'rules' in INSTALLED_APPS
  ```bash
  grep -n "rules" ownfirebase/settings.py
  ```

- [ ] All migration files exist and are valid
  ```bash
  ls -la rules/migrations/
  ls -la core/migrations/0002_*.py
  ```

- [ ] Test suite passes
  ```bash
  pytest tests/test_rules.py -v
  ```

- [ ] No import errors in modules
  ```bash
  python manage.py shell
  >>> from rules.models import SecurityPolicy
  >>> from rules.dsl import RuleEngine
  >>> from rules.permissions import DocumentRules
  >>> print("All imports OK")
  ```

## Deployment Steps

### Step 1: Database Migrations
```bash
# Review migration plan
python manage.py migrate --plan rules

# Review migration plan for core.Document
python manage.py migrate --plan core

# Run migrations (creates tables)
python manage.py migrate
```

### Step 2: Verify Database Tables
```bash
python manage.py dbshell
```

In the database shell, verify tables exist:
```sql
-- Check tables were created
\dt rules_security_policy
\dt rules_policy_audit_log
\dt core_document

-- Verify indexes
\di rules_secu*
\di core_docume*

-- Check default policies were seeded
SELECT COUNT(*) FROM rules_security_policy;
-- Should return > 0 if projects exist
```

### Step 3: Admin Interface Verification
```bash
# Start Django admin
python manage.py runserver

# Navigate to http://localhost:8000/admin/
# Verify you can see:
#   - Security Policies (Rules → Security Policy)
#   - Policy Audit Logs (Rules → Policy Audit Logs)
#   - Documents (Core → Documents)
```

### Step 4: API Verification
```bash
# Create test project
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123",
    "password_confirm": "TestPassword123"
  }'

# Login and get token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPassword123"}' \
  | jq -r '.access')

# Create a project
PROJECT=$(curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "slug": "test-project"}' \
  | jq -r '.id')

# Create a document
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "'$PROJECT'",
    "collection": "documents",
    "data": {"title": "Test Document"}
  }'

# Should succeed with 201 Created
```

### Step 5: Rule Enforcement Verification
```bash
# Create two test users
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "Password123",
    "password_confirm": "Password123"
  }'

curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bob@example.com",
    "password": "Password123",
    "password_confirm": "Password123"
  }'

# Login as Alice and create project
TOKEN_A=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "Password123"}' \
  | jq -r '.access')

PROJECT=$(curl -s -X POST http://localhost:8000/api/v1/projects/ \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "slug": "test"}' \
  | jq -r '.id')

# Alice creates document
DOC=$(curl -s -X POST http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{
    "project": "'$PROJECT'",
    "collection": "documents",
    "data": {"title": "Alice Doc"}
  }' \
  | jq -r '.id')

# Login as Bob
TOKEN_B=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "password": "Password123"}' \
  | jq -r '.access')

# Add Bob to Alice's project
curl -s -X POST http://localhost:8000/api/v1/projects/$PROJECT/invite_member/ \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "role": "viewer"}'

# Bob tries to modify Alice's document (should fail with 403)
curl -X PATCH http://localhost:8000/api/v1/documents/$DOC/ \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{"data": {"title": "Bob Hacked It"}}'

# Expected Response: 403 Forbidden
# If you get 200, rules are NOT being enforced - CHECK PERMISSIONS CLASS
```

### Step 6: Audit Log Verification
```python
# In Django shell:
python manage.py shell

from rules.models import PolicyAuditLog
from django.utils import timezone
from datetime import timedelta

# Check recent audit logs
recent = PolicyAuditLog.objects.filter(
    created_at__gte=timezone.now() - timedelta(minutes=5)
).order_by('-created_at')

for log in recent:
    print(f"{log.user.email} {log.operation} {log.document_id}: {log.allowed}")

# Should see entries for:
#   - alice@example.com write documents/...: True (allowed)
#   - bob@example.com write documents/...: False (denied)
```

## Post-Deployment

- [ ] Backup database (production environments)
  ```bash
  pg_dump -U postgres dbname > backup_$(date +%Y%m%d).sql
  ```

- [ ] Monitor logs for errors
  ```bash
  tail -f /var/log/django/error.log
  # Look for: rules, RuleEngine, DocumentRules
  ```

- [ ] Set up audit log retention policy
  ```python
  # Create management command or Celery task
  from django.utils import timezone
  from datetime import timedelta
  from rules.models import PolicyAuditLog
  
  cutoff = timezone.now() - timedelta(days=30)
  deleted, _ = PolicyAuditLog.objects.filter(created_at__lt=cutoff).delete()
  print(f"Deleted {deleted} audit logs")
  ```

- [ ] Enable monitoring/alerting for 403 errors
  ```bash
  # Monitor denied rule evaluations
  SELECT COUNT(*) FROM rules_policy_audit_log
  WHERE allowed=false AND created_at > NOW() - INTERVAL '1 hour';
  ```

- [ ] Document custom rules configuration
  ```bash
  # Export current rules
  python manage.py dumpdata rules.securitypolicy > rules_backup.json
  ```

## Rollback Plan

If issues occur post-deployment:

### Option 1: Disable Rules (Quick Rollback)
```python
# Set all security policies to inactive
from rules.models import SecurityPolicy
SecurityPolicy.objects.all().update(active=False)
```

### Option 2: Revert Migrations
```bash
python manage.py migrate rules zero      # Remove all rules migrations
python manage.py migrate core 0001       # Revert Document model
```

### Option 3: Database Restore
```bash
# Restore from backup
psql -U postgres dbname < backup_20260618.sql
```

## Troubleshooting During Deployment

### Issue: Migration fails with "table already exists"
**Solution:**
```bash
python manage.py migrate rules --fake-initial
python manage.py migrate core 0001 --fake
python manage.py migrate core 0002
```

### Issue: Permission class not being called
**Check:**
1. DocumentViewSet has `permission_classes = [..., DocumentRules]`
2. 'rules' is in INSTALLED_APPS
3. App is installed: `python manage.py check rules`

### Issue: All requests return 403 (rules too strict)
**Check:**
1. Default policies were seeded: `SecurityPolicy.objects.count()`
2. Rules are active: `SecurityPolicy.objects.filter(active=True).count()`
3. Check audit logs: PolicyAuditLog shows what's being denied

### Issue: Audit logs not being created
**Check:**
1. `DocumentRules` permission class is used (not `DocumentRulesNoAudit`)
2. Table exists: `SELECT COUNT(*) FROM rules_policy_audit_log;`
3. Logging level is DEBUG or INFO (not ERROR)

## Performance Verification

```python
import time
from rules.permissions import DocumentRules
from rest_framework.test import APIRequestFactory

factory = APIRequestFactory()
perm = DocumentRules()

# Time a permission check
start = time.time()
for _ in range(100):
    perm.has_object_permission(request, view, obj)
elapsed = time.time() - start

print(f"100 checks: {elapsed:.2f}s ({elapsed/100*1000:.2f}ms each)")
# Should be < 10ms per check (typical: 1-5ms)
```

## Sign-Off Checklist

- [ ] All migrations applied successfully
- [ ] Database tables verified to exist
- [ ] Admin interface working
- [ ] API endpoints responding
- [ ] Rule enforcement verified (403 Forbidden on denied access)
- [ ] Audit logs capturing evaluations
- [ ] No error logs in Django logging
- [ ] Performance acceptable (< 50ms per request)
- [ ] Rollback procedure tested
- [ ] Team trained on admin interface
- [ ] Documentation accessible to team
- [ ] Monitoring configured

## Maintenance Tasks

### Daily
- [ ] Monitor error logs for rule evaluation failures
- [ ] Check for unusual audit log patterns

### Weekly
- [ ] Review audit logs for access patterns
- [ ] Check database size (audit logs growing too large?)
- [ ] Update documentation with new rule examples

### Monthly
- [ ] Prune old audit logs (retention policy)
- [ ] Review performance metrics
- [ ] Backup rules configuration
- [ ] Test rollback procedure

### Quarterly
- [ ] Audit all active rules for correctness
- [ ] Review permissions for all users/projects
- [ ] Plan Phase 2 enhancements
- [ ] Update security policy documentation

## References

- Full documentation: `/rules/README.md`
- Quick start: `/rules/QUICK_START.md`
- Architecture: `/RULES_IMPLEMENTATION.md`
- Tests: `/tests/test_rules.py`
