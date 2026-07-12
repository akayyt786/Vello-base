"""Tests for OwnFirebase error handling."""

import pytest
from ownfirebase import APIError


class TestAPIError:
    """Tests for APIError exception."""

    def test_api_error_creation(self):
        """Test creating APIError."""
        error = APIError(status=400, message='Bad Request', detail={'error': 'Invalid input'})
        assert error.status == 400
        assert error.message == 'Bad Request'
        assert error.detail == {'error': 'Invalid input'}

    def test_api_error_string_representation(self):
        """Test APIError string representation."""
        error = APIError(status=404, message='Not Found')
        assert str(error) == 'API Error 404: Not Found'

    def test_api_error_repr(self):
        """Test APIError repr."""
        error = APIError(status=500, message='Server Error', detail='Internal failure')
        repr_str = repr(error)
        assert 'APIError' in repr_str
        assert '500' in repr_str

    def test_api_error_without_detail(self):
        """Test APIError without detail."""
        error = APIError(status=401, message='Unauthorized')
        assert error.detail is None

    def test_api_error_with_text_detail(self):
        """Test APIError with text detail."""
        error = APIError(status=502, message='Bad Gateway', detail='Service unavailable')
        assert isinstance(error.detail, str)

    def test_api_error_with_dict_detail(self):
        """Test APIError with dict detail."""
        error = APIError(status=400, message='Bad Request', detail={'field': 'email', 'reason': 'invalid'})
        assert isinstance(error.detail, dict)

    def test_api_error_is_exception(self):
        """Test that APIError is an Exception."""
        error = APIError(status=400, message='Bad Request')
        assert isinstance(error, Exception)

    def test_api_error_can_be_raised(self):
        """Test raising APIError."""
        with pytest.raises(APIError) as exc_info:
            raise APIError(status=403, message='Forbidden')
        assert exc_info.value.status == 403

    def test_api_error_catch_as_exception(self):
        """Test catching APIError as Exception."""
        with pytest.raises(Exception):
            raise APIError(status=500, message='Internal Server Error')

    def test_api_error_status_codes(self):
        """Test various HTTP status codes."""
        status_codes = [400, 401, 403, 404, 409, 429, 500, 502, 503]
        for status in status_codes:
            error = APIError(status=status, message=f'Error {status}')
            assert error.status == status

    def test_api_error_network_error(self):
        """Test APIError for network errors."""
        error = APIError(status=0, message='Request failed', detail='Connection refused')
        assert error.status == 0
        assert 'Request' in error.message
