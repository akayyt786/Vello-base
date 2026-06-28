import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class SocialAccount(models.Model):
    PROVIDER_CHOICES = [("google", "Google"), ("github", "GitHub"), ("apple", "Apple")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_accounts")
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES)
    provider_uid = models.CharField(max_length=256)  # google sub or github id
    email = models.EmailField(blank=True)
    name = models.CharField(max_length=255, blank=True)
    avatar_url = models.URLField(blank=True)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("provider", "provider_uid")]
        indexes = [
            models.Index(fields=["user", "provider"]),
            models.Index(fields=["provider", "provider_uid"]),
        ]
