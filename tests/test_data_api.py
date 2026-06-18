"""
Tests for Data API (Collections, Documents, Queries, Transactions).
"""

import json
import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership
from data.models import Collection, Document


@pytest.mark.django_db
class TestDataAPI(APITestCase):
    """Test Data API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create project
        self.project = Project.objects.create(
            name='Test Project',
            slug='test-project',
            owner=self.user,
            is_active=True
        )

        # Add user as project member
        ProjectMembership.objects.create(
            project=self.project,
            user=self.user,
            role='owner'
        )

        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)

        # API client
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_create_collection(self):
        """Test creating a collection."""
        url = f'/api/projects/{self.project.id}/collections/'
        data = {
            'name': 'users',
            'path': 'users',
            'schema': {
                'fields': {
                    'email': {'type': 'string', 'indexed': True},
                    'age': {'type': 'number'}
                }
            }
        }

        response = self.client.post(url, data, format='json')
        assert response.status_code == 201
        assert response.data['name'] == 'users'
        assert response.data['path'] == 'users'
        assert Collection.objects.filter(project=self.project, name='users').exists()

    def test_list_collections(self):
        """Test listing collections."""
        # Create collections
        Collection.objects.create(
            project=self.project,
            name='users',
            path='users'
        )
        Collection.objects.create(
            project=self.project,
            name='posts',
            path='posts'
        )

        url = f'/api/projects/{self.project.id}/collections/'
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data['count'] == 2
        assert len(response.data['collections']) == 2

    def test_create_document(self):
        """Test creating a document."""
        # Create collection first
        collection = Collection.objects.create(
            project=self.project,
            name='users',
            path='users'
        )

        url = f'/api/projects/{self.project.id}/collections/users/docs/'
        data = {
            'doc_id': 'alice',
            'data': {
                'name': 'Alice',
                'age': 30,
                'email': 'alice@example.com',
                'tags': ['admin', 'beta'],
                'address': {
                    'city': 'NYC',
                    'zip': '10001'
                }
            }
        }

        response = self.client.post(url, data, format='json')
        assert response.status_code == 201
        assert response.data['doc_id'] == 'alice'
        assert response.data['data']['name'] == 'Alice'
        assert response.data['__v'] == 0
        assert Document.objects.filter(
            project=self.project,
            collection_path='users',
            doc_id='alice'
        ).exists()

    def test_get_document(self):
        """Test retrieving a document."""
        # Create document
        doc = Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='alice',
            data={'name': 'Alice', 'age': 30}
        )

        url = f'/api/projects/{self.project.id}/collections/users/docs/alice/'
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data['doc_id'] == 'alice'
        assert response.data['data']['name'] == 'Alice'

    def test_update_document(self):
        """Test updating a document (PATCH)."""
        # Create document
        doc = Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='alice',
            data={'name': 'Alice', 'age': 30}
        )

        url = f'/api/projects/{self.project.id}/collections/users/docs/alice/'
        data = {
            'data': {'age': 31},
            '__v': 0
        }

        response = self.client.patch(url, data, format='json')
        assert response.status_code == 200
        assert response.data['data']['age'] == 31
        assert response.data['data']['name'] == 'Alice'  # Old field preserved
        assert response.data['__v'] == 1

        # Verify in DB
        doc.refresh_from_db()
        assert doc.__v == 1
        assert doc.data['age'] == 31

    def test_delete_document(self):
        """Test deleting a document."""
        # Create document
        doc = Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='alice',
            data={'name': 'Alice'}
        )

        url = f'/api/projects/{self.project.id}/collections/users/docs/alice/'
        response = self.client.delete(url)
        assert response.status_code == 204
        assert not Document.objects.filter(
            project=self.project,
            collection_path='users',
            doc_id='alice'
        ).exists()

    def test_list_documents(self):
        """Test listing documents in a collection."""
        # Create documents
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='alice',
            data={'name': 'Alice', 'age': 30, 'status': 'active'}
        )
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='bob',
            data={'name': 'Bob', 'age': 25, 'status': 'active'}
        )
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='charlie',
            data={'name': 'Charlie', 'age': 35, 'status': 'inactive'}
        )

        url = f'/api/projects/{self.project.id}/collections/users/docs/'
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data['count'] == 3
        assert len(response.data['documents']) == 3

    def test_query_documents_with_filter(self):
        """Test querying documents with WHERE filter."""
        # Create documents
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='alice',
            data={'name': 'Alice', 'status': 'active'}
        )
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='bob',
            data={'name': 'Bob', 'status': 'inactive'}
        )

        # Query with filter
        url = f'/api/projects/{self.project.id}/collections/users/docs/'
        query = {
            'collection_path': 'users',
            'where': [
                {'field': 'status', 'op': '==', 'value': 'active'}
            ]
        }
        response = self.client.get(url, {'query': json.dumps(query)})
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['documents'][0]['data']['name'] == 'Alice'

    def test_query_documents_with_ordering(self):
        """Test querying documents with ORDER BY."""
        # Create documents
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='alice',
            data={'name': 'Alice', 'age': 30}
        )
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='bob',
            data={'name': 'Bob', 'age': 25}
        )
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='charlie',
            data={'name': 'Charlie', 'age': 35}
        )

        # Query with order by age DESC
        url = f'/api/projects/{self.project.id}/collections/users/docs/'
        query = {
            'collection_path': 'users',
            'order_by': [
                {'field': 'age', 'direction': 'desc'}
            ],
            'limit': 10
        }
        response = self.client.get(url, {'query': json.dumps(query)})
        assert response.status_code == 200
        docs = response.data['documents']
        assert len(docs) == 3
        assert docs[0]['data']['name'] == 'Charlie'  # age 35
        assert docs[1]['data']['name'] == 'Alice'    # age 30
        assert docs[2]['data']['name'] == 'Bob'      # age 25

    def test_transaction_write_batch(self):
        """Test atomic batch write transaction."""
        url = f'/api/projects/{self.project.id}/transaction/'
        data = {
            'writes': [
                {
                    'op': 'set',
                    'path': 'users/alice',
                    'data': {'name': 'Alice', 'age': 30}
                },
                {
                    'op': 'set',
                    'path': 'users/bob',
                    'data': {'name': 'Bob', 'age': 25}
                },
                {
                    'op': 'update',
                    'path': 'users/alice',
                    'data': {'age': 31}
                }
            ]
        }

        response = self.client.post(url, data, format='json')
        assert response.status_code == 200
        assert len(response.data['results']) == 3
        assert all(r['success'] for r in response.data['results'])

        # Verify documents were created/updated
        alice = Document.objects.get(
            project=self.project,
            collection_path='users',
            doc_id='alice'
        )
        assert alice.data['age'] == 31

        bob = Document.objects.get(
            project=self.project,
            collection_path='users',
            doc_id='bob'
        )
        assert bob.data['name'] == 'Bob'

    def test_transaction_delete_operation(self):
        """Test delete operation in transaction."""
        # Pre-create a document
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='alice',
            data={'name': 'Alice'}
        )

        url = f'/api/projects/{self.project.id}/transaction/'
        data = {
            'writes': [
                {
                    'op': 'delete',
                    'path': 'users/alice'
                }
            ]
        }

        response = self.client.post(url, data, format='json')
        assert response.status_code == 200
        assert response.data['results'][0]['success']
        assert not Document.objects.filter(
            project=self.project,
            collection_path='users',
            doc_id='alice'
        ).exists()

    def test_document_version_conflict(self):
        """Test optimistic locking with version conflict."""
        # Create document
        doc = Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='alice',
            data={'name': 'Alice', 'age': 30}
        )

        url = f'/api/projects/{self.project.id}/collections/users/docs/alice/'
        data = {
            'data': {'age': 31},
            '__v': 999  # Wrong version
        }

        response = self.client.patch(url, data, format='json')
        assert response.status_code == 409
        assert 'version mismatch' in response.data['detail'].lower()

    def test_subcollection_path(self):
        """Test working with subcollections."""
        # Create document in subcollection: users/alice/posts/post1
        url = f'/api/projects/{self.project.id}/collections/users%2Falice%2Fposts/docs/'
        data = {
            'doc_id': 'post1',
            'data': {
                'title': 'Hello World',
                'content': 'My first post'
            }
        }

        response = self.client.post(url, data, format='json')
        assert response.status_code == 201
        assert response.data['doc_id'] == 'post1'

        # Verify full path
        doc = Document.objects.get(
            project=self.project,
            collection_path='users/alice/posts',
            doc_id='post1'
        )
        assert doc.full_path == 'users/alice/posts/post1'

    def test_missing_project_returns_404(self):
        """Test accessing non-existent project returns 404."""
        import uuid
        fake_project_id = uuid.uuid4()
        url = f'/api/projects/{fake_project_id}/collections/'
        response = self.client.get(url)
        assert response.status_code == 404

    def test_unauthorized_access_denied(self):
        """Test accessing project without membership returns 403."""
        # Create another user not in the project
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )

        # Get token for other user
        other_refresh = RefreshToken.for_user(other_user)
        other_token = str(other_refresh.access_token)

        # Try to access project with other user
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')

        url = f'/api/projects/{self.project.id}/collections/'
        response = client.get(url)
        assert response.status_code == 403

    def test_array_contains_query(self):
        """Test array-contains operator in queries."""
        # Create documents with array fields
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='alice',
            data={'name': 'Alice', 'tags': ['admin', 'beta']}
        )
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='bob',
            data={'name': 'Bob', 'tags': ['beta', 'user']}
        )
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='charlie',
            data={'name': 'Charlie', 'tags': ['user']}
        )

        # Query for documents with 'admin' tag
        url = f'/api/projects/{self.project.id}/collections/users/docs/'
        query = {
            'collection_path': 'users',
            'where': [
                {'field': 'tags', 'op': 'array-contains', 'value': 'admin'}
            ]
        }
        response = self.client.get(url, {'query': json.dumps(query)})
        assert response.status_code == 200
        assert response.data['count'] == 1
        assert response.data['documents'][0]['data']['name'] == 'Alice'

    def test_comparison_operators(self):
        """Test various comparison operators."""
        # Create documents
        for i in range(5):
            Document.objects.create(
                project=self.project,
                collection_path='products',
                doc_id=f'product{i}',
                data={'name': f'Product {i}', 'price': (i + 1) * 10}
            )

        # Query: price > 20
        url = f'/api/projects/{self.project.id}/collections/products/docs/'
        query = {
            'collection_path': 'products',
            'where': [
                {'field': 'price', 'op': '>', 'value': 20}
            ]
        }
        response = self.client.get(url, {'query': json.dumps(query)})
        assert response.status_code == 200
        assert response.data['count'] == 3  # products 2, 3, 4 (prices 30, 40, 50)

    def test_pagination_limit_and_offset(self):
        """Test pagination with limit and offset parameters."""
        # Create 10 documents
        for i in range(10):
            Document.objects.create(
                project=self.project,
                collection_path='items',
                doc_id=f'item{i}',
                data={'title': f'Item {i}', 'index': i}
            )

        # Query with limit 5
        url = f'/api/projects/{self.project.id}/collections/items/docs/'
        query = {
            'collection_path': 'items',
            'limit': 5,
            'offset': 0
        }
        response = self.client.get(url, {'query': json.dumps(query)})
        assert response.status_code == 200
        assert len(response.data['documents']) == 5

        # Query with offset 5
        query['offset'] = 5
        response = self.client.get(url, {'query': json.dumps(query)})
        assert response.status_code == 200
        assert len(response.data['documents']) == 5

    def test_complex_nested_data_structure(self):
        """Test storing and retrieving complex nested data."""
        url = f'/api/projects/{self.project.id}/collections/users/docs/'
        data = {
            'doc_id': 'bob',
            'data': {
                'name': 'Bob Smith',
                'email': 'bob@example.com',
                'profile': {
                    'avatar_url': 'https://example.com/bob.jpg',
                    'bio': 'Software developer',
                    'social': {
                        'twitter': '@bobsmith',
                        'github': 'bobsmith'
                    }
                },
                'preferences': {
                    'notifications': True,
                    'theme': 'dark',
                    'language': 'en'
                },
                'tags': ['developer', 'python', 'open-source'],
                'metadata': {
                    'created_via': 'mobile_app',
                    'device': 'iPhone'
                }
            }
        }

        response = self.client.post(url, data, format='json')
        assert response.status_code == 201
        assert response.data['data']['profile']['social']['github'] == 'bobsmith'
        assert 'python' in response.data['data']['tags']

        # Retrieve and verify
        get_url = f'/api/projects/{self.project.id}/collections/users/docs/bob/'
        get_response = self.client.get(get_url)
        assert get_response.status_code == 200
        assert get_response.data['data']['profile']['bio'] == 'Software developer'

    def test_update_document_increments_version(self):
        """Test that each update increments the version counter."""
        # Create document
        doc = Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='alice',
            data={'name': 'Alice', 'age': 30}
        )
        assert doc.__v == 0

        # First update
        url = f'/api/projects/{self.project.id}/collections/users/docs/alice/'
        data = {
            'data': {'age': 31},
            '__v': 0
        }
        response = self.client.patch(url, data, format='json')
        assert response.status_code == 200
        assert response.data['__v'] == 1

        # Second update
        data = {
            'data': {'age': 32},
            '__v': 1
        }
        response = self.client.patch(url, data, format='json')
        assert response.status_code == 200
        assert response.data['__v'] == 2

        # Verify in DB
        doc.refresh_from_db()
        assert doc.__v == 2

    def test_multiple_queries_with_filters_and_ordering(self):
        """Test combining WHERE and ORDER BY filters."""
        # Create documents
        for i, name in enumerate(['Alice', 'Bob', 'Charlie', 'Diana', 'Eve']):
            Document.objects.create(
                project=self.project,
                collection_path='users',
                doc_id=name.lower(),
                data={'name': name, 'status': 'active' if i % 2 == 0 else 'inactive', 'score': 100 - (i * 10)}
            )

        # Query: WHERE status == 'active' ORDER BY score DESC
        url = f'/api/projects/{self.project.id}/collections/users/docs/'
        query = {
            'collection_path': 'users',
            'where': [
                {'field': 'status', 'op': '==', 'value': 'active'}
            ],
            'order_by': [
                {'field': 'score', 'direction': 'desc'}
            ],
            'limit': 10
        }
        response = self.client.get(url, {'query': json.dumps(query)})
        assert response.status_code == 200
        docs = response.data['documents']
        # Filter for active users: Alice (100), Charlie (80), Eve (60)
        assert len(docs) == 3
        assert docs[0]['data']['name'] == 'Alice'  # score 100
        assert docs[1]['data']['name'] == 'Charlie'  # score 80
        assert docs[2]['data']['name'] == 'Eve'  # score 60

    def test_transaction_rollback_on_error(self):
        """Test that transaction rolls back if any operation fails."""
        # Create initial document
        Document.objects.create(
            project=self.project,
            collection_path='users',
            doc_id='alice',
            data={'name': 'Alice', 'balance': 1000}
        )

        # Attempt transaction with an invalid path (should fail gracefully)
        url = f'/api/projects/{self.project.id}/transaction/'
        data = {
            'writes': [
                {
                    'op': 'update',
                    'path': 'users/alice',
                    'data': {'balance': 900}
                },
                {
                    'op': 'set',
                    'path': 'users/bob',
                    'data': {'name': 'Bob', 'balance': 100}
                }
            ]
        }

        response = self.client.post(url, data, format='json')
        # Transaction should succeed (both ops are valid)
        assert response.status_code == 200
        assert all(r['success'] for r in response.data['results'])

    def test_document_created_updated_timestamps_present(self):
        """Test that documents have created_at and updated_at timestamps."""
        url = f'/api/projects/{self.project.id}/collections/users/docs/'
        data = {
            'doc_id': 'charlie',
            'data': {'name': 'Charlie', 'email': 'charlie@example.com'}
        }

        response = self.client.post(url, data, format='json')
        assert response.status_code == 201
        assert 'created_at' in response.data
        assert 'updated_at' in response.data
        assert response.data['created_at'] == response.data['updated_at']

    def test_get_document_by_id_not_found(self):
        """Test retrieving non-existent document returns 404."""
        url = f'/api/projects/{self.project.id}/collections/users/docs/nonexistent/'
        response = self.client.get(url)
        assert response.status_code == 404

    def test_delete_document_not_found(self):
        """Test deleting non-existent document returns 404."""
        url = f'/api/projects/{self.project.id}/collections/users/docs/nonexistent/'
        response = self.client.delete(url)
        assert response.status_code == 404
