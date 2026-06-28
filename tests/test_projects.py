"""
Tests for project endpoints.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from django.contrib.auth.models import User
from core.models import Project, ProjectMembership


@pytest.mark.django_db
class TestProjectViewSet:
    """Tests for project CRUD endpoints."""

    def test_list_projects(self, authenticated_client, test_project):
        """Test listing projects for authenticated user."""
        url = reverse('project-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['id'] == str(test_project.id)

    def test_create_project(self, authenticated_client, test_user):
        """Test creating a new project."""
        url = reverse('project-list')
        data = {
            'name': 'New Project',
            'slug': 'new-project',
            'description': 'A test project'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Project'
        assert response.data['owner']['id'] == test_user.id

    def test_update_project(self, authenticated_client, test_project):
        """Test updating a project."""
        url = reverse('project-detail', kwargs={'pk': test_project.id})
        data = {
            'name': 'Updated Project Name',
            'slug': test_project.slug,
            'description': 'Updated description'
        }
        response = authenticated_client.put(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Project Name'

    def test_delete_project(self, authenticated_client, test_project):
        """Test deleting a project."""
        url = reverse('project-detail', kwargs={'pk': test_project.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Project.objects.filter(id=test_project.id).exists()

    def test_invite_member(self, authenticated_client, test_project, test_user, db):
        """Test inviting a member to a project."""
        other_user = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='password'
        )
        url = reverse('project-invite-member', kwargs={'pk': test_project.id})
        data = {
            'email': other_user.email,
            'role': 'editor'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert ProjectMembership.objects.filter(
            project=test_project,
            user=other_user,
            role='editor'
        ).exists()

    def test_invite_member_not_owner(self, api_client, test_project, test_user, db):
        """Test that non-owners cannot invite members."""
        viewer_user = User.objects.create_user(
            username='viewer@example.com',
            email='viewer@example.com',
            password='password'
        )
        ProjectMembership.objects.create(
            project=test_project,
            user=viewer_user,
            role='viewer'
        )

        # Authenticate as viewer
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(viewer_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        url = reverse('project-invite-member', kwargs={'pk': test_project.id})
        data = {'email': 'newmember@example.com', 'role': 'viewer'}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_members(self, authenticated_client, test_project, test_user):
        """Test listing project members."""
        url = reverse('project-members', kwargs={'pk': test_project.id})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['user']['id'] == test_user.id
        assert response.data[0]['role'] == 'owner'
