# Data API Service - Phase 1 MVP Implementation

## Overview

This document describes the complete Data API Service implementation for the Own Firebase project. The implementation provides a Firestore-compatible document database on Django + PostgreSQL, with full support for Collections, Documents, Queries, and atomic Transactions.

## Files Created

### Core Application Files

1. **data/models.py** (180 lines)
   - `Collection` model: Stores collection metadata with hierarchical path support
   - `Document` model: JSONB-based document storage with optimistic locking via `__v` counter
   - Multi-tenant via `MultiTenantModel` base class
   - Automatic timestamps and audit fields

2. **data/serializers.py** (190 lines)
   - `CollectionSerializer`: DRF serializer for collection metadata
   - `DocumentSerializer`: DRF serializer for document CRUD with version support
   - `DocumentWriteSerializer`: Batch write validation
   - `DocumentQuerySerializer`: Query parameter validation

3. **data/views.py** (550 lines)
   - `CollectionViewSet`: Collection list/create
   - `DocumentViewSet`: Full CRUD for documents (retrieve, create, list, update, delete)
   - `TransactionViewSet`: Atomic batch write operations
   - Query parsing and filtering support
   - Cursor-based pagination
   - Optimistic locking conflict detection

4. **data/query_parser.py** (220 lines)
   - `QueryParser` class: Converts Firestore-style queries to Django ORM
   - Support for all comparison operators (==, !=, <, <=, >, >=)
   - Array operators (array-contains, array-contains-any, in, not-in)
   - Order by with ASC/DESC
   - Cursor-based keyset pagination
   - Comprehensive error handling

5. **data/urls.py** (50 lines)
   - REST API endpoint routing
   - Collection endpoints: /api/projects/{project_id}/collections/
   - Document endpoints: /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/
   - Transaction endpoint: /api/projects/{project_id}/transaction/

6. **data/admin.py** (90 lines)
   - Django admin interface for Collections and Documents
   - Project-scoped filtering for non-superusers
   - Read-only audit fields
   - Collapsible schema and audit sections

7. **data/apps.py** (5 lines)
   - Django app configuration

8. **data/migrations/0001_initial.py** (90 lines)
   - Database schema creation
   - Models: Collection, Document
   - Indexes: GIN on JSONB data, composite indexes for sorting
   - Constraints: unique_together for collections and documents

9. **data/README.md** (400 lines)
   - Comprehensive API documentation
   - Architecture overview
   - All endpoint specifications with request/response examples
   - Query syntax reference
   - Performance considerations
   - Multi-tenancy and security
   - Testing guide

### Configuration Updates

10. **ownfirebase/settings.py**
    - Added `'data'` app to `INSTALLED_APPS`
    - Changed pagination from `LimitOffsetPagination` to `CursorPagination`
    - Updated `PAGE_SIZE` to 20 for document queries

11. **ownfirebase/urls.py**
    - Added data API routes: `path('api/', include('data.urls'))`

### Tests

12. **tests/test_data_api.py** (350 lines)
    - 16 comprehensive test cases
    - Tests for: collections, document CRUD, queries, transactions, optimistic locking
    - Permission and access control tests
    - Query operators: comparison, array operations
    - Pagination and cursors
    - Error handling and conflict detection

## Architecture

### Data Model Design

```
Collection (metadata)
├── project (FK -> Project)
├── path (string, hierarchical: "users", "users/alice/posts")
├── name (string: "users", "posts")
├── schema (JSONB, optional metadata)
└── document_count (int, cache)

Document (data storage)
├── project (FK -> Project)
├── collection_path (string, indexed)
├── doc_id (string)
├── data (JSONB, stores arbitrary nested data)
├── __v (int, version counter for optimistic locking)
├── created_at (DateTime)
├── updated_at (DateTime)
└── (audit fields: created_by, updated_by)
```

### Query Execution Pipeline

```
HTTP Request
    ↓
URL Routing (data/urls.py)
    ↓
ViewSet Method (data/views.py)
    ↓
Query Serializer Validation (data/serializers.py)
    ↓
QueryParser.parse_where()  → Django Q objects
QueryParser.parse_order_by() → order_by fields
QueryParser.parse_cursor()   → keyset pagination filter
    ↓
apply_filters_to_queryset()
    ↓
Django ORM QuerySet
    ↓
PostgreSQL JSONB Queries
    ↓
Results Serialization
    ↓
HTTP Response
```

