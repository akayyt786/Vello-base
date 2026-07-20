"""Tests for OwnFirebase Remote Config SDK."""

import time
from unittest.mock import Mock, patch

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.remote_config import RemoteConfigSDK

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
    return RemoteConfigSDK(config)


class TestRemoteConfigSDK:
    """Tests for the Remote Config SDK — one test per real method."""

    def test_remote_config_init(self, sdk):
        assert sdk.base_url == BASE_URL
        assert sdk.project_id == PROJECT_ID

    def test_set_cache_ttl(self, sdk):
        sdk.set_cache_ttl(60000)
        assert sdk._cache_ttl_ms == 60000

    def test_clear_cache(self, sdk):
        sdk._cache['k'] = {'value': 1, 'expires_at': time.time() + 100}
        sdk.clear_cache()
        assert sdk._cache == {}

    @patch('requests.request')
    def test_list_parameters(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'next': None, 'previous': None, 'results': []})
        sdk.list_parameters()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/config/parameters/'

    @patch('requests.request')
    def test_get_parameter(self, mock_request, sdk):
        _ok(mock_request, {'id': 'p1', 'key': 'flag', 'default_value': 'true', 'value_type': 'boolean'})
        result = sdk.get_parameter('p1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/config/parameters/p1/'
        assert result['key'] == 'flag'

    @patch('requests.request')
    def test_create_parameter(self, mock_request, sdk):
        parameter = {
            'key': 'flag', 'default_value': 'true', 'description': 'desc', 'value_type': 'boolean'
        }
        _ok(mock_request, {**parameter, 'id': 'p1'}, status=201)
        result = sdk.create_parameter(parameter)
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/config/parameters/'
        assert kw['json'] == parameter
        assert result['id'] == 'p1'

    @patch('requests.request')
    def test_update_parameter(self, mock_request, sdk):
        _ok(mock_request, {'id': 'p1', 'default_value': 'false'})
        result = sdk.update_parameter('p1', {'default_value': 'false'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'PATCH'
        assert kw['url'] == f'{PROJECT_PREFIX}/config/parameters/p1/'
        assert kw['json'] == {'default_value': 'false'}
        assert result['default_value'] == 'false'

    @patch('requests.request')
    def test_delete_parameter(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.delete_parameter('p1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'DELETE'
        assert kw['url'] == f'{PROJECT_PREFIX}/config/parameters/p1/'
        assert result is None

    @patch('requests.request')
    def test_list_conditions(self, mock_request, sdk):
        _ok(mock_request, [{'id': 'cond-1', 'name': 'beta_users'}])
        result = sdk.list_conditions('p1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/config/parameters/p1/conditions/'
        assert result[0]['name'] == 'beta_users'

    @patch('requests.request')
    def test_create_condition(self, mock_request, sdk):
        condition = {'name': 'beta_users', 'expression': 'user.beta == true', 'value': 'true'}
        _ok(mock_request, {**condition, 'id': 'cond-1'}, status=201)
        result = sdk.create_condition('p1', condition)
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/config/parameters/p1/conditions/'
        assert kw['json'] == condition
        assert result['id'] == 'cond-1'

    @patch('requests.request')
    def test_update_condition(self, mock_request, sdk):
        _ok(mock_request, {'id': 'cond-1', 'value': 'false'})
        result = sdk.update_condition('p1', 'cond-1', {'value': 'false'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'PATCH'
        assert kw['url'] == f'{PROJECT_PREFIX}/config/parameters/p1/conditions/cond-1/'
        assert kw['json'] == {'value': 'false'}
        assert result['value'] == 'false'

    @patch('requests.request')
    def test_delete_condition(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.delete_condition('p1', 'cond-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'DELETE'
        assert kw['url'] == f'{PROJECT_PREFIX}/config/parameters/p1/conditions/cond-1/'
        assert result is None

    @patch('requests.request')
    def test_fetch_all_parameters(self, mock_request, sdk):
        _ok(mock_request, {'count': 1, 'results': [{'id': 'p1', 'key': 'flag'}]})
        result = sdk.fetch_all_parameters()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/config/parameters/'
        assert result == [{'id': 'p1', 'key': 'flag'}]

    @patch('requests.request')
    def test_fetch_all_parameters_uses_cache(self, mock_request, sdk):
        _ok(mock_request, {'count': 1, 'results': [{'id': 'p1', 'key': 'flag'}]})
        sdk.fetch_all_parameters()
        sdk.fetch_all_parameters()  # second call should be served from cache
        assert mock_request.call_count == 1

    @patch('requests.request')
    def test_fetch_all_parameters_force_refresh_bypasses_cache(self, mock_request, sdk):
        _ok(mock_request, {'count': 1, 'results': [{'id': 'p1', 'key': 'flag'}]})
        sdk.fetch_all_parameters()
        sdk.fetch_all_parameters(force_refresh=True)
        assert mock_request.call_count == 2

    @patch('requests.request')
    def test_get_parameter_by_key(self, mock_request, sdk):
        _ok(mock_request, {'count': 1, 'results': [
            {'id': 'p1', 'key': 'flag', 'default_value': 'true', 'value_type': 'boolean'}
        ]})
        result = sdk.get_parameter_by_key('flag')
        assert result['id'] == 'p1'

    @patch('requests.request')
    def test_get_parameter_by_key_not_found(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        result = sdk.get_parameter_by_key('missing')
        assert result is None

    @patch('requests.request')
    def test_get_config_value_boolean(self, mock_request, sdk):
        _ok(mock_request, {'count': 1, 'results': [
            {'id': 'p1', 'key': 'flag', 'default_value': 'true', 'value_type': 'boolean'}
        ]})
        assert sdk.get_config_value('flag') is True

    @patch('requests.request')
    def test_get_config_value_number(self, mock_request, sdk):
        _ok(mock_request, {'count': 1, 'results': [
            {'id': 'p1', 'key': 'limit', 'default_value': '42', 'value_type': 'number'}
        ]})
        assert sdk.get_config_value('limit') == 42.0

    @patch('requests.request')
    def test_get_config_value_json(self, mock_request, sdk):
        _ok(mock_request, {'count': 1, 'results': [
            {'id': 'p1', 'key': 'obj', 'default_value': '{"a": 1}', 'value_type': 'json'}
        ]})
        assert sdk.get_config_value('obj') == {'a': 1}

    @patch('requests.request')
    def test_get_config_value_missing_uses_default(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        assert sdk.get_config_value('missing', default_value='fallback') == 'fallback'

    @patch('requests.request')
    def test_get_config_value_missing_without_default_raises(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        with pytest.raises(ValueError, match='Config key not found'):
            sdk.get_config_value('missing')

    def test_prune_cache(self, sdk):
        sdk._cache['expired'] = {'value': 1, 'expires_at': time.time() - 10}
        sdk._cache['fresh'] = {'value': 2, 'expires_at': time.time() + 1000}
        sdk.prune_cache()
        assert 'expired' not in sdk._cache
        assert 'fresh' in sdk._cache
