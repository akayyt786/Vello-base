"""
Query parser: Convert Firebase-style query params to Django ORM Q objects.
Supports: where, orderBy, limit, cursor-based pagination.
"""

from django.db.models import Q, F
from datetime import datetime
from typing import List, Dict, Any, Tuple


class QueryParser:
    """
    Parse Firestore-style queries into Django ORM filters.

    Supported operators:
    - Comparison: ==, !=, <, <=, >, >=
    - Membership: in, not-in, array-contains, array-contains-any
    """

    # Mapping of Firestore operators to Django ORM lookup suffixes
    OPERATOR_MAPPING = {
        '==': 'exact',
        '!=': 'exact',  # handled separately with Q object negation
        '<': 'lt',
        '<=': 'lte',
        '>': 'gt',
        '>=': 'gte',
        'in': 'in',
        'not-in': 'in',  # handled separately with Q object negation
        'array-contains': 'contains',
        'array-contains-any': 'overlap',  # PostgreSQL array overlap
    }

    @staticmethod
    def parse_where(conditions: List[Dict[str, Any]]) -> Q:
        """
        Parse WHERE conditions and return a Q object for Django ORM.

        Input:
            [
                {'field': 'status', 'op': '==', 'value': 'active'},
                {'field': 'age', 'op': '>', 'value': 18},
                {'field': 'tags', 'op': 'array-contains', 'value': 'admin'}
            ]

        Output:
            Q(data__status='active') & Q(data__age__gt=18) & Q(data__tags__contains=['admin'])

        Args:
            conditions: List of filter dicts with 'field', 'op', 'value'

        Returns:
            Combined Q object for filtering

        Raises:
            ValueError: If operator is unsupported or condition format is invalid
        """
        if not conditions:
            return Q()

        q = Q()
        for condition in conditions:
            field = condition.get('field')
            op = condition.get('op')
            value = condition.get('value')

            if not field or op not in QueryParser.OPERATOR_MAPPING:
                raise ValueError(
                    f"Invalid condition: field='{field}', op='{op}'. "
                    f"Valid ops: {list(QueryParser.OPERATOR_MAPPING.keys())}"
                )

            # Build the JSONB field path: data->>'field_name' for string comparison
            # Use data->'field_name' for JSON/array/object operations
            if op in ['array-contains', 'array-contains-any', 'in', 'not-in']:
                # Array/list operations: use data->>'field' or data->'field'
                lookup_key = f"data__{field}"
            else:
                # Scalar operations: use data->>'field' (string extraction)
                lookup_key = f"data__{field}"

            django_op = QueryParser.OPERATOR_MAPPING[op]

            if op == '!=':
                # NOT EQUAL: use Q negation
                q &= ~Q(**{f"{lookup_key}__{django_op}": value})
            elif op == 'not-in':
                # NOT IN: use Q negation
                q &= ~Q(**{f"{lookup_key}__{django_op}": value})
            elif op == 'array-contains':
                # ARRAY CONTAINS: for JSONB arrays, check if value is in array
                # PostgreSQL: data->'field' @> to_jsonb(value)
                # Django ORM: data__field__contains translates to @> operator
                q &= Q(**{f"{lookup_key}__{django_op}": [value]})
            elif op == 'array-contains-any':
                # ARRAY CONTAINS ANY: check if any value from list is in document array
                # PostgreSQL: data->'field' ?| ARRAY[...]
                # Django ORM: data__field__overlap translates to ?| for arrays
                if not isinstance(value, list):
                    value = [value]
                q &= Q(**{f"{lookup_key}__{django_op}": value})
            else:
                # Standard comparison: ==, <, <=, >, >=, in
                q &= Q(**{f"{lookup_key}__{django_op}": value})

        return q

    @staticmethod
    def parse_order_by(specs: List[Dict[str, str]]) -> List[str]:
        """
        Parse ORDER BY specs into Django ORM order_by() arguments.

        Input:
            [
                {'field': 'created_at', 'direction': 'desc'},
                {'field': 'name', 'direction': 'asc'}
            ]

        Output:
            ['-data__created_at', 'data__name']

        Args:
            specs: List of sort specs with 'field' and optional 'direction' ('asc'/'desc')

        Returns:
            List of order_by field strings
        """
        if not specs:
            return []

        order_fields = []
        for spec in specs:
            field = spec.get('field', '').strip()
            direction = spec.get('direction', 'asc').lower()

            if not field:
                raise ValueError("Order spec missing 'field'")
            if direction not in ['asc', 'desc']:
                raise ValueError(f"Direction must be 'asc' or 'desc', got '{direction}'")

            # For JSONB fields: use data->>'field'
            # Prefix with '-' for DESC
            prefix = '-' if direction == 'desc' else ''
            order_fields.append(f"{prefix}data__{field}")

        return order_fields

    @staticmethod
    def parse_cursor(cursor: str, order_by_fields: List[str], queryset) -> Tuple[Q, Any]:
        """
        Parse cursor (document ID) for keyset pagination.

        Firestore uses document snapshots as cursors (immutable).
        We use document IDs as simple cursors here; production would use full snapshot encoding.

        Args:
            cursor: Document ID (UUID or doc_id) to start after
            order_by_fields: List of order_by field specs
            queryset: Django queryset to fetch pivot document from

        Returns:
            Tuple of (Q object for cursor filter, pivot document)

        Raises:
            ValueError: If cursor document not found
        """
        if not cursor:
            return Q(), None

        try:
            # Fetch the pivot document
            pivot = queryset.filter(id=cursor).first()
            if not pivot:
                # Try by doc_id if UUID fails
                pivot = queryset.filter(doc_id=cursor).first()
            if not pivot:
                raise ValueError(f"Cursor document '{cursor}' not found")
        except Exception as e:
            raise ValueError(f"Error fetching cursor document: {e}")

        # Build cursor filter: order by field > pivot value
        # For cursor-based pagination, we use the first sort field
        if order_by_fields and len(order_by_fields) > 0:
            # Strip '-' prefix to get field name
            sort_field = order_by_fields[0].lstrip('-')
            pivot_value = pivot.data.get(sort_field.split('__')[-1])  # Extract field name from 'data__field'

            if pivot_value is not None:
                # Filter: field > pivot_value (handles DESC automatically via ordering)
                return Q(**{f"{sort_field}__gt": pivot_value}), pivot

        return Q(), pivot


