"""OwnFirebase A/B Testing SDK."""

from typing import Any, Dict, Optional

from .client import OwnFirebaseClient


class ABTestingSDK(OwnFirebaseClient):
    """A/B testing and experiments service."""

    # ─── Experiments ─────────────────────────────────────────────────────────────

    def list_experiments(self) -> Dict[str, Any]:
        """List experiments. Returns a paginated response."""
        return self.request('GET', self.project_url('abtesting/experiments/'))

    def get_experiment(self, id: str) -> Dict[str, Any]:
        """Get a single experiment by ID."""
        return self.request('GET', self.project_url(f'abtesting/experiments/{id}/'))

    def create_experiment(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new experiment."""
        return self.request(
            'POST', self.project_url('abtesting/experiments/'), json_data=experiment
        )

    def update_experiment(self, id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Partially update an experiment."""
        return self.request(
            'PATCH', self.project_url(f'abtesting/experiments/{id}/'), json_data=updates
        )

    def delete_experiment(self, id: str) -> None:
        """Delete an experiment."""
        return self.request('DELETE', self.project_url(f'abtesting/experiments/{id}/'))

    # ─── Assignment & Conversion ─────────────────────────────────────────────────

    def get_assignment(self, experiment_id: str, targeting_value: str) -> Dict[str, Any]:
        """Get a stable variant assignment for the given targeting value.

        The server uses consistent hashing so the same value always maps to
        the same variant.
        """
        return self.request(
            'POST',
            self.project_url(f'abtesting/experiments/{experiment_id}/assign/'),
            json_data={'targeting_value': targeting_value},
        )

    def record_conversion(
        self,
        experiment_id: str,
        targeting_value: str,
        event_name: str,
        value: Optional[float] = None,
    ) -> None:
        """Record a conversion event for an experiment assignment."""
        body: Dict[str, Any] = {
            'targeting_value': targeting_value,
            'event_name': event_name,
        }
        if value is not None:
            body['value'] = value
        return self.request(
            'POST',
            self.project_url(f'abtesting/experiments/{experiment_id}/convert/'),
            json_data=body,
        )
