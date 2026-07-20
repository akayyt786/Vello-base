"""OwnFirebase Crashlytics SDK."""

from typing import Any, Dict, Optional

from .client import OwnFirebaseClient


class CrashlyticsSDK(OwnFirebaseClient):
    """Error and crash tracking service."""

    # ─── Crash Groups ────────────────────────────────────────────────────────────

    def list_crash_groups(self, filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """List crash groups. Returns a paginated response."""
        return self.request(
            'GET', self.project_url('crashlytics/groups/'), query_params=filters
        )

    def get_crash_group(self, id: str) -> Dict[str, Any]:
        """Get a single crash group by ID."""
        return self.request('GET', self.project_url(f'crashlytics/groups/{id}/'))

    # ─── Crash Reports ───────────────────────────────────────────────────────────

    def report_crash(
        self,
        exception_type: str,
        message: str,
        stack_trace: str,
        app_version: str,
        platform: str,
        device_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Report a crash."""
        body: Dict[str, Any] = {
            'exception_type': exception_type,
            'message': message,
            'stack_trace': stack_trace,
            'app_version': app_version,
            'platform': platform,
        }
        if device_info is not None:
            body['device_info'] = device_info
        return self.request('POST', self.project_url('crashlytics/reports/'), json_data=body)

    def list_crash_reports(self, filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """List crash reports. Returns a paginated response."""
        return self.request(
            'GET', self.project_url('crashlytics/reports/'), query_params=filters
        )

    def get_crash_summary(self) -> Dict[str, Any]:
        """Get aggregate crash statistics for the project."""
        return self.request('GET', self.project_url('crashlytics/summary/'))

    # ─── Performance Traces ──────────────────────────────────────────────────────

    def record_trace(
        self,
        name: str,
        duration_ms: int,
        started_at: str,
        attributes: Optional[Dict[str, str]] = None,
        metrics: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Record a performance trace."""
        body: Dict[str, Any] = {
            'name': name,
            'duration_ms': duration_ms,
            'started_at': started_at,
        }
        if attributes is not None:
            body['attributes'] = attributes
        if metrics is not None:
            body['metrics'] = metrics
        return self.request('POST', self.project_url('crashlytics/traces/'), json_data=body)

    def list_traces(self, filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """List performance traces. Returns a paginated response."""
        return self.request(
            'GET', self.project_url('crashlytics/traces/'), query_params=filters
        )

    # ─── Network Requests ────────────────────────────────────────────────────────

    def record_network_request(
        self,
        url: str,
        method: str,
        status_code: int,
        duration_ms: int,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Record a network request for performance monitoring."""
        body: Dict[str, Any] = {
            'url': url,
            'method': method,
            'status_code': status_code,
            'duration_ms': duration_ms,
        }
        if request_size is not None:
            body['request_size'] = request_size
        if response_size is not None:
            body['response_size'] = response_size
        return self.request('POST', self.project_url('crashlytics/network/'), json_data=body)

    def list_network_requests(self, filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """List recorded network requests. Returns a paginated response."""
        return self.request(
            'GET', self.project_url('crashlytics/network/'), query_params=filters
        )
