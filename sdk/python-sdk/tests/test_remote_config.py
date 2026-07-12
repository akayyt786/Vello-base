"""Tests for OwnFirebase Remote Config SDK."""

import pytest
from unittest.mock import Mock, patch
from ownfirebase import OwnFirebaseConfig, APIError
from ownfirebase.remote_config import RemoteConfigSDK


class TestRemoteConfigSDK:
    """Tests for the Remote Config SDK."""

    def test_remote_config_init(self):
        """Test Remote Config SDK initialization."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        remote_config = RemoteConfigSDK(config)
        assert remote_config.base_url == 'http://localhost:8000'
        assert remote_config.project_id == 'test-project'

    @patch('requests.request')
    def test_get_config(self, mock_request):
        """Test getting remote config."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'config': {
                'feature_flag_new_ui': True,
                'max_upload_size_mb': 100,
                'api_timeout_seconds': 30
            },
            'version': '1.2.3',
            'updated_at': '2024-01-01T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        remote_config = RemoteConfigSDK(config)

        result = remote_config.request(
            'GET',
            remote_config.project_url('remote-config')
        )

        assert result['config']['feature_flag_new_ui'] is True
        assert result['config']['max_upload_size_mb'] == 100

    @patch('requests.request')
    def test_get_config_value(self, mock_request):
        """Test getting specific config value."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'key': 'feature_flag_new_ui',
            'value': True,
            'type': 'boolean'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        remote_config = RemoteConfigSDK(config)

        result = remote_config.request(
            'GET',
            remote_config.project_url('remote-config/feature_flag_new_ui')
        )

        assert result['value'] is True
        assert result['type'] == 'boolean'

    @patch('requests.request')
    def test_update_config(self, mock_request):
        """Test updating remote config."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'config': {
                'feature_flag_new_ui': False,
                'max_upload_size_mb': 200
            },
            'version': '1.2.4'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        remote_config = RemoteConfigSDK(config)

        result = remote_config.request(
            'PUT',
            remote_config.project_url('remote-config'),
            json_data={
                'feature_flag_new_ui': False,
                'max_upload_size_mb': 200
            }
        )

        assert result['config']['feature_flag_new_ui'] is False

    @patch('requests.request')
    def test_publish_config(self, mock_request):
        """Test publishing config changes."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'version': '1.2.4',
            'status': 'published',
            'published_at': '2024-01-02T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        remote_config = RemoteConfigSDK(config)

        result = remote_config.request(
            'POST',
            remote_config.project_url('remote-config/publish'),
            json_data={'version': '1.2.4'}
        )

        assert result['status'] == 'published'

    @patch('requests.request')
    def test_get_config_versions(self, mock_request):
        """Test getting version history."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'versions': [
                {'version': '1.2.4', 'published_at': '2024-01-02T00:00:00Z'},
                {'version': '1.2.3', 'published_at': '2024-01-01T00:00:00Z'},
                {'version': '1.2.2', 'published_at': '2023-12-31T00:00:00Z'}
            ],
            'total': 3
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        remote_config = RemoteConfigSDK(config)

        result = remote_config.request(
            'GET',
            remote_config.project_url('remote-config/versions')
        )

        assert len(result['versions']) == 3

    @patch('requests.request')
    def test_rollback_config(self, mock_request):
        """Test rolling back to previous version."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'version': '1.2.3',
            'status': 'rolled_back',
            'rolled_back_at': '2024-01-02T12:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        remote_config = RemoteConfigSDK(config)

        result = remote_config.request(
            'POST',
            remote_config.project_url('remote-config/rollback'),
            json_data={'version': '1.2.3'}
        )

        assert result['status'] == 'rolled_back'


class TestRemoteConfigWorkflow:
    """Integration tests for remote config workflows."""

    @patch('requests.request')
    def test_config_update_publish_workflow(self, mock_request):
        """Test complete workflow: get -> update -> publish."""
        responses = [
            # Get current config
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'config': {'feature_flag': True, 'timeout': 30},
                'version': '1.0.0'
            })),
            # Update config
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'config': {'feature_flag': False, 'timeout': 60},
                'version': '1.0.1'
            })),
            # Publish
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'version': '1.0.1',
                'status': 'published'
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        remote_config = RemoteConfigSDK(config)

        # Get current
        current = remote_config.request(
            'GET',
            remote_config.project_url('remote-config')
        )

        # Update
        updated = remote_config.request(
            'PUT',
            remote_config.project_url('remote-config'),
            json_data={'feature_flag': False, 'timeout': 60}
        )

        # Publish
        published = remote_config.request(
            'POST',
            remote_config.project_url('remote-config/publish'),
            json_data={'version': updated['version']}
        )

        assert published['status'] == 'published'

    @patch('requests.request')
    def test_config_version_history(self, mock_request):
        """Test managing config versions."""
        responses = [
            # Get versions
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'versions': [
                    {'version': '1.0.2', 'published_at': '2024-01-03T00:00:00Z'},
                    {'version': '1.0.1', 'published_at': '2024-01-02T00:00:00Z'},
                    {'version': '1.0.0', 'published_at': '2024-01-01T00:00:00Z'}
                ],
                'total': 3
            })),
            # Rollback
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'version': '1.0.1',
                'status': 'rolled_back'
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        remote_config = RemoteConfigSDK(config)

        # Get versions
        versions = remote_config.request(
            'GET',
            remote_config.project_url('remote-config/versions')
        )
        assert versions['total'] == 3

        # Rollback to v1.0.1
        rollback = remote_config.request(
            'POST',
            remote_config.project_url('remote-config/rollback'),
            json_data={'version': '1.0.1'}
        )

        assert rollback['status'] == 'rolled_back'
