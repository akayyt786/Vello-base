"""Tests for OwnFirebase Storage SDK."""

from unittest.mock import Mock, patch

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.storage import StorageSDK

BASE_URL = 'http://localhost:8000'
PROJECT_ID = 'test-project'
TOKEN = 'test-token'
PROJECT_PREFIX = f'{BASE_URL}/api/projects/{PROJECT_ID}'


def _ok(mock_request, json_data=None, status=200):
    resp = Mock()
    resp.ok = True
    resp.status_code = status
    resp.json.return_value = {} if json_data is None else json_data
    mock_request.return_value = resp
    return resp


def _kwargs(mock_request):
    return mock_request.call_args[1]


@pytest.fixture
def sdk():
    config = OwnFirebaseConfig(base_url=BASE_URL, project_id=PROJECT_ID, access_token=TOKEN)
    return StorageSDK(config)


class TestStorageSDK:
    """Tests for the Storage SDK — one test per real method."""

    def test_storage_init(self, sdk):
        assert sdk.base_url == BASE_URL
        assert sdk.project_id == PROJECT_ID

    @patch('requests.request')
    def test_get_upload_url(self, mock_request, sdk):
        _ok(mock_request, {
            'file_id': 'file-1',
            'upload_url': 'https://minio.example.com/presigned',
            'method': 'PUT',
            'expires_in': 3600,
            'path': 'docs/a.txt',
            'bucket': 'my-bucket',
        }, status=201)
        result = sdk.get_upload_url(
            path='docs/a.txt', content_type='text/plain', size=1024, metadata={'k': 'v'}
        )
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/storage/upload-url/'
        assert kw['json'] == {
            'path': 'docs/a.txt',
            'content_type': 'text/plain',
            'size': 1024,
            'metadata': {'k': 'v'},
        }
        assert result['file_id'] == 'file-1'

    @patch('requests.request')
    def test_confirm_upload(self, mock_request, sdk):
        _ok(mock_request, {'id': 'file-1', 'name': 'a.txt', 'size': 1024})
        result = sdk.confirm_upload('file-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/storage/confirm/'
        assert kw['json'] == {'file_id': 'file-1'}
        assert result['id'] == 'file-1'

    @patch('requests.request')
    def test_list_files(self, mock_request, sdk):
        _ok(mock_request, {'count': 1, 'next': None, 'previous': None, 'results': []})
        sdk.list_files(prefix='docs/')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/storage/files/'
        assert kw['params'] == {'prefix': 'docs/'}

    @patch('requests.request')
    def test_list_files_without_prefix(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        sdk.list_files()
        kw = _kwargs(mock_request)
        assert kw['params'] == {}

    @patch('requests.request')
    def test_get_file(self, mock_request, sdk):
        _ok(mock_request, {'id': 'file-1', 'name': 'a.txt'})
        result = sdk.get_file('docs/a.txt')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/storage/files/docs/a.txt/'
        assert result['name'] == 'a.txt'

    @patch('requests.request')
    def test_delete_file(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.delete_file('docs/a.txt')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'DELETE'
        assert kw['url'] == f'{PROJECT_PREFIX}/storage/files/docs/a.txt/'
        assert result is None

    @patch('requests.put')
    @patch('requests.request')
    def test_upload_helper(self, mock_request, mock_put, sdk):
        upload_url_resp = Mock()
        upload_url_resp.ok = True
        upload_url_resp.status_code = 201
        upload_url_resp.json.return_value = {
            'file_id': 'file-1',
            'upload_url': 'https://minio.example.com/presigned',
            'method': 'PUT',
            'expires_in': 3600,
            'path': 'docs/a.txt',
            'bucket': 'my-bucket',
        }
        confirm_resp = Mock()
        confirm_resp.ok = True
        confirm_resp.status_code = 200
        confirm_resp.json.return_value = {'id': 'file-1', 'name': 'a.txt', 'size': 11}
        mock_request.side_effect = [upload_url_resp, confirm_resp]

        put_resp = Mock()
        put_resp.ok = True
        put_resp.status_code = 200
        mock_put.return_value = put_resp

        result = sdk.upload(b'hello world', path='docs/a.txt', content_type='text/plain')

        # First call to self.request is get_upload_url; confirm_upload is the second.
        assert mock_request.call_count == 2
        first_call_kwargs = mock_request.call_args_list[0][1]
        assert first_call_kwargs['method'] == 'POST'
        assert first_call_kwargs['url'] == f'{PROJECT_PREFIX}/storage/upload-url/'

        second_call_kwargs = mock_request.call_args_list[1][1]
        assert second_call_kwargs['method'] == 'POST'
        assert second_call_kwargs['url'] == f'{PROJECT_PREFIX}/storage/confirm/'
        assert second_call_kwargs['json'] == {'file_id': 'file-1'}

        mock_put.assert_called_once()
        put_call_args, put_call_kwargs = mock_put.call_args
        assert put_call_args[0] == 'https://minio.example.com/presigned'
        assert put_call_kwargs['data'] == b'hello world'
        assert put_call_kwargs['headers'] == {'Content-Type': 'text/plain'}

        assert result['id'] == 'file-1'
