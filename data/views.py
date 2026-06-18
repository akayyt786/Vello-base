"""
DRF ViewSets for Data API: Collections and Documents (Firestore-like).
Phase 1 MVP: Full CRUD + queries + transactions.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404

from core.models import Project, ProjectMembership
from core.permissions import IsProjectMember, IsProjectEditorOrOwner
from data.models import Collection, Document
from data.serializers import (
    CollectionSerializer,
    DocumentSerializer,
    DocumentWriteSerializer,
    DocumentQuerySerializer,
)
from data.query_parser import apply_filters_to_queryset

logger = logging.getLogger(__name__)


class CollectionViewSet(viewsets.ViewSet):
    """
    Collection endpoints.
    GET /api/projects/{project_id}/collections/ — list collections
    POST /api/projects/{project_id}/collections/ — create collection
    """
    permission_classes = [IsAuthenticated, IsProjectMember]

    def get_permissions(self):
        """Enforce role-based access: reads for members, writes for editors/owners."""
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsProjectMember()]
        return [IsAuthenticated(), IsProjectEditorOrOwner()]

    def get_project(self, project_id: str) -> Project:
        """Get project and verify user access."""
        project = get_object_or_404(Project, id=project_id)
        # Verify user is member of project
        if not ProjectMembership.objects.filter(
            project=project,
            user=self.request.user
        ).exists():
            self.permission_denied(
                self.request,
                message="You do not have access to this project"
            )
        return project

    def list(self, request, project_id=None):
        """
        GET /api/projects/{project_id}/collections/
        List all collections in the project.

        Query params:
            ?skip=0&limit=50 — pagination

        Returns:
            {
                "collections": [
                    {
                        "id": "uuid",
                        "name": "users",
                        "path": "users",
                        "document_count": 42,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z"
                    },
                    ...
                ],
                "count": 5
            }
        """
        project = self.get_project(project_id)

        # Get all collections for this project
        collections = Collection.objects.filter(project=project).order_by('path')

        # Pagination
        skip = int(request.query_params.get('skip', 0))
        limit = int(request.query_params.get('limit', 50))
        total_count = collections.count()

        collections = collections[skip:skip + limit]

        serializer = CollectionSerializer(collections, many=True)
        return Response({
            'collections': serializer.data,
            'count': total_count,
            'skip': skip,
            'limit': limit,
        })

    def create(self, request, project_id=None):
        """
        POST /api/projects/{project_id}/collections/
        Create a new collection.

        Body:
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

        Returns:
            {
                "id": "uuid",
                "name": "users",
                "path": "users",
                "schema": {...},
                "document_count": 0,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        """
        project = self.get_project(project_id)

        serializer = CollectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create collection
        collection = Collection(
            project=project,
            **serializer.validated_data
        )
        collection.save()

        return Response(
            CollectionSerializer(collection).data,
            status=status.HTTP_201_CREATED
        )


class DocumentViewSet(viewsets.ViewSet):
    """
    Document endpoints for a specific collection.
    GET /api/projects/{project_id}/collections/{collection}/docs/ — list documents
    POST /api/projects/{project_id}/collections/{collection}/docs/ — create document
    GET /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/ — get document
    PATCH /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/ — update document
    DELETE /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/ — delete document
    """
    permission_classes = [IsAuthenticated, IsProjectMember]

    def get_permissions(self):
        """Enforce role-based access: reads for members, writes for editors/owners."""
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), IsProjectMember()]
        return [IsAuthenticated(), IsProjectEditorOrOwner()]

    def get_project(self, project_id: str) -> Project:
        """Get project and verify user access."""
        project = get_object_or_404(Project, id=project_id)
        if not ProjectMembership.objects.filter(
            project=project,
            user=self.request.user
        ).exists():
            self.permission_denied(
                self.request,
                message="You do not have access to this project"
            )
        return project

    def list(self, request, project_id=None, collection=None):
        """
        GET /api/projects/{project_id}/collections/{collection}/docs/
        List documents in a collection with optional filtering.

        Query params:
            ?where=field:value&where=status:active — filter by field value (simple)
            ?orderBy=field:asc — order by field
            ?limit=20 — max documents
            ?startAfter=doc-id — cursor pagination

        Advanced: pass JSON-encoded query:
            ?query={"where":[{"field":"status","op":"==","value":"active"}],"orderBy":[{"field":"created_at","direction":"desc"}]}

        Returns:
            {
                "documents": [
                    {
                        "id": "uuid",
                        "collection_path": "users",
                        "doc_id": "alice",
                        "data": {...},
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "__v": 1
                    },
                    ...
                ],
                "count": 42,
                "limit": 20
            }
        """
        project = self.get_project(project_id)

        # Base queryset: all documents in this collection
        queryset = Document.objects.filter(
            project=project,
            collection_path=collection
        )

        # Parse query params
        try:
            import json
            query_json = request.query_params.get('query')
            if query_json:
                query = json.loads(query_json)
            else:
                # Build from individual params for backward compatibility
                where = []
                for key, value in request.query_params.items():
                    if key.startswith('where_'):
                        field = key.replace('where_', '')
                        where.append({'field': field, 'op': '==', 'value': value})

                order_by = []
                for key, value in request.query_params.items():
                    if key.startswith('orderBy_'):
                        field = key.replace('orderBy_', '')
                        order_by.append({'field': field, 'direction': value or 'asc'})

                query = {
                    'where': where,
                    'order_by': order_by,
                    'limit': int(request.query_params.get('limit', 20)),
                    'start_after': request.query_params.get('startAfter', ''),
                }

            # Validate query
            query_serializer = DocumentQuerySerializer(data={
                'collection_path': collection,
                **query
            })
            query_serializer.is_valid(raise_exception=True)

            # Apply filters
            queryset, total_count = apply_filters_to_queryset(
                queryset,
                where=query_serializer.validated_data.get('where', []),
                order_by=query_serializer.validated_data.get('order_by', []),
                limit=query_serializer.validated_data.get('limit'),
                cursor=query_serializer.validated_data.get('start_after', '')
            )

            documents = list(queryset)
            serializer = DocumentSerializer(documents, many=True, context={'request': request})

            # Return cursor for next page if available
            next_cursor = None
            if documents and total_count > len(documents):
                next_cursor = str(documents[-1].id)

            return Response({
                'documents': serializer.data,
                'count': total_count,
                'limit': query_serializer.validated_data.get('limit'),
                'next_cursor': next_cursor,
            })

        except json.JSONDecodeError as e:
            return Response(
                {'detail': f'Invalid query JSON: {e}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as e:
            return Response(
                {'detail': f'Query error: {e}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, project_id=None, collection=None):
        """
        POST /api/projects/{project_id}/collections/{collection}/docs/
        Create a new document. If no doc_id provided, one is auto-generated (UUID).

        Body:
            {
                "doc_id": "alice",  # optional; auto-generated if omitted
                "data": {
                    "name": "Alice",
                    "age": 30,
                    "tags": ["admin", "beta"],
                    "address": {"city": "NYC", "zip": "10001"}
                }
            }

        Returns: 201 Created
            {
                "id": "uuid",
                "collection_path": "users",
                "doc_id": "alice",
                "data": {...},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "__v": 0
            }
        """
        project = self.get_project(project_id)

        # Extract doc_id; if not provided, auto-generate
        doc_id = request.data.get('doc_id')
        if not doc_id:
            import uuid
            doc_id = str(uuid.uuid4())

        # Check for duplicate
        if Document.objects.filter(
            project=project,
            collection_path=collection,
            doc_id=doc_id
        ).exists():
            return Response(
                {'detail': f'Document "{doc_id}" already exists in collection "{collection}"'},
                status=status.HTTP_409_CONFLICT
            )

        # Create document
        data = request.data.get('data', {})
        document = Document(
            project=project,
            collection_path=collection,
            doc_id=doc_id,
            data=data,
            __v=0
        )
        document.save()

        serializer = DocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, project_id=None, collection=None, doc_id=None):
        """
        GET /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/
        Retrieve a single document.

        Returns: 200 OK
            {
                "id": "uuid",
                "collection_path": "users",
                "doc_id": "alice",
                "data": {...},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "__v": 1
            }
        """
        project = self.get_project(project_id)

        document = get_object_or_404(
            Document,
            project=project,
            collection_path=collection,
            doc_id=doc_id
        )

        serializer = DocumentSerializer(document, context={'request': request})
        return Response(serializer.data)

    def partial_update(self, request, project_id=None, collection=None, doc_id=None):
        """
        PATCH /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/
        Update a document (merge with existing data).

        Body:
            {
                "data": {
                    "age": 31,
                    "updated_at": "2024-01-02T00:00:00Z"
                },
                "__v": 1  # optional; for optimistic locking validation
            }

        Returns: 200 OK with updated document
        """
        project = self.get_project(project_id)

        document = get_object_or_404(
            Document,
            project=project,
            collection_path=collection,
            doc_id=doc_id
        )

        # Optimistic locking: check version if provided
        if '__v' in request.data:
            expected_version = request.data['__v']
            if document.__v != expected_version:
                return Response(
                    {
                        'detail': f'Document version mismatch. Expected {expected_version}, got {document.__v}',
                        'current_version': document.__v
                    },
                    status=status.HTTP_409_CONFLICT
                )

        # Merge data (shallow merge; nested objects overwrite)
        if 'data' in request.data:
            document.data.update(request.data['data'])

        # Increment version
        document.__v += 1
        document.save()

        serializer = DocumentSerializer(document, context={'request': request})
        return Response(serializer.data)

    def update(self, request, project_id=None, collection=None, doc_id=None):
        """
        PUT /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/
        Replace entire document.

        Body:
            {
                "data": {...}
            }

        Returns: 200 OK
        """
        project = self.get_project(project_id)

        document = get_object_or_404(
            Document,
            project=project,
            collection_path=collection,
            doc_id=doc_id
        )

        # Replace entire data object
        document.data = request.data.get('data', {})
        document.__v += 1
        document.save()

        serializer = DocumentSerializer(document, context={'request': request})
        return Response(serializer.data)

    def destroy(self, request, project_id=None, collection=None, doc_id=None):
        """
        DELETE /api/projects/{project_id}/collections/{collection}/docs/{doc_id}/
        Delete a document.

        Returns: 204 No Content
        """
        project = self.get_project(project_id)

        document = get_object_or_404(
            Document,
            project=project,
            collection_path=collection,
            doc_id=doc_id
        )

        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionViewSet(viewsets.ViewSet):
    """
    Transaction endpoints for atomic batch writes.
    POST /api/projects/{project_id}/transaction/ — execute transaction
    """
    permission_classes = [IsAuthenticated, IsProjectMember]

    def get_permissions(self):
        """Transactions are always write operations — require editor/owner role."""
        return [IsAuthenticated(), IsProjectEditorOrOwner()]

    def get_project(self, project_id: str) -> Project:
        """Get project and verify user access."""
        project = get_object_or_404(Project, id=project_id)
        if not ProjectMembership.objects.filter(
            project=project,
            user=self.request.user
        ).exists():
            self.permission_denied(
                self.request,
                message="You do not have access to this project"
            )
        return project

    @action(detail=False, methods=['post'])
    def write_batch(self, request, project_id=None):
        """
        POST /api/projects/{project_id}/transaction/
        Execute a batch of write operations atomically.

        Body:
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
                ],
                "options": {}
            }

        Returns: 200 OK
            {
                "results": [
                    {
                        "op": "set",
                        "path": "users/alice",
                        "doc_id": "alice",
                        "success": true
                    },
                    ...
                ],
                "committed_at": "2024-01-01T00:00:00Z",
                "transaction_id": "txn-uuid"
            }

        Errors return 400 Bad Request with details.
        """
        project = self.get_project(project_id)

        # Validate input
        serializer = DocumentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        writes = serializer.validated_data['writes']
        results = []

        # Execute writes atomically
        try:
            with transaction.atomic():
                for write in writes:
                    op = write['op']
                    path = write['path']
                    data = write.get('data', {})

                    # Parse path: "collection/doc_id" or "collection/subcol/doc_id"
                    path_parts = path.split('/')
                    if len(path_parts) < 2:
                        return Response(
                            {'detail': f'Invalid path: "{path}". Expected "collection/doc_id" or "collection/subcol/doc_id"'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    collection_path = '/'.join(path_parts[:-1])
                    doc_id = path_parts[-1]

                    result = {
                        'op': op,
                        'path': path,
                        'collection_path': collection_path,
                        'doc_id': doc_id,
                        'success': False,
                    }

                    if op == 'set':
                        # Create or replace
                        doc, created = Document.objects.update_or_create(
                            project=project,
                            collection_path=collection_path,
                            doc_id=doc_id,
                            defaults={'data': data, '__v': 0}
                        )
                        result['success'] = True
                        result['created'] = created

                    elif op == 'update':
                        # Merge with existing data
                        try:
                            doc = Document.objects.get(
                                project=project,
                                collection_path=collection_path,
                                doc_id=doc_id
                            )
                            doc.data.update(data)
                            doc.__v += 1
                            doc.save()
                            result['success'] = True
                        except Document.DoesNotExist:
                            result['success'] = False
                            result['error'] = f'Document not found: {path}'

                    elif op == 'delete':
                        # Delete
                        _, deleted_count = Document.objects.filter(
                            project=project,
                            collection_path=collection_path,
                            doc_id=doc_id
                        ).delete()
                        result['success'] = deleted_count > 0
                        if not result['success']:
                            result['error'] = f'Document not found: {path}'

                    else:
                        result['error'] = f'Unknown operation: {op}'

                    results.append(result)

        except Exception as e:
            logger.error(f"Transaction error: {e}")
            return Response(
                {'detail': f'Transaction failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'results': results,
            'committed_at': request.META.get('HTTP_DATE', ''),
            'transaction_id': request.data.get('transaction_id', ''),
        })
