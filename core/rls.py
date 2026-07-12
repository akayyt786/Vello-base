"""
RLS context helper for code paths outside HTTP requests (Celery tasks,
management commands) that touch RLS-protected tenant tables.

Permission classes (core/permissions.py) set the same session variables
per-request, inside Django's ATOMIC_REQUESTS transaction. Celery tasks have
no such transaction, so this wraps the block in one explicitly.
"""

from contextlib import contextmanager

from django.db import connection, transaction


@contextmanager
def tenant_context(project_id, user_id=None):
    """
    Run a block of code with Postgres RLS session variables set so it can
    access RLS-protected tables scoped to one known project_id.

    No-op (still yields) on non-Postgres backends, since RLS doesn't apply.
    """
    if connection.vendor != 'postgresql':
        yield
        return

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL app.current_project = %s", [str(project_id)])
            if user_id is not None:
                cursor.execute("SET LOCAL app.current_user = %s", [str(user_id)])
        yield
