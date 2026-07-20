"""OwnFirebase Data SDK."""

from typing import Any, Dict, List, Optional

from .client import OwnFirebaseClient


class DataSDK(OwnFirebaseClient):
    """Data storage service."""

    # ─── Collections ─────────────────────────────────────────────────────────────

    def list_collections(self) -> List[Dict[str, Any]]:
        """List collections in the current project."""
        return self.request('GET', self.project_url('collections/'))

    def create_collection(self, name: str) -> Dict[str, Any]:
        """Create a new collection."""
        return self.request('POST', self.project_url('collections/'), json_data={'name': name})

    # ─── Documents ────────────────────────────────────────────────────────────────

    def list_documents(
        self, collection: str, filters: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """List documents in a collection. Returns a paginated response.

        `collection` supports subcollection paths using forward slashes
        (e.g. "users/uid/posts").
        """
        return self.request(
            'GET',
            self.project_url(f'collections/{collection}/docs/'),
            query_params=filters,
        )

    def get_document(self, collection: str, doc_id: str) -> Dict[str, Any]:
        """Get a single document by ID."""
        return self.request(
            'GET', self.project_url(f'collections/{collection}/docs/{doc_id}/')
        )

    def create_document(self, collection: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document in a collection."""
        return self.request(
            'POST',
            self.project_url(f'collections/{collection}/docs/'),
            json_data={'data': data},
        )

    def update_document(
        self, collection: str, doc_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Partially update a document."""
        return self.request(
            'PATCH',
            self.project_url(f'collections/{collection}/docs/{doc_id}/'),
            json_data={'data': data},
        )

    def replace_document(
        self, collection: str, doc_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Replace a document's data entirely."""
        return self.request(
            'PUT',
            self.project_url(f'collections/{collection}/docs/{doc_id}/'),
            json_data={'data': data},
        )

    def delete_document(self, collection: str, doc_id: str) -> None:
        """Delete a document by ID."""
        return self.request(
            'DELETE', self.project_url(f'collections/{collection}/docs/{doc_id}/')
        )

    # ─── Batch / Transactions ─────────────────────────────────────────────────────

    def write_batch(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a batch of set/update/delete operations transactionally."""
        return self.request(
            'POST', self.project_url('transaction/'), json_data={'operations': operations}
        )

    # ─── Security Rules ───────────────────────────────────────────────────────────

    def get_rules(self) -> Dict[str, Any]:
        """Get the current security rules source."""
        return self.request('GET', f'{self.base_url}/api/v1/rules/')

    def update_rules(self, rules: str) -> Dict[str, Any]:
        """Update the security rules source."""
        return self.request('POST', f'{self.base_url}/api/v1/rules/', json_data={'rules': rules})

    def test_rules(self, rule: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Test a security rule against a simulated request context."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/rules/test/',
            json_data={'rule': rule, 'context': context},
        )
