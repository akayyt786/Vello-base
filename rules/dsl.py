"""
Security Rules DSL: parser and evaluator.

Parses Firebase Security Rules syntax:
  "allow read if request.auth != null && resource.data.owner == request.auth.uid"

Evaluates rules against (request_user, doc, operation) context.
"""

import re
import logging
from typing import Optional, Any, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    """Context of the incoming request."""
    auth_user: Optional[Any]  # Django User object
    auth_uid: Optional[str]   # User ID as string
    operation: str             # 'read', 'write', 'delete'
    is_admin: bool = False

    @property
    def is_authenticated(self) -> bool:
        return self.auth_user is not None and self.auth_user.is_authenticated


@dataclass
class Document:
    """Document being accessed."""
    id: str
    data: Dict[str, Any]
    owner_id: Optional[str] = None

    def get_field(self, path: str) -> Any:
        """Get a nested field from the document using dot notation."""
        parts = path.split('.')
        value = self.data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value


class DSLParseError(Exception):
    """DSL parsing error."""
    pass


class RuleEngine:
    """
    Evaluates security rules against request + document context.

    Supports:
    1. Direct JSON condition evaluation (structured format)
    2. Simple text-based DSL parsing (Firebase-like syntax)
    """

    def __init__(self, enable_audit: bool = True):
        self.enable_audit = enable_audit

    def check(
        self,
        condition_json: Dict[str, Any],
        request: RequestContext,
        doc: Optional[Document] = None,
    ) -> bool:
        """
        Evaluate a condition against request + document.

        Args:
            condition_json: Condition tree from SecurityPolicy.condition_json
            request: RequestContext with auth info
            doc: Document being accessed (optional for some conditions)

        Returns:
            True if rule allows, False if denies
        """
        if not condition_json:
            # No condition = deny by default (fail-safe)
            return False

        return self._evaluate_condition(condition_json, request, doc)

    def _evaluate_condition(
        self,
        condition: Dict[str, Any],
        request: RequestContext,
        doc: Optional[Document],
    ) -> bool:
        """Recursively evaluate a condition tree."""
        if not isinstance(condition, dict):
            return False

        operator = condition.get('operator', 'and')
        conditions = condition.get('conditions', [])

        if operator == 'and':
            # All conditions must be true
            return all(self._evaluate_atomic(cond, request, doc) for cond in conditions)
        elif operator == 'or':
            # Any condition can be true
            return any(self._evaluate_atomic(cond, request, doc) for cond in conditions)
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False

    def _evaluate_atomic(
        self,
        condition: Dict[str, Any],
        request: RequestContext,
        doc: Optional[Document],
    ) -> bool:
        """Evaluate a single atomic condition."""
        cond_type = condition.get('type')

        if cond_type == 'auth_check':
            return self._eval_auth_check(condition.get('value', {}), request)
        elif cond_type == 'field_check':
            return self._eval_field_check(condition.get('value', {}), request, doc)
        elif cond_type == 'owner_check':
            return self._eval_owner_check(condition.get('value', {}), request, doc)
        elif cond_type == 'role_check':
            return self._eval_role_check(condition.get('value', {}), request)
        else:
            logger.warning(f"Unknown condition type: {cond_type}")
            return False

    def _eval_auth_check(self, value: Dict, request: RequestContext) -> bool:
        """
        Check request.auth conditions.

        Example: {"field": "request.auth", "op": "!=", "rhs": "null"}
        """
        field = value.get('field', 'request.auth')
        op = value.get('op', '!=')
        rhs = value.get('rhs', 'null')

        # Evaluate left-hand side
        if field == 'request.auth':
            lhs = request.auth_user if request.is_authenticated else None
        else:
            lhs = None

        # Compare
        if op == '!=':
            return (lhs is None) != (rhs == 'null')
        elif op == '==':
            return (lhs is None) == (rhs == 'null')
        elif op == 'exists':
            return lhs is not None
        else:
            logger.warning(f"Unknown auth_check operator: {op}")
            return False

    def _eval_field_check(
        self,
        value: Dict,
        request: RequestContext,
        doc: Optional[Document],
    ) -> bool:
        """
        Check document field conditions.

        Example: {"path": "data.owner", "op": "==", "rhs_field": "request.auth.uid"}
        or       {"path": "data.owner", "op": "==", "rhs": "123"}
        """
        if not doc:
            return False

        path = value.get('path', '')
        op = value.get('op', '==')

        # Get left-hand side
        lhs = doc.get_field(path)

        # Get right-hand side (from rhs_field or rhs)
        if 'rhs_field' in value:
            rhs_field = value['rhs_field']
            rhs = self._resolve_field(rhs_field, request, doc)
        else:
            rhs = value.get('rhs')

        # Compare
        return self._compare(lhs, op, rhs)

    def _eval_owner_check(
        self,
        value: Dict,
        request: RequestContext,
        doc: Optional[Document],
    ) -> bool:
        """
        Check if request user is the document owner.

        Example: {"field": "owner_id"}
        Checks if request.auth.uid == doc.owner_id
        """
        if not doc or not request.is_authenticated:
            return False

        field = value.get('field', 'owner_id')
        owner_id = doc.get_field(field)

        return request.auth_uid == str(owner_id)

    def _eval_role_check(self, value: Dict, request: RequestContext) -> bool:
        """
        Check user's project role.

        Example: {"role": "admin"} or {"role": ["admin", "editor"]}
        Requires request user to be staff (admin) or have specific role.
        """
        if not request.is_authenticated:
            return False

        # For Phase 1, check Django user.is_staff for admin
        if request.is_admin:
            return True

        # More complex role checks would query ProjectMembership
        # For now, just check is_admin flag
        return False

    def _resolve_field(
        self,
        field_expr: str,
        request: RequestContext,
        doc: Optional[Document],
    ) -> Any:
        """Resolve a field expression like 'request.auth.uid' or 'resource.data.owner'."""
        if field_expr.startswith('request.auth.'):
            attr = field_expr.replace('request.auth.', '')
            if attr == 'uid':
                return request.auth_uid
            else:
                # Could be custom claim like request.auth.admin
                if request.auth_user and hasattr(request.auth_user, 'profile'):
                    claims = request.auth_user.profile.custom_claims or {}
                    return claims.get(attr)
        elif field_expr.startswith('resource.data.') or field_expr.startswith('data.'):
            path = field_expr.replace('resource.data.', '').replace('data.', '')
            if doc:
                return doc.get_field(path)
        return None

    def _compare(self, lhs: Any, op: str, rhs: Any) -> bool:
        """Compare two values."""
        if op == '==':
            return lhs == rhs
        elif op == '!=':
            return lhs != rhs
        elif op == '<':
            return (lhs is not None and rhs is not None) and lhs < rhs
        elif op == '<=':
            return (lhs is not None and rhs is not None) and lhs <= rhs
        elif op == '>':
            return (lhs is not None and rhs is not None) and lhs > rhs
        elif op == '>=':
            return (lhs is not None and rhs is not None) and lhs >= rhs
        elif op == 'in':
            # rhs should be a list
            if isinstance(rhs, (list, tuple)):
                return lhs in rhs
            return False
        elif op == 'contains':
            # lhs should contain rhs
            if isinstance(lhs, (list, tuple)):
                return rhs in lhs
            elif isinstance(lhs, str):
                return rhs in lhs
            return False
        elif op == 'matches':
            # String regex match
            if isinstance(lhs, str) and isinstance(rhs, str):
                try:
                    return re.match(rhs, lhs) is not None
                except Exception:
                    return False
            return False
        else:
            logger.warning(f"Unknown comparison operator: {op}")
            return False


