"""Tests for OwnFirebase Storage SDK."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ownfirebase import OwnFirebaseConfig, APIError
from ownfirebase.storage import StorageSDK


class TestStorageSDK:
    """Tests for the Storage SDK."""

    def test_storage_init(self):
        """Test Storage SDK initialization."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        storage = StorageSDK(config)
        assert storage.base_url == 'http://localhost:8000'
        assert storage.project_id == 'test-project'

    @patch('requests.request')
    def test_upload_file(self, mock_request):
        """Test uploading a file."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'file_id': 'file-123',
            'filename': 'test.txt',
            'size': 1024,
            'url': 'https://storage.example.com/files/file-123',
            'content_type': 'text/plain'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        storage = StorageSDK(config)

        result = storage.request(
            'POST',
            storage.project_url('storage/upload'),
            json_data={'filename': 'test.txt', 'content_type': 'text/plain'}
        )

        assert result['file_id'] == 'file-123'
        assert result['url'] == 'https://storage.example.com/files/file-123'

    @patch('requests.request')
    def test_get_file_info(self, mock_request):
        """Test getting file metadata."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'file_id': 'file-123',
            'filename': 'test.txt',
            'size': 1024,
            'content_type': 'text/plain',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-02T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        storage = StorageSDK(config)

        result = storage.request(
            'GET',
            storage.project_url('storage/files/file-123')
        )

        assert result['file_id'] == 'file-123'
        assert result['size'] == 1024

    @patch('requests.request')
    def test_delete_file(self, mock_request):
        """Test deleting a file."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        storage = StorageSDK(config)

        result = storage.request(
            'DELETE',
            storage.project_url('storage/files/file-123')
        )

        assert result is None

    @patch('requests.request')
    def test_list_files(self, mock_request):
        """Test listing files in storage."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'files': [
                {'file_id': 'file-1', 'filename': 'image.jpg'},
                {'file_id': 'file-2', 'filename': 'document.pdf'},
                {'file_id': 'file-3', 'filename': 'video.mp4'}
            ],
            'total': 3
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        storage = StorageSDK(config)

        result = storage.request(
            'GET',
            storage.project_url('storage/files')
        )

        assert len(result['files']) == 3

    @patch('requests.request')
    def test_get_download_url(self, mock_request):
        """Test getting a download URL for a file."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'file_id': 'file-123',
            'download_url': 'https://storage.example.com/download/file-123',
            'expires_in': 3600
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        storage = StorageSDK(config)

        result = storage.request(
            'GET',
            storage.project_url('storage/files/file-123/download-url')
        )

        assert 'download_url' in result
        assert result['expires_in'] == 3600

    @patch('requests.request')
    def test_create_file_directory(self, mock_request):
        """Test creating a virtual directory/prefix."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'prefix': 'documents/2024/',
            'status': 'created'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        storage = StorageSDK(config)

        result = storage.request(
            'POST',
            storage.project_url('storage/directories'),
            json_data={'prefix': 'documents/2024/'}
        )

        assert result['prefix'] == 'documents/2024/'


class TestStorageWorkflow:
    """Integration tests for storage workflows."""

    @patch('requests.request')
    def test_upload_and_retrieve_workflow(self, mock_request):
        """Test uploading a file and retrieving it."""
        responses = [
            # Upload
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'file_id': 'file-workflow',
                'filename': 'document.pdf',
                'size': 2048,
                'url': 'https://storage.example.com/files/file-workflow'
            })),
            # Get info
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'file_id': 'file-workflow',
                'filename': 'document.pdf',
                'size': 2048
            })),
            # Get download URL
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'download_url': 'https://storage.example.com/download/file-workflow'
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        storage = StorageSDK(config)

        # Upload
        upload_result = storage.request(
            'POST',
            storage.project_url('storage/upload'),
            json_data={'filename': 'document.pdf'}
        )
        file_id = upload_result['file_id']

        # Get info
        info = storage.request(
            'GET',
            storage.project_url(f'storage/files/{file_id}')
        )
        assert info['size'] == 2048

        # Get download URL
        download = storage.request(
            'GET',
            storage.project_url(f'storage/files/{file_id}/download-url')
        )
        assert 'download_url' in download

    @patch('requests.request')
    def test_bulk_file_operations(self, mock_request):
        """Test managing multiple files."""
        responses = [
            # Upload file 1
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'file_id': 'file-1',
                'filename': 'image1.jpg'
            })),
            # Upload file 2
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'file_id': 'file-2',
                'filename': 'image2.jpg'
            })),
            # List files
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'files': [
                    {'file_id': 'file-1', 'filename': 'image1.jpg'},
                    {'file_id': 'file-2', 'filename': 'image2.jpg'}
                ],
                'total': 2
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        storage = StorageSDK(config)

        # Upload multiple files
        file1 = storage.request(
            'POST',
            storage.project_url('storage/upload'),
            json_data={'filename': 'image1.jpg'}
        )

        file2 = storage.request(
            'POST',
            storage.project_url('storage/upload'),
            json_data={'filename': 'image2.jpg'}
        )

        # List all files
        files_list = storage.request(
            'GET',
            storage.project_url('storage/files')
        )

        assert files_list['total'] == 2
