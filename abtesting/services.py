"""
A/B Testing assignment service.

Deterministic variant assignment ensures the same targeting_value always gets
the same variant (sticky assignment), even if called from multiple processes
simultaneously (get_or_create handles the race).
"""

import hashlib

from .models import Experiment, ExperimentVariant, ExperimentAssignment


def get_or_assign_variant(experiment: Experiment, targeting_value: str):
    """
    Deterministically assign a variant to a targeting_value.
    Same targeting_value always gets same variant (sticky).
    Returns ExperimentVariant or None if experiment is not running.
    """
    if experiment.status != 'running':
        return None

    # Return existing sticky assignment if already done
    existing = (
        ExperimentAssignment.objects
        .filter(experiment=experiment, targeting_value=str(targeting_value))
        .select_related('variant')
        .first()
    )
    if existing:
        return existing.variant

    # Deterministic bucket: hash(experiment_id:targeting_value) mod 100
    key = f"{experiment.id}:{targeting_value}"
    bucket = int(hashlib.sha256(key.encode()).hexdigest(), 16) % 100

    # Walk variants (sorted by name for determinism) and find the bucket owner
    variants = list(
        ExperimentVariant.objects.filter(experiment=experiment).order_by('name')
    )
    cumulative = 0
    assigned_variant = None
    for v in variants:
        cumulative += v.allocation
        if bucket < cumulative:
            assigned_variant = v
            break

    # Safety: overflow (allocations < 100) or empty bucket → last variant
    if not assigned_variant and variants:
        assigned_variant = variants[-1]

    if not assigned_variant:
        return None

    # Persist the assignment; get_or_create is race-safe
    assignment, _ = ExperimentAssignment.objects.get_or_create(
        experiment=experiment,
        targeting_value=str(targeting_value),
        defaults={'variant': assigned_variant},
    )
    return assignment.variant
