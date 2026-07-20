"""Tests for OwnFirebase Functions SDK."""

from unittest.mock import Mock, patch

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.functions import FunctionsSDK

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
    return FunctionsSDK(config)


class TestFunctionsSDK:
    """Tests for the Cloud Functions SDK — one test per real method."""

    def test_functions_init(self, sdk):
        assert sdk.base_url == BASE_URL
        assert sdk.project_id == PROJECT_ID

    @patch('requests.request')
    def test_list_functions(self, mock_request, sdk):
        _ok(mock_request, [{'id': 'f1', 'name': 'add'}])
        result = sdk.list_functions()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/functions/'
        assert result[0]['name'] == 'add'

    @patch('requests.request')
    def test_get_function(self, mock_request, sdk):
        _ok(mock_request, {'id': 'f1', 'name': 'add', 'runtime': 'python3.11'})
        result = sdk.get_function('add')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/functions/add/'
        assert result['name'] == 'add'

    @patch('requests.request')
    def test_create_function(self, mock_request, sdk):
        definition = {
            'name': 'add',
            'runtime': 'python3.11',
            'entry_point': 'main.handler',
            'source_code': 'def handler(): pass',
            'is_active': True,
        }
        _ok(mock_request, {**definition, 'id': 'f1'}, status=201)
        result = sdk.create_function(definition)
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/functions/'
        assert kw['json'] == definition
        assert result['id'] == 'f1'

    @patch('requests.request')
    def test_update_function(self, mock_request, sdk):
        updates = {'is_active': False}
        _ok(mock_request, {'id': 'f1', 'name': 'add', 'is_active': False})
        result = sdk.update_function('add', updates)
        kw = _kwargs(mock_request)
        assert kw['method'] == 'PUT'
        assert kw['url'] == f'{PROJECT_PREFIX}/functions/add/'
        assert kw['json'] == updates
        assert result['is_active'] is False

    @patch('requests.request')
    def test_delete_function(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.delete_function('add')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'DELETE'
        assert kw['url'] == f'{PROJECT_PREFIX}/functions/add/'
        assert result is None

    @patch('requests.request')
    def test_invoke(self, mock_request, sdk):
        _ok(mock_request, {'invocation_id': 'inv-1', 'status': 'success', 'result': {'sum': 15}})
        result = sdk.invoke('add', {'a': 5, 'b': 10})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/functions/add/invoke/'
        assert kw['json'] == {'data': {'a': 5, 'b': 10}}
        assert result['result']['sum'] == 15

    @patch('requests.request')
    def test_invoke_without_payload(self, mock_request, sdk):
        _ok(mock_request, {'invocation_id': 'inv-2', 'status': 'success'})
        sdk.invoke('ping')
        kw = _kwargs(mock_request)
        assert kw['json'] == {'data': {}}

    @patch('requests.request')
    def test_get_logs(self, mock_request, sdk):
        _ok(mock_request, [{'id': 'log-1', 'level': 'INFO', 'message': 'started'}])
        result = sdk.get_logs('add', limit=10, since='2024-01-01T00:00:00Z')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/functions/add/logs/'
        assert kw['params'] == {'limit': '10', 'since': '2024-01-01T00:00:00Z'}
        assert result[0]['level'] == 'INFO'

    @patch('requests.request')
    def test_get_logs_without_options(self, mock_request, sdk):
        _ok(mock_request, [])
        sdk.get_logs('add')
        kw = _kwargs(mock_request)
        assert kw['params'] == {}
