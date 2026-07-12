"""
Celery tasks: invoke webhooks for function triggers, scheduled invocations.
"""

import json
import logging
import time
import urllib.request
import urllib.error
from celery import shared_task

from core.rls import tenant_context

logger = logging.getLogger(__name__)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Block all HTTP redirects — prevents SSRF bypass via open redirectors."""

    def http_error_301(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, 'Redirect not allowed', headers, fp)

    http_error_302 = http_error_303 = http_error_307 = http_error_308 = http_error_301


_OPENER = urllib.request.build_opener(_NoRedirectHandler)


def _post_webhook(url, payload, timeout, secret='', extra_headers=None):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'OwnFirebase/1.0')
    if secret:
        req.add_header('X-OwnFirebase-Secret', secret)
    for k, v in (extra_headers or {}).items():
        req.add_header(k, str(v))

    start = time.monotonic()
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8', errors='replace')[:4096]
            duration_ms = int((time.monotonic() - start) * 1000)
            return {
                'status': 'success',
                'response_status': resp.status,
                'response_body': body,
                'duration_ms': duration_ms,
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:4096]
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            'status': 'error',
            'response_status': e.code,
            'response_body': body,
            'duration_ms': duration_ms,
            'error': f'HTTP {e.code}',
        }
    except Exception as e:
        duration_ms = int((time.monotonic() - start) * 1000)
        status = 'timeout' if 'timed out' in str(e).lower() else 'error'
        return {
            'status': status,
            'response_status': None,
            'response_body': '',
            'duration_ms': duration_ms,
            'error': str(e),
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def invoke_function_for_event(self, function_id, trigger_data, project_id):
    from functions.models import CloudFunction, FunctionLog

    # self.retry() below raises, which would roll back an enclosing atomic
    # block — so the retry is raised *after* tenant_context() (and its
    # transaction) has already exited and committed the log write.
    with tenant_context(project_id):
        try:
            fn = CloudFunction.objects.get(id=function_id, is_enabled=True)
        except CloudFunction.DoesNotExist:
            return {'skipped': True, 'reason': 'function_not_found_or_disabled'}

        log = FunctionLog.objects.create(
            function=fn,
            trigger_data=trigger_data,
            status=FunctionLog.STATUS_RUNNING,
        )

        result = _post_webhook(
            fn.endpoint_url, trigger_data, fn.timeout_seconds,
            fn.secret_header, fn.extra_headers,
        )

        # Persist per-attempt diagnostics regardless of retry outcome.
        log.response_status = result.get('response_status')
        log.response_body = result.get('response_body', '')
        log.duration_ms = result.get('duration_ms')
        log.error = result.get('error', '')

        # Retry on both 'error' and 'timeout' outcomes — not just 'error'.
        will_retry = (
            result['status'] in ('error', 'timeout')
            and fn.retry_count > 0
            and self.request.retries < fn.retry_count
        )

        if will_retry:
            # Keep log.status = STATUS_RUNNING so the record correctly reflects
            # that this attempt is not the final outcome.  STATUS_ERROR/TIMEOUT is
            # only set once all retries are exhausted.
            log.save(update_fields=['response_status', 'response_body', 'duration_ms', 'error'])
        else:
            # Final outcome (success, or all retries exhausted).
            log.status = result['status']
            log.save(update_fields=['status', 'response_status', 'response_body', 'duration_ms', 'error'])

    if will_retry:
        raise self.retry(countdown=60 * (self.request.retries + 1))
    return result
