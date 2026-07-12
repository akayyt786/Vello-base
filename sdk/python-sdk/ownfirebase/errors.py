"""OwnFirebase SDK Exception Types."""

from typing import Any, Optional


class APIError(Exception):
    """Raised when an API request returns a non-2xx status code.

    Attributes:
        status: HTTP status code
        message: HTTP status text or error message
        detail: Response body (dict or str, depending on the endpoint)
    """

    def __init__(
        self,
        status: int,
        message: str,
        detail: Optional[Any] = None
    ) -> None:
        """Initialize APIError."""
        self.status = status
        self.message = message
        self.detail = detail
        super().__init__(f"API Error {status}: {message}")

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"APIError(status={self.status}, message={self.message}, "
            f"detail={self.detail!r})"
        )
