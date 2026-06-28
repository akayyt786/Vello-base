"""
Phase 3: Cloud Functions tests.
Covers models, webhook tasks (mocked urllib), views, signals.
"""

import uuid
import json
from unittest.mock import MagicMock, patch, call
import urllib.error

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership, UserProfile
from functions.models import CloudFunction, FunctionLog
from functions import tasks as fn_tasks


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def make_client(user):
    refresh = RefreshToken.for_user(user)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return c


@pytest.fixture
def owner(db):
    u = User.objects.create_user('fn_owner@ex.com', 'fn_owner@ex.com', 'pass123')
    UserProfile.objects.create(user=u, sign_in_provider='password', email_verified=True)
    return u


@pytest.fixture
def viewer(db):
    u = User.objects.create_user('fn_viewer@ex.com', 'fn_viewer@ex.com', 'pass123')
    UserProfile.objects.create(user=u, sign_in_provider='password', email_verified=True)
    return u


@pytest.fixture
def project(db, owner):
    p = Project.objects.create(name='FnProj', slug='fn-proj', owner=owner, is_active=True)
    ProjectMembership.objects.create(project=p, user=owner, role='owner')
    return p


@pytest.fixture
def project_with_viewer(db, project, viewer):
    ProjectMembership.objects.create(project=project, user=viewer, role='viewer')
    return project


@pytest.fixture
def owner_client(owner):
    return make_client(owner)


@pytest.fixture
def viewer_client(viewer):
    return make_client(viewer)


@pytest.fixture
def http_function(db, project, owner):
    return CloudFunction.objects.create(
        project=project,
        name='my-http-fn',
        trigger_type=CloudFunction.TRIGGER_HTTP,
        endpoint_url='https://example.com/webhook',
        is_enabled=True,
        timeout_seconds=10,
        created_by=owner,
        updated_by=owner,
    )


@pytest.fixture
def doc_function(db, project, owner):
    return CloudFunction.objects.create(
        project=project,
        name='on-user-create',
        trigger_type=CloudFunction.TRIGGER_ON_CREATE,
        collection_path='users',
        endpoint_url='https://example.com/on-create',
        is_enabled=True,
        timeout_seconds=10,
        created_by=owner,
        updated_by=owner,
    )


# ---------------------------------------------------------------------------
# CloudFunction model tests
# ---------------------------------------------------------------------------

class TestCloudFunctionModel:
    def test_create_http_function(self, db, project, owner):
        fn = CloudFunction.objects.create(
            project=project,
            name='hello-world',
            trigger_type='http',
            endpoint_url='https://my-server.com/hello',
            created_by=owner,
            updated_by=owner,
        )
        assert fn.is_enabled is True
        assert fn.timeout_seconds == 30
        assert fn.retry_count == 0
        assert fn.extra_headers == {}
        assert str(fn.id)

    def test_create_scheduled_function(self, db, project, owner):
        fn = CloudFunction.objects.create(
            project=project,
            name='daily-cleanup',
            trigger_type='scheduled',
            schedule='0 2 * * *',
            endpoint_url='https://my-server.com/cleanup',
            created_by=owner,
            updated_by=owner,
        )
        assert fn.schedule == '0 2 * * *'

    def test_create_document_trigger_function(self, db, project, owner):
        fn = CloudFunction.objects.create(
            project=project,
            name='user-created',
            trigger_type='on_create',
            collection_path='users',
            endpoint_url='https://my-server.com/user-created',
            created_by=owner,
            updated_by=owner,
        )
        assert fn.collection_path == 'users'

    def test_unique_name_per_project(self, db, project, owner, http_function):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            CloudFunction.objects.create(
                project=project,
                name='my-http-fn',
                trigger_type='http',
                endpoint_url='https://other.com/webhook',
                created_by=owner,
                updated_by=owner,
            )

    def test_str_representation(self, http_function):
        assert 'fn-proj' in str(http_function)
        assert 'my-http-fn' in str(http_function)

    def test_trigger_type_choices(self):
        choices = dict(CloudFunction.TRIGGER_CHOICES)
        assert 'http' in choices
        assert 'on_create' in choices
        assert 'on_update' in choices
        assert 'on_delete' in choices
        assert 'scheduled' in choices
        assert 'on_storage' in choices
        assert 'on_auth' in choices


