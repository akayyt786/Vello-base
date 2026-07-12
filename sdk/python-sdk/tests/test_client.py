"""Tests for OwnFirebaseClient base class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ownfirebase import OwnFirebaseConfig, APIError
from ownfirebase.client import OwnFirebaseClient


class TestOwnFirebaseClient:
    """Tests for the base OwnFirebaseClient."""

    def test_client_init(self):
        """Test client initialization with config."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project-123',
            access_token='test-token-xyz',
        )
        client = OwnFirebaseClient(config)
        assert client.base_url == 'http://localhost:8000'
        assert client.project_id == 'test-project-123'
        assert client.access_token == 'test-token-xyz'

    def test_set_access_token(self):
        """Test setting access token."""
        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)
        client.set_access_token('new-token-xyz')
        assert client.access_token == 'new-token-xyz'

    def test_set_project_id(self):
        """Test setting project ID."""
        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)
        client.set_project_id('new-project-456')
        assert client.project_id == 'new-project-456'

    def test_project_url_valid(self):
        """Test project URL generation with valid project ID."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project-123',
        )
        client = OwnFirebaseClient(config)
        url = client.project_url('auth/login')
        assert url == 'http://localhost:8000/api/projects/test-project-123/auth/login'

    def test_project_url_without_project_id(self):
        """Test project URL generation raises error without project ID."""
        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)
        with pytest.raises(ValueError, match='project_id is required'):
            client.project_url('auth/login')

    @patch('requests.request')
    def test_request_success(self, mock_request):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': '123', 'name': 'test'}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            access_token='test-token',
        )
        client = OwnFirebaseClient(config)
        result = client.request('GET', 'http://localhost:8000/api/test')

        assert result == {'id': '123', 'name': 'test'}
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs['method'] == 'GET'
        assert call_kwargs['headers']['Authorization'] == 'Bearer test-token'

    @patch('requests.request')
    def test_request_with_auth_header(self, mock_request):
        """Test that Authorization header is added with access token."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            access_token='my-token-123',
        )
        client = OwnFirebaseClient(config)
        client.request('GET', 'http://localhost:8000/api/test')

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs['headers']['Authorization'] == 'Bearer my-token-123'

    @patch('requests.request')
    def test_request_no_auth(self, mock_request):
        """Test request without authentication."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)
        client.request('GET', 'http://localhost:8000/api/test', no_auth=True)

        call_kwargs = mock_request.call_args[1]
        assert 'Authorization' not in call_kwargs['headers']

    @patch('requests.request')
    def test_request_with_json_data(self, mock_request):
        """Test request with JSON body."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': '456'}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)
        data = {'name': 'test', 'email': 'test@example.com'}
        result = client.request('POST', 'http://localhost:8000/api/users', json_data=data)

        assert result == {'id': '456'}
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs['json'] == data

    @patch('requests.request')
    def test_request_with_query_params(self, mock_request):
        """Test request with query parameters."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)
        params = {'limit': '10', 'offset': '5'}
        client.request('GET', 'http://localhost:8000/api/users', query_params=params)

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs['params'] == params

    @patch('requests.request')
    def test_request_204_no_content(self, mock_request):
        """Test request returning 204 No Content."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)
        result = client.request('DELETE', 'http://localhost:8000/api/resource/123')

        assert result is None

    @patch('requests.request')
    def test_request_error_response(self, mock_request):
        """Test request with error response."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.reason = 'Bad Request'
        mock_response.json.return_value = {'error': 'Invalid input'}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)

        with pytest.raises(APIError) as exc_info:
            client.request('POST', 'http://localhost:8000/api/test', json_data={})

        assert exc_info.value.status == 400
        assert exc_info.value.message == 'Bad Request'
        assert exc_info.value.detail == {'error': 'Invalid input'}

    @patch('requests.request')
    def test_request_error_non_json_response(self, mock_request):
        """Test request with error response that is not JSON."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.reason = 'Internal Server Error'
        mock_response.json.side_effect = ValueError('Not JSON')
        mock_response.text = 'Internal Server Error'
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)

        with pytest.raises(APIError) as exc_info:
            client.request('GET', 'http://localhost:8000/api/test')

        assert exc_info.value.status == 500
        assert exc_info.value.detail == 'Internal Server Error'

    @patch('requests.request')
    def test_request_network_error(self, mock_request):
        """Test request with network error."""
        import requests
        mock_request.side_effect = requests.exceptions.ConnectionError('Connection failed')

        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)

        with pytest.raises(APIError) as exc_info:
            client.request('GET', 'http://localhost:8000/api/test')

        assert exc_info.value.status == 0
        assert exc_info.value.message == 'Request failed'

    @patch('requests.request')
    def test_request_timeout(self, mock_request):
        """Test request timeout."""
        import requests
        mock_request.side_effect = requests.exceptions.Timeout('Request timed out')

        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)

        with pytest.raises(APIError) as exc_info:
            client.request('GET', 'http://localhost:8000/api/test')

        assert exc_info.value.status == 0

    @patch('requests.request')
    def test_request_non_json_success_response(self, mock_request):
        """Test request with non-JSON success response."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError('Not JSON')
        mock_response.text = 'Plain text response'
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)
        result = client.request('GET', 'http://localhost:8000/api/test')

        assert result == 'Plain text response'

    @patch('requests.request')
    def test_request_content_type_header(self, mock_request):
        """Test that Content-Type header is set correctly."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)
        client.request('POST', 'http://localhost:8000/api/test', json_data={})

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs['headers']['Content-Type'] == 'application/json'

    @patch('requests.request')
    def test_request_timeout_parameter(self, mock_request):
        """Test that request includes timeout parameter."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(base_url='http://localhost:8000')
        client = OwnFirebaseClient(config)
        client.request('GET', 'http://localhost:8000/api/test')

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs['timeout'] == 30
