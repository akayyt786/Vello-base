from django.apps import AppConfig


class ABTestingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "abtesting"
    verbose_name = "A/B Testing"
