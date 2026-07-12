"""
Health check endpoints.

These are plain Django views (NOT DRF views) so they bypass DRF's default
IsAuthenticated permission and JWT authentication entirely. They must be
publicly accessible with zero auth for use by load balancers / orchestrators.
"""

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse


def liveness(request):
    """
    Liveness probe: proves the process is alive.
    No dependency checks — just returns 200 OK.
    """
    return JsonResponse({"status": "ok"})


def readiness(request):
    """
    Readiness probe: checks that the database and cache are reachable.
    Returns 200 if both checks pass, 503 if either fails.
    """
    checks = {}
    healthy = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:
        healthy = False
        checks["database"] = f"error: {exc}"

    try:
        cache.set("health_check", "ok", timeout=5)
        if cache.get("health_check") != "ok":
            raise Exception("cache roundtrip mismatch")
        checks["cache"] = "ok"
    except Exception as exc:
        healthy = False
        checks["cache"] = f"error: {exc}"

    if healthy:
        return JsonResponse({"status": "ok", "checks": checks})
    return JsonResponse({"status": "unavailable", "checks": checks}, status=503)