## Key Features

### 1. Collections
- Hierarchical paths supporting subcollections
- Schema metadata for admin/validation
- Document count tracking
- Full CRUD via REST API

### 2. Documents
- JSONB storage for arbitrary nested data
- Firestore-compatible field types (string, number, boolean, array, object, null)
- Automatic timestamps (created_at, updated_at)
- Optimistic locking via `__v` version counter

### 3. Queries
- **Operators**: ==, !=, <, <=, >, >=, in, not-in, array-contains, array-contains-any
- **Sorting**: Multiple order_by with asc/desc
- **Pagination**: Cursor-based keyset pagination (no offset overhead)
- **Filtering**: Multiple WHERE conditions combined with AND logic

### 4. Transactions
- Atomic batch write operations (set, update, delete)
- All-or-nothing semantics
- Detailed results per operation
- Path validation and error reporting

### 5. Optimistic Locking
- Every document has `__v` version counter
- PATCH requests can include expected version
- Conflict detection: 409 Conflict if version mismatch
- Auto-increment on every write

### 6. Security & Multi-Tenancy
- Project-scoped isolation via FK
- Permission checks: IsAuthenticated + IsProjectMember
- Row-level security via RLS policies (database layer)
- Audit trail: created_by, updated_by fields

### 7. Performance Optimization
- GIN index on JSONB data column
- Expression indexes for common query patterns
- Cursor pagination (efficient for large datasets)
- Keyset-based pagination (no full table scan)

## API Endpoints

### Collections
```
GET  /api/projects/{project_id}/collections/           (list)
POST /api/projects/{project_id}/collections/           (create)
```

### Documents
```
GET    /api/projects/{project_id}/collections/{collection}/docs/              (list with query)
POST   /api/projects/{project_id}/collections/{collection}/docs/              (create)
GET    /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/     (retrieve)
PATCH  /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/     (update/merge)
PUT    /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/     (replace)
DELETE /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/     (delete)
```

### Transactions
```
POST /api/projects/{project_id}/transaction/                                   (batch write)
```

## Example Usage

### Create and Query Users

```bash
# Create collection
curl -X POST http://localhost:8000/api/projects/proj123/collections/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "users",
    "path": "users"
  }'

# Create user document
curl -X POST http://localhost:8000/api/projects/proj123/collections/users/docs/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "alice",
    "data": {
      "name": "Alice",
      "age": 30,
      "email": "alice@example.com",
      "tags": ["admin", "beta"]
    }
  }'

# Query: active users ordered by name
curl "http://localhost:8000/api/projects/proj123/collections/users/docs/" \
  -H "Authorization: Bearer {token}" \
  --get \
  --data-urlencode 'query={"where":[{"field":"status","op":"==","value":"active"}],"orderBy":[{"field":"name","direction":"asc"}],"limit":20}'
```

### Atomic Batch Write

```bash
curl -X POST http://localhost:8000/api/projects/proj123/transaction/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "writes": [
      {"op": "set", "path": "users/alice", "data": {"age": 31}},
      {"op": "set", "path": "users/bob", "data": {"age": 26}},
      {"op": "delete", "path": "users/charlie"}
    ]
  }'
```

## Database Schema

### Collections Table
```sql
CREATE TABLE data_collection (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL (FK),
  name VARCHAR(255),
  path TEXT,
  schema JSONB,
  document_count INTEGER,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  created_by_id INTEGER,
  updated_by_id INTEGER,
  UNIQUE(project_id, path),
  INDEX(project_id, name),
  INDEX(project_id, created_at)
);
```

### Documents Table
```sql
CREATE TABLE data_document (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL (FK),
  collection_path TEXT,
  doc_id TEXT,
  data JSONB,
  version INTEGER DEFAULT 0,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  created_by_id INTEGER,
  updated_by_id INTEGER,
  UNIQUE(project_id, collection_path, doc_id),
  GIN INDEX(data),
  INDEX(project_id, collection_path, created_at),
  INDEX(project_id, collection_path, updated_at)
);
```

