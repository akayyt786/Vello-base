# Data API: Firestore-like Document Database

This module implements a Firestore-compatible document database API on top of Django + PostgreSQL. It provides Collections, Documents, Queries, and atomic Transactions.

## Architecture

### Models

#### Collection
- **Name**: Collection name (e.g., "users", "posts")
- **Path**: Full hierarchical path supporting subcollections (e.g., "users/alice/posts")
- **Schema**: Optional metadata for admin console
- **Document Count**: Cache of document count per collection

#### Document
- **Collection Path**: Parent collection path (e.g., "users", "users/alice/posts")
- **Doc ID**: Document ID within collection (e.g., "alice", "post1")
- **Data**: JSONB field storing arbitrary nested document data
- **__v**: Version counter for optimistic locking
- **Created/Updated At**: Automatic timestamps

### Query Engine

The `query_parser.py` module converts Firestore-style query parameters to Django ORM Q objects:

```python
# Input
where = [
    {'field': 'status', 'op': '==', 'value': 'active'},
    {'field': 'age', 'op': '>', 'value': 18}
]
order_by = [
    {'field': 'created_at', 'direction': 'desc'}
]
limit = 20

# Output
Q(data__status='active') & Q(data__age__gt=18)
-> .order_by('-data__created_at')[:20]
```

### Indexes

- **GIN Index on data column**: For JSONB containment queries
- **Expression indexes**: Created via migrations for commonly queried fields

## API Endpoints

### Collections

#### List Collections
```
GET /api/projects/{project_id}/collections/
```

Query params:
- `skip=0`: Offset for pagination
- `limit=50`: Max collections to return

Response:
```json
{
  "collections": [
    {
      "id": "uuid",
      "name": "users",
      "path": "users",
      "schema": {},
      "document_count": 42,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 5,
  "skip": 0,
  "limit": 50
}
```

#### Create Collection
```
POST /api/projects/{project_id}/collections/
```

Request:
```json
{
  "name": "users",
  "path": "users",
  "schema": {
    "fields": {
      "email": {"type": "string", "indexed": true},
      "age": {"type": "number"}
    }
  }
}
```

### Documents

#### List Documents
```
GET /api/projects/{project_id}/collections/{collection}/docs/
```

Query params (via JSON):
- `query={"where": [...], "order_by": [...], "limit": 20, "start_after": "doc-id"}`

OR simple params:
- `where_{field}=value`: Simple equality filter
- `orderBy_{field}=asc|desc`: Order by field
- `limit=20`: Max documents
- `startAfter=doc-id`: Cursor pagination

Response:
```json
{
  "documents": [
    {
      "id": "uuid",
      "collection_path": "users",
      "doc_id": "alice",
      "data": {
        "name": "Alice",
        "age": 30,
        "tags": ["admin", "beta"],
        "address": {"city": "NYC"}
      },
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "__v": 1
    }
  ],
  "count": 42,
  "limit": 20,
  "next_cursor": "uuid-of-last-doc"
}
```

#### Create Document
```
POST /api/projects/{project_id}/collections/{collection}/docs/
```

Request:
```json
{
  "doc_id": "alice",
  "data": {
    "name": "Alice",
    "age": 30,
    "tags": ["admin"],
    "address": {"city": "NYC", "zip": "10001"}
  }
}
```

If `doc_id` is omitted, a UUID is auto-generated.

#### Get Document
```
GET /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/
```

#### Update Document (Merge)
```
PATCH /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/
```

Request:
```json
{
  "data": {
    "age": 31
  },
  "__v": 1
}
```

- `data` is merged with existing data (shallow merge)
- `__v` is optional; if provided, version conflict returns 409
- `__v` is auto-incremented on update

#### Replace Document
```
PUT /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/
```

Request:
```json
{
  "data": {
    "name": "Alice",
    "age": 31
  }
}
```

Replaces entire document data.

#### Delete Document
```
DELETE /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/
```

### Transactions

#### Atomic Batch Write
```
POST /api/projects/{project_id}/transaction/
```

Request:
```json
{
  "writes": [
    {
      "op": "set",
      "path": "users/alice",
      "data": {"name": "Alice", "age": 30}
    },
    {
      "op": "update",
      "path": "users/bob",
      "data": {"age": 31}
    },
    {
      "op": "delete",
      "path": "users/charlie"
    }
  ]
}
```

Operations:
- `set`: Create or replace document
- `update`: Merge with existing data
- `delete`: Remove document

Response:
```json
{
  "results": [
    {
      "op": "set",
      "path": "users/alice",
      "collection_path": "users",
      "doc_id": "alice",
      "success": true,
      "created": true
    },
    {
      "op": "update",
      "path": "users/bob",
      "success": true
    },
    {
      "op": "delete",
      "path": "users/charlie",
      "success": true
    }
  ],
  "committed_at": "2024-01-01T00:00:00Z"
}
```

