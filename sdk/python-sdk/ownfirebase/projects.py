"""OwnFirebase Projects SDK."""

from typing import Any, Dict, Optional

from .client import OwnFirebaseClient


class ProjectsSDK(OwnFirebaseClient):
    """Project management service."""

    def list_projects(self) -> Dict[str, Any]:
        """List projects the authenticated user can access. Paginated response."""
        return self.request('GET', f'{self.base_url}/api/v1/projects/')

    def get_project(self, id: str) -> Dict[str, Any]:
        """Get a single project by ID."""
        return self.request('GET', f'{self.base_url}/api/v1/projects/{id}/')

    def create_project(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new project."""
        body: Dict[str, Any] = {'name': name}
        if description is not None:
            body['description'] = description
        return self.request('POST', f'{self.base_url}/api/v1/projects/', json_data=body)

    def update_project(
        self,
        id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Partially update a project's name and/or description."""
        body: Dict[str, Any] = {}
        if name is not None:
            body['name'] = name
        if description is not None:
            body['description'] = description
        return self.request(
            'PATCH', f'{self.base_url}/api/v1/projects/{id}/', json_data=body
        )

    def delete_project(self, id: str) -> None:
        """Delete a project."""
        return self.request('DELETE', f'{self.base_url}/api/v1/projects/{id}/')

    # ─── Memberships ─────────────────────────────────────────────────────────────

    def list_members(self, project_id: str) -> Dict[str, Any]:
        """List members of a project. Returns a paginated response."""
        return self.request(
            'GET',
            f'{self.base_url}/api/v1/memberships/',
            query_params={'project': project_id},
        )

    def add_member(self, project_id: str, user_id: str, role: str) -> Dict[str, Any]:
        """Add a member to a project. role is one of 'owner', 'editor', 'viewer'."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/memberships/',
            json_data={'project': project_id, 'user': user_id, 'role': role},
        )

    def update_member_role(self, membership_id: str, role: str) -> Dict[str, Any]:
        """Update a member's role."""
        return self.request(
            'PATCH',
            f'{self.base_url}/api/v1/memberships/{membership_id}/',
            json_data={'role': role},
        )

    def remove_member(self, membership_id: str) -> None:
        """Remove a member from a project."""
        return self.request('DELETE', f'{self.base_url}/api/v1/memberships/{membership_id}/')
