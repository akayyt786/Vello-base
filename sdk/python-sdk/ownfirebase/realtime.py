"""OwnFirebase Realtime SDK.

The TypeScript reference implementation (sdk/src/realtime.ts) is a browser
WebSocket wrapper: it owns a persistent `WebSocket` connection, dispatches
`subscribe`/`unsubscribe`/`ping` frames over it, and fans incoming messages
out to registered listeners.

This Python SDK only depends on `requests` (see pyproject.toml) — no
WebSocket client library is bundled. Rather than silently add a new
dependency (e.g. `websockets` or `websocket-client`), this module sticks to
the connection-agnostic pieces that don't require holding an open socket:

  * building the correct realtime WebSocket URL (matching realtime/routing.py)
  * building the subscribe/unsubscribe/ping message envelopes as plain dicts
  * parsing a raw incoming frame into a plain dict

Callers bring their own synchronous or async WebSocket client (e.g.
`websocket-client`, `websockets`, or a framework-specific one), `json.dumps()`
the envelope dicts below, send them over the socket, and pass received frames
to `parse_message`.

If a batteries-included synchronous WS client is desired, adding
`websocket-client` as an optional dependency (extra, not a hard requirement)
would be a reasonable follow-up — flagged here for review rather than added
unilaterally.
"""

import json
from typing import Any, Dict, Optional

from .client import OwnFirebaseClient
from .config import OwnFirebaseConfig


class RealtimeSDK(OwnFirebaseClient):
    """Realtime listeners service."""

    def __init__(self, config: OwnFirebaseConfig) -> None:
        super().__init__(config)
        self._request_id = 0

    def _next_request_id(self) -> str:
        self._request_id += 1
        return str(self._request_id)

    def _ws_base_url(self) -> str:
        """Convert the configured HTTP(S) base_url to its ws(s):// equivalent."""
        url = self.base_url.rstrip('/')
        if url.startswith('https://'):
            return 'wss://' + url[len('https://'):]
        if url.startswith('http://'):
            return 'ws://' + url[len('http://'):]
        return url

    def get_websocket_url(self) -> str:
        """Build the realtime WebSocket URL for the current project.

        Matches realtime/routing.py: ^ws/v1/projects/(?P<project_id>[^/]+)/listen/$
        """
        if not self.project_id:
            raise ValueError('project_id is required for this operation')
        return f'{self._ws_base_url()}/ws/v1/projects/{self.project_id}/listen/'

    def build_subscribe_message(
        self,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a 'subscribe' message envelope to send over the WebSocket."""
        return {
            'type': 'subscribe',
            'requestId': request_id or self._next_request_id(),
            'path': path,
            'query': query,
        }

    def build_unsubscribe_message(
        self, subscription_id: str, request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build an 'unsubscribe' message envelope to send over the WebSocket."""
        return {
            'type': 'unsubscribe',
            'requestId': request_id or self._next_request_id(),
            'subscriptionId': subscription_id,
        }

    def build_ping_message(self) -> Dict[str, Any]:
        """Build a 'ping' message envelope to keep the connection alive."""
        return {'type': 'ping'}

    @staticmethod
    def parse_message(raw: str) -> Dict[str, Any]:
        """Parse a raw JSON frame received over the WebSocket into a dict.

        The resulting dict's 'type' key is one of: 'pong', 'subscribed',
        'unsubscribed', 'error', 'change' — mirroring the TS handleMessage
        switch.
        """
        return json.loads(raw)
