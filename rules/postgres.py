"""
Postgres Row-Level Security (RLS) integration.

When a SecurityPolicy is created/updated, generates and applies RLS policies
to the Postgres database. This enforces rules at the database level in addition
to application-level checks.

Example policy:
  CREATE POLICY "doc_owner_read" ON documents
    FOR SELECT
    USING (
      auth.uid() IS NOT NULL AND
      (data->>'owner') = auth.uid()::TEXT
    );
"""

import logging
from typing import Optional, Dict, Any
from django.db import connection, transaction
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class RLSPolicyBuilder:
    """Build SQL RLS policies from SecurityPolicy objects."""

    def __init__(self, table_name: str = "documents"):
        self.table_name = table_name

    def build_policy_name(
        self,
        project_id: str,
        collection: str,
        rule_type: str,
        policy_id: str,
    ) -> str:
        """Generate a unique policy name."""
        # Truncate to 63 chars (Postgres identifier limit)
        name = f"{collection}_{rule_type}_{policy_id[:8]}"
        return name[:63]

    def build_policy_sql(
        self,
        policy_name: str,
        rule_type: str,
        where_clause: str,
    ) -> str:
        """
        Generate a CREATE POLICY statement.

        Args:
            policy_name: Unique policy name
            rule_type: 'read', 'write', 'delete'
            where_clause: SQL USING/WITH CHECK clause

        Returns:
            SQL statement
        """
        if rule_type == "read":
            return f"""
            CREATE POLICY "{policy_name}" ON {self.table_name}
            FOR SELECT
            USING ({where_clause});
            """
        elif rule_type == "write":
            return f"""
            CREATE POLICY "{policy_name}" ON {self.table_name}
            FOR INSERT WITH CHECK ({where_clause});
            """
        elif rule_type == "delete":
            return f"""
            CREATE POLICY "{policy_name}" ON {self.table_name}
            FOR DELETE
            USING ({where_clause});
            """
        else:
            raise ValueError(f"Unknown rule_type: {rule_type}")

    def condition_to_sql(self, condition_json: Dict[str, Any]) -> Optional[str]:
        """
        Convert a condition tree to SQL WHERE clause.

        This is a simplified converter that handles common patterns.
        For complex conditions, manual SQL may be needed.

        Example condition:
          {
            "operator": "and",
            "conditions": [
              {"type": "auth_check", "value": {"op": "!=", "rhs": "null"}},
              {"type": "field_check", "value": {"path": "data.owner", "op": "==", "rhs_field": "request.auth.uid"}}
            ]
          }

        Returns:
          "auth.uid() IS NOT NULL AND (data->>'owner') = auth.uid()::TEXT"
        """
        if not condition_json:
            return None

        operator = condition_json.get("operator", "and")
        conditions = condition_json.get("conditions", [])

        sql_parts = []
        for cond in conditions:
            sql = self._condition_to_sql(cond)
            if sql:
                sql_parts.append(sql)

        if not sql_parts:
            return None

        if operator == "and":
            return " AND ".join(f"({part})" for part in sql_parts)
        elif operator == "or":
            return " OR ".join(f"({part})" for part in sql_parts)
        else:
            return None

    def _condition_to_sql(self, condition: Dict[str, Any]) -> Optional[str]:
        """Convert a single condition to SQL."""
        cond_type = condition.get("type")

        if cond_type == "auth_check":
            return self._auth_check_to_sql(condition.get("value", {}))
        elif cond_type == "field_check":
            return self._field_check_to_sql(condition.get("value", {}))
        elif cond_type == "owner_check":
            return self._owner_check_to_sql(condition.get("value", {}))
        elif cond_type == "role_check":
            # Role checks are harder in SQL; would need role lookup
            # For now, just check if user is staff (admins bypass RLS anyway)
            return None
        else:
            return None

    def _auth_check_to_sql(self, value: Dict) -> Optional[str]:
        """Convert auth_check to SQL."""
        op = value.get("op", "!=")
        rhs = value.get("rhs", "null")

        if rhs == "null":
            if op == "!=":
                return "auth.uid() IS NOT NULL"
            elif op == "==":
                return "auth.uid() IS NULL"
        return None

    def _field_check_to_sql(self, value: Dict) -> Optional[str]:
        """Convert field_check to SQL."""
        path = value.get("path", "")
        op = value.get("op", "==")
        rhs_field = value.get("rhs_field")
        rhs = value.get("rhs")

        if not path:
            return None

        # Convert path to JSONB accessor
        # "data.owner" -> (data->>'owner')
        json_accessor = self._path_to_json_accessor(path)

        if rhs_field:
            # Resolve rhs_field
            rhs_sql = self._field_to_sql_value(rhs_field)
            if not rhs_sql:
                return None
        else:
            rhs_sql = self._literal_to_sql(rhs)

        # Build comparison
        return self._build_comparison(json_accessor, op, rhs_sql)

    def _owner_check_to_sql(self, value: Dict) -> Optional[str]:
        """Convert owner_check to SQL."""
        field = value.get("field", "owner_id")
        json_accessor = self._path_to_json_accessor(f"data.{field}")
        return f"{json_accessor} = auth.uid()::TEXT"

    def _path_to_json_accessor(self, path: str) -> str:
        """Convert dot notation path to Postgres JSONB accessor."""
        # Remove 'data.' prefix if present
        path = path.replace("data.", "")
        parts = path.split(".")

        if len(parts) == 1:
            # Simple field: data->'key'
            return f"(data->>'{parts[0]}')"
        else:
            # Nested: data->'key1'->'key2'
            accessor = "data"
            for i, part in enumerate(parts[:-1]):
                accessor += f"->'{part}'"
            accessor += f"->>'{parts[-1]}'"
            return f"({accessor})"

    def _field_to_sql_value(self, field_expr: str) -> Optional[str]:
        """Convert a field reference to SQL value."""
        if field_expr == "request.auth.uid":
            return "auth.uid()::TEXT"
        elif field_expr.startswith("request.auth."):
            # Custom claim; would need to look up from JWT
            # For Phase 1, not supported
            return None
        else:
            return None

    def _literal_to_sql(self, value: Any) -> str:
        """Convert a literal value to SQL."""
        if value is None or value == "null":
            return "NULL"
        elif value == "true":
            return "true"
        elif value == "false":
            return "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # Escape single quotes
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        else:
            return f"'{value}'"

    def _build_comparison(self, lhs: str, op: str, rhs: str) -> str:
        """Build a comparison expression."""
        if op == "==":
            return f"{lhs} = {rhs}"
        elif op == "!=":
            return f"{lhs} != {rhs}"
        elif op == "<":
            return f"{lhs} < {rhs}"
        elif op == "<=":
            return f"{lhs} <= {rhs}"
        elif op == ">":
            return f"{lhs} > {rhs}"
        elif op == ">=":
            return f"{lhs} >= {rhs}"
        elif op == "in":
            return f"{lhs} = ANY({rhs}::TEXT[])"
        elif op == "contains":
            return f"{lhs} LIKE {rhs}"
        else:
            return f"{lhs} = {rhs}"


