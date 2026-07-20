"""Tests for OwnFirebase Analytics SDK."""

from unittest.mock import Mock, patch

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.analytics import AnalyticsSDK

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
    instance = AnalyticsSDK(config)
    yield instance
    instance.destroy()  # avoid leaking a background flush timer across tests


class TestAnalyticsSDK:
    """Tests for the Analytics SDK — one test per real method."""

    def test_analytics_init(self, sdk):
        assert sdk.base_url == BASE_URL
        assert sdk.project_id == PROJECT_ID

    @patch('requests.request')
    def test_log_event(self, mock_request, sdk):
        _ok(mock_request, {'id': 'evt-1', 'name': 'signup', 'params': {}, 'timestamp': 't'}, status=201)
        result = sdk.log_event('signup', params={'method': 'email'}, user_id='u1', session_id='s1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/analytics/events/'
        assert kw['json'] == {
            'name': 'signup',
            'params': {'method': 'email'},
            'user_id': 'u1',
            'session_id': 's1',
        }
        assert result['id'] == 'evt-1'

    @patch('requests.request')
    def test_log_event_defaults(self, mock_request, sdk):
        _ok(mock_request, {'id': 'evt-2'}, status=201)
        sdk.log_event('page_view')
        kw = _kwargs(mock_request)
        assert kw['json'] == {
            'name': 'page_view',
            'params': {},
            'user_id': None,
            'session_id': None,
        }

    def test_add_event_to_batch_queues_without_request(self, sdk):
        with patch('requests.request') as mock_request:
            sdk.add_event_to_batch('click', params={'x': 1})
            mock_request.assert_not_called()
        assert len(sdk._event_batch) == 1
        assert sdk._event_batch[0]['name'] == 'click'
        assert sdk._batch_timer is not None

    def test_add_event_to_batch_flushes_when_full(self, sdk):
        with patch('requests.request') as mock_request:
            _ok(mock_request, None, status=201)
            for i in range(sdk._BATCH_MAX_SIZE):
                sdk.add_event_to_batch(f'evt-{i}')
            # Reaching the max size triggers an immediate flush.
            mock_request.assert_called_once()
            kw = _kwargs(mock_request)
            assert kw['method'] == 'POST'
            assert kw['url'] == f'{PROJECT_PREFIX}/analytics/events/batch/'
            assert len(kw['json']['events']) == sdk._BATCH_MAX_SIZE
        assert sdk._event_batch == []

    @patch('requests.request')
    def test_flush_batch(self, mock_request, sdk):
        sdk._event_batch = [{'name': 'a'}, {'name': 'b'}]
        _ok(mock_request, None, status=201)
        sdk.flush_batch()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/analytics/events/batch/'
        assert kw['json'] == {'events': [{'name': 'a'}, {'name': 'b'}]}
        assert sdk._event_batch == []

    def test_flush_batch_empty_is_noop(self, sdk):
        with patch('requests.request') as mock_request:
            sdk.flush_batch()
            mock_request.assert_not_called()

    @patch('requests.request')
    def test_flush_batch_requeues_on_failure(self, mock_request, sdk):
        from ownfirebase.errors import APIError

        sdk._event_batch = [{'name': 'a'}]
        mock_request.side_effect = APIError(status=500, message='Server Error')
        with pytest.raises(APIError):
            sdk.flush_batch()
        assert sdk._event_batch == [{'name': 'a'}]

    @patch('requests.request')
    def test_list_events(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'next': None, 'previous': None, 'results': []})
        sdk.list_events(filters={'name': 'signup'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/analytics/events/'
        assert kw['params'] == {'name': 'signup'}

    @patch('requests.request')
    def test_set_user_property(self, mock_request, sdk):
        _ok(mock_request, {'id': 'up-1', 'name': 'plan', 'value': 'pro'}, status=201)
        result = sdk.set_user_property('plan', 'pro')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/analytics/user-properties/'
        assert kw['json'] == {'name': 'plan', 'value': 'pro'}
        assert result['value'] == 'pro'

    @patch('requests.request')
    def test_list_user_properties(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        sdk.list_user_properties()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/analytics/user-properties/'

    @patch('requests.request')
    def test_list_conversion_events(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        sdk.list_conversion_events()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/analytics/conversion-events/'

    @patch('requests.request')
    def test_mark_conversion_event(self, mock_request, sdk):
        _ok(mock_request, {'id': 'ce-1', 'name': 'purchase'}, status=201)
        result = sdk.mark_conversion_event('purchase')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/analytics/conversion-events/'
        assert kw['json'] == {'name': 'purchase'}
        assert result['name'] == 'purchase'

    @patch('requests.request')
    def test_query(self, mock_request, sdk):
        _ok(mock_request, {'metric': 'events', 'rows': []})
        params = {'metric': 'events', 'dimension': 'country'}
        result = sdk.query(params)
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/analytics/query/'
        assert kw['json'] == params
        assert result['metric'] == 'events'

    def test_destroy_cancels_timer(self, sdk):
        with patch('requests.request'):
            sdk.add_event_to_batch('click')
        assert sdk._batch_timer is not None
        sdk.destroy()
        assert sdk._batch_timer is None
