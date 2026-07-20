"""OwnFirebase Remote Config SDK."""

import json
import time
from typing import Any, Dict, List, Optional

from .client import OwnFirebaseClient
from .config import OwnFirebaseConfig


class RemoteConfigSDK(OwnFirebaseClient):
    """Remote configuration service."""

    _DEFAULT_CACHE_TTL_MS = 3600000  # 1 hour

    def __init__(self, config: OwnFirebaseConfig) -> None:
        super().__init__(config)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_ms = self._DEFAULT_CACHE_TTL_MS

    def set_cache_ttl(self, ttl_ms: int) -> None:
        """Set the cache TTL (time-to-live) in milliseconds. Default is 1 hour."""
        self._cache_ttl_ms = ttl_ms

    def clear_cache(self) -> None:
        """Clear all cached remote config values."""
        self._cache.clear()

    # ─── Parameters ──────────────────────────────────────────────────────────────

    def list_parameters(self) -> Dict[str, Any]:
        """List remote config parameters. Returns a paginated response."""
        return self.request('GET', self.project_url('config/parameters/'))

    def get_parameter(self, id: str) -> Dict[str, Any]:
        """Get a single parameter by ID."""
        return self.request('GET', self.project_url(f'config/parameters/{id}/'))

    def create_parameter(self, parameter: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new remote config parameter."""
        return self.request(
            'POST', self.project_url('config/parameters/'), json_data=parameter
        )

    def update_parameter(self, id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Partially update a remote config parameter."""
        return self.request(
            'PATCH', self.project_url(f'config/parameters/{id}/'), json_data=updates
        )

    def delete_parameter(self, id: str) -> None:
        """Delete a remote config parameter."""
        return self.request('DELETE', self.project_url(f'config/parameters/{id}/'))

    # ─── Conditions ──────────────────────────────────────────────────────────────

    def list_conditions(self, config_id: str) -> List[Dict[str, Any]]:
        """List conditions for a parameter."""
        return self.request(
            'GET', self.project_url(f'config/parameters/{config_id}/conditions/')
        )

    def create_condition(self, config_id: str, condition: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new condition for a parameter."""
        return self.request(
            'POST',
            self.project_url(f'config/parameters/{config_id}/conditions/'),
            json_data=condition,
        )

    def update_condition(
        self, config_id: str, condition_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Partially update a condition."""
        return self.request(
            'PATCH',
            self.project_url(f'config/parameters/{config_id}/conditions/{condition_id}/'),
            json_data=updates,
        )

    def delete_condition(self, config_id: str, condition_id: str) -> None:
        """Delete a condition."""
        return self.request(
            'DELETE',
            self.project_url(f'config/parameters/{config_id}/conditions/{condition_id}/'),
        )

    # ─── Fetch & Cache ───────────────────────────────────────────────────────────

    def fetch_all_parameters(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch all remote config parameters with built-in caching.

        Results are cached for the configured TTL. Pass force_refresh=True to
        bypass the cache.
        """
        cache_key = '__all_params__'

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached and cached['expires_at'] > time.time():
                return cached['value']

        response = self.list_parameters()
        params = response.get('results') or []

        self._cache[cache_key] = {
            'value': params,
            'expires_at': time.time() + (self._cache_ttl_ms / 1000.0),
        }

        return params

    def get_parameter_by_key(
        self, key: str, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a single parameter by key with caching.

        Pass force_refresh=True to bypass the cache.
        """
        cache_key = f'param:{key}'

        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached and cached['expires_at'] > time.time():
                return cached['value']

        try:
            params = self.fetch_all_parameters(force_refresh)
            param = next((p for p in params if p.get('key') == key), None)

            self._cache[cache_key] = {
                'value': param,
                'expires_at': time.time() + (self._cache_ttl_ms / 1000.0),
            }

            return param
        except Exception:
            return None

    def get_config_value(
        self,
        key: str,
        default_value: Optional[Any] = None,
        force_refresh: bool = False,
    ) -> Any:
        """Get a parameter value by key, with type coercion based on value_type."""
        param = self.get_parameter_by_key(key, force_refresh)

        if not param or not param.get('default_value'):
            if default_value is not None:
                return default_value
            raise ValueError(f'Config key not found: {key}')

        try:
            value_type = param.get('value_type')
            raw_value = param['default_value']
            if value_type == 'json':
                return json.loads(raw_value)
            if value_type == 'boolean':
                return raw_value == 'true' or raw_value == '1'
            if value_type == 'number':
                return float(raw_value)
            return raw_value
        except Exception:
            if default_value is not None:
                return default_value
            raise ValueError(f'Failed to parse config value for key: {key}')

    def prune_cache(self) -> None:
        """Clear expired cache entries."""
        now = time.time()
        expired_keys = [k for k, entry in self._cache.items() if entry['expires_at'] <= now]
        for k in expired_keys:
            del self._cache[k]