def apply_rls_policy(
    project_id: str,
    collection: str,
    rule_type: str,
    policy_id: str,
    condition_json: Dict[str, Any],
    table_name: str = "documents",
) -> bool:
    """
    Apply an RLS policy to the database.

    Args:
        project_id: Project UUID
        collection: Collection name
        rule_type: 'read', 'write', 'delete'
        policy_id: Policy UUID
        condition_json: Condition tree
        table_name: Postgres table name

    Returns:
        True if successful, False otherwise
    """
    builder = RLSPolicyBuilder(table_name)

    try:
        policy_name = builder.build_policy_name(project_id, collection, rule_type, str(policy_id))
        where_clause = builder.condition_to_sql(condition_json)

        if not where_clause:
            logger.warning(
                f"Could not convert condition_json to SQL for {collection}:{rule_type}. "
                "Policy will not be applied. Manual SQL may be needed."
            )
            return False

        policy_sql = builder.build_policy_sql(policy_name, rule_type, where_clause)

        with connection.cursor() as cursor:
            cursor.execute(policy_sql)
            logger.info(f"Applied RLS policy: {policy_name}")

        return True

    except Exception as e:
        logger.error(f"Failed to apply RLS policy: {e}")
        return False


def drop_rls_policy(
    policy_id: str,
    collection: str,
    rule_type: str,
    table_name: str = "documents",
) -> bool:
    """
    Drop an RLS policy from the database.

    Args:
        policy_id: Policy UUID
        collection: Collection name
        rule_type: 'read', 'write', 'delete'
        table_name: Postgres table name

    Returns:
        True if successful, False otherwise
    """
    builder = RLSPolicyBuilder(table_name)

    try:
        # Reconstruct the policy name (must match apply_rls_policy)
        policy_name = f"{collection}_{rule_type}_{str(policy_id)[:8]}"

        drop_sql = f'DROP POLICY IF EXISTS "{policy_name}" ON {table_name};'

        with connection.cursor() as cursor:
            cursor.execute(drop_sql)
            logger.info(f"Dropped RLS policy: {policy_name}")

        return True

    except Exception as e:
        logger.error(f"Failed to drop RLS policy: {e}")
        return False


def enable_rls_on_table(table_name: str = "documents") -> bool:
    """
    Enable Row-Level Security on a table.
    This must be done before applying any policies.

    Args:
        table_name: Postgres table name

    Returns:
        True if successful, False otherwise
    """
    try:
        with connection.cursor() as cursor:
            # Enable RLS
            cursor.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;")

            # Default deny policy (for safety)
            cursor.execute(
                f"""
                CREATE POLICY "default_deny" ON {table_name}
                USING (FALSE);
                """
            )
            logger.info(f"Enabled RLS on table: {table_name}")

        return True

    except Exception as e:
        logger.error(f"Failed to enable RLS on {table_name}: {e}")
        return False


def disable_rls_on_table(table_name: str = "documents") -> bool:
    """
    Disable Row-Level Security on a table.
    Warning: disables all policies.

    Args:
        table_name: Postgres table name

    Returns:
        True if successful, False otherwise
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")
            logger.info(f"Disabled RLS on table: {table_name}")

        return True

    except Exception as e:
        logger.error(f"Failed to disable RLS on {table_name}: {e}")
        return False