# ---------------------------------------------------------------------------
# FunctionLog model tests
# ---------------------------------------------------------------------------

class TestFunctionLogModel:
    def test_create_log(self, db, http_function):
        log = FunctionLog.objects.create(
            function=http_function,
            trigger_data={'event': 'http'},
            status=FunctionLog.STATUS_RUNNING,
        )
        assert log.status == 'running'
        assert log.response_status is None
        assert log.duration_ms is None

    def test_log_statuses(self):
        choices = dict(FunctionLog.STATUS_CHOICES)
        assert 'running' in choices
        assert 'success' in choices
        assert 'error' in choices
        assert 'timeout' in choices

    def test_log_fk_cascade_delete(self, db, http_function):
        log = FunctionLog.objects.create(
            function=http_function,
            trigger_data={},
            status='running',
        )
        log_id = log.id
        http_function.delete()
        assert not FunctionLog.objects.filter(id=log_id).exists()


# ---------------------------------------------------------------------------
# _post_webhook helper tests (mocked urllib)
# ---------------------------------------------------------------------------

class TestPostWebhook:
    def _make_mock_resp(self, status_code, body):
        mock_resp = MagicMock()
        mock_resp.status = status_code
        mock_resp.read.return_value = body.encode('utf-8')
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    @patch('functions.tasks._OPENER.open')
    def test_success_response(self, mock_urlopen):
        mock_urlopen.return_value = self._make_mock_resp(200, '{"ok": true}')
        result = fn_tasks._post_webhook(
            'https://example.com/hook', {'event': 'test'}, timeout=10,
        )
        assert result['status'] == 'success'
        assert result['response_status'] == 200
        assert '{"ok": true}' in result['response_body']
        assert result['duration_ms'] >= 0

    @patch('functions.tasks._OPENER.open')
    def test_http_error_response(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='https://example.com/hook',
            code=500,
            msg='Internal Server Error',
            hdrs=None,
            fp=MagicMock(read=lambda: b'error body'),
        )
        result = fn_tasks._post_webhook(
            'https://example.com/hook', {'event': 'test'}, timeout=10,
        )
        assert result['status'] == 'error'
        assert result['response_status'] == 500
        assert 'HTTP 500' in result['error']

    @patch('functions.tasks._OPENER.open')
    def test_timeout_response(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError('timed out')
        result = fn_tasks._post_webhook(
            'https://example.com/hook', {'event': 'test'}, timeout=1,
        )
        assert result['status'] == 'timeout'
        assert result['response_status'] is None

    @patch('functions.tasks._OPENER.open')
    def test_secret_header_added(self, mock_urlopen):
        mock_urlopen.return_value = self._make_mock_resp(200, 'ok')
        fn_tasks._post_webhook(
            'https://example.com/hook', {}, timeout=5,
            secret='my-secret',
        )
        req = mock_urlopen.call_args[0][0]
        assert req.get_header('X-ownfirebase-secret') == 'my-secret'

    @patch('functions.tasks._OPENER.open')
    def test_extra_headers_added(self, mock_urlopen):
        mock_urlopen.return_value = self._make_mock_resp(200, 'ok')
        fn_tasks._post_webhook(
            'https://example.com/hook', {}, timeout=5,
            extra_headers={'X-Custom': 'value'},
        )
        req = mock_urlopen.call_args[0][0]
        assert req.get_header('X-custom') == 'value'

    @patch('functions.tasks._OPENER.open')
    def test_general_exception_returns_error(self, mock_urlopen):
        mock_urlopen.side_effect = ConnectionRefusedError('connection refused')
        result = fn_tasks._post_webhook(
            'https://example.com/hook', {}, timeout=5,
        )
        assert result['status'] == 'error'
        assert result['response_status'] is None


# ---------------------------------------------------------------------------
# invoke_function_for_event task tests
# ---------------------------------------------------------------------------

class TestInvokeFunctionForEvent:
    def _make_mock_urlopen(self, status_code=200, body='ok'):
        mock_resp = MagicMock()
        mock_resp.status = status_code
        mock_resp.read.return_value = body.encode('utf-8')
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    @patch('functions.tasks._OPENER.open')
    def test_invoke_success(self, mock_urlopen, db, http_function):
        mock_urlopen.return_value = self._make_mock_urlopen(200, 'ok')
        result = fn_tasks.invoke_function_for_event(str(http_function.id), {'event': 'http'})
        assert result['status'] == 'success'
        log = FunctionLog.objects.filter(function=http_function).first()
        assert log is not None
        assert log.status == 'success'

    @patch('functions.tasks._OPENER.open')
    def test_invoke_creates_log_running_then_updates(self, mock_urlopen, db, http_function):
        mock_urlopen.return_value = self._make_mock_urlopen(200, '{"result": "done"}')
        fn_tasks.invoke_function_for_event(str(http_function.id), {'event': 'http'})
        log = FunctionLog.objects.filter(function=http_function).latest('created_at')
        assert log.status == 'success'
        assert log.response_status == 200
        assert log.duration_ms is not None

    def test_invoke_skips_disabled_function(self, db, project, owner):
        disabled = CloudFunction.objects.create(
            project=project, name='disabled-fn', trigger_type='http',
            endpoint_url='https://example.com/x', is_enabled=False,
            created_by=owner, updated_by=owner,
        )
        result = fn_tasks.invoke_function_for_event(str(disabled.id), {})
        assert result['skipped'] is True

    def test_invoke_nonexistent_function_returns_skipped(self, db):
        result = fn_tasks.invoke_function_for_event(str(uuid.uuid4()), {})
        assert result['skipped'] is True

    @patch('functions.tasks._OPENER.open')
    def test_invoke_stores_error_on_webhook_failure(self, mock_urlopen, db, http_function):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='https://example.com/webhook', code=503, msg='Service Unavailable',
            hdrs=None, fp=MagicMock(read=lambda: b'fail'),
        )
        result = fn_tasks.invoke_function_for_event(str(http_function.id), {'event': 'http'})
        assert result['status'] == 'error'
        log = FunctionLog.objects.filter(function=http_function).latest('created_at')
        assert log.status == 'error'
        assert log.response_status == 503


