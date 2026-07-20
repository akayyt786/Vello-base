"""Tests for OwnFirebase Data SDK (CRUD operations)."""

from unittest.mock import Mock, patch

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.data import DataSDK

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
    return DataSDK(config)


class TestDataSDK:
    """Tests for the Data SDK — one test per real method."""

    def test_data_init(self, sdk):
        assert sdk.base_url == BASE_URL
        assert sdk.project_id == PROJECT_ID

    @patch('requests.request')
    def test_list_collections(self, mock_request, sdk):
        _ok(mock_request, [{'id': 'c1', 'name': 'users', 'document_count': 3}])
        result = sdk.list_collections()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/collections/'
        assert result[0]['name'] == 'users'

    @patch('requests.request')
    def test_create_collection(self, mock_request, sdk):
        _ok(mock_request, {'id': 'c1', 'name': 'users', 'document_count': 0}, status=201)
        result = sdk.create_collection('users')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/collections/'
        assert kw['json'] == {'name': 'users'}
        assert result['name'] == 'users'

    @patch('requests.request')
    def test_list_documents(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'next': None, 'previous': None, 'results': []})
        sdk.list_documents('users', filters={'status': 'active'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/collections/users/docs/'
        assert kw['params'] == {'status': 'active'}

    @patch('requests.request')
    def test_list_documents_subcollection_path(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        sdk.list_documents('users/uid/posts')
        kw = _kwargs(mock_request)
        assert kw['url'] == f'{PROJECT_PREFIX}/collections/users/uid/posts/docs/'

    @patch('requests.request')
    def test_get_document(self, mock_request, sdk):
        _ok(mock_request, {
            'id': 'doc-1', 'collection': 'users', 'data': {'name': 'John'},
            'created_at': '2024-01-01T00:00:00Z', 'updated_at': '2024-01-01T00:00:00Z',
        })
        result = sdk.get_document('users', 'doc-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/collections/users/docs/doc-1/'
        assert result['data']['name'] == 'John'

    @patch('requests.request')
    def test_create_document(self, mock_request, sdk):
        _ok(mock_request, {'id': 'doc-1', 'collection': 'users', 'data': {'name': 'John'}}, status=201)
        result = sdk.create_document('users', {'name': 'John'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/collections/users/docs/'
        assert kw['json'] == {'data': {'name': 'John'}}
        assert result['id'] == 'doc-1'

    @patch('requests.request')
    def test_update_document(self, mock_request, sdk):
        _ok(mock_request, {'id': 'doc-1', 'data': {'name': 'Jane'}})
        result = sdk.update_document('users', 'doc-1', {'name': 'Jane'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'PATCH'
        assert kw['url'] == f'{PROJECT_PREFIX}/collections/users/docs/doc-1/'
        assert kw['json'] == {'data': {'name': 'Jane'}}
        assert result['data']['name'] == 'Jane'

    @patch('requests.request')
    def test_replace_document(self, mock_request, sdk):
        _ok(mock_request, {'id': 'doc-1', 'data': {'name': 'Jane'}})
        result = sdk.replace_document('users', 'doc-1', {'name': 'Jane'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'PUT'
        assert kw['url'] == f'{PROJECT_PREFIX}/collections/users/docs/doc-1/'
        assert kw['json'] == {'data': {'name': 'Jane'}}
        assert result['data']['name'] == 'Jane'

    @patch('requests.request')
    def test_delete_document(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.delete_document('users', 'doc-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'DELETE'
        assert kw['url'] == f'{PROJECT_PREFIX}/collections/users/docs/doc-1/'
        assert result is None

    @patch('requests.request')
    def test_write_batch(self, mock_request, sdk):
        operations = [
            {'op': 'set', 'collection': 'users', 'doc_id': 'doc-1', 'data': {'name': 'X'}},
            {'op': 'delete', 'collection': 'users', 'doc_id': 'doc-2'},
        ]
        _ok(mock_request, {'written': 2, 'errors': []})
        result = sdk.write_batch(operations)
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/transaction/'
        assert kw['json'] == {'operations': operations}
        assert result['written'] == 2

    @patch('requests.request')
    def test_get_rules(self, mock_request, sdk):
        _ok(mock_request, {'rules': 'allow read, write: if true;'})
        result = sdk.get_rules()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{BASE_URL}/api/v1/rules/'
        assert 'rules' in result

    @patch('requests.request')
    def test_update_rules(self, mock_request, sdk):
        _ok(mock_request, {'rules': 'allow read: if true;'})
        result = sdk.update_rules('allow read: if true;')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/rules/'
        assert kw['json'] == {'rules': 'allow read: if true;'}
        assert result['rules'] == 'allow read: if true;'

    @patch('requests.request')
    def test_test_rules(self, mock_request, sdk):
        _ok(mock_request, {'allowed': True})
        result = sdk.test_rules('allow read: if true;', {'auth': {'uid': 'u1'}})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/rules/test/'
        assert kw['json'] == {'rule': 'allow read: if true;', 'context': {'auth': {'uid': 'u1'}}}
        assert result['allowed'] is True
