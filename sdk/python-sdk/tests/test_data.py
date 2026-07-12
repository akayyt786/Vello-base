"""Tests for OwnFirebase Data SDK (CRUD operations)."""

import pytest
from unittest.mock import Mock, patch
from ownfirebase import OwnFirebaseConfig, APIError
from ownfirebase.data import DataSDK


class TestDataSDK:
    """Tests for the Data SDK."""

    def test_data_init(self):
        """Test Data SDK initialization."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)
        assert data.base_url == 'http://localhost:8000'
        assert data.project_id == 'test-project'

    @patch('requests.request')
    def test_create_document(self, mock_request):
        """Test creating a new document."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'doc-123',
            'collection': 'users',
            'data': {'name': 'John', 'email': 'john@example.com'},
            'created_at': '2024-01-01T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        result = data.request(
            'POST',
            data.project_url('data/collections/users/documents'),
            json_data={'name': 'John', 'email': 'john@example.com'}
        )

        assert result['id'] == 'doc-123'
        assert result['data']['name'] == 'John'

    @patch('requests.request')
    def test_get_document(self, mock_request):
        """Test retrieving a document."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'doc-123',
            'collection': 'users',
            'data': {'name': 'John', 'email': 'john@example.com'},
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-02T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        result = data.request(
            'GET',
            data.project_url('data/collections/users/documents/doc-123')
        )

        assert result['id'] == 'doc-123'
        assert result['data']['email'] == 'john@example.com'

    @patch('requests.request')
    def test_update_document(self, mock_request):
        """Test updating a document."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'doc-123',
            'collection': 'users',
            'data': {'name': 'John', 'email': 'newemail@example.com'},
            'updated_at': '2024-01-03T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        result = data.request(
            'PUT',
            data.project_url('data/collections/users/documents/doc-123'),
            json_data={'email': 'newemail@example.com'}
        )

        assert result['data']['email'] == 'newemail@example.com'

    @patch('requests.request')
    def test_delete_document(self, mock_request):
        """Test deleting a document."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        result = data.request(
            'DELETE',
            data.project_url('data/collections/users/documents/doc-123')
        )

        assert result is None

    @patch('requests.request')
    def test_list_documents(self, mock_request):
        """Test listing documents in a collection."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'documents': [
                {'id': 'doc-1', 'data': {'name': 'John'}},
                {'id': 'doc-2', 'data': {'name': 'Jane'}},
                {'id': 'doc-3', 'data': {'name': 'Bob'}}
            ],
            'total': 3,
            'page': 1
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        result = data.request(
            'GET',
            data.project_url('data/collections/users/documents')
        )

        assert len(result['documents']) == 3
        assert result['total'] == 3

    @patch('requests.request')
    def test_query_documents(self, mock_request):
        """Test querying documents with filters."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'documents': [
                {'id': 'doc-1', 'data': {'name': 'John', 'age': 30}},
                {'id': 'doc-3', 'data': {'name': 'Bob', 'age': 30}}
            ],
            'total': 2
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        result = data.request(
            'GET',
            data.project_url('data/collections/users/documents'),
            query_params={'where': 'age', 'operator': '==', 'value': '30'}
        )

        assert result['total'] == 2

    @patch('requests.request')
    def test_get_nonexistent_document(self, mock_request):
        """Test retrieving a non-existent document."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.reason = 'Not Found'
        mock_response.json.return_value = {'error': 'Document not found'}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        with pytest.raises(APIError) as exc_info:
            data.request(
                'GET',
                data.project_url('data/collections/users/documents/nonexistent')
            )

        assert exc_info.value.status == 404

    @patch('requests.request')
    def test_list_documents_with_pagination(self, mock_request):
        """Test listing documents with pagination."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'documents': [
                {'id': f'doc-{i}', 'data': {'name': f'User {i}'}}
                for i in range(10)
            ],
            'total': 100,
            'page': 1,
            'page_size': 10,
            'has_next': True
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        result = data.request(
            'GET',
            data.project_url('data/collections/users/documents'),
            query_params={'page': '1', 'limit': '10'}
        )

        assert len(result['documents']) == 10
        assert result['total'] == 100
        assert result['has_next'] is True

    @patch('requests.request')
    def test_batch_create_documents(self, mock_request):
        """Test creating multiple documents in batch."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'created': 3,
            'documents': [
                {'id': 'doc-1', 'data': {'name': 'User 1'}},
                {'id': 'doc-2', 'data': {'name': 'User 2'}},
                {'id': 'doc-3', 'data': {'name': 'User 3'}}
            ]
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        result = data.request(
            'POST',
            data.project_url('data/collections/users/batch'),
            json_data={
                'documents': [
                    {'name': 'User 1'},
                    {'name': 'User 2'},
                    {'name': 'User 3'}
                ]
            }
        )

        assert result['created'] == 3

    @patch('requests.request')
    def test_batch_delete_documents(self, mock_request):
        """Test deleting multiple documents in batch."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {'deleted': 3}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        result = data.request(
            'POST',
            data.project_url('data/collections/users/batch-delete'),
            json_data={'ids': ['doc-1', 'doc-2', 'doc-3']}
        )

        assert result['deleted'] == 3


class TestDataCRUD:
    """Integration tests for complete CRUD workflows."""

    @patch('requests.request')
    def test_complete_crud_workflow(self, mock_request):
        """Test complete create-read-update-delete workflow."""
        responses = [
            # Create
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'id': 'doc-workflow-1',
                'data': {'name': 'Test User', 'email': 'test@example.com'},
                'created_at': '2024-01-01T00:00:00Z'
            })),
            # Read
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'id': 'doc-workflow-1',
                'data': {'name': 'Test User', 'email': 'test@example.com'},
                'updated_at': '2024-01-01T00:00:00Z'
            })),
            # Update
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'id': 'doc-workflow-1',
                'data': {'name': 'Updated User', 'email': 'updated@example.com'},
                'updated_at': '2024-01-02T00:00:00Z'
            })),
            # Delete
            Mock(ok=True, status_code=204)
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        # Create
        create_result = data.request(
            'POST',
            data.project_url('data/collections/users/documents'),
            json_data={'name': 'Test User', 'email': 'test@example.com'}
        )
        doc_id = create_result['id']

        # Read
        read_result = data.request(
            'GET',
            data.project_url(f'data/collections/users/documents/{doc_id}')
        )
        assert read_result['data']['name'] == 'Test User'

        # Update
        update_result = data.request(
            'PUT',
            data.project_url(f'data/collections/users/documents/{doc_id}'),
            json_data={'name': 'Updated User', 'email': 'updated@example.com'}
        )
        assert update_result['data']['name'] == 'Updated User'

        # Delete
        delete_result = data.request(
            'DELETE',
            data.project_url(f'data/collections/users/documents/{doc_id}')
        )
        assert delete_result is None

    @patch('requests.request')
    def test_multi_collection_operations(self, mock_request):
        """Test operations across multiple collections."""
        responses = [
            # Create in users
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'id': 'user-1',
                'data': {'name': 'John'}
            })),
            # Create in posts
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'id': 'post-1',
                'data': {'title': 'First Post', 'author_id': 'user-1'}
            })),
            # List posts by author
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'documents': [
                    {'id': 'post-1', 'data': {'title': 'First Post'}}
                ],
                'total': 1
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        data = DataSDK(config)

        # Create user
        user = data.request(
            'POST',
            data.project_url('data/collections/users/documents'),
            json_data={'name': 'John'}
        )

        # Create post
        post = data.request(
            'POST',
            data.project_url('data/collections/posts/documents'),
            json_data={'title': 'First Post', 'author_id': user['id']}
        )

        # List posts by author
        posts = data.request(
            'GET',
            data.project_url('data/collections/posts/documents'),
            query_params={'where': 'author_id', 'operator': '==', 'value': user['id']}
        )

        assert posts['total'] == 1
