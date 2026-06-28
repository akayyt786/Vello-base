import uuid
from django.db import models


class RemoteConfigParameter(models.Model):
    """A single key/value config parameter scoped to a project."""
    PARAM_TYPES = [
        ('string', 'String'),
        ('number', 'Number'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        # 'remote_configs' is already taken by config.RemoteConfig; use a distinct accessor
        related_name='remoteconfig_params',
    )
    key = models.CharField(max_length=256)
    value = models.TextField(help_text="Stored as string; type field controls client-side casting")
    param_type = models.CharField(max_length=16, choices=PARAM_TYPES, default='string')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('project', 'key')]
        ordering = ['key']

    def __str__(self):
        return f"{self.project} / {self.key}"

    def cast_value(self):
        """Return value cast to its declared type."""
        if self.param_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes')
        if self.param_type == 'number':
            try:
                return int(self.value) if '.' not in self.value else float(self.value)
            except ValueError:
                return self.value
        if self.param_type == 'json':
            import json
            try:
                return json.loads(self.value)
            except Exception:
                return self.value
        return self.value
