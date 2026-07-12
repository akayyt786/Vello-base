# Wires up PostgreSQL Row-Level Security for multi-tenant tables.
#
# No-op on SQLite (used for local dev/tests) since RLS is Postgres-only —
# this only takes effect when running against a real Postgres database.
#
# Depends on core.middleware.MultiTenantMiddleware / core.permissions setting
# the `app.current_project` session variable via `SET LOCAL` on every
# authorized request (see core/permissions.py:_set_rls_context). RLS here is
# a defense-in-depth layer beneath the application-level project-membership
# checks — even a bug in application code (or a raw SQL query) cannot leak
# rows across projects once this is enabled.

from django.db import migrations

# Tables inheriting core.models.MultiTenantModel (have a `project_id` column).
TENANT_TABLES = [
    'storage_file',
    'rules_security_policy',
    'functions_cloudfunction',
    'data_collection',
    'data_document',
]

CREATE_HELPER_FUNCTIONS_SQL = """
CREATE SCHEMA IF NOT EXISTS app_funcs;

CREATE OR REPLACE FUNCTION app_funcs.current_project()
RETURNS UUID AS $$
  SELECT NULLIF(current_setting('app.current_project', true), '')::UUID;
$$ LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION app_funcs.current_user()
RETURNS INTEGER AS $$
  SELECT NULLIF(current_setting('app.current_user', true), '')::INTEGER;
$$ LANGUAGE SQL STABLE;

GRANT USAGE ON SCHEMA app_funcs TO PUBLIC;
GRANT EXECUTE ON FUNCTION app_funcs.current_project() TO PUBLIC;
GRANT EXECUTE ON FUNCTION app_funcs.current_user() TO PUBLIC;
"""


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    schema_editor.execute(CREATE_HELPER_FUNCTIONS_SQL)

    for table in TENANT_TABLES:
        schema_editor.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')
        # FORCE is essential: without it, RLS does not apply to the table
        # owner — which is exactly the role Django's own connection uses.
        schema_editor.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY;')
        schema_editor.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (project_id = app_funcs.current_project())
            WITH CHECK (project_id = app_funcs.current_project());
        """)


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    for table in TENANT_TABLES:
        schema_editor.execute(f'DROP POLICY IF EXISTS tenant_isolation ON {table};')
        schema_editor.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_initial'),
        ('storage', '0001_initial'),
        ('rules', '0002_default_policies'),
        ('functions', '0001_initial'),
        ('data', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
