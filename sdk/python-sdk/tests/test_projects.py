"""Tests for OwnFirebase Projects SDK."""

from unittest.mock import Mock, patch

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.projects import ProjectsSDK

BASE_URL = 'http://localhost:8000'
PROJECT_ID = 'test-project'
TOKEN = 'test-token'


def _ok(mock_request, json_data=None, status=200):
    resp = Mock()
    resp.ok = True
    resp.status_code = status
    resp.json.return_value = {} if json_data is None else json_data
    mock_request.return_value = resp
    return resp


def _kwargs(mock_request):
    return mock_request.call_args[1]


@pytest.fixture
def sdk():
    config = OwnFirebaseConfig(base_url=BASE_URL, project_id=PROJECT_ID, access_token=TOKEN)
    return ProjectsSDK(config)


class TestProjectsSDK:
    """Tests for the Projects SDK — one test per real method."""

    def test_projects_init(self, sdk):
        assert sdk.base_url == BASE_URL

    @patch('requests.request')
    def test_list_projects(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'next': None, 'previous': None, 'results': []})
        sdk.list_projects()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{BASE_URL}/api/v1/projects/'

    @patch('requests.request')
    def test_get_project(self, mock_request, sdk):
        _ok(mock_request, {'id': 'proj-1', 'name': 'My Project', 'slug': 'my-project'})
        result = sdk.get_project('proj-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{BASE_URL}/api/v1/projects/proj-1/'
        assert result['name'] == 'My Project'

    @patch('requests.request')
    def test_create_project(self, mock_request, sdk):
        _ok(mock_request, {'id': 'proj-1', 'name': 'My Project', 'description': 'desc'}, status=201)
        result = sdk.create_project('My Project', description='desc')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/projects/'
        assert kw['json'] == {'name': 'My Project', 'description': 'desc'}
        assert result['id'] == 'proj-1'

    @patch('requests.request')
    def test_create_project_without_description(self, mock_request, sdk):
        _ok(mock_request, {'id': 'proj-2', 'name': 'No Desc'}, status=201)
        sdk.create_project('No Desc')
        kw = _kwargs(mock_request)
        assert kw['json'] == {'name': 'No Desc'}

    @patch('requests.request')
    def test_update_project(self, mock_request, sdk):
        _ok(mock_request, {'id': 'proj-1', 'name': 'Renamed'})
        result = sdk.update_project('proj-1', name='Renamed', description='new desc')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'PATCH'
        assert kw['url'] == f'{BASE_URL}/api/v1/projects/proj-1/'
        assert kw['json'] == {'name': 'Renamed', 'description': 'new desc'}
        assert result['name'] == 'Renamed'

    @patch('requests.request')
    def test_update_project_partial(self, mock_request, sdk):
        _ok(mock_request, {'id': 'proj-1', 'name': 'Renamed'})
        sdk.update_project('proj-1', name='Renamed')
        kw = _kwargs(mock_request)
        assert kw['json'] == {'name': 'Renamed'}

    @patch('requests.request')
    def test_delete_project(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.delete_project('proj-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'DELETE'
        assert kw['url'] == f'{BASE_URL}/api/v1/projects/proj-1/'
        assert result is None

    @patch('requests.request')
    def test_list_members(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'next': None, 'previous': None, 'results': []})
        sdk.list_members('proj-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{BASE_URL}/api/v1/memberships/'
        assert kw['params'] == {'project': 'proj-1'}

    @patch('requests.request')
    def test_add_member(self, mock_request, sdk):
        _ok(mock_request, {'id': 'mem-1', 'user': 'user-1', 'role': 'editor'}, status=201)
        result = sdk.add_member('proj-1', 'user-1', 'editor')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/memberships/'
        assert kw['json'] == {'project': 'proj-1', 'user': 'user-1', 'role': 'editor'}
        assert result['role'] == 'editor'

    @patch('requests.request')
    def test_update_member_role(self, mock_request, sdk):
        _ok(mock_request, {'id': 'mem-1', 'role': 'viewer'})
        result = sdk.update_member_role('mem-1', 'viewer')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'PATCH'
        assert kw['url'] == f'{BASE_URL}/api/v1/memberships/mem-1/'
        assert kw['json'] == {'role': 'viewer'}
        assert result['role'] == 'viewer'

    @patch('requests.request')
    def test_remove_member(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.remove_member('mem-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'DELETE'
        assert kw['url'] == f'{BASE_URL}/api/v1/memberships/mem-1/'
        assert result is None
