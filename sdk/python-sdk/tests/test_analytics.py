"""Tests for OwnFirebase Analytics SDK."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from ownfirebase import OwnFirebaseConfig, APIError
from ownfirebase.analytics import AnalyticsSDK


class TestAnalyticsSDK:
    """Tests for the Analytics SDK."""

    def test_analytics_init(self):
        """Test Analytics SDK initialization."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        analytics = AnalyticsSDK(config)
        assert analytics.base_url == 'http://localhost:8000'
        assert analytics.project_id == 'test-project'

    @patch('requests.request')
    def test_log_event(self, mock_request):
        """Test logging a single analytics event."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'event_id': 'event-123',
            'event_name': 'user_signup',
            'timestamp': '2024-01-01T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        analytics = AnalyticsSDK(config)

        result = analytics.request(
            'POST',
            analytics.project_url('analytics/events'),
            json_data={
                'event_name': 'user_signup',
                'user_id': 'user-123',
                'properties': {'signup_method': 'email'}
            }
        )

        assert result['event_id'] == 'event-123'
        assert result['event_name'] == 'user_signup'

    @patch('requests.request')
    def test_batch_log_events(self, mock_request):
        """Test logging multiple events in batch."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'batch_id': 'batch-456',
            'events_count': 5,
            'failed': 0,
            'created_at': '2024-01-01T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        analytics = AnalyticsSDK(config)

        result = analytics.request(
            'POST',
            analytics.project_url('analytics/batch-events'),
            json_data={
                'events': [
                    {'event_name': 'page_view', 'user_id': 'user-1'},
                    {'event_name': 'page_view', 'user_id': 'user-2'},
                    {'event_name': 'button_click', 'user_id': 'user-1'},
                    {'event_name': 'form_submit', 'user_id': 'user-3'},
                    {'event_name': 'page_view', 'user_id': 'user-4'}
                ]
            }
        )

        assert result['events_count'] == 5
        assert result['failed'] == 0

    @patch('requests.request')
    def test_get_event(self, mock_request):
        """Test retrieving a specific event."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'event_id': 'event-123',
            'event_name': 'user_signup',
            'user_id': 'user-123',
            'properties': {'signup_method': 'email'},
            'timestamp': '2024-01-01T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        analytics = AnalyticsSDK(config)

        result = analytics.request(
            'GET',
            analytics.project_url('analytics/events/event-123')
        )

        assert result['event_id'] == 'event-123'
        assert result['user_id'] == 'user-123'

    @patch('requests.request')
    def test_query_events(self, mock_request):
        """Test querying events with filters."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'events': [
                {'event_id': 'event-1', 'event_name': 'user_signup', 'user_id': 'user-1'},
                {'event_id': 'event-2', 'event_name': 'user_signup', 'user_id': 'user-2'},
                {'event_id': 'event-3', 'event_name': 'user_signup', 'user_id': 'user-3'}
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
        analytics = AnalyticsSDK(config)

        result = analytics.request(
            'GET',
            analytics.project_url('analytics/events'),
            query_params={'event_name': 'user_signup', 'limit': '10'}
        )

        assert result['total'] == 3
        assert len(result['events']) == 3

    @patch('requests.request')
    def test_get_event_analytics(self, mock_request):
        """Test getting aggregated analytics for an event."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'event_name': 'user_signup',
            'total_events': 1500,
            'unique_users': 1200,
            'daily_average': 50,
            'daily_breakdown': {
                '2024-01-01': 45,
                '2024-01-02': 52,
                '2024-01-03': 48
            }
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        analytics = AnalyticsSDK(config)

        result = analytics.request(
            'GET',
            analytics.project_url('analytics/events/user_signup/analytics'),
            query_params={'date_from': '2024-01-01', 'date_to': '2024-01-03'}
        )

        assert result['total_events'] == 1500
        assert result['unique_users'] == 1200

    @patch('requests.request')
    def test_get_user_analytics(self, mock_request):
        """Test getting analytics for a specific user."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'user_id': 'user-123',
            'total_events': 45,
            'event_breakdown': {
                'page_view': 30,
                'button_click': 10,
                'form_submit': 5
            },
            'first_seen': '2024-01-01T00:00:00Z',
            'last_seen': '2024-01-05T12:30:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        analytics = AnalyticsSDK(config)

        result = analytics.request(
            'GET',
            analytics.project_url('analytics/users/user-123/analytics')
        )

        assert result['user_id'] == 'user-123'
        assert result['total_events'] == 45

    @patch('requests.request')
    def test_delete_events(self, mock_request):
        """Test deleting events."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {'deleted': 10}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        analytics = AnalyticsSDK(config)

        result = analytics.request(
            'DELETE',
            analytics.project_url('analytics/events'),
            json_data={'ids': ['event-1', 'event-2', 'event-3']}
        )

        assert result['deleted'] == 10

    @patch('requests.request')
    def test_export_events(self, mock_request):
        """Test exporting events as CSV/JSON."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'export_id': 'export-123',
            'format': 'csv',
            'download_url': 'https://example.com/exports/export-123.csv',
            'expires_in': 3600
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        analytics = AnalyticsSDK(config)

        result = analytics.request(
            'POST',
            analytics.project_url('analytics/export'),
            json_data={
                'format': 'csv',
                'date_from': '2024-01-01',
                'date_to': '2024-01-31'
            }
        )

        assert result['format'] == 'csv'
        assert 'download_url' in result


