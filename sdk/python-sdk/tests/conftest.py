"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import Mock
from ownfirebase import OwnFirebaseConfig, init_ownfirebase, OwnFirebase

@pytest.fixture
def config() -> OwnFirebaseConfig:
    """Fixture for OwnFirebaseConfig with test defaults."""
    return OwnFirebaseConfig(
        base_url='http://localhost:8000',
        project_id='test-project-123',
        access_token='test-token-xyz',
    )

@pytest.fixture
def app(config: OwnFirebaseConfig) -> OwnFirebase:
    """Fixture for initialized OwnFirebase SDK instance."""
    return init_ownfirebase(config)

@pytest.fixture
def config_no_project() -> OwnFirebaseConfig:
    """Fixture for config without project_id."""
    return OwnFirebaseConfig(
        base_url='http://localhost:8000',
        access_token='test-token-xyz',
    )

@pytest.fixture
def config_no_token() -> OwnFirebaseConfig:
    """Fixture for config without access token."""
    return OwnFirebaseConfig(
        base_url='http://localhost:8000',
        project_id='test-project-123',
    )

@pytest.fixture
def mock_response_success():
    """Fixture for successful mock response."""
    response = Mock()
    response.ok = True
    response.status_code = 200
    response.json.return_value = {'result': 'success'}
    return response

@pytest.fixture
def mock_response_created():
    """Fixture for 201 created mock response."""
    response = Mock()
    response.ok = True
    response.status_code = 201
    response.json.return_value = {'id': 'resource-123', 'created': True}
    return response

@pytest.fixture
def mock_response_no_content():
    """Fixture for 204 no content mock response."""
    response = Mock()
    response.ok = True
    response.status_code = 204
    return response

@pytest.fixture
def mock_response_error():
    """Fixture for error mock response."""
    response = Mock()
    response.ok = False
    response.status_code = 400
    response.reason = 'Bad Request'
    response.json.return_value = {'error': 'Invalid request'}
    return response
