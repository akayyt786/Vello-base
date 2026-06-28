"""
Crashlytics business logic.

group_crash_report: Deduplicate crash reports into CrashGroups by fingerprint.
"""

import hashlib

from django.db.models import Count
from django.utils import timezone

from .models import CrashGroup, CrashReport


def group_crash_report(report: CrashReport) -> CrashGroup:
    """
    Compute a deterministic signature for the crash and upsert a CrashGroup.

    The signature is the first 64 hex chars of sha256(exception_type + ":" + stack_trace[:500]).
    On first occurrence the group is created with first_seen_at = report.occurred_at.
    On subsequent occurrences last_seen_at is advanced and occurrence_count incremented.
    The report's group FK is set and saved before returning.
    """
    raw = f"{report.exception_type}:{report.stack_trace[:500]}"
    signature = hashlib.sha256(raw.encode('utf-8', errors='replace')).hexdigest()[:64]

    # Derive a human-readable title from the first line of the stack trace or the exception type
    first_line = report.stack_trace.splitlines()[0].strip() if report.stack_trace else ''
    title = first_line[:512] if first_line else report.exception_type[:512]

    crash_group, created = CrashGroup.objects.get_or_create(
        project=report.project,
        signature=signature,
        defaults={
            'title': title,
            'exception_type': report.exception_type,
            'first_seen_at': report.occurred_at,
            'last_seen_at': report.occurred_at,
            'occurrence_count': 1,
        },
    )

    if not created:
        # Advance last_seen_at and bump occurrence count atomically
        update_fields = ['occurrence_count', 'updated_at']
        crash_group.occurrence_count += 1
        if report.occurred_at > crash_group.last_seen_at:
            crash_group.last_seen_at = report.occurred_at
            update_fields.append('last_seen_at')
        crash_group.save(update_fields=update_fields)

    # Link the report to its group
    report.group = crash_group
    report.save(update_fields=['group'])

    # Recompute affected_users_count using a DB Count aggregate so it is always
    # accurate and never computed as a Python-level list count.
    # This runs after report.group is saved so the current report is included.
    new_affected = (
        CrashReport.objects
        .filter(group=crash_group)
        .exclude(user_id='')
        .aggregate(cnt=Count('user_id', distinct=True))['cnt']
    )
    CrashGroup.objects.filter(pk=crash_group.pk).update(affected_users_count=new_affected)
    crash_group.affected_users_count = new_affected

    return crash_group