class DSLParser:
    """
    Parse Firebase Security Rules DSL into condition JSON.

    Example input:
      "allow read if request.auth != null && resource.data.owner == request.auth.uid"

    Output:
      {
        "operator": "and",
        "conditions": [
          {"type": "auth_check", "value": {"field": "request.auth", "op": "!=", "rhs": "null"}},
          {"type": "field_check", "value": {"path": "data.owner", "op": "==", "rhs_field": "request.auth.uid"}}
        ]
      }

    Note: This is a simplified parser for Phase 1. A full Firebase-compatible parser
    would handle CEL expressions more comprehensively.
    """

    # Patterns
    EXPR_PATTERN = re.compile(
        r'(?P<field>request\.auth\.\w+|data\.\w+|resource\.data\.\w+)\s*'
        r'(?P<op>==|!=|<|<=|>|>=|in|contains|matches)\s*'
        r'(?P<rhs>null|true|false|\d+|[\w\.]+|"[^"]*")'
    )

    def __init__(self):
        self.engine = RuleEngine()

    def parse(self, rule_str: str) -> Dict[str, Any]:
        """
        Parse a simple rule string.

        Args:
            rule_str: Rule string like "request.auth != null && data.owner == request.auth.uid"

        Returns:
            Condition JSON dict
        """
        # Simple tokenization by && (and) and || (or)
        # This is a basic parser; a production implementation would use a full expression parser

        if not rule_str:
            return {"operator": "and", "conditions": []}

        # Split on && and ||
        and_parts = [p.strip() for p in rule_str.split('&&')]
        conditions = []

        for part in and_parts:
            or_parts = [p.strip() for p in part.split('||')]
            for expr in or_parts:
                expr_cond = self._parse_expression(expr)
                if expr_cond:
                    conditions.append(expr_cond)

        return {
            "operator": "and",
            "conditions": conditions if conditions else []
        }

    def _parse_expression(self, expr: str) -> Optional[Dict[str, Any]]:
        """Parse a single expression."""
        expr = expr.strip()

        # Check for auth conditions
        if 'request.auth' in expr:
            return self._parse_auth_expr(expr)

        # Check for field conditions
        if 'data.' in expr or 'resource.data.' in expr:
            return self._parse_field_expr(expr)

        return None

    def _parse_auth_expr(self, expr: str) -> Optional[Dict[str, Any]]:
        """Parse request.auth expressions."""
        # Pattern: request.auth op value
        match = re.search(
            r'request\.auth\s*(?P<op>!=|==|exists)\s*(?P<value>null|true|false)',
            expr
        )
        if match:
            return {
                "type": "auth_check",
                "value": {
                    "field": "request.auth",
                    "op": match.group('op'),
                    "rhs": match.group('value')
                }
            }
        return None

    def _parse_field_expr(self, expr: str) -> Optional[Dict[str, Any]]:
        """Parse data.* field expressions."""
        # Pattern: data.field op value or data.field op request.auth.uid
        match = re.search(
            r'(?P<path>(?:resource\.)?data\.\w+)\s*'
            r'(?P<op>==|!=|<|<=|>|>=|in|contains|matches)\s*'
            r'(?P<rhs>request\.auth\.\w+|null|true|false|\d+|[\w\.]+|"[^"]*")',
            expr
        )
        if match:
            path = match.group('path').replace('resource.', '')
            op = match.group('op')
            rhs = match.group('rhs')

            # Check if rhs is a field reference
            if rhs.startswith('request.'):
                return {
                    "type": "field_check",
                    "value": {
                        "path": path,
                        "op": op,
                        "rhs_field": rhs
                    }
                }
            else:
                # Clean up string values
                if rhs.startswith('"') and rhs.endswith('"'):
                    rhs = rhs[1:-1]

                return {
                    "type": "field_check",
                    "value": {
                        "path": path,
                        "op": op,
                        "rhs": rhs
                    }
                }
        return None
