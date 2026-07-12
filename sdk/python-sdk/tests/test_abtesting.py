"""Tests for OwnFirebase A/B Testing SDK."""

import pytest
from unittest.mock import Mock, patch
from ownfirebase import OwnFirebaseConfig, APIError
from ownfirebase.abtesting import ABTestingSDK


class TestABTestingSDK:
    """Tests for the A/B Testing SDK."""

    def test_abtesting_init(self):
        """Test A/B Testing SDK initialization."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        abtesting = ABTestingSDK(config)
        assert abtesting.base_url == 'http://localhost:8000'
        assert abtesting.project_id == 'test-project'

    @patch('requests.request')
    def test_create_experiment(self, mock_request):
        """Test creating an A/B test experiment."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'experiment_id': 'exp-123',
            'name': 'Button Color Test',
            'status': 'draft',
            'variants': [
                {'variant_id': 'var-1', 'name': 'Control', 'traffic_percentage': 50},
                {'variant_id': 'var-2', 'name': 'Test', 'traffic_percentage': 50}
            ],
            'created_at': '2024-01-01T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        abtesting = ABTestingSDK(config)

        result = abtesting.request(
            'POST',
            abtesting.project_url('abtesting/experiments'),
            json_data={
                'name': 'Button Color Test',
                'variants': [
                    {'name': 'Control', 'traffic_percentage': 50},
                    {'name': 'Test', 'traffic_percentage': 50}
                ]
            }
        )

        assert result['experiment_id'] == 'exp-123'
        assert len(result['variants']) == 2

    @patch('requests.request')
    def test_list_experiments(self, mock_request):
        """Test listing experiments."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'experiments': [
                {
                    'experiment_id': 'exp-1',
                    'name': 'Button Color',
                    'status': 'running'
                },
                {
                    'experiment_id': 'exp-2',
                    'name': 'Layout Test',
                    'status': 'running'
                },
                {
                    'experiment_id': 'exp-3',
                    'name': 'Font Size',
                    'status': 'completed'
                }
            ],
            'total': 3
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        abtesting = ABTestingSDK(config)

        result = abtesting.request(
            'GET',
            abtesting.project_url('abtesting/experiments')
        )

        assert len(result['experiments']) == 3

    @patch('requests.request')
    def test_start_experiment(self, mock_request):
        """Test starting an experiment."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'experiment_id': 'exp-123',
            'status': 'running',
            'started_at': '2024-01-02T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        abtesting = ABTestingSDK(config)

        result = abtesting.request(
            'POST',
            abtesting.project_url('abtesting/experiments/exp-123/start'),
            json_data={}
        )

        assert result['status'] == 'running'

    @patch('requests.request')
    def test_stop_experiment(self, mock_request):
        """Test stopping an experiment."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'experiment_id': 'exp-123',
            'status': 'stopped',
            'stopped_at': '2024-01-05T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        abtesting = ABTestingSDK(config)

        result = abtesting.request(
            'POST',
            abtesting.project_url('abtesting/experiments/exp-123/stop'),
            json_data={}
        )

        assert result['status'] == 'stopped'

    @patch('requests.request')
    def test_get_experiment_results(self, mock_request):
        """Test getting experiment results."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'experiment_id': 'exp-123',
            'name': 'Button Color Test',
            'status': 'completed',
            'results': {
                'var-1': {
                    'variant_name': 'Control',
                    'users': 10000,
                    'conversions': 1200,
                    'conversion_rate': 0.12,
                    'confidence': 0.95
                },
                'var-2': {
                    'variant_name': 'Test',
                    'users': 10000,
                    'conversions': 1400,
                    'conversion_rate': 0.14,
                    'confidence': 0.98
                }
            },
            'winner': 'var-2'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        abtesting = ABTestingSDK(config)

        result = abtesting.request(
            'GET',
            abtesting.project_url('abtesting/experiments/exp-123/results')
        )

        assert result['winner'] == 'var-2'
        assert result['results']['var-2']['conversion_rate'] == 0.14

    @patch('requests.request')
    def test_get_user_variant(self, mock_request):
        """Test getting assigned variant for a user."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'user_id': 'user-123',
            'experiment_id': 'exp-123',
            'variant_id': 'var-2',
            'variant_name': 'Test'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        abtesting = ABTestingSDK(config)

        result = abtesting.request(
            'GET',
            abtesting.project_url('abtesting/experiments/exp-123/user-variant'),
            query_params={'user_id': 'user-123'}
        )

        assert result['variant_name'] == 'Test'

    @patch('requests.request')
    def test_track_conversion(self, mock_request):
        """Test tracking conversion event."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'user_id': 'user-123',
            'experiment_id': 'exp-123',
            'variant_id': 'var-2',
            'conversion_tracked': True
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        abtesting = ABTestingSDK(config)

        result = abtesting.request(
            'POST',
            abtesting.project_url('abtesting/experiments/exp-123/track-conversion'),
            json_data={'user_id': 'user-123', 'value': 29.99}
        )

        assert result['conversion_tracked'] is True

    @patch('requests.request')
    def test_delete_experiment(self, mock_request):
        """Test deleting an experiment."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        abtesting = ABTestingSDK(config)

        result = abtesting.request(
            'DELETE',
            abtesting.project_url('abtesting/experiments/exp-123')
        )

        assert result is None


class TestABTestingWorkflow:
    """Integration tests for A/B testing workflows."""

    @patch('requests.request')
    def test_complete_experiment_lifecycle(self, mock_request):
        """Test complete experiment lifecycle: create -> start -> track -> stop -> results."""
        responses = [
            # Create
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'experiment_id': 'exp-lifecycle',
                'status': 'draft'
            })),
            # Start
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'experiment_id': 'exp-lifecycle',
                'status': 'running'
            })),
            # Get variant
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'variant_id': 'var-2',
                'variant_name': 'Test'
            })),
            # Track conversion
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'conversion_tracked': True
            })),
            # Stop
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'experiment_id': 'exp-lifecycle',
                'status': 'stopped'
            })),
            # Get results
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'experiment_id': 'exp-lifecycle',
                'status': 'completed',
                'results': {
                    'var-1': {'conversion_rate': 0.12},
                    'var-2': {'conversion_rate': 0.15}
                },
                'winner': 'var-2'
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        abtesting = ABTestingSDK(config)

        # Create
        exp = abtesting.request(
            'POST',
            abtesting.project_url('abtesting/experiments'),
            json_data={'name': 'Test'}
        )

        # Start
        abtesting.request(
            'POST',
            abtesting.project_url(f"abtesting/experiments/{exp['experiment_id']}/start"),
            json_data={}
        )

        # Get variant
        variant = abtesting.request(
            'GET',
            abtesting.project_url(f"abtesting/experiments/{exp['experiment_id']}/user-variant"),
            query_params={'user_id': 'user-1'}
        )

        # Track conversion
        abtesting.request(
            'POST',
            abtesting.project_url(f"abtesting/experiments/{exp['experiment_id']}/track-conversion"),
            json_data={'user_id': 'user-1'}
        )

        # Stop
        abtesting.request(
            'POST',
            abtesting.project_url(f"abtesting/experiments/{exp['experiment_id']}/stop"),
            json_data={}
        )

        # Get results
        results = abtesting.request(
            'GET',
            abtesting.project_url(f"abtesting/experiments/{exp['experiment_id']}/results")
        )

        assert results['winner'] == 'var-2'

    @patch('requests.request')
    def test_multiple_experiments(self, mock_request):
        """Test managing multiple experiments simultaneously."""
        responses = [
            # Create exp 1
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'experiment_id': 'exp-1',
                'status': 'draft'
            })),
            # Create exp 2
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'experiment_id': 'exp-2',
                'status': 'draft'
            })),
            # List all
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'experiments': [
                    {'experiment_id': 'exp-1', 'status': 'running'},
                    {'experiment_id': 'exp-2', 'status': 'running'}
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
        abtesting = ABTestingSDK(config)

        # Create multiple experiments
        exp1 = abtesting.request(
            'POST',
            abtesting.project_url('abtesting/experiments'),
            json_data={'name': 'Exp 1'}
        )

        exp2 = abtesting.request(
            'POST',
            abtesting.project_url('abtesting/experiments'),
            json_data={'name': 'Exp 2'}
        )

        # List all
        all_exp = abtesting.request(
            'GET',
            abtesting.project_url('abtesting/experiments')
        )

        assert all_exp['total'] == 2
