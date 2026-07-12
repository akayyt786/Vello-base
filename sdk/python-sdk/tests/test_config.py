"""Tests for SDK configuration."""

import pytest
from ownfirebase import OwnFirebaseConfig, init_ownfirebase, OwnFirebase

def test_config_init():
    config = OwnFirebaseConfig(
        base_url='http://api.example.com',
        project_id='proj-123',
        access_token='token-xyz',
    )
    assert config.base_url == 'http://api.example.com'
    assert config.project_id == 'proj-123'

def test_config_strips_trailing_slash():
    config = OwnFirebaseConfig(base_url='http://api.example.com/')
    assert config.base_url == 'http://api.example.com'

def test_init_ownfirebase():
    config = OwnFirebaseConfig(base_url='http://localhost:8000')
    app = init_ownfirebase(config)
    assert isinstance(app, OwnFirebase)
    assert app.auth is not None
    assert app.data is not None

def test_set_access_token(app):
    app.set_access_token('new-token-123')
    assert app.auth.access_token == 'new-token-123'
    assert app.data.access_token == 'new-token-123'

def test_set_project_id(app):
    app.set_project_id('new-project-xyz')
    assert app.auth.project_id == 'new-project-xyz'
    assert app.data.project_id == 'new-project-xyz'
