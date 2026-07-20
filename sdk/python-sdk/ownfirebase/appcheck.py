"""OwnFirebase App Check SDK."""

from typing import Any, Dict

from .client import OwnFirebaseClient


class AppCheckSDK(OwnFirebaseClient):
    """App attestation service."""

    def exchange_token(self, provider: str, platform: str, raw_token: str) -> Dict[str, Any]:
        """Exchange a platform attestation for an OwnFirebase App Check token.

        provider is one of 'recaptcha_v3', 'recaptcha_enterprise', 'play_integrity',
        'device_check', 'debug'. platform is one of 'web', 'android', 'ios'.
        The returned token must be included in subsequent API requests as the
        `X-App-Check-Token` header when App Check enforcement is enabled.
        """
        return self.request(
            'POST',
            self.project_url('app-check/exchange/'),
            json_data={'provider': provider, 'platform': platform, 'raw_token': raw_token},
        )
