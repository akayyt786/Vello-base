"""OwnFirebase SDK Configuration."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class OwnFirebaseConfig:
    """Configuration for OwnFirebaseClient.

    Attributes:
        base_url: Backend API base URL (e.g., 'http://localhost:8000')
        project_id: UUID of the target OwnFirebase project (optional, can be set later)
        access_token: JWT access token for authentication (optional, set via setAccessToken())
    """

    base_url: str
    project_id: Optional[str] = None
    access_token: Optional[str] = None

    def __post_init__(self) -> None:
        """Normalize base_url to remove trailing slashes."""
        self.base_url = self.base_url.rstrip('/')
