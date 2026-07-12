"""Tests for OwnFirebase Crashlytics SDK."""

import pytest
from unittest.mock import Mock, patch
from ownfirebase import OwnFirebaseConfig, APIError
from ownfirebase.crashlytics import CrashlyticsSDK


class TestCrashlyticsSDK:
    """Tests for the Crashlytics SDK."""

    def test_crashlytics_init(self):
        """Test Crashlytics SDK initialization."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        crashlytics = CrashlyticsSDK(config)
        assert crashlytics.base_url == 'http://localhost:8000'
        assert crashlytics.project_id == 'test-project'

    @patch('requests.request')
    def test_log_crash(self, mock_request):
        """Test logging a crash report."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'crash_id': 'crash-123',
            'app_version': '1.0.0',
            'os': 'iOS',
            'status': 'received',
            'timestamp': '2024-01-01T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        crashlytics = CrashlyticsSDK(config)

        result = crashlytics.request(
            'POST',
            crashlytics.project_url('crashlytics/crashes'),
            json_data={
                'message': 'NullPointerException',
                'stacktrace': 'at com.example.app.Main.run(Main.java:42)',
                'app_version': '1.0.0',
                'os': 'iOS'
            }
        )

        assert result['crash_id'] == 'crash-123'
        assert result['status'] == 'received'

    @patch('requests.request')
    def test_log_custom_log(self, mock_request):
        """Test logging custom log message."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'log_id': 'log-456',
            'level': 'error',
            'timestamp': '2024-01-01T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        crashlytics = CrashlyticsSDK(config)

        result = crashlytics.request(
            'POST',
            crashlytics.project_url('crashlytics/logs'),
            json_data={
                'message': 'Critical error occurred',
                'level': 'error',
                'user_id': 'user-123'
            }
        )

        assert result['level'] == 'error'

    @patch('requests.request')
    def test_get_crash_details(self, mock_request):
        """Test retrieving crash details."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'crash_id': 'crash-123',
            'message': 'NullPointerException',
            'stacktrace': 'at com.example.app.Main.run(Main.java:42)',
            'app_version': '1.0.0',
            'os': 'iOS',
            'device': 'iPhone 12',
            'user_id': 'user-456',
            'timestamp': '2024-01-01T00:00:00Z',
            'status': 'received'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        crashlytics = CrashlyticsSDK(config)

        result = crashlytics.request(
            'GET',
            crashlytics.project_url('crashlytics/crashes/crash-123')
        )

        assert result['message'] == 'NullPointerException'
        assert result['device'] == 'iPhone 12'

    @patch('requests.request')
    def test_list_crashes(self, mock_request):
        """Test listing crashes."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'crashes': [
                {'crash_id': 'crash-1', 'message': 'Error 1', 'count': 5},
                {'crash_id': 'crash-2', 'message': 'Error 2', 'count': 3},
                {'crash_id': 'crash-3', 'message': 'Error 3', 'count': 1}
            ],
            'total': 3
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        crashlytics = CrashlyticsSDK(config)

        result = crashlytics.request(
            'GET',
            crashlytics.project_url('crashlytics/crashes')
        )

        assert len(result['crashes']) == 3

    @patch('requests.request')
    def test_get_crash_stats(self, mock_request):
        """Test getting crash statistics."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'total_crashes': 150,
            'unique_crashes': 12,
            'affected_users': 85,
            'critical_issues': 3,
            'day_breakdown': {
                '2024-01-01': 10,
                '2024-01-02': 15,
                '2024-01-03': 12
            }
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        crashlytics = CrashlyticsSDK(config)

        result = crashlytics.request(
            'GET',
            crashlytics.project_url('crashlytics/stats')
        )

        assert result['total_crashes'] == 150
        assert result['unique_crashes'] == 12

    @patch('requests.request')
    def test_mark_crash_resolved(self, mock_request):
        """Test marking a crash as resolved."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'crash_id': 'crash-123',
            'status': 'resolved',
            'resolved_at': '2024-01-02T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        crashlytics = CrashlyticsSDK(config)

        result = crashlytics.request(
            'PUT',
            crashlytics.project_url('crashlytics/crashes/crash-123'),
            json_data={'status': 'resolved'}
        )

        assert result['status'] == 'resolved'

    @patch('requests.request')
    def test_search_crashes(self, mock_request):
        """Test searching crashes by criteria."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'crashes': [
                {'crash_id': 'crash-1', 'message': 'NullPointerException'},
                {'crash_id': 'crash-2', 'message': 'NullPointerException'}
            ],
            'total': 2
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        crashlytics = CrashlyticsSDK(config)

        result = crashlytics.request(
            'GET',
            crashlytics.project_url('crashlytics/crashes'),
            query_params={'search': 'NullPointerException'}
        )

        assert result['total'] == 2


class TestCrashlyticsWorkflow:
    """Integration tests for crashlytics workflows."""

    @patch('requests.request')
    def test_crash_reporting_workflow(self, mock_request):
        """Test complete crash reporting and resolution workflow."""
        responses = [
            # Log crash
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'crash_id': 'crash-work',
                'status': 'received'
            })),
            # Get details
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'crash_id': 'crash-work',
                'message': 'OutOfMemoryError',
                'count': 50,
                'affected_users': 25
            })),
            # Mark resolved
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'crash_id': 'crash-work',
                'status': 'resolved'
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        crashlytics = CrashlyticsSDK(config)

        # Report crash
        crash = crashlytics.request(
            'POST',
            crashlytics.project_url('crashlytics/crashes'),
            json_data={'message': 'OutOfMemoryError', 'stacktrace': '...'}
        )

        # Get details
        details = crashlytics.request(
            'GET',
            crashlytics.project_url(f"crashlytics/crashes/{crash['crash_id']}")
        )
        assert details['affected_users'] == 25

        # Mark resolved
        resolved = crashlytics.request(
            'PUT',
            crashlytics.project_url(f"crashlytics/crashes/{crash['crash_id']}"),
            json_data={'status': 'resolved'}
        )

        assert resolved['status'] == 'resolved'

    @patch('requests.request')
    def test_crash_statistics_monitoring(self, mock_request):
        """Test monitoring crash statistics."""
        responses = [
            # Get stats
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'total_crashes': 200,
                'unique_crashes': 15,
                'critical_issues': 5,
                'day_breakdown': {'2024-01-01': 20, '2024-01-02': 25}
            })),
            # List crashes
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'crashes': [
                    {'crash_id': f'crash-{i}', 'message': f'Error {i}', 'count': i*10}
                    for i in range(1, 4)
                ],
                'total': 3
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        crashlytics = CrashlyticsSDK(config)

        # Get overall stats
        stats = crashlytics.request(
            'GET',
            crashlytics.project_url('crashlytics/stats')
        )
        assert stats['critical_issues'] == 5

        # List top crashes
        crashes = crashlytics.request(
            'GET',
            crashlytics.project_url('crashlytics/crashes')
        )
        assert crashes['total'] == 3
