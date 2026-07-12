"""
Tests for health check endpoints.
"""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestHealthEndpoints:
    """Tests for liveness and readiness probes."""

    def test_liveness_returns_ok(self, api_client):
        """Test /health/ returns 200 with status ok."""
        url = reverse('health')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}

    def test_readiness_returns_ok_when_healthy(self, api_client):
        """Test /ready/ returns 200 with status ok when DB/cache are healthy."""
        url = reverse('ready')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['status'] == 'ok'
        assert data['checks']['database'] == 'ok'
        assert data['checks']['cache'] == 'ok'

    def test_readiness_returns_503_when_database_fails(self, api_client):
        """Test /ready/ returns 503 when the database check fails."""
        url = reverse('ready')
        with patch('django.db.connection.cursor', side_effect=Exception('connection refused')):
            response = api_client.get(url)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data['status'] == 'unavailable'
        assert 'error: connection refused' in data['checks']['database']
        assert data['checks']['cache'] == 'ok'
