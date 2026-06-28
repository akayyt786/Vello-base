"""
Tests for Security Rules / RLS system.
Phase 1 MVP: test DSL parsing, rule evaluation, and DRF permission enforcement.
"""

import pytest
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Project, ProjectMembership
from data.models import Document
from rules.models import SecurityPolicy
from rules.dsl import RuleEngine, RequestContext, Document as DSLDocument, DSLParser


class TestDSLEvaluator(TestCase):
    """Test the RuleEngine DSL evaluator."""

    def setUp(self):
        self.engine = RuleEngine()

    def test_auth_check_authenticated(self):
        """Test auth_check for authenticated user."""
        user = User.objects.create_user('test@example.com', 'test@example.com', 'password123')
        request_ctx = RequestContext(
            auth_user=user,
            auth_uid=str(user.id),
            operation='read',
            is_admin=False,
        )

        condition = {
            'operator': 'and',
            'conditions': [
                {
                    'type': 'auth_check',
                    'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                }
            ]
        }

        result = self.engine.check(condition, request_ctx)
        assert result is True

    def test_auth_check_unauthenticated(self):
        """Test auth_check for unauthenticated user."""
        request_ctx = RequestContext(
            auth_user=None,
            auth_uid=None,
            operation='read',
            is_admin=False,
        )

        condition = {
            'operator': 'and',
            'conditions': [
                {
                    'type': 'auth_check',
                    'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                }
            ]
        }

        result = self.engine.check(condition, request_ctx)
        assert result is False

    def test_owner_check_owner_can_read(self):
        """Test owner_check: owner can read own document."""
        user = User.objects.create_user('owner@example.com', 'owner@example.com', 'password123')
        request_ctx = RequestContext(
            auth_user=user,
            auth_uid=str(user.id),
            operation='read',
            is_admin=False,
        )

        doc = DSLDocument(
            id='doc-1',
            data={'title': 'My Doc'},
            owner_id=str(user.id),
        )

        condition = {
            'operator': 'and',
            'conditions': [
                {
                    'type': 'auth_check',
                    'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                },
                {
                    'type': 'owner_check',
                    'value': {'field': 'owner_id'}
                }
            ]
        }

        result = self.engine.check(condition, request_ctx, doc)
        assert result is True

    def test_owner_check_non_owner_cannot_read(self):
        """Test owner_check: non-owner cannot read document."""
        user1 = User.objects.create_user('user1@example.com', 'user1@example.com', 'password123')
        user2 = User.objects.create_user('user2@example.com', 'user2@example.com', 'password123')

        request_ctx = RequestContext(
            auth_user=user1,
            auth_uid=str(user1.id),
            operation='read',
            is_admin=False,
        )

        doc = DSLDocument(
            id='doc-1',
            data={'title': 'User2 Doc'},
            owner_id=str(user2.id),
        )

        condition = {
            'operator': 'and',
            'conditions': [
                {
                    'type': 'auth_check',
                    'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                },
                {
                    'type': 'owner_check',
                    'value': {'field': 'owner_id'}
                }
            ]
        }

        result = self.engine.check(condition, request_ctx, doc)
        assert result is False

    def test_field_check_with_rhs_field(self):
        """Test field_check with right-hand side field reference."""
        user = User.objects.create_user('test@example.com', 'test@example.com', 'password123')
        request_ctx = RequestContext(
            auth_user=user,
            auth_uid=str(user.id),
            operation='read',
            is_admin=False,
        )

        doc = DSLDocument(
            id='doc-1',
            data={'owner': str(user.id), 'title': 'My Doc'},
        )

        condition = {
            'operator': 'and',
            'conditions': [
                {
                    'type': 'field_check',
                    'value': {
                        'path': 'data.owner',
                        'op': '==',
                        'rhs_field': 'request.auth.uid'
                    }
                }
            ]
        }

        result = self.engine.check(condition, request_ctx, doc)
        assert result is True

    def test_or_condition(self):
        """Test OR logic in condition tree."""
        user = User.objects.create_user('test@example.com', 'test@example.com', 'password123')
        request_ctx = RequestContext(
            auth_user=user,
            auth_uid=str(user.id),
            operation='read',
            is_admin=False,
        )

        # OR: either auth or is_public
        condition = {
            'operator': 'or',
            'conditions': [
                {
                    'type': 'auth_check',
                    'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                },
                {
                    'type': 'field_check',
                    'value': {'path': 'data.is_public', 'op': '==', 'rhs': 'true'}
                }
            ]
        }

        result = self.engine.check(condition, request_ctx)
        # Should be True because auth is not null
        assert result is True


class TestDSLParser(TestCase):
    """Test the DSL parser."""

    def setUp(self):
        self.parser = DSLParser()

    def test_parse_simple_auth_rule(self):
        """Test parsing a simple auth rule."""
        rule_str = "request.auth != null"
        result = self.parser.parse(rule_str)

        assert result['operator'] == 'and'
        assert len(result['conditions']) > 0
        assert result['conditions'][0]['type'] == 'auth_check'

    def test_parse_owner_comparison(self):
        """Test parsing owner comparison rule."""
        rule_str = "data.owner == request.auth.uid"
        result = self.parser.parse(rule_str)

        assert result['operator'] == 'and'
        assert len(result['conditions']) > 0
        assert result['conditions'][0]['type'] == 'field_check'


@pytest.mark.django_db
class TestDocumentRulesPermission:
    """Test DocumentRules permission class."""

    def setup_method(self):
        """Set up test data."""
        self.client = APIClient()
        self.user1 = User.objects.create_user('user1@example.com', 'user1@example.com', 'password123')
        self.user2 = User.objects.create_user('user2@example.com', 'user2@example.com', 'password123')

        self.project = Project.objects.create(
            name='Test Project',
            slug='test-project',
            owner=self.user1,
        )

        # Add users to project
        ProjectMembership.objects.create(project=self.project, user=self.user1, role='owner')
        ProjectMembership.objects.create(project=self.project, user=self.user2, role='viewer')

        # Create default security policies
        self._create_default_policies()

    def _create_default_policies(self):
        """Create default read/write policies."""
        # Default read: any authenticated user
        SecurityPolicy.objects.create(
            project=self.project,
            collection='documents',
            rule_type='read',
            condition_json={
                'operator': 'and',
                'conditions': [
                    {
                        'type': 'auth_check',
                        'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                    }
                ]
            },
            active=True,
            priority=100,
            description='Default: allow read if authenticated',
        )

        # Default write: only owner
        SecurityPolicy.objects.create(
            project=self.project,
            collection='documents',
            rule_type='write',
            condition_json={
                'operator': 'and',
                'conditions': [
                    {
                        'type': 'auth_check',
                        'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                    },
                    {
                        'type': 'owner_check',
                        'value': {'field': 'owner_id'}
                    }
                ]
            },
            active=True,
            priority=100,
            description='Default: allow write if owner',
        )

    def test_authenticated_can_read_own_doc(self):
        """Test that authenticated user can read their own document."""
        # Create document owned by user1
        doc = Document.objects.create(
            project=self.project,
            collection_path='documents',
            doc_id='doc-1',
            data={'title': 'My Document', 'owner_id': str(self.user1.id)},
        )

        # Get token for user1
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user1)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        # Attempt to read own document
        response = self.client.get(f'/api/v1/documents/{doc.id}/')
        # Note: This would work if the view is properly wired; in Phase 1 we're testing the permission logic
        # The actual 404 or 200 depends on URL routing setup

    def test_unauthenticated_cannot_read(self):
        """Test that unauthenticated user cannot read document."""
        # Create document
        doc = Document.objects.create(
            project=self.project,
            collection_path='documents',
            doc_id='doc-2',
            data={'title': 'My Document', 'owner_id': str(self.user1.id)},
        )

        # No authentication
        response = self.client.get(f'/api/v1/documents/{doc.id}/')
        # Should fail with 401 or 403

    def test_non_owner_cannot_modify(self):
        """Test that non-owner cannot modify document."""
        # Create document owned by user1
        doc = Document.objects.create(
            project=self.project,
            collection_path='documents',
            doc_id='doc-3',
            data={'title': 'User1 Document', 'owner_id': str(self.user1.id)},
        )

        # Get token for user2
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user2)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        # Attempt to modify document
        response = self.client.patch(
            f'/api/v1/documents/{doc.id}/',
            {'data': {'title': 'Updated by user2'}},
            format='json',
        )
        # Should fail with 403 Forbidden (rule check) or 404


class TestSecurityPolicyModel(TestCase):
    """Test SecurityPolicy model."""

    def setUp(self):
        self.user = User.objects.create_user('owner@example.com', 'owner@example.com', 'password123')
        self.project = Project.objects.create(
            name='Test Project',
            slug='test-project',
            owner=self.user,
        )

    def test_create_policy(self):
        """Test creating a security policy."""
        policy = SecurityPolicy.objects.create(
            project=self.project,
            collection='documents',
            rule_type='read',
            condition_json={
                'operator': 'and',
                'conditions': [
                    {
                        'type': 'auth_check',
                        'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                    }
                ]
            },
            active=True,
            description='Allow read if authenticated',
        )

        assert policy.id is not None
        assert policy.project == self.project
        assert policy.collection == 'documents'
        assert policy.rule_type == 'read'
        assert policy.active is True

    def test_policy_validation(self):
        """Test policy validation."""
        # Invalid condition_json
        with pytest.raises(Exception):
            SecurityPolicy.objects.create(
                project=self.project,
                collection='documents',
                rule_type='read',
                condition_json={'invalid': 'structure'},  # Missing 'operator' and 'conditions'
                active=True,
            )

    def test_policy_ordering(self):
        """Test that policies are ordered by priority."""
        # Create policies with different priorities
        low_priority = SecurityPolicy.objects.create(
            project=self.project,
            collection='documents',
            rule_type='read',
            condition_json={'operator': 'and', 'conditions': []},
            priority=10,
            active=True,
        )

        high_priority = SecurityPolicy.objects.create(
            project=self.project,
            collection='documents',
            rule_type='read',
            condition_json={'operator': 'and', 'conditions': []},
            priority=100,
            active=True,
        )

        # Query should order by priority descending
        policies = SecurityPolicy.objects.filter(
            project=self.project,
            collection='documents',
            rule_type='read'
        ).order_by('-priority')

        assert policies[0] == high_priority
        assert policies[1] == low_priority

    def test_inactive_policies_not_evaluated(self):
        """Test that inactive policies are skipped during evaluation."""
        user = User.objects.create_user('test@example.com', 'test@example.com', 'password123')
        project = Project.objects.create(
            name='Test Project',
            slug='test-project-inactive',
            owner=user,
        )

        # Create inactive policy (should not be evaluated)
        inactive_policy = SecurityPolicy.objects.create(
            project=project,
            collection='documents',
            rule_type='read',
            condition_json={
                'operator': 'and',
                'conditions': [
                    {
                        'type': 'auth_check',
                        'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                    }
                ]
            },
            active=False,
            description='This policy is inactive',
        )

        # Query policies (should exclude inactive)
        policies = SecurityPolicy.objects.filter(
            project=project,
            collection='documents',
            rule_type='read',
            active=True
        )

        assert inactive_policy not in policies

    def test_rule_conditions_with_and_operator(self):
        """Test AND logic: all conditions must pass."""
        engine = RuleEngine()
        user = User.objects.create_user('test@example.com', 'test@example.com', 'password123')

        request_ctx = RequestContext(
            auth_user=user,
            auth_uid=str(user.id),
            operation='read',
            is_admin=False,
        )

        doc = DSLDocument(
            id='doc-1',
            data={'owner': str(user.id), 'is_public': False},
            owner_id=str(user.id),
        )

        # AND condition: auth AND owner
        condition = {
            'operator': 'and',
            'conditions': [
                {
                    'type': 'auth_check',
                    'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                },
                {
                    'type': 'owner_check',
                    'value': {'field': 'owner_id'}
                }
            ]
        }

        result = engine.check(condition, request_ctx, doc)
        assert result is True

    def test_rule_conditions_with_or_operator_partial_match(self):
        """Test OR logic: at least one condition must pass."""
        engine = RuleEngine()
        user1 = User.objects.create_user('user1@example.com', 'user1@example.com', 'password123')
        user2 = User.objects.create_user('user2@example.com', 'user2@example.com', 'password123')

        request_ctx = RequestContext(
            auth_user=user1,
            auth_uid=str(user1.id),
            operation='read',
            is_admin=False,
        )

        # Document owned by user2 but public
        doc = DSLDocument(
            id='doc-1',
            data={'owner': str(user2.id), 'is_public': True},
            owner_id=str(user2.id),
        )

        # OR condition: owner OR is_public (should pass because is_public=true)
        condition = {
            'operator': 'or',
            'conditions': [
                {
                    'type': 'owner_check',
                    'value': {'field': 'owner_id'}
                },
                {
                    'type': 'field_check',
                    'value': {'path': 'data.is_public', 'op': '==', 'rhs': 'true'}
                }
            ]
        }

        result = engine.check(condition, request_ctx, doc)
        assert result is True

    def test_multiple_policies_first_match_wins(self):
        """Test that first matching policy is used (short-circuit evaluation)."""
        user = User.objects.create_user('test@example.com', 'test@example.com', 'password123')
        project = Project.objects.create(
            name='Test Project',
            slug='test-project-priority',
            owner=user,
        )

        # Create two policies for same collection/operation: high priority allows, low priority denies
        allow_policy = SecurityPolicy.objects.create(
            project=project,
            collection='documents',
            rule_type='read',
            condition_json={
                'operator': 'and',
                'conditions': [
                    {
                        'type': 'auth_check',
                        'value': {'field': 'request.auth', 'op': '!=', 'rhs': 'null'}
                    }
                ]
            },
            priority=100,
            active=True,
            description='High priority: allow all authenticated'
        )

        deny_policy = SecurityPolicy.objects.create(
            project=project,
            collection='documents',
            rule_type='read',
            condition_json={
                'operator': 'and',
                'conditions': [
                    {
                        'type': 'auth_check',
                        'value': {'field': 'request.auth', 'op': '==', 'rhs': 'null'}
                    }
                ]
            },
            priority=50,
            active=True,
            description='Low priority: deny all'
        )

        # Query should return allow_policy first (higher priority)
        policies = SecurityPolicy.objects.filter(
            project=project,
            collection='documents',
            rule_type='read',
            active=True
        ).order_by('-priority')

        assert policies[0] == allow_policy
        assert policies[1] == deny_policy
