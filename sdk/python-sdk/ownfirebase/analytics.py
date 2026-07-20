"""OwnFirebase Analytics SDK."""

import threading
from typing import Any, Dict, List, Optional

from .client import OwnFirebaseClient
from .config import OwnFirebaseConfig


class AnalyticsSDK(OwnFirebaseClient):
    """Analytics tracking service."""

    _BATCH_MAX_SIZE = 100
    _BATCH_MAX_DELAY_SECONDS = 5.0

    def __init__(self, config: OwnFirebaseConfig) -> None:
        super().__init__(config)
        self._event_batch: List[Dict[str, Any]] = []
        self._batch_timer: Optional[threading.Timer] = None
        self._batch_lock = threading.Lock()

    # ─── Events ──────────────────────────────────────────────────────────────────

    def log_event(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log a single analytics event immediately."""
        return self.request(
            'POST',
            self.project_url('analytics/events/'),
            json_data={
                'name': name,
                'params': params if params is not None else {},
                'user_id': user_id,
                'session_id': session_id,
            },
        )

    def add_event_to_batch(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Add an event to the batch queue.

        Events are sent in bulk after a delay or when the batch is full.
        """
        with self._batch_lock:
            self._event_batch.append(
                {
                    'name': name,
                    'params': params,
                    'user_id': user_id,
                    'session_id': session_id,
                }
            )

            if len(self._event_batch) >= self._BATCH_MAX_SIZE:
                should_flush = True
            else:
                should_flush = False
                if self._batch_timer is None:
                    self._batch_timer = threading.Timer(
                        self._BATCH_MAX_DELAY_SECONDS, self.flush_batch
                    )
                    self._batch_timer.daemon = True
                    self._batch_timer.start()

        if should_flush:
            self.flush_batch()

    def flush_batch(self) -> None:
        """Send all batched events to the server."""
        with self._batch_lock:
            if self._batch_timer is not None:
                self._batch_timer.cancel()
                self._batch_timer = None

            if not self._event_batch:
                return

            batch = self._event_batch[:]
            self._event_batch.clear()

        try:
            self.request(
                'POST', self.project_url('analytics/events/batch/'), json_data={'events': batch}
            )
        except Exception:
            # Re-add failed events to the batch for retry.
            with self._batch_lock:
                self._event_batch[0:0] = batch
            raise

    def list_events(self, filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """List logged events. Returns a paginated response."""
        return self.request(
            'GET', self.project_url('analytics/events/'), query_params=filters
        )

    # ─── User Properties ─────────────────────────────────────────────────────────

    def set_user_property(self, name: str, value: str) -> Dict[str, Any]:
        """Set a user property."""
        return self.request(
            'POST',
            self.project_url('analytics/user-properties/'),
            json_data={'name': name, 'value': value},
        )

    def list_user_properties(self) -> Dict[str, Any]:
        """List user properties. Returns a paginated response."""
        return self.request('GET', self.project_url('analytics/user-properties/'))

    # ─── Conversion Events ───────────────────────────────────────────────────────

    def list_conversion_events(self) -> Dict[str, Any]:
        """List conversion events. Returns a paginated response."""
        return self.request('GET', self.project_url('analytics/conversion-events/'))

    def mark_conversion_event(self, name: str) -> Dict[str, Any]:
        """Mark an event name as a conversion event."""
        return self.request(
            'POST', self.project_url('analytics/conversion-events/'), json_data={'name': name}
        )

    # ─── Query ───────────────────────────────────────────────────────────────────

    def query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run an analytics query (metric/dimension/date range/filters)."""
        return self.request('POST', self.project_url('analytics/query/'), json_data=params)

    def destroy(self) -> None:
        """Clean up the batch timer on SDK teardown."""
        with self._batch_lock:
            if self._batch_timer is not None:
                self._batch_timer.cancel()
                self._batch_timer = None
