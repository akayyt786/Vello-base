import uuid
from django.conf import settings
from django.db import models


class AIProviderConfig(models.Model):
    PROVIDER_CHOICES = [
        ("anthropic", "Anthropic Claude"),
        ("google", "Google Gemini"),
        ("openai", "OpenAI"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "core.Project", on_delete=models.CASCADE, related_name="ai_provider_configs"
    )
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES)
    # TODO: Replace XOR encryption with proper KMS (e.g. AWS KMS, GCP KMS) in production.
    api_key_encrypted = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("project", "provider")]
        verbose_name = "AI Provider Config"
        verbose_name_plural = "AI Provider Configs"

    def __str__(self):
        return f"{self.project_id} / {self.provider}"


class AIUsageLog(models.Model):
    STATUS_CHOICES = [
        ("success", "Success"),
        ("error", "Error"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "core.Project", on_delete=models.CASCADE, related_name="ai_usage_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_usage_logs",
    )
    provider = models.CharField(max_length=32)
    model = models.CharField(max_length=64)
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="success")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "created_at"]),
            models.Index(fields=["project", "provider", "created_at"]),
        ]
        verbose_name = "AI Usage Log"
        verbose_name_plural = "AI Usage Logs"

    def __str__(self):
        return f"{self.project_id} / {self.provider} / {self.model} / {self.status}"
