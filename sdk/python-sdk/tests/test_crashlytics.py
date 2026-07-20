"""Tests for OwnFirebase Crashlytics SDK."""

from unittest.mock import Mock, patch

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.crashlytics import CrashlyticsSDK

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
    return CrashlyticsSDK(config)


class TestCrashlyticsSDK:
    """Tests for the Crashlytics SDK — one test per real method."""

    def test_crashlytics_init(self, sdk):
        assert sdk.base_url == BASE_URL
        assert sdk.project_id == PROJECT_ID

    @patch('requests.request')
    def test_list_crash_groups(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'next': None, 'previous': None, 'results': []})
        sdk.list_crash_groups(filters={'status': 'open'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/crashlytics/groups/'
        assert kw['params'] == {'status': 'open'}

    @patch('requests.request')
    def test_get_crash_group(self, mock_request, sdk):
        _ok(mock_request, {'id': 'grp-1', 'exception_type': 'NullPointerException'})
        result = sdk.get_crash_group('grp-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/crashlytics/groups/grp-1/'
        assert result['exception_type'] == 'NullPointerException'

    @patch('requests.request')
    def test_report_crash(self, mock_request, sdk):
        _ok(mock_request, {'id': 'crash-1', 'exception_type': 'NullPointerException'}, status=201)
        result = sdk.report_crash(
            exception_type='NullPointerException',
            message='npe at line 42',
            stack_trace='at Main.run(Main.java:42)',
            app_version='1.0.0',
            platform='android',
            device_info={'model': 'Pixel 6'},
        )
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/crashlytics/reports/'
        assert kw['json'] == {
            'exception_type': 'NullPointerException',
            'message': 'npe at line 42',
            'stack_trace': 'at Main.run(Main.java:42)',
            'app_version': '1.0.0',
            'platform': 'android',
            'device_info': {'model': 'Pixel 6'},
        }
        assert result['id'] == 'crash-1'

    @patch('requests.request')
    def test_report_crash_without_device_info(self, mock_request, sdk):
        _ok(mock_request, {'id': 'crash-2'}, status=201)
        sdk.report_crash(
            exception_type='Error',
            message='m',
            stack_trace='s',
            app_version='1.0.0',
            platform='ios',
        )
        kw = _kwargs(mock_request)
        assert 'device_info' not in kw['json']

    @patch('requests.request')
    def test_list_crash_reports(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        sdk.list_crash_reports(filters={'platform': 'ios'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/crashlytics/reports/'
        assert kw['params'] == {'platform': 'ios'}

    @patch('requests.request')
    def test_get_crash_summary(self, mock_request, sdk):
        _ok(mock_request, {
            'total_crashes': 10, 'crash_free_users_percentage': 98.5,
            'affected_users': 3, 'open_issues': 2,
        })
        result = sdk.get_crash_summary()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/crashlytics/summary/'
        assert result['total_crashes'] == 10

    @patch('requests.request')
    def test_record_trace(self, mock_request, sdk):
        _ok(mock_request, {'id': 'trace-1', 'name': 'app_start'}, status=201)
        result = sdk.record_trace(
            name='app_start',
            duration_ms=250,
            started_at='2024-01-01T00:00:00Z',
            attributes={'screen': 'home'},
            metrics={'cpu': 12.5},
        )
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/crashlytics/traces/'
        assert kw['json'] == {
            'name': 'app_start',
            'duration_ms': 250,
            'started_at': '2024-01-01T00:00:00Z',
            'attributes': {'screen': 'home'},
            'metrics': {'cpu': 12.5},
        }
        assert result['id'] == 'trace-1'

    @patch('requests.request')
    def test_record_trace_minimal(self, mock_request, sdk):
        _ok(mock_request, {'id': 'trace-2'}, status=201)
        sdk.record_trace(name='app_start', duration_ms=100, started_at='2024-01-01T00:00:00Z')
        kw = _kwargs(mock_request)
        assert kw['json'] == {
            'name': 'app_start', 'duration_ms': 100, 'started_at': '2024-01-01T00:00:00Z'
        }

    @patch('requests.request')
    def test_list_traces(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        sdk.list_traces()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/crashlytics/traces/'

    @patch('requests.request')
    def test_record_network_request(self, mock_request, sdk):
        _ok(mock_request, {'id': 'net-1', 'url': 'https://api.example.com'}, status=201)
        result = sdk.record_network_request(
            url='https://api.example.com',
            method='GET',
            status_code=200,
            duration_ms=120,
            request_size=64,
            response_size=512,
        )
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/crashlytics/network/'
        assert kw['json'] == {
            'url': 'https://api.example.com',
            'method': 'GET',
            'status_code': 200,
            'duration_ms': 120,
            'request_size': 64,
            'response_size': 512,
        }
        assert result['id'] == 'net-1'

    @patch('requests.request')
    def test_record_network_request_minimal(self, mock_request, sdk):
        _ok(mock_request, {'id': 'net-2'}, status=201)
        sdk.record_network_request(
            url='https://api.example.com', method='POST', status_code=500, duration_ms=90
        )
        kw = _kwargs(mock_request)
        assert kw['json'] == {
            'url': 'https://api.example.com',
            'method': 'POST',
            'status_code': 500,
            'duration_ms': 90,
        }

    @patch('requests.request')
    def test_list_network_requests(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        sdk.list_network_requests()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/crashlytics/network/'
