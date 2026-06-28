from rest_framework import serializers
from .models import AIProviderConfig, AIUsageLog


class AIProviderConfigSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(
        write_only=True, required=True,
        help_text="Plain-text API key — stored encrypted",
    )

    class Meta:
        model = AIProviderConfig
        fields = ["id", "provider", "api_key", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ChatMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant", "system"])
    content = serializers.CharField()


class ChatCompletionRequestSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(
        choices=["anthropic", "google", "openai"], default="anthropic"
    )
    model = serializers.CharField(default="claude-sonnet-4-6", max_length=64)
    messages = ChatMessageSerializer(many=True, min_length=1)
    max_tokens = serializers.IntegerField(default=1024, min_value=1, max_value=8192)
    temperature = serializers.FloatField(default=0.7, min_value=0.0, max_value=2.0)
    system = serializers.CharField(required=False, allow_blank=True)


class ChatCompletionResponseSerializer(serializers.Serializer):
    content = serializers.CharField()
    model = serializers.CharField()
    provider = serializers.CharField()
    usage = serializers.DictField()


class EmbeddingRequestSerializer(serializers.Serializer):
    input = serializers.ListField(
        child=serializers.CharField(), min_length=1, max_length=100
    )
    model = serializers.CharField(default="text-embedding-3-small", max_length=64)


class AIUsageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIUsageLog
        fields = "__all__"
