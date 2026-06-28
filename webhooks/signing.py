import hashlib
import hmac
import json
import time


def sign_payload(secret: str, payload: dict) -> str:
    """Return HMAC-SHA256 signature: 't=<timestamp>,v1=<hex>'."""
    ts = str(int(time.time()))
    body = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    signed = f"{ts}.{body}"
    sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def verify_signature(secret: str, payload_body: str, header: str, tolerance_seconds=300) -> bool:
    """Verify Stripe-style webhook signature."""
    try:
        parts = dict(p.split('=', 1) for p in header.split(','))
        ts = int(parts['t'])
        sig = parts['v1']
    except Exception:
        return False
    if abs(time.time() - ts) > tolerance_seconds:
        return False
    signed = f"{ts}.{payload_body}"
    expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)
