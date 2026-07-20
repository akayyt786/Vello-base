"""
Phase 4 comprehensive tests: Analytics, Remote Config, and Crashlytics apps.

Covers:
  - Analytics: event logging, batch, user properties, conversion events, query
  - Config: remote config parameters, fetch, publish
  - Crashlytics: crash reports, crash grouping, crash groups, performance traces, summary

A/B experiments used to be tested here too (config.Experiment), but that model
was a duplicate of the dedicated abtesting app (which SDKs actually use, and
which additionally tracks assignment/conversion) -- see tests/test_phase5a.py's
TestABTesting for the real, current experiment coverage.
"""

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership, UserProfile
from analytics.models import Event, UserProperty, ConversionEvent
from config.models import RemoteConfig, ConfigVersion
from crashlytics.models import CrashGroup, CrashReport, PerformanceTrace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(user):
    """Return an authenticated APIClient for the given user."""
    refresh = RefreshToken.for_user(user)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return c


def now_iso():
    """Return current UTC time as an ISO 8601 string for event payloads."""
    return timezone.now().isoformat()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def owner(db):
    u = User.objects.create_user('phase4_owner@ex.com', 'phase4_owner@ex.com', 'pass123')
    UserProfile.objects.create(user=u, sign_in_provider='password', email_verified=True)
    return u


@pytest.fixture
def editor(db):
    u = User.objects.create_user('phase4_editor@ex.com', 'phase4_editor@ex.com', 'pass123')
    UserProfile.objects.create(user=u, sign_in_provider='password', email_verified=True)
    return u


@pytest.fixture
def viewer(db):
    u = User.objects.create_user('phase4_viewer@ex.com', 'phase4_viewer@ex.com', 'pass123')
    UserProfile.objects.create(user=u, sign_in_provider='password', email_verified=True)
    return u


@pytest.fixture
def outsider(db):
    """A user who is not a member of the primary project."""
    u = User.objects.create_user('phase4_outsider@ex.com', 'phase4_outsider@ex.com', 'pass123')
    UserProfile.objects.create(user=u, sign_in_provider='password', email_verified=True)
    return u


@pytest.fixture
def project(db, owner):
    p = Project.objects.create(
        name='Phase4 Project',
        slug='phase4-proj',
        owner=owner,
        is_active=True,
    )
    ProjectMembership.objects.create(project=p, user=owner, role='owner')
    return p


@pytest.fixture
def project_with_editor(db, project, editor):
    ProjectMembership.objects.create(project=project, user=editor, role='editor')
    return project


@pytest.fixture
def project_with_viewer(db, project, viewer):
    ProjectMembership.objects.create(project=project, user=viewer, role='viewer')
    return project


@pytest.fixture
def project2(db, outsider):
    """Second project owned by outsider — used for cross-project isolation tests."""
    p = Project.objects.create(
        name='Phase4 Project 2',
        slug='phase4-proj-2',
        owner=outsider,
        is_active=True,
    )
    ProjectMembership.objects.create(project=p, user=outsider, role='owner')
    return p


@pytest.fixture
def owner_client(owner):
    return make_client(owner)


@pytest.fixture
def editor_client(editor):
    return make_client(editor)


@pytest.fixture
def viewer_client(viewer):
    return make_client(viewer)


@pytest.fixture
def outsider_client(outsider):
    return make_client(outsider)


@pytest.fixture
def anon_client():
    return APIClient()


