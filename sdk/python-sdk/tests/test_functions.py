"""Tests for OwnFirebase Functions SDK."""

import pytest
from unittest.mock import Mock, patch
from ownfirebase import OwnFirebaseConfig, APIError
from ownfirebase.functions import FunctionsSDK


class TestFunctionsSDK:
    """Tests for the Cloud Functions SDK."""

    def test_functions_init(self):
        """Test Functions SDK initialization."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        functions = FunctionsSDK(config)
        assert functions.base_url == 'http://localhost:8000'
        assert functions.project_id == 'test-project'

    @patch('requests.request')
    def test_call_function(self, mock_request):
        """Test calling a cloud function."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'data': {'sum': 15},
            'execution_time_ms': 125
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        functions = FunctionsSDK(config)

        result = functions.request(
            'POST',
            functions.project_url('functions/add'),
            json_data={'a': 5, 'b': 10}
        )

        assert result['result'] == 'success'
        assert result['data']['sum'] == 15

    @patch('requests.request')
    def test_list_functions(self, mock_request):
        """Test listing deployed functions."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'functions': [
                {
                    'name': 'add',
                    'runtime': 'python3.9',
                    'status': 'active',
                    'url': 'https://api.example.com/functions/add'
                },
                {
                    'name': 'process_image',
                    'runtime': 'python3.9',
                    'status': 'active',
                    'url': 'https://api.example.com/functions/process_image'
                }
            ],
            'total': 2
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        functions = FunctionsSDK(config)

        result = functions.request(
            'GET',
            functions.project_url('functions')
        )

        assert len(result['functions']) == 2

    @patch('requests.request')
    def test_get_function_info(self, mock_request):
        """Test getting function metadata."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'name': 'add',
            'runtime': 'python3.9',
            'status': 'active',
            'memory': 256,
            'timeout': 60,
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-05T12:00:00Z',
            'invocation_count': 1500
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        functions = FunctionsSDK(config)

        result = functions.request(
            'GET',
            functions.project_url('functions/add')
        )

        assert result['name'] == 'add'
        assert result['memory'] == 256

    @patch('requests.request')
    def test_call_function_with_error(self, mock_request):
        """Test calling function that returns error."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'error',
            'error': 'Division by zero',
            'execution_time_ms': 50
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        functions = FunctionsSDK(config)

        result = functions.request(
            'POST',
            functions.project_url('functions/divide'),
            json_data={'a': 10, 'b': 0}
        )

        assert result['result'] == 'error'

    @patch('requests.request')
    def test_function_not_found(self, mock_request):
        """Test calling non-existent function."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.reason = 'Not Found'
        mock_response.json.return_value = {'error': 'Function not found'}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        functions = FunctionsSDK(config)

        with pytest.raises(APIError) as exc_info:
            functions.request(
                'POST',
                functions.project_url('functions/nonexistent'),
                json_data={}
            )

        assert exc_info.value.status == 404

    @patch('requests.request')
    def test_get_function_logs(self, mock_request):
        """Test retrieving function execution logs."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'function_name': 'process_data',
            'logs': [
                {'timestamp': '2024-01-01T00:00:00Z', 'level': 'INFO', 'message': 'Starting'},
                {'timestamp': '2024-01-01T00:00:01Z', 'level': 'INFO', 'message': 'Processing...'},
                {'timestamp': '2024-01-01T00:00:02Z', 'level': 'INFO', 'message': 'Complete'}
            ],
            'total': 3
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        functions = FunctionsSDK(config)

        result = functions.request(
            'GET',
            functions.project_url('functions/process_data/logs')
        )

        assert len(result['logs']) == 3


class TestFunctionsWorkflow:
    """Integration tests for functions workflows."""

    @patch('requests.request')
    def test_function_call_workflow(self, mock_request):
        """Test calling multiple functions in sequence."""
        responses = [
            # Call function 1
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'result': 'success',
                'data': {'value': 100}
            })),
            # Call function 2 with result from function 1
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'result': 'success',
                'data': {'value': 200}
            })),
            # Call function 3
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'result': 'success',
                'data': {'value': 300}
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        functions = FunctionsSDK(config)

        # Call function 1
        result1 = functions.request(
            'POST',
            functions.project_url('functions/fetch_data'),
            json_data={'id': '123'}
        )

        # Call function 2 with result from function 1
        result2 = functions.request(
            'POST',
            functions.project_url('functions/process_data'),
            json_data={'data': result1['data']}
        )

        # Call function 3
        result3 = functions.request(
            'POST',
            functions.project_url('functions/save_result'),
            json_data={'result': result2['data']}
        )

        assert result3['result'] == 'success'

    @patch('requests.request')
    def test_concurrent_function_calls(self, mock_request):
        """Test calling multiple functions."""
        responses = [
            # Get user
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'result': 'success',
                'data': {'name': 'John', 'id': 'user-1'}
            })),
            # Get user posts
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'result': 'success',
                'data': {'posts': [{'id': 'post-1', 'title': 'Hello'}]}
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        functions = FunctionsSDK(config)

        # Get user
        user = functions.request(
            'POST',
            functions.project_url('functions/get_user'),
            json_data={'user_id': 'user-1'}
        )

        # Get user's posts
        posts = functions.request(
            'POST',
            functions.project_url('functions/get_user_posts'),
            json_data={'user_id': user['data']['id']}
        )

        assert len(posts['data']['posts']) == 1