# ---------------------------------------------------------------------------
# Function list/create view tests
# ---------------------------------------------------------------------------

class TestFunctionListView:
    URL = '/api/projects/{project_id}/functions/'

    def test_list_functions(self, owner_client, project, http_function):
        resp = owner_client.get(self.URL.format(project_id=project.id))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['functions']) == 1
        assert data['functions'][0]['name'] == 'my-http-fn'

    def test_list_functions_with_trigger_filter(self, owner_client, project, http_function, doc_function):
        resp = owner_client.get(
            self.URL.format(project_id=project.id) + '?trigger_type=http'
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['functions']) == 1
        assert data['functions'][0]['trigger_type'] == 'http'

    def test_list_functions_viewer_can_read(self, viewer_client, project_with_viewer, http_function):
        resp = viewer_client.get(self.URL.format(project_id=project_with_viewer.id))
        assert resp.status_code == 200

    def test_list_functions_unauthenticated_returns_401(self, api_client, project):
        resp = api_client.get(self.URL.format(project_id=project.id))
        assert resp.status_code == 401

    def test_create_http_function(self, owner_client, project):
        resp = owner_client.post(
            self.URL.format(project_id=project.id),
            {
                'name': 'new-fn',
                'trigger_type': 'http',
                'endpoint_url': 'https://example.com/new',
            },
            format='json',
        )
        assert resp.status_code == 201
        assert resp.json()['name'] == 'new-fn'

    def test_create_function_viewer_forbidden(self, viewer_client, project_with_viewer):
        resp = viewer_client.post(
            self.URL.format(project_id=project_with_viewer.id),
            {'name': 'bad', 'trigger_type': 'http', 'endpoint_url': 'https://x.com'},
            format='json',
        )
        assert resp.status_code == 403

    def test_create_doc_trigger_requires_collection_path(self, owner_client, project):
        resp = owner_client.post(
            self.URL.format(project_id=project.id),
            {
                'name': 'bad-trigger',
                'trigger_type': 'on_create',
                'endpoint_url': 'https://example.com/x',
            },
            format='json',
        )
        assert resp.status_code == 400

    def test_create_scheduled_requires_schedule(self, owner_client, project):
        resp = owner_client.post(
            self.URL.format(project_id=project.id),
            {
                'name': 'bad-scheduled',
                'trigger_type': 'scheduled',
                'endpoint_url': 'https://example.com/x',
            },
            format='json',
        )
        assert resp.status_code == 400

    def test_create_wrong_project_returns_404(self, owner_client):
        resp = owner_client.post(
            self.URL.format(project_id=uuid.uuid4()),
            {'name': 'fn', 'trigger_type': 'http', 'endpoint_url': 'https://x.com'},
            format='json',
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Function detail view tests
# ---------------------------------------------------------------------------

class TestFunctionDetailView:
    def _url(self, project_id, name):
        return f'/api/projects/{project_id}/functions/{name}/'

    def test_get_function(self, owner_client, project, http_function):
        resp = owner_client.get(self._url(project.id, 'my-http-fn'))
        assert resp.status_code == 200
        assert resp.json()['trigger_type'] == 'http'

    def test_get_nonexistent_returns_404(self, owner_client, project):
        resp = owner_client.get(self._url(project.id, 'ghost-fn'))
        assert resp.status_code == 404

    def test_update_function(self, owner_client, project, http_function):
        resp = owner_client.put(
            self._url(project.id, 'my-http-fn'),
            {'endpoint_url': 'https://example.com/new-hook'},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.json()['endpoint_url'] == 'https://example.com/new-hook'

    def test_update_function_viewer_forbidden(self, viewer_client, project_with_viewer, http_function):
        resp = viewer_client.put(
            self._url(project_with_viewer.id, 'my-http-fn'),
            {'endpoint_url': 'https://example.com/other'},
            format='json',
        )
        assert resp.status_code == 403

    def test_delete_function(self, owner_client, project, http_function):
        resp = owner_client.delete(self._url(project.id, 'my-http-fn'))
        assert resp.status_code == 204
        assert not CloudFunction.objects.filter(id=http_function.id).exists()

    def test_delete_function_viewer_forbidden(self, viewer_client, project_with_viewer, http_function):
        resp = viewer_client.delete(self._url(project_with_viewer.id, 'my-http-fn'))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Function invoke view tests
# ---------------------------------------------------------------------------

class TestFunctionInvokeView:
    def _url(self, project_id, name):
        return f'/api/projects/{project_id}/functions/{name}/invoke/'

    @patch('functions.tasks.invoke_function_for_event')
    def test_invoke_http_function(self, mock_task, owner_client, project, http_function):
        mock_task.delay.return_value = MagicMock(id='task-123')
        resp = owner_client.post(
            self._url(project.id, 'my-http-fn'),
            {'data': {'key': 'value'}},
            format='json',
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data['status'] == 'queued'
        assert data['task_id'] == 'task-123'
        mock_task.delay.assert_called_once()

    def test_invoke_non_http_returns_404(self, owner_client, project, doc_function):
        resp = owner_client.post(
            self._url(project.id, 'on-user-create'),
            {},
            format='json',
        )
        assert resp.status_code == 404

    @patch('functions.tasks.invoke_function_for_event')
    def test_invoke_disabled_function_returns_404(self, mock_task, owner_client, project, db, owner):
        disabled = CloudFunction.objects.create(
            project=project, name='disabled', trigger_type='http',
            endpoint_url='https://x.com', is_enabled=False,
            created_by=owner, updated_by=owner,
        )
        resp = owner_client.post(self._url(project.id, 'disabled'), {}, format='json')
        assert resp.status_code == 404

    def test_invoke_unauthenticated_returns_401(self, api_client, project, http_function):
        resp = api_client.post(self._url(project.id, 'my-http-fn'), {}, format='json')
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Function logs view tests
# ---------------------------------------------------------------------------

class TestFunctionLogsView:
    def _url(self, project_id, name):
        return f'/api/projects/{project_id}/functions/{name}/logs/'

    def test_list_logs(self, owner_client, project, http_function):
        FunctionLog.objects.create(
            function=http_function,
            trigger_data={'event': 'http'},
            status='success',
            response_status=200,
            duration_ms=55,
        )
        resp = owner_client.get(self._url(project.id, 'my-http-fn'))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['logs']) == 1
        assert data['logs'][0]['status'] == 'success'

    def test_list_logs_limit_param(self, owner_client, project, http_function):
        for i in range(10):
            FunctionLog.objects.create(
                function=http_function,
                trigger_data={'i': i},
                status='success',
            )
        resp = owner_client.get(self._url(project.id, 'my-http-fn') + '?limit=3')
        assert resp.status_code == 200
        assert len(resp.json()['logs']) == 3

    def test_list_logs_viewer_can_read(self, viewer_client, project_with_viewer, http_function):
        resp = viewer_client.get(self._url(project_with_viewer.id, 'my-http-fn'))
        assert resp.status_code == 200

    def test_list_logs_unauthenticated_returns_401(self, api_client, project, http_function):
        resp = api_client.get(self._url(project.id, 'my-http-fn'))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Functions signals tests (document event triggers)
# ---------------------------------------------------------------------------

class TestFunctionSignals:
    @patch('functions.tasks.invoke_function_for_event')
    def test_document_create_triggers_on_create_functions(self, mock_task, db, project, doc_function):
        from data.models import Collection, Document
        Collection.objects.get_or_create(
            project=project, name='users', path='users',
            defaults={'schema': {}},
        )
        Document.objects.create(
            project=project,
            collection_path='users',
            doc_id='new-user-1',
            data={'name': 'Bob'},
        )
        mock_task.delay.assert_called()
        call_args = mock_task.delay.call_args
        assert str(doc_function.id) == call_args[0][0]
        assert call_args[0][1]['event'] == 'on_create'

    @patch('functions.tasks.invoke_function_for_event')
    def test_document_update_triggers_on_update_functions(self, mock_task, db, project, owner):
        from data.models import Collection, Document
        update_fn = CloudFunction.objects.create(
            project=project, name='on-update', trigger_type='on_update',
            collection_path='users', endpoint_url='https://x.com',
            created_by=owner, updated_by=owner,
        )
        Collection.objects.get_or_create(
            project=project, name='users', path='users',
            defaults={'schema': {}},
        )
        doc = Document.objects.create(
            project=project, collection_path='users', doc_id='bob',
            data={'name': 'Bob'},
        )
        mock_task.delay.reset_mock()
        doc.data = {'name': 'Bobby'}
        doc.save()
        mock_task.delay.assert_called()
        call_args = mock_task.delay.call_args
        assert call_args[0][1]['event'] == 'on_update'

    @patch('functions.tasks.invoke_function_for_event')
    def test_document_delete_triggers_on_delete_functions(self, mock_task, db, project, owner):
        from data.models import Collection, Document
        del_fn = CloudFunction.objects.create(
            project=project, name='on-delete', trigger_type='on_delete',
            collection_path='users', endpoint_url='https://x.com',
            created_by=owner, updated_by=owner,
        )
        Collection.objects.get_or_create(
            project=project, name='users', path='users',
            defaults={'schema': {}},
        )
        doc = Document.objects.create(
            project=project, collection_path='users', doc_id='to-delete',
            data={'name': 'Eve'},
        )
        mock_task.delay.reset_mock()
        doc.delete()
        mock_task.delay.assert_called()
        call_args = mock_task.delay.call_args
        assert call_args[0][1]['event'] == 'on_delete'

    @patch('functions.tasks.invoke_function_for_event')
    def test_signal_does_not_fire_for_wrong_collection(self, mock_task, db, project, doc_function):
        from data.models import Collection, Document
        Collection.objects.get_or_create(
            project=project, name='orders', path='orders',
            defaults={'schema': {}},
        )
        Document.objects.create(
            project=project, collection_path='orders', doc_id='order-1',
            data={'total': 99},
        )
        mock_task.delay.assert_not_called()

    @patch('functions.tasks.invoke_function_for_event')
    def test_disabled_function_not_triggered(self, mock_task, db, project, owner):
        from data.models import Collection, Document
        CloudFunction.objects.create(
            project=project, name='disabled-trigger', trigger_type='on_create',
            collection_path='users', endpoint_url='https://x.com',
            is_enabled=False, created_by=owner, updated_by=owner,
        )
        Collection.objects.get_or_create(
            project=project, name='users', path='users',
            defaults={'schema': {}},
        )
        Document.objects.create(
            project=project, collection_path='users', doc_id='new',
            data={'name': 'X'},
        )
        mock_task.delay.assert_not_called()
