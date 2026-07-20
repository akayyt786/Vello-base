"""Tests for OwnFirebase A/B Testing SDK."""

from unittest.mock import Mock, patch

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.abtesting import ABTestingSDK

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
    return ABTestingSDK(config)


class TestABTestingSDK:
    """Tests for the A/B Testing SDK — one test per real method."""

    def test_abtesting_init(self, sdk):
        assert sdk.base_url == BASE_URL
        assert sdk.project_id == PROJECT_ID

    @patch('requests.request')
    def test_list_experiments(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'next': None, 'previous': None, 'results': []})
        sdk.list_experiments()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/abtesting/experiments/'

    @patch('requests.request')
    def test_get_experiment(self, mock_request, sdk):
        _ok(mock_request, {'id': 'exp-1', 'name': 'Button Color', 'status': 'running', 'variants': []})
        result = sdk.get_experiment('exp-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/abtesting/experiments/exp-1/'
        assert result['name'] == 'Button Color'

    @patch('requests.request')
    def test_create_experiment(self, mock_request, sdk):
        experiment = {'name': 'Button Color', 'status': 'draft'}
        _ok(mock_request, {**experiment, 'id': 'exp-1', 'variants': []}, status=201)
        result = sdk.create_experiment(experiment)
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/abtesting/experiments/'
        assert kw['json'] == experiment
        assert result['id'] == 'exp-1'

    @patch('requests.request')
    def test_update_experiment(self, mock_request, sdk):
        _ok(mock_request, {'id': 'exp-1', 'status': 'paused'})
        result = sdk.update_experiment('exp-1', {'status': 'paused'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'PATCH'
        assert kw['url'] == f'{PROJECT_PREFIX}/abtesting/experiments/exp-1/'
        assert kw['json'] == {'status': 'paused'}
        assert result['status'] == 'paused'

    @patch('requests.request')
    def test_delete_experiment(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.delete_experiment('exp-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'DELETE'
        assert kw['url'] == f'{PROJECT_PREFIX}/abtesting/experiments/exp-1/'
        assert result is None

    @patch('requests.request')
    def test_get_assignment(self, mock_request, sdk):
        _ok(mock_request, {
            'variant_name': 'Test', 'config': {'color': 'blue'}, 'experiment_name': 'Button Color'
        })
        result = sdk.get_assignment('exp-1', 'user-123')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/abtesting/experiments/exp-1/assign/'
        assert kw['json'] == {'targeting_value': 'user-123'}
        assert result['variant_name'] == 'Test'

    @patch('requests.request')
    def test_record_conversion(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.record_conversion('exp-1', 'user-123', 'purchase', value=29.99)
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/abtesting/experiments/exp-1/convert/'
        assert kw['json'] == {
            'targeting_value': 'user-123', 'event_name': 'purchase', 'value': 29.99
        }
        assert result is None

    @patch('requests.request')
    def test_record_conversion_without_value(self, mock_request, sdk):
        _ok(mock_request, status=204)
        sdk.record_conversion('exp-1', 'user-123', 'signup')
        kw = _kwargs(mock_request)
        assert kw['json'] == {'targeting_value': 'user-123', 'event_name': 'signup'}