class TestAnalyticsBatch:
    """Integration tests for batch analytics operations."""

    @patch('requests.request')
    def test_batch_event_logging_workflow(self, mock_request):
        """Test workflow for batching multiple events."""
        responses = [
            # Batch log 5 events
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'batch_id': 'batch-1',
                'events_count': 5,
                'failed': 0
            })),
            # Batch log 3 more events
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'batch_id': 'batch-2',
                'events_count': 3,
                'failed': 0
            })),
            # Get event count
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'event_name': 'page_view',
                'total_events': 8
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        analytics = AnalyticsSDK(config)

        # First batch
        batch1 = analytics.request(
            'POST',
            analytics.project_url('analytics/batch-events'),
            json_data={
                'events': [
                    {'event_name': 'page_view', 'user_id': f'user-{i}'}
                    for i in range(5)
                ]
            }
        )
        assert batch1['events_count'] == 5

        # Second batch
        batch2 = analytics.request(
            'POST',
            analytics.project_url('analytics/batch-events'),
            json_data={
                'events': [
                    {'event_name': 'page_view', 'user_id': f'user-{i}'}
                    for i in range(5, 8)
                ]
            }
        )
        assert batch2['events_count'] == 3

        # Query total
        analytics_result = analytics.request(
            'GET',
            analytics.project_url('analytics/events/page_view/analytics')
        )
        assert analytics_result['total_events'] == 8

    @patch('requests.request')
    def test_event_aggregation_over_time(self, mock_request):
        """Test aggregating events over time periods."""
        responses = [
            # Log events
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'batch_id': 'batch',
                'events_count': 10,
                'failed': 0
            })),
            # Get daily breakdown
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'event_name': 'purchase',
                'daily_breakdown': {
                    '2024-01-01': 150,
                    '2024-01-02': 175,
                    '2024-01-03': 160,
                    '2024-01-04': 190,
                    '2024-01-05': 185
                },
                'total_events': 860
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        analytics = AnalyticsSDK(config)

        # Log purchase events
        batch = analytics.request(
            'POST',
            analytics.project_url('analytics/batch-events'),
            json_data={'events': [{'event_name': 'purchase'} for _ in range(10)]}
        )

        # Get analytics
        analytics_result = analytics.request(
            'GET',
            analytics.project_url('analytics/events/purchase/analytics'),
            query_params={'date_from': '2024-01-01', 'date_to': '2024-01-05'}
        )

        assert analytics_result['total_events'] == 860
        assert len(analytics_result['daily_breakdown']) == 5

    @patch('requests.request')
    def test_event_filtering_and_analysis(self, mock_request):
        """Test filtering events and analyzing subsets."""
        responses = [
            # Log diverse events
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'batch_id': 'batch-diverse',
                'events_count': 20,
                'failed': 0
            })),
            # Query signup events
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'events': [{'event_id': f'event-{i}', 'event_name': 'signup'}
                          for i in range(1, 6)],
                'total': 5
            })),
            # Query purchase events
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'events': [{'event_id': f'event-{i}', 'event_name': 'purchase'}
                          for i in range(11, 16)],
                'total': 5
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        analytics = AnalyticsSDK(config)

        # Log mixed events
        batch = analytics.request(
            'POST',
            analytics.project_url('analytics/batch-events'),
            json_data={
                'events': [
                    {'event_name': 'signup'},
                    {'event_name': 'purchase'},
                ] * 10
            }
        )

        # Query signup events
        signups = analytics.request(
            'GET',
            analytics.project_url('analytics/events'),
            query_params={'event_name': 'signup'}
        )
        assert signups['total'] == 5

        # Query purchase events
        purchases = analytics.request(
            'GET',
            analytics.project_url('analytics/events'),
            query_params={'event_name': 'purchase'}
        )
        assert purchases['total'] == 5
