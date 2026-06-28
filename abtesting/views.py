"""
A/B Testing API views.

  GET    /api/projects/{id}/abtesting/experiments/                   — list experiments (member)
  POST   /api/projects/{id}/abtesting/experiments/                   — create experiment (editor)
  GET    /api/projects/{id}/abtesting/experiments/{pk}/              — experiment detail (member)
  PATCH  /api/projects/{id}/abtesting/experiments/{pk}/              — update experiment (editor)
  DELETE /api/projects/{id}/abtesting/experiments/{pk}/              — delete experiment (editor)
  POST   /api/projects/{id}/abtesting/experiments/{pk}/start/        — set status=running (editor)
  POST   /api/projects/{id}/abtesting/experiments/{pk}/pause/        — set status=paused (editor)
  POST   /api/projects/{id}/abtesting/experiments/{pk}/assign/       — get/create assignment (member)
  POST   /api/projects/{id}/abtesting/experiments/{pk}/convert/      — record conversion (member)
  GET    /api/projects/{id}/abtesting/experiments/{pk}/results/      — aggregate results (member)
"""

import logging

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Project, ProjectMembership
from .models import Experiment, ExperimentAssignment, ExperimentConversion
from .serializers import (
    AssignmentResponseSerializer,
    ConversionSerializer,
    ExperimentSerializer,
)
from .services import get_or_assign_variant

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers — same pattern as crashlytics/push/analytics
# ---------------------------------------------------------------------------

def _get_project_and_membership(request, project_id, require_editor=False):
    """
    Fetch project + verify membership.
    Raises PermissionDenied instead of returning a tuple so callers can be inline.
    Returns (project, membership).
    """
    project = get_object_or_404(Project, id=project_id, is_active=True)
    membership = get_object_or_404(ProjectMembership, project=project, user=request.user)
    if require_editor and membership.role not in ('owner', 'editor'):
        raise PermissionDenied('Editor role required.')
    return project, membership


# ---------------------------------------------------------------------------
# ExperimentViewSet
# ---------------------------------------------------------------------------

class ExperimentViewSet(viewsets.ModelViewSet):
    """
    CRUD for experiments + custom actions: start, pause, assign, convert, results.
    """
    serializer_class = ExperimentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    # ---- queryset / project scoping ----------------------------------------

    def _get_project(self, require_editor=False):
        project, _ = _get_project_and_membership(
            self.request,
            self.kwargs['project_id'],
            require_editor=require_editor,
        )
        return project

    def get_queryset(self):
        project = self._get_project()
        return Experiment.objects.filter(project=project).prefetch_related('variants')

    # ---- write hooks --------------------------------------------------------

    def perform_create(self, serializer):
        project = self._get_project(require_editor=True)
        serializer.save(project=project)

    def perform_update(self, serializer):
        self._get_project(require_editor=True)
        serializer.save()

    def perform_destroy(self, instance):
        self._get_project(require_editor=True)
        instance.delete()

    # ---- custom actions -----------------------------------------------------

    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, pk=None, project_id=None):
        """Set experiment status to 'running'. Validates variant allocation sums to 100."""
        project = self._get_project(require_editor=True)
        experiment = get_object_or_404(Experiment, pk=pk, project=project)

        # Guard: must have variants summing to 100
        variants = list(experiment.variants.all())
        if not variants:
            raise ValidationError('Cannot start an experiment with no variants.')
        total_allocation = sum(v.allocation for v in variants)
        if total_allocation != 100:
            raise ValidationError(
                f'Variant allocations must sum to 100 (currently {total_allocation}).'
            )

        experiment.status = 'running'
        experiment.save(update_fields=['status', 'updated_at'])
        return Response(ExperimentSerializer(experiment).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='pause')
    def pause(self, request, pk=None, project_id=None):
        """Set experiment status to 'paused'."""
        project = self._get_project(require_editor=True)
        experiment = get_object_or_404(Experiment, pk=pk, project=project)
        experiment.status = 'paused'
        experiment.save(update_fields=['status', 'updated_at'])
        return Response(ExperimentSerializer(experiment).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None, project_id=None):
        """
        Deterministically assign (or retrieve the existing assignment for)
        a targeting_value and return the variant config.

        Input:  {"targeting_value": "user_123"}
        Output: {"variant_name": "control", "config": {}, "experiment_name": "btn_color"}
        """
        project = self._get_project(require_editor=False)
        experiment = get_object_or_404(Experiment, pk=pk, project=project)

        targeting_value = request.data.get('targeting_value')
        if not targeting_value:
            raise ValidationError({'targeting_value': 'This field is required.'})

        variant = get_or_assign_variant(experiment, targeting_value)
        if variant is None:
            return Response(
                {'detail': f'Experiment is not running (status: {experiment.status}).'},
                status=status.HTTP_409_CONFLICT,
            )

        data = {
            'variant_name': variant.name,
            'config': variant.config,
            'experiment_name': experiment.name,
        }
        serializer = AssignmentResponseSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='convert')
    def convert(self, request, pk=None, project_id=None):
        """
        Record a conversion event for a previously assigned targeting_value.

        Input:  {"targeting_value": "user_123", "event_name": "purchase", "value": 49.99}
        Output: 201 with the created conversion id + recorded_at
        """
        project = self._get_project(require_editor=False)
        experiment = get_object_or_404(Experiment, pk=pk, project=project)

        serializer = ConversionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        assignment = ExperimentAssignment.objects.filter(
            experiment=experiment,
            targeting_value=data['targeting_value'],
        ).first()
        if assignment is None:
            raise ValidationError(
                f"No assignment found for targeting_value '{data['targeting_value']}' "
                f"in experiment '{experiment.name}'."
            )

        conversion = ExperimentConversion.objects.create(
            assignment=assignment,
            event_name=data['event_name'],
            value=data.get('value'),
        )
        return Response(
            {
                'id': str(conversion.id),
                'event_name': conversion.event_name,
                'value': conversion.value,
                'recorded_at': conversion.recorded_at,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='results')
    def results(self, request, pk=None, project_id=None):
        """
        Aggregate per-variant assignment counts and conversion counts.

        Response shape:
        {
          "experiment": {...},
          "variants": [
            {
              "variant_id": "...",
              "variant_name": "control",
              "assignments": 412,
              "conversions": 38,
              "conversion_rate": 0.0922
            },
            ...
          ]
        }
        """
        project = self._get_project(require_editor=False)
        experiment = get_object_or_404(Experiment, pk=pk, project=project)

        variants = experiment.variants.all()
        rows = []
        for variant in variants:
            assignment_count = ExperimentAssignment.objects.filter(
                experiment=experiment,
                variant=variant,
            ).count()

            conversion_count = ExperimentConversion.objects.filter(
                assignment__experiment=experiment,
                assignment__variant=variant,
            ).count()

            rate = (conversion_count / assignment_count) if assignment_count > 0 else 0.0

            rows.append({
                'variant_id': str(variant.id),
                'variant_name': variant.name,
                'allocation': variant.allocation,
                'assignments': assignment_count,
                'conversions': conversion_count,
                'conversion_rate': round(rate, 6),
            })

        return Response(
            {
                'experiment': ExperimentSerializer(experiment).data,
                'variants': rows,
            },
            status=status.HTTP_200_OK,
        )
