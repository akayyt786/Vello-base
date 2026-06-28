from django.apps import AppConfig


class RemoteConfigApp(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "remoteconfig"
    # Explicit label avoids collision with the 'config' app whose label is also 'remoteconfig'
    label = "remoteconfig_params"
    verbose_name = "Remote Config"