All writes execute atomically; if any fails, entire transaction fails.

## Query Syntax

### WHERE Operators

Supported operators in `where` array:

| Operator | Example | Notes |
|----------|---------|-------|
| `==` | `{"field": "status", "op": "==", "value": "active"}` | Equality |
| `!=` | `{"field": "status", "op": "!=", "value": "inactive"}` | Not equal |
| `<` | `{"field": "age", "op": "<", "value": 18}` | Less than |
| `<=` | `{"field": "age", "op": "<=", "value": 18}` | Less than or equal |
| `>` | `{"field": "age", "op": ">", "value": 65}` | Greater than |
| `>=` | `{"field": "age", "op": ">=", "value": 65}` | Greater than or equal |
| `in` | `{"field": "status", "op": "in", "value": ["active", "pending"]}` | Value in list |
| `not-in` | `{"field": "status", "op": "not-in", "value": ["deleted"]}` | Value not in list |
| `array-contains` | `{"field": "tags", "op": "array-contains", "value": "admin"}` | Array contains value |
| `array-contains-any` | `{"field": "tags", "op": "array-contains-any", "value": ["admin", "editor"]}` | Array contains any value |

### ORDER BY

Order specs in `order_by` array:

```json
{
  "order_by": [
    {"field": "created_at", "direction": "desc"},
    {"field": "name", "direction": "asc"}
  ]
}
```

Direction: `asc` (default) or `desc`

### Pagination

Keyset pagination using cursor (document ID):

```json
{
  "limit": 20,
  "start_after": "doc-uuid-or-id"
}
```

Response includes `next_cursor` for fetching next page.

## Examples

### Example 1: Create and Query Users

```bash
# Create collection
curl -X POST http://localhost:8000/api/projects/proj123/collections/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "users",
    "path": "users"
  }'

# Create documents
curl -X POST http://localhost:8000/api/projects/proj123/collections/users/docs/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "alice",
    "data": {
      "name": "Alice",
      "age": 30,
      "email": "alice@example.com",
      "status": "active"
    }
  }'

# Query: active users older than 25
curl "http://localhost:8000/api/projects/proj123/collections/users/docs/" \
  -H "Authorization: Bearer {token}" \
  --get \
  --data-urlencode 'query={"where":[{"field":"status","op":"==","value":"active"},{"field":"age","op":">","value":25}],"orderBy":[{"field":"name","direction":"asc"}],"limit":10}'
```

### Example 2: Batch Write with Transaction

```bash
curl -X POST http://localhost:8000/api/projects/proj123/transaction/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "writes": [
      {
        "op": "set",
        "path": "orders/order1",
        "data": {"status": "pending", "total": 99.99}
      },
      {
        "op": "update",
        "path": "users/alice",
        "data": {"last_order": "order1"}
      }
    ]
  }'
```

### Example 3: Subcollections

```bash
# Create document in subcollection: users/alice/posts/post1
curl -X POST "http://localhost:8000/api/projects/proj123/collections/users%2Falice%2Fposts/docs/" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "post1",
    "data": {
      "title": "Hello World",
      "content": "My first post",
      "published": true
    }
  }'

# Query posts by user
curl "http://localhost:8000/api/projects/proj123/collections/users%2Falice%2Fposts/docs/" \
  -H "Authorization: Bearer {token}"
```

## Optimistic Locking

Every document has a `__v` (version) counter. On update/PATCH, include the expected version:

```json
{
  "data": {"age": 31},
  "__v": 1
}
```

If the version doesn't match (concurrent update), the API returns 409 Conflict:

```json
{
  "detail": "Document version mismatch. Expected 1, got 2",
  "current_version": 2
}
```

The `__v` counter is automatically incremented on every write.

## Performance Considerations

### Indexes

- **GIN Index**: Automatically created on `data` JSONB column for general containment queries
- **Expression Indexes**: Add via migrations for specific frequently-queried fields:
  ```sql
  CREATE INDEX doc_data_status ON documents ((data->>'status'), collection_path);
  ```

### Query Limits

- Max documents per query: 1,000 (enforced via `limit`)
- Max WHERE conditions: 10 (recommended)
- Max ORDER BY fields: 3 (recommended)

### Cursor Pagination

Uses keyset pagination for efficient large result sets:
- No offset overhead
- Consistent ordering required
- Next cursor returned in response

## Multi-Tenancy & Security

- All endpoints require authentication (JWT Bearer token)
- Documents are filtered by `project_id` from user's JWT
- User must be member of project to access data
- RLS policies (PostgreSQL row-level security) enforce project isolation at database level

## Testing

Run tests:

```bash
pytest tests/test_data_api.py -v
```

## Future Enhancements (Phase 2+)

- Collection group queries (query across all collections with same name)
- Real-time listeners (WebSocket-based change notifications)
- Advanced composite indexes with automatic suggestion
- Batch import/export
- Document versioning and history
- Full-text search support
- Geo-spatial queries