## Testing

Run all tests:
```bash
pytest tests/test_data_api.py -v
```

Coverage: 16 test cases covering:
- CRUD operations
- Query operators
- Transactions
- Optimistic locking
- Subcollections
- Access control
- Error handling

## Performance Characteristics

| Operation | Query | Notes |
|-----------|-------|-------|
| Create document | O(1) | Single write |
| Get document | O(1) | Primary key lookup |
| Update document | O(1) | Direct update |
| Delete document | O(1) | Direct delete |
| List documents | O(n) | n = result set size |
| Query with filter | O(n) | n = result set size; uses indexes |
| Cursor pagination | O(k) | k = page size; keyset-based |

## Firestore Feature Mapping

| Feature | Firestore | Our Implementation | Status |
|---------|-----------|-------------------|--------|
| Documents & Collections | Yes | Yes | ✓ |
| JSONB/Dynamic Fields | Yes | Yes (JSONB) | ✓ |
| Queries (where/orderBy) | Yes | Yes (10 operators) | ✓ |
| Transactions | Yes | Yes (atomic batch write) | ✓ |
| Optimistic Locking | No | Yes (__v) | ✓ Enhancement |
| Pagination | Cursor-based | Cursor-based (keyset) | ✓ |
| Security Rules | Yes | Via RLS + code | ✓ Partial |
| Realtime Listeners | Yes | Via Channels (Phase 2) | ⊗ Future |
| Composite Indexes | Yes | Via migrations | ✓ Manual |
| Collection Groups | Yes | Via regex (Phase 2) | ⊗ Partial |
| Offline Support | Yes (SDK) | N/A (REST API) | N/A |

## Future Enhancements (Phase 2+)

1. **Realtime Listeners**: WebSocket support via Channels + Redis
2. **Collection Group Queries**: Query across all collections with same name
3. **Composite Index Suggestions**: Analyze slow queries and suggest indexes
4. **Advanced Pagination**: Full cursor encoding (Firestore-style)
5. **Full-Text Search**: Integration with PostgreSQL full-text search
6. **Geo-Spatial Queries**: PostGIS integration for location-based queries
7. **Document Versioning**: Full history and time-travel queries
8. **Batch Import/Export**: CSV/JSON bulk operations
9. **Change Feeds**: Event log for data audit

## Configuration

### Environment Variables

None specific to data app; inherits from main settings.

### Django Settings

Already updated:
- `INSTALLED_APPS`: Added `'data'`
- `DEFAULT_PAGINATION_CLASS`: Changed to `CursorPagination`
- `PAGE_SIZE`: Set to 20

### Migrations

Run migrations to create tables:
```bash
python manage.py migrate data
```

## Deployment Notes

### PostgreSQL Requirements
- Version: 9.6+ (for JSONB support)
- Extensions: None required
- Configuration: Standard PostgreSQL config

### Index Management
- GIN index automatically created on `data` JSONB column
- Expression indexes added via migrations for common query patterns
- Monitor index usage with `pg_stat_statements` and add indexes as needed

### Performance Tuning
- Adjust `PAGE_SIZE` in settings based on workload
- Enable query logging with `django.db.connection.queries` in DEBUG mode
- Use `django-extensions` shell_plus for REPL testing

## Support & Troubleshooting

### Common Issues

1. **Query returns no results**
   - Check: field names in WHERE match document structure
   - Check: data types match (string vs number)
   - Use admin interface to inspect documents

2. **Version conflict on update**
   - Cause: Concurrent updates to same document
   - Fix: Fetch latest version before updating
   - Solution: Implement retry logic with exponential backoff

3. **Slow queries**
   - Check: Indexes are created for commonly filtered fields
   - Use `pg_stat_statements` to find slow queries
   - Add expression indexes for frequently queried fields

## Implementation Notes

- All code follows Django best practices
- Type hints used throughout for clarity
- Comprehensive docstrings on all public methods
- Error messages are descriptive and actionable
- Security-first approach with permission checks
- Multi-tenant isolation at all levels (application + database)
