from django.contrib import admin
from .models import SocialAccount


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "provider", "provider_uid", "email", "created_at"]
    list_filter = ["provider"]
    search_fields = ["user__email", "provider_uid", "email"]