# ---------------------------------------------------------------------------
# Analytics: TestAnalyticsEvents
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAnalyticsEvents:
    EVENTS_URL = '/api/projects/{pid}/analytics/events/'
    BATCH_URL = '/api/projects/{pid}/analytics/events/batch/'

    def test_log_single_event_as_member(self, owner_client, project):
        """Any project member (owner role) can log an analytics event."""
        resp = owner_client.post(
            self.EVENTS_URL.format(pid=project.id),
            {
                'event_name': 'page_view',
                'platform': 'web',
                'occurred_at': now_iso(),
            },
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['event_name'] == 'page_view'
        assert data['platform'] == 'web'

    def test_log_event_with_params(self, owner_client, project):
        """Event params JSON is stored and returned verbatim."""
        resp = owner_client.post(
            self.EVENTS_URL.format(pid=project.id),
            {
                'event_name': 'purchase',
                'event_params': {'item': 'widget', 'price': 9.99},
                'platform': 'android',
                'occurred_at': now_iso(),
            },
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['event_params']['item'] == 'widget'

    def test_unauthenticated_rejected_events(self, anon_client, project):
        """Unauthenticated requests to the events endpoint must return 401."""
        resp = anon_client.post(
            self.EVENTS_URL.format(pid=project.id),
            {'event_name': 'anon_event', 'occurred_at': now_iso()},
            format='json',
        )
        assert resp.status_code == 401

    def test_list_events_own_project_only(self, owner_client, project, project2, outsider_client):
        """GET events only returns events belonging to the requested project."""
        # Create an event in project
        Event.objects.create(
            project=project,
            event_name='proj1_event',
            occurred_at=timezone.now(),
        )
        # Create an event in project2
        Event.objects.create(
            project=project2,
            event_name='proj2_event',
            occurred_at=timezone.now(),
        )

        resp = owner_client.get(self.EVENTS_URL.format(pid=project.id))
        assert resp.status_code == 200
        results = resp.json()
        items = results if isinstance(results, list) else results.get('results', results)
        names = [e['event_name'] for e in items]
        assert 'proj1_event' in names
        assert 'proj2_event' not in names

    def test_events_cross_project_isolation_non_member(self, owner_client, project2):
        """A user who is not a member of project2 gets 404 when accessing project2 events."""
        resp = owner_client.get(self.EVENTS_URL.format(pid=project2.id))
        assert resp.status_code == 404

    def test_batch_events_success(self, owner_client, project):
        """Batch endpoint accepts a list and creates multiple events atomically."""
        payload = [
            {'event_name': 'batch_event_1', 'platform': 'web', 'occurred_at': now_iso()},
            {'event_name': 'batch_event_2', 'platform': 'ios', 'occurred_at': now_iso()},
            {'event_name': 'batch_event_3', 'platform': 'android', 'occurred_at': now_iso()},
        ]
        resp = owner_client.post(
            self.BATCH_URL.format(pid=project.id),
            payload,
            format='json',
        )
        assert resp.status_code == 201
        assert resp.json()['count'] == 3
        assert Event.objects.filter(project=project, event_name__startswith='batch_event_').count() == 3

    def test_batch_events_over_500_rejected(self, owner_client, project):
        """Batch endpoint rejects payloads with more than 500 events."""
        payload = [
            {'event_name': f'e{i}', 'occurred_at': now_iso()}
            for i in range(501)
        ]
        resp = owner_client.post(
            self.BATCH_URL.format(pid=project.id),
            payload,
            format='json',
        )
        assert resp.status_code == 400
        assert 'error' in resp.json()

    def test_batch_events_empty_list_returns_zero(self, owner_client, project):
        """Empty batch returns 200 with count=0."""
        resp = owner_client.post(
            self.BATCH_URL.format(pid=project.id),
            [],
            format='json',
        )
        assert resp.status_code == 200
        assert resp.json()['count'] == 0

    def test_batch_events_non_list_rejected(self, owner_client, project):
        """Batch endpoint must reject a non-list body (e.g., a plain dict)."""
        resp = owner_client.post(
            self.BATCH_URL.format(pid=project.id),
            {'event_name': 'not_a_list', 'occurred_at': now_iso()},
            format='json',
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Analytics: TestUserProperties
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserProperties:
    PROPS_URL = '/api/projects/{pid}/analytics/user-properties/'
    SET_URL = '/api/projects/{pid}/analytics/user-properties/set/'

    def test_set_user_properties_bulk_upsert(self, owner_client, project):
        """set/ endpoint upserts multiple user properties in one call."""
        resp = owner_client.post(
            self.SET_URL.format(pid=project.id),
            {
                'user_id': 'user-abc',
                'properties': {'plan': 'pro', 'country': 'US'},
            },
            format='json',
        )
        assert resp.status_code == 200
        assert resp.json()['updated'] == 2
        assert UserProperty.objects.filter(project=project, user_id='user-abc').count() == 2

    def test_set_user_properties_upsert_updates_existing(self, owner_client, project):
        """Calling set/ twice on the same user+property updates rather than duplicates."""
        for val in ('free', 'pro'):
            owner_client.post(
                self.SET_URL.format(pid=project.id),
                {'user_id': 'user-xyz', 'properties': {'plan': val}},
                format='json',
            )
        props = UserProperty.objects.filter(project=project, user_id='user-xyz', name='plan')
        assert props.count() == 1
        assert props.first().value == 'pro'

    def test_set_user_properties_missing_user_id_rejected(self, owner_client, project):
        """Missing user_id must return 400."""
        resp = owner_client.post(
            self.SET_URL.format(pid=project.id),
            {'properties': {'plan': 'free'}},
            format='json',
        )
        assert resp.status_code == 400
        assert 'error' in resp.json()

    def test_set_user_properties_invalid_properties_type_rejected(self, owner_client, project):
        """properties field must be a JSON object; lists and strings are rejected."""
        resp = owner_client.post(
            self.SET_URL.format(pid=project.id),
            {'user_id': 'u1', 'properties': ['plan', 'pro']},
            format='json',
        )
        assert resp.status_code == 400

    def test_list_user_properties(self, owner_client, project):
        """GET user-properties/ lists properties belonging to the project."""
        UserProperty.objects.create(project=project, user_id='u2', name='theme', value='dark')
        resp = owner_client.get(self.PROPS_URL.format(pid=project.id))
        assert resp.status_code == 200
        results = resp.json()
        items = results if isinstance(results, list) else results.get('results', results)
        assert any(p['name'] == 'theme' for p in items)


# ---------------------------------------------------------------------------
# Analytics: TestConversionEvents
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConversionEvents:
    CE_URL = '/api/projects/{pid}/analytics/conversion-events/'

    def test_create_conversion_event_as_editor(self, project_with_editor, editor_client, project):
        """Editors can register a conversion event name."""
        resp = editor_client.post(
            self.CE_URL.format(pid=project.id),
            {'event_name': 'purchase'},
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['event_name'] == 'purchase'
        assert ConversionEvent.objects.filter(project=project, event_name='purchase').exists()

    def test_create_conversion_event_as_owner(self, owner_client, project):
        """Owners (who have editor-level access) can create conversion events."""
        resp = owner_client.post(
            self.CE_URL.format(pid=project.id),
            {'event_name': 'signup'},
            format='json',
        )
        assert resp.status_code == 201

    def test_create_conversion_event_fails_for_viewer(self, project_with_viewer, viewer_client, project):
        """Viewers must not be able to create conversion events."""
        resp = viewer_client.post(
            self.CE_URL.format(pid=project.id),
            {'event_name': 'add_to_cart'},
            format='json',
        )
        assert resp.status_code in (403, 404)

    def test_list_conversion_events(self, owner_client, project):
        """GET conversion-events/ returns all registered conversion events for the project."""
        ConversionEvent.objects.create(project=project, event_name='checkout')
        resp = owner_client.get(self.CE_URL.format(pid=project.id))
        assert resp.status_code == 200
        results = resp.json()
        items = results if isinstance(results, list) else results.get('results', results)
        assert any(ce['event_name'] == 'checkout' for ce in items)

    def test_unauthenticated_conversion_events_rejected(self, anon_client, project):
        """Unauthenticated access to conversion-events/ returns 401."""
        resp = anon_client.get(self.CE_URL.format(pid=project.id))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Analytics: TestAnalyticsQuery
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAnalyticsQuery:
    QUERY_URL = '/api/projects/{pid}/analytics/query/'

    def _seed_event(self, project, event_name='test_event', day='2024-06-15'):
        Event.objects.create(
            project=project,
            event_name=event_name,
            platform='web',
            occurred_at=timezone.datetime.fromisoformat(f'{day}T12:00:00+00:00'),
        )

    def test_query_event_count(self, owner_client, project):
        """event_count metric returns results grouped by day."""
        self._seed_event(project, event_name='click', day='2024-06-15')
        self._seed_event(project, event_name='click', day='2024-06-15')

        resp = owner_client.get(
            self.QUERY_URL.format(pid=project.id),
            {
                'metric': 'event_count',
                'start_date': '2024-06-01',
                'end_date': '2024-06-30',
                'group_by': 'day',
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['metric'] == 'event_count'
        assert data['group_by'] == 'day'
        assert 'results' in data
        total = sum(r['event_count'] for r in data['results'])
        assert total >= 2

    def test_query_unique_users_metric(self, owner_client, project):
        """unique_users metric counts distinct user_ids."""
        for uid in ['u1', 'u1', 'u2']:
            Event.objects.create(
                project=project,
                event_name='login',
                user_id=uid,
                occurred_at=timezone.datetime.fromisoformat('2024-07-01T10:00:00+00:00'),
            )
        resp = owner_client.get(
            self.QUERY_URL.format(pid=project.id),
            {
                'metric': 'unique_users',
                'start_date': '2024-07-01',
                'end_date': '2024-07-31',
                'group_by': 'day',
            },
        )
        assert resp.status_code == 200
        total_unique = sum(r['unique_users'] for r in resp.json()['results'])
        assert total_unique == 2

    def test_query_missing_start_date_rejected(self, owner_client, project):
        """Omitting start_date returns 400."""
        resp = owner_client.get(
            self.QUERY_URL.format(pid=project.id),
            {'metric': 'event_count', 'end_date': '2024-06-30', 'group_by': 'day'},
        )
        assert resp.status_code == 400

    def test_query_invalid_metric_rejected(self, owner_client, project):
        """Unsupported metric value returns 400."""
        resp = owner_client.get(
            self.QUERY_URL.format(pid=project.id),
            {
                'metric': 'bad_metric',
                'start_date': '2024-06-01',
                'end_date': '2024-06-30',
                'group_by': 'day',
            },
        )
        assert resp.status_code == 400
        assert 'error' in resp.json()

    def test_query_invalid_group_by_rejected(self, owner_client, project):
        """Unsupported group_by value returns 400."""
        resp = owner_client.get(
            self.QUERY_URL.format(pid=project.id),
            {
                'metric': 'event_count',
                'start_date': '2024-06-01',
                'end_date': '2024-06-30',
                'group_by': 'year',
            },
        )
        assert resp.status_code == 400

    def test_unauthenticated_query_rejected(self, anon_client, project):
        """Unauthenticated query requests return 401."""
        resp = anon_client.get(
            self.QUERY_URL.format(pid=project.id),
            {
                'metric': 'event_count',
                'start_date': '2024-06-01',
                'end_date': '2024-06-30',
                'group_by': 'day',
            },
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Config: TestRemoteConfig
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRemoteConfig:
    PARAMS_URL = '/api/projects/{pid}/config/parameters/'
    FETCH_URL = '/api/projects/{pid}/config/parameters/fetch/'
    PUBLISH_URL = '/api/projects/{pid}/config/parameters/publish/'

    def test_create_param_as_editor(self, project_with_editor, editor_client, project):
        """Editors can create a remote config parameter."""
        resp = editor_client.post(
            self.PARAMS_URL.format(pid=project.id),
            {
                'key': 'dark_mode_enabled',
                'value_type': 'boolean',
                'default_value': 'false',
                'description': 'Toggles dark mode UI',
            },
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['key'] == 'dark_mode_enabled'
        assert data['value_type'] == 'boolean'
        assert RemoteConfig.objects.filter(project=project, key='dark_mode_enabled').exists()

    def test_create_param_as_owner(self, owner_client, project):
        """Owners can create remote config parameters."""
        resp = owner_client.post(
            self.PARAMS_URL.format(pid=project.id),
            {'key': 'max_retries', 'value_type': 'number', 'default_value': '3'},
            format='json',
        )
        assert resp.status_code == 201

    def test_create_param_viewer_rejected(self, project_with_viewer, viewer_client, project):
        """Viewers must not be able to create remote config parameters."""
        resp = viewer_client.post(
            self.PARAMS_URL.format(pid=project.id),
            {'key': 'viewer_key', 'value_type': 'string', 'default_value': 'nope'},
            format='json',
        )
        assert resp.status_code in (403, 404)

    def test_list_parameters(self, owner_client, project):
        """GET parameters/ returns all parameters for the project."""
        RemoteConfig.objects.create(
            project=project,
            key='feature_flag',
            value_type='boolean',
            default_value='true',
        )
        resp = owner_client.get(self.PARAMS_URL.format(pid=project.id))
        assert resp.status_code == 200
        results = resp.json()
        items = results if isinstance(results, list) else results.get('results', results)
        assert any(p['key'] == 'feature_flag' for p in items)

    def test_fetch_evaluated_params_returns_key_value_dict(self, owner_client, project):
        """fetch/ returns a flat {key: value} dict of resolved parameters."""
        RemoteConfig.objects.create(
            project=project,
            key='banner_text',
            value_type='string',
            default_value='Hello World',
            is_active=True,
        )
        resp = owner_client.get(
            self.FETCH_URL.format(pid=project.id),
            {'platform': 'web'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'banner_text' in data
        assert data['banner_text'] == 'Hello World'

    def test_fetch_inactive_params_excluded(self, owner_client, project):
        """fetch/ does not include inactive parameters."""
        RemoteConfig.objects.create(
            project=project,
            key='hidden_param',
            value_type='string',
            default_value='secret',
            is_active=False,
        )
        resp = owner_client.get(self.FETCH_URL.format(pid=project.id))
        assert resp.status_code == 200
        assert 'hidden_param' not in resp.json()

    def test_publish_snapshot_creates_version(self, owner_client, project):
        """publish/ creates a ConfigVersion with the current parameter values."""
        RemoteConfig.objects.create(
            project=project, key='timeout', value_type='number', default_value='30', is_active=True
        )
        resp = owner_client.post(
            self.PUBLISH_URL.format(pid=project.id),
            {'description': 'Initial release'},
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['version_number'] == 1
        assert 'timeout' in data['params']
        assert data['params']['timeout'] == '30'

    def test_publish_increments_version_number(self, owner_client, project):
        """Second publish creates version 2."""
        RemoteConfig.objects.create(
            project=project, key='k', value_type='string', default_value='v', is_active=True
        )
        owner_client.post(self.PUBLISH_URL.format(pid=project.id), {}, format='json')
        resp2 = owner_client.post(self.PUBLISH_URL.format(pid=project.id), {}, format='json')
        assert resp2.status_code == 201
        assert resp2.json()['version_number'] == 2

    def test_cross_project_config_isolation(self, owner_client, project2):
        """A user not in project2 cannot list project2's config parameters."""
        resp = owner_client.get(self.PARAMS_URL.format(pid=project2.id))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Crashlytics: TestCrashReports
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCrashReports:
    REPORTS_URL = '/api/projects/{pid}/crashlytics/reports/'
    REPORTS_BATCH_URL = '/api/projects/{pid}/crashlytics/reports/batch/'

    _CRASH_PAYLOAD = {
        'exception_type': 'NullPointerException',
        'exception_message': 'Attempt to dereference null object',
        'stack_trace': 'NullPointerException: null\n  at com.example.MainActivity.onCreate(MainActivity.java:42)',
        'platform': 'android',
        'app_version': '1.0.0',
        'fatal': True,
        'occurred_at': None,  # set in tests
    }

    def _crash_payload(self, **overrides):
        payload = {**self._CRASH_PAYLOAD, 'occurred_at': now_iso()}
        payload.update(overrides)
        return payload

    def test_submit_crash_any_member(self, owner_client, project):
        """Any project member (owner) can submit a crash report."""
        resp = owner_client.post(
            self.REPORTS_URL.format(pid=project.id),
            self._crash_payload(),
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['exception_type'] == 'NullPointerException'
        assert CrashReport.objects.filter(project=project).count() == 1

    def test_submit_crash_viewer_can_also_submit(self, project_with_viewer, viewer_client, project):
        """Viewers (any member) can also submit crash reports — not editor-gated."""
        resp = viewer_client.post(
            self.REPORTS_URL.format(pid=project.id),
            self._crash_payload(exception_type='IllegalStateException'),
            format='json',
        )
        assert resp.status_code == 201

    def test_unauthenticated_crash_report_rejected(self, anon_client, project):
        """Unauthenticated crash report submission returns 401."""
        resp = anon_client.post(
            self.REPORTS_URL.format(pid=project.id),
            self._crash_payload(),
            format='json',
        )
        assert resp.status_code == 401

    def test_crash_grouping_same_exception_creates_one_group(self, owner_client, project):
        """Two reports with the same exception_type + stack create exactly one CrashGroup."""
        common_stack = 'NullPointerException: null\n  at com.example.Foo.bar(Foo.java:10)'
        for _ in range(2):
            owner_client.post(
                self.REPORTS_URL.format(pid=project.id),
                self._crash_payload(
                    exception_type='NullPointerException',
                    stack_trace=common_stack,
                ),
                format='json',
            )
        groups = CrashGroup.objects.filter(project=project)
        assert groups.count() == 1
        assert groups.first().occurrence_count == 2

    def test_crash_grouping_different_exception_creates_separate_groups(self, owner_client, project):
        """Reports with different exception types produce separate crash groups."""
        for exc in ('NullPointerException', 'OutOfMemoryError'):
            owner_client.post(
                self.REPORTS_URL.format(pid=project.id),
                self._crash_payload(
                    exception_type=exc,
                    stack_trace=f'{exc}: message\n  at com.example.App.run(App.java:1)',
                ),
                format='json',
            )
        assert CrashGroup.objects.filter(project=project).count() == 2

    def test_list_crash_reports(self, owner_client, project):
        """GET reports/ returns all reports for the project."""
        CrashReport.objects.create(
            project=project,
            exception_type='TestError',
            stack_trace='TestError\n  at com.test.A.b(A.java:5)',
            occurred_at=timezone.now(),
        )
        resp = owner_client.get(self.REPORTS_URL.format(pid=project.id))
        assert resp.status_code == 200
        results = resp.json()
        items = results if isinstance(results, list) else results.get('results', results)
        assert len(items) >= 1

    def test_batch_crash_reports_endpoint_does_not_exist(self, owner_client, project):
        """POST to reports/batch/ must not be a valid endpoint (safety: single submit only)."""
        resp = owner_client.post(
            self.REPORTS_BATCH_URL.format(pid=project.id),
            [{'exception_type': 'Foo', 'stack_trace': 'Foo\nat Bar', 'occurred_at': now_iso()}],
            format='json',
        )
        # The CrashReportViewSet has no batch action — must be 404 or 405
        assert resp.status_code in (404, 405)


# ---------------------------------------------------------------------------
# Crashlytics: TestCrashGroups
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCrashGroups:
    GROUPS_URL = '/api/projects/{pid}/crashlytics/groups/'
    GROUP_DETAIL_URL = '/api/projects/{pid}/crashlytics/groups/{pk}/'
    RESOLVE_URL = '/api/projects/{pid}/crashlytics/groups/{pk}/resolve/'
    UNRESOLVE_URL = '/api/projects/{pid}/crashlytics/groups/{pk}/unresolve/'

    def _make_group(self, project):
        return CrashGroup.objects.create(
            project=project,
            signature='abc123' * 10 + 'abc1',  # 64-char hex
            title='NullPointerException in MainActivity',
            exception_type='NullPointerException',
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
            occurrence_count=5,
        )

    def test_list_crash_groups(self, owner_client, project):
        """GET groups/ lists all crash groups for the project."""
        self._make_group(project)
        resp = owner_client.get(self.GROUPS_URL.format(pid=project.id))
        assert resp.status_code == 200
        results = resp.json()
        items = results if isinstance(results, list) else results.get('results', results)
        assert len(items) >= 1

    def test_patch_notes_as_editor(self, project_with_editor, editor_client, project):
        """Editors can PATCH crash group notes."""
        group = self._make_group(project)
        resp = editor_client.patch(
            self.GROUP_DETAIL_URL.format(pid=project.id, pk=group.id),
            {'notes': 'Fix pending in v2.1'},
            format='json',
        )
        assert resp.status_code == 200
        group.refresh_from_db()
        assert group.notes == 'Fix pending in v2.1'

    def test_patch_notes_viewer_rejected(self, project_with_viewer, viewer_client, project):
        """Viewers must not be able to PATCH crash group notes."""
        group = self._make_group(project)
        resp = viewer_client.patch(
            self.GROUP_DETAIL_URL.format(pid=project.id, pk=group.id),
            {'notes': 'Viewer note attempt'},
            format='json',
        )
        assert resp.status_code in (403, 404)

    def test_post_to_groups_not_allowed(self, owner_client, project):
        """Direct POST to crash groups is not permitted (groups are created by the service)."""
        resp = owner_client.post(
            self.GROUPS_URL.format(pid=project.id),
            {
                'signature': 'a' * 64,
                'title': 'Manual Group',
                'exception_type': 'FakeError',
                'first_seen_at': now_iso(),
                'last_seen_at': now_iso(),
            },
            format='json',
        )
        # CrashGroupViewSet http_method_names excludes 'post' → 405
        assert resp.status_code == 405

    def test_resolve_crash_group(self, owner_client, project):
        """resolve/ marks a crash group as resolved and sets resolved_at."""
        group = self._make_group(project)
        assert group.is_resolved is False

        resp = owner_client.post(self.RESOLVE_URL.format(pid=project.id, pk=group.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data['is_resolved'] is True
        assert data['resolved_at'] is not None

        group.refresh_from_db()
        assert group.is_resolved is True
        assert group.resolved_at is not None

    def test_unresolve_crash_group(self, owner_client, project):
        """unresolve/ clears is_resolved on a previously resolved group."""
        group = self._make_group(project)
        group.is_resolved = True
        group.resolved_at = timezone.now()
        group.save()

        resp = owner_client.post(self.UNRESOLVE_URL.format(pid=project.id, pk=group.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data['is_resolved'] is False
        assert data['resolved_at'] is None

    def test_cross_project_group_isolation(self, owner_client, project2, outsider):
        """Owner of project cannot see crash groups of project2."""
        CrashGroup.objects.create(
            project=project2,
            signature='b' * 64,
            title='Other Project Crash',
            exception_type='OtherError',
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        resp = owner_client.get(self.GROUPS_URL.format(pid=project2.id))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Crashlytics: TestPerformance
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPerformance:
    TRACES_URL = '/api/projects/{pid}/crashlytics/traces/'
    TRACES_BATCH_URL = '/api/projects/{pid}/crashlytics/traces/batch/'
    SUMMARY_URL = '/api/projects/{pid}/crashlytics/summary/'

    def _trace_payload(self, **overrides):
        base = {
            'trace_name': 'app_startup',
            'duration_ms': 350,
            'platform': 'ios',
            'occurred_at': now_iso(),
        }
        base.update(overrides)
        return base

    def test_submit_trace(self, owner_client, project):
        """Any project member can submit a performance trace."""
        resp = owner_client.post(
            self.TRACES_URL.format(pid=project.id),
            self._trace_payload(),
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['trace_name'] == 'app_startup'
        assert data['duration_ms'] == 350
        assert PerformanceTrace.objects.filter(project=project).count() == 1

    def test_unauthenticated_trace_rejected(self, anon_client, project):
        """Unauthenticated trace submission returns 401."""
        resp = anon_client.post(
            self.TRACES_URL.format(pid=project.id),
            self._trace_payload(),
            format='json',
        )
        assert resp.status_code == 401

    def test_batch_traces_success(self, owner_client, project):
        """batch/ endpoint creates multiple traces atomically."""
        payload = [
            self._trace_payload(trace_name=f'trace_{i}', duration_ms=100 + i)
            for i in range(5)
        ]
        resp = owner_client.post(
            self.TRACES_BATCH_URL.format(pid=project.id),
            payload,
            format='json',
        )
        assert resp.status_code == 201
        assert len(resp.json()) == 5
        assert PerformanceTrace.objects.filter(project=project).count() == 5

    def test_batch_traces_over_limit_rejected(self, owner_client, project):
        """Batch endpoint rejects payloads with more than 500 traces."""
        payload = [self._trace_payload(trace_name=f't{i}') for i in range(501)]
        resp = owner_client.post(
            self.TRACES_BATCH_URL.format(pid=project.id),
            payload,
            format='json',
        )
        assert resp.status_code == 400
        assert 'error' in resp.json()

    def test_batch_traces_non_list_rejected(self, owner_client, project):
        """batch/ rejects a non-list JSON body."""
        resp = owner_client.post(
            self.TRACES_BATCH_URL.format(pid=project.id),
            self._trace_payload(),
            format='json',
        )
        assert resp.status_code == 400

    def test_get_summary_returns_expected_keys(self, owner_client, project):
        """summary/ returns a dict with all expected top-level keys."""
        resp = owner_client.get(self.SUMMARY_URL.format(pid=project.id))
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = {
            'total_crash_groups',
            'unresolved_groups',
            'total_reports_last_7d',
            'affected_users_last_7d',
            'top_crashes',
        }
        assert expected_keys.issubset(set(data.keys()))

    def test_summary_counts_are_integers(self, owner_client, project):
        """All numeric summary fields are non-negative integers."""
        resp = owner_client.get(self.SUMMARY_URL.format(pid=project.id))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data['total_crash_groups'], int)
        assert isinstance(data['unresolved_groups'], int)
        assert isinstance(data['total_reports_last_7d'], int)
        assert isinstance(data['affected_users_last_7d'], int)
        assert isinstance(data['top_crashes'], list)

    def test_summary_top_crashes_structure(self, owner_client, project):
        """top_crashes entries have the required fields: signature, title, count, last_seen."""
        CrashGroup.objects.create(
            project=project,
            signature='c' * 64,
            title='TopCrash in App',
            exception_type='TopError',
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
            occurrence_count=10,
        )
        resp = owner_client.get(self.SUMMARY_URL.format(pid=project.id))
        assert resp.status_code == 200
        top = resp.json()['top_crashes']
        assert len(top) >= 1
        entry = top[0]
        assert 'signature' in entry
        assert 'title' in entry
        assert 'count' in entry
        assert 'last_seen' in entry

    def test_unauthenticated_summary_rejected(self, anon_client, project):
        """Unauthenticated summary requests return 401."""
        resp = anon_client.get(self.SUMMARY_URL.format(pid=project.id))
        assert resp.status_code == 401

    def test_list_traces(self, owner_client, project):
        """GET traces/ returns all traces for the project."""
        PerformanceTrace.objects.create(
            project=project,
            trace_name='list_test_trace',
            duration_ms=200,
            occurred_at=timezone.now(),
        )
        resp = owner_client.get(self.TRACES_URL.format(pid=project.id))
        assert resp.status_code == 200
        results = resp.json()
        items = results if isinstance(results, list) else results.get('results', results)
        assert any(t['trace_name'] == 'list_test_trace' for t in items)
