"""SSRF protection for outbound webhook requests."""
import ipaddress
import socket
from urllib.parse import urlparse

from rest_framework import serializers

_BLOCKED_HOSTNAMES = {
    'localhost',
    'metadata.google.internal',
    '169.254.169.254',
    'metadata.internal',
}

ALLOWED_SCHEMES = {'https'}


def _resolve_and_check(hostname: str) -> None:
    """
    Resolve hostname to all IPs; raise ValueError if any is private/internal.
    Defends against DNS rebinding when called at delivery time too.
    """
    try:
        results = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve host '{hostname}': {exc}") from exc

    for _family, _type, _proto, _canon, sockaddr in results:
        raw_ip = sockaddr[0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise ValueError(f"Host '{hostname}' resolves to blocked IP {ip}")


def validate_webhook_url(url: str) -> str:
    """
    Validate a user-supplied webhook URL for SSRF safety.
    Returns cleaned URL or raises serializers.ValidationError / ValueError.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise serializers.ValidationError(
            f"Webhook URL must use HTTPS. Got scheme: '{parsed.scheme}'."
        )

    hostname = parsed.hostname or ''
    if not hostname:
        raise serializers.ValidationError("Webhook URL has no hostname.")

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise serializers.ValidationError(
            f"Webhook URL hostname '{hostname}' is not allowed."
        )

    try:
        _resolve_and_check(hostname)
    except ValueError as exc:
        raise serializers.ValidationError(str(exc))

    return url


def assert_url_safe(url: str) -> None:
    """
    Re-validate URL immediately before making an outbound request.
    Raises ValueError on failure (caught in deliver_webhook task).
    DNS rebinding defence: re-resolved each delivery attempt.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Blocked scheme '{parsed.scheme}' on delivery.")
    hostname = parsed.hostname or ''
    if not hostname or hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Blocked hostname '{hostname}' on delivery.")
    _resolve_and_check(hostname)
