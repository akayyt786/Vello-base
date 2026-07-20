"""OwnFirebase Functions SDK."""

from typing import Any, Dict, List, Optional

from .client import OwnFirebaseClient


class FunctionsSDK(OwnFirebaseClient):
    """Cloud functions service."""

    def list_functions(self) -> List[Dict[str, Any]]:
        """List deployed function definitions."""
        return self.request('GET', self.project_url('functions/'))

    def get_function(self, name: str) -> Dict[str, Any]:
        """Get a single function definition by name."""
        return self.request('GET', self.project_url(f'functions/{name}/'))

    def create_function(self, definition: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new function definition."""
        return self.request('POST', self.project_url('functions/'), json_data=definition)

    def update_function(self, name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a function definition.

        Backend only implements GET/PUT/DELETE on this route (no PATCH), but the
        PUT handler applies the serializer with partial=True, so a sparse body
        here is safe — it behaves like a partial update despite the verb.
        """
        return self.request('PUT', self.project_url(f'functions/{name}/'), json_data=updates)

    def delete_function(self, name: str) -> None:
        """Delete a function definition."""
        return self.request('DELETE', self.project_url(f'functions/{name}/'))

    def invoke(self, name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invoke a cloud function with an optional data payload."""
        return self.request(
            'POST',
            self.project_url(f'functions/{name}/invoke/'),
            json_data={'data': payload if payload is not None else {}},
        )

    def get_logs(
        self,
        name: str,
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get execution logs for a function."""
        query: Dict[str, str] = {}
        if limit is not None:
            query['limit'] = str(limit)
        if since:
            query['since'] = since
        return self.request(
            'GET', self.project_url(f'functions/{name}/logs/'), query_params=query
        )
