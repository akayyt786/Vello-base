"""OwnFirebase Push SDK."""

from typing import Any, Dict

from .client import OwnFirebaseClient


class PushSDK(OwnFirebaseClient):
    """Push notifications service."""

    # ─── Device Tokens ───────────────────────────────────────────────────────────

    def register_token(self, token: str, platform: str) -> Dict[str, Any]:
        """Register a device token. platform is one of 'fcm', 'apns', 'web'."""
        return self.request(
            'POST',
            self.project_url('push/tokens/'),
            json_data={'token': token, 'platform': platform},
        )

    def list_tokens(self) -> Dict[str, Any]:
        """List registered device tokens. Returns a paginated response."""
        return self.request('GET', self.project_url('push/tokens/'))

    def delete_token(self, id: str) -> None:
        """Delete a registered device token."""
        return self.request('DELETE', self.project_url(f'push/tokens/{id}/'))

    # ─── Topics ───────────────────────────────────────────────────────────────────

    def list_topics(self) -> Dict[str, Any]:
        """List push topics. Returns a paginated response."""
        return self.request('GET', self.project_url('push/topics/'))

    def create_topic(self, name: str) -> Dict[str, Any]:
        """Create a new push topic."""
        return self.request('POST', self.project_url('push/topics/'), json_data={'name': name})

    def subscribe_topic(self, topic_id: str, device_token_id: str) -> Dict[str, Any]:
        """Subscribe a device token to a topic."""
        return self.request(
            'POST',
            self.project_url(f'push/topics/{topic_id}/subscribe/'),
            json_data={'device_token_id': device_token_id},
        )

    # ─── Send Notifications ──────────────────────────────────────────────────────

    def send_to_device(self, token_id: str, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send a push notification to a single device token."""
        return self.request(
            'POST',
            self.project_url('push/notifications/'),
            json_data={'device_token': token_id, **notification},
        )

    def send_to_topic(self, topic_id: str, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Send a push notification to all subscribers of a topic."""
        return self.request(
            'POST',
            self.project_url('push/notifications/'),
            json_data={'topic': topic_id, **notification},
        )

    def list_notifications(self) -> Dict[str, Any]:
        """List sent push notifications. Returns a paginated response."""
        return self.request('GET', self.project_url('push/notifications/'))

    # ─── Campaigns ───────────────────────────────────────────────────────────────

    def list_campaigns(self) -> Dict[str, Any]:
        """List push campaigns. Returns a paginated response."""
        return self.request('GET', self.project_url('push/campaigns/'))

    def create_campaign(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Create a push campaign. notification may include scheduled_at/audience."""
        return self.request(
            'POST', self.project_url('push/campaigns/'), json_data=notification
        )