def apply_filters_to_queryset(queryset, where: List[Dict] = None, order_by: List[Dict] = None,
                              limit: int = None, cursor: str = None) -> Tuple:
    """
    Apply query parameters to a queryset and return filtered queryset + count.

    Args:
        queryset: Base Django queryset
        where: List of WHERE conditions
        order_by: List of ORDER BY specs
        limit: Max documents to return
        cursor: Cursor (doc ID) for pagination

    Returns:
        Tuple of (filtered queryset, total count, cursor info)

    Raises:
        ValueError: If query is invalid
    """
    # Parse WHERE
    try:
        q_where = QueryParser.parse_where(where or [])
        queryset = queryset.filter(q_where)
    except ValueError as e:
        raise ValueError(f"Invalid WHERE clause: {e}")

    # Parse ORDER BY
    try:
        order_fields = QueryParser.parse_order_by(order_by or [])
        if order_fields:
            queryset = queryset.order_by(*order_fields)
    except ValueError as e:
        raise ValueError(f"Invalid ORDER BY clause: {e}")

    # Apply cursor pagination if provided
    if cursor:
        try:
            q_cursor, pivot = QueryParser.parse_cursor(cursor, order_fields, queryset)
            queryset = queryset.filter(q_cursor)
        except ValueError as e:
            raise ValueError(f"Invalid cursor: {e}")

    # Count before limiting
    total_count = queryset.count()

    # Apply limit
    if limit:
        queryset = queryset[:limit]

    return queryset, total_count
