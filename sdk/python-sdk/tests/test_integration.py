"""Integration tests for OwnFirebase SDK.

These tests can be run against a live backend running on localhost:8000.
Set INTEGRATION_TESTS=true environment variable to enable these tests.
Otherwise, they are skipped.
"""

import os
import pytest
from ownfirebase import OwnFirebaseConfig, init_ownfirebase, APIError

# Skip all tests in this module unless explicitly enabled
pytestmark = pytest.mark.skipif(
    not os.getenv('INTEGRATION_TESTS'),
    reason="Integration tests require INTEGRATION_TESTS=true and a running backend"
)


class TestIntegration:
    """Live integration tests against backend."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for integration tests."""
        self.backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.project_id = os.getenv('TEST_PROJECT_ID', 'test-project')
        self.access_token = os.getenv('TEST_ACCESS_TOKEN', 'test-token')

    def test_backend_health(self):
        """Test backend is accessible."""
        import requests
        try:
            response = requests.get(f'{self.backend_url}/health', timeout=5)
            assert response.status_code == 200
        except requests.exceptions.RequestException:
            pytest.skip("Backend not available")

    def test_init_sdk(self):
        """Test initializing SDK."""
        config = OwnFirebaseConfig(
            base_url=self.backend_url,
            project_id=self.project_id,
            access_token=self.access_token
        )
        app = init_ownfirebase(config)
        assert app is not None
        assert app.auth is not None
        assert app.data is not None

    def test_auth_module_exists(self):
        """Test auth module is accessible."""
        config = OwnFirebaseConfig(
            base_url=self.backend_url,
            project_id=self.project_id,
            access_token=self.access_token
        )
        app = init_ownfirebase(config)
        assert hasattr(app, 'auth')

    def test_data_module_exists(self):
        """Test data module is accessible."""
        config = OwnFirebaseConfig(
            base_url=self.backend_url,
            project_id=self.project_id,
            access_token=self.access_token
        )
        app = init_ownfirebase(config)
        assert hasattr(app, 'data')

    def test_all_modules_initialized(self):
        """Test all SDK modules are initialized."""
        config = OwnFirebaseConfig(
            base_url=self.backend_url,
            project_id=self.project_id,
            access_token=self.access_token
        )
        app = init_ownfirebase(config)

        modules = [
            'auth', 'data', 'storage', 'functions', 'realtime',
            'analytics', 'remote_config', 'crashlytics', 'abtesting',
            'push', 'projects', 'appcheck'
        ]

        for module in modules:
            assert hasattr(app, module), f"Module {module} not found"


class TestDataIntegration:
    """Integration tests for Data SDK."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for data integration tests."""
        self.backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.project_id = os.getenv('TEST_PROJECT_ID', 'test-project')
        self.access_token = os.getenv('TEST_ACCESS_TOKEN', 'test-token')

        self.config = OwnFirebaseConfig(
            base_url=self.backend_url,
            project_id=self.project_id,
            access_token=self.access_token
        )
        self.app = init_ownfirebase(self.config)

    def test_create_document_integration(self):
        """Test creating a document via live API."""
        try:
            result = self.app.data.request(
                'POST',
                self.app.data.project_url('data/collections/test/documents'),
                json_data={'name': 'integration-test', 'value': 42}
            )
            # If we get here, API is working
            assert result is not None
        except APIError as e:
            # Expected if backend auth fails
            if e.status == 401:
                pytest.skip("Authentication failed - check test token")
            raise

    def test_list_collections_integration(self):
        """Test listing collections via live API."""
        try:
            result = self.app.data.request(
                'GET',
                self.app.data.project_url('data/collections')
            )
            assert isinstance(result, dict)
        except APIError as e:
            if e.status == 401:
                pytest.skip("Authentication failed")
            raise


class TestAuthIntegration:
    """Integration tests for Auth SDK."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for auth integration tests."""
        self.backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.project_id = os.getenv('TEST_PROJECT_ID', 'test-project')
        self.access_token = os.getenv('TEST_ACCESS_TOKEN', 'test-token')

        self.config = OwnFirebaseConfig(
            base_url=self.backend_url,
            project_id=self.project_id,
            access_token=self.access_token
        )
        self.app = init_ownfirebase(self.config)

    def test_auth_module_initialized(self):
        """Test auth module is ready."""
        assert self.app.auth is not None
        assert self.app.auth.base_url == self.backend_url
        assert self.app.auth.project_id == self.project_id


class TestAnalyticsIntegration:
    """Integration tests for Analytics SDK."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for analytics integration tests."""
        self.backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.project_id = os.getenv('TEST_PROJECT_ID', 'test-project')
        self.access_token = os.getenv('TEST_ACCESS_TOKEN', 'test-token')

        self.config = OwnFirebaseConfig(
            base_url=self.backend_url,
            project_id=self.project_id,
            access_token=self.access_token
        )
        self.app = init_ownfirebase(self.config)

    def test_analytics_module_initialized(self):
        """Test analytics module is ready."""
        assert self.app.analytics is not None
        assert self.app.analytics.base_url == self.backend_url


class TestPushIntegration:
    """Integration tests for Push Notifications SDK."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for push integration tests."""
        self.backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.project_id = os.getenv('TEST_PROJECT_ID', 'test-project')
        self.access_token = os.getenv('TEST_ACCESS_TOKEN', 'test-token')

        self.config = OwnFirebaseConfig(
            base_url=self.backend_url,
            project_id=self.project_id,
            access_token=self.access_token
        )
        self.app = init_ownfirebase(self.config)

    def test_push_module_initialized(self):
        """Test push module is ready."""
        assert self.app.push is not None


class TestStorageIntegration:
    """Integration tests for Storage SDK."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for storage integration tests."""
        self.backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.project_id = os.getenv('TEST_PROJECT_ID', 'test-project')
        self.access_token = os.getenv('TEST_ACCESS_TOKEN', 'test-token')

        self.config = OwnFirebaseConfig(
            base_url=self.backend_url,
            project_id=self.project_id,
            access_token=self.access_token
        )
        self.app = init_ownfirebase(self.config)

    def test_storage_module_initialized(self):
        """Test storage module is ready."""
        assert self.app.storage is not None
