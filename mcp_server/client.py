"""HTTP client wrapper for OwnFirebase backend API calls."""

import json
import os
from typing import Any

import httpx

# Module-level auth state — set by auth_login tool, used by all other tools
_token: str | None = None
_refresh_token: str | None = None
_base_url: str = os.environ.get("OWNFIREBASE_BASE_URL", "http://localhost:8000")


def set_token(access: str, refresh: str = "") -> None:
    global _token, _refresh_token
    _token = access
    _refresh_token = refresh


def get_token() -> str | None:
    return _token


def set_base_url(url: str) -> None:
    global _base_url
    _base_url = url.rstrip("/")


def _headers() -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    if _token:
        h["Authorization"] = f"Bearer {_token}"
    return h


async def request(method: str, path: str, **kwargs: Any) -> Any:
    """Make an HTTP request to the OwnFirebase backend. Returns parsed JSON or raises."""
    url = f"{_base_url}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(method, url, headers=_headers(), **kwargs)
    if resp.status_code == 204:
        return {"status": "ok"}
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    if not resp.is_success:
        raise RuntimeError(f"HTTP {resp.status_code}: {json.dumps(data)}")
    return data


async def get(path: str, **kwargs: Any) -> Any:
    return await request("GET", path, **kwargs)


async def post(path: str, **kwargs: Any) -> Any:
    return await request("POST", path, **kwargs)


async def put(path: str, **kwargs: Any) -> Any:
    return await request("PUT", path, **kwargs)


async def patch(path: str, **kwargs: Any) -> Any:
    return await request("PATCH", path, **kwargs)


async def delete(path: str, **kwargs: Any) -> Any:
    return await request("DELETE", path, **kwargs)
