"""Serializers for the Push Notifications API."""

from rest_framework import serializers
from .models import DeviceToken, Topic, TopicSubscription, PushNotification, NotificationCampaign


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = [
            'id', 'project', 'user', 'platform', 'token', 'app_id',
            'is_active', 'created_at', 'updated_at',
        ]
        # user is read_only: callers cannot register tokens on behalf of other users.
        read_only_fields = ['id', 'project', 'user', 'created_at', 'updated_at']

    def validate_platform(self, value):
        valid = [choice[0] for choice in DeviceToken.PLATFORM_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(
                f'Invalid platform. Must be one of: {", ".join(valid)}.'
            )
        return value

    def validate_token(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Token must not be blank.')
        return value.strip()


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'project', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'project', 'created_at']

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Topic name must not be blank.')
        return value.strip()


class TopicSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicSubscription
        fields = ['id', 'topic', 'device_token', 'created_at']
        read_only_fields = ['id', 'created_at']


class PushNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushNotification
        fields = [
            'id', 'project', 'title', 'body', 'data', 'image_url',
            'device_token', 'topic',
            'status', 'error', 'delivered_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'project',
            'status', 'error', 'delivered_at',
            'created_at', 'updated_at',
        ]

    def validate(self, data):
        device_token = data.get('device_token')
        topic = data.get('topic')
        if not device_token and not topic:
            raise serializers.ValidationError(
                'Either device_token or topic must be specified.'
            )
        if device_token and topic:
            raise serializers.ValidationError(
                'Specify either device_token or topic, not both.'
            )
        # Cross-project IDOR guard: FK targets must belong to the same project.
        view = self.context.get('view')
        if view:
            project_id = str(view.kwargs.get('project_id', ''))
            if device_token and str(device_token.project_id) != project_id:
                raise serializers.ValidationError(
                    {'device_token': 'Device token does not belong to this project.'}
                )
            if topic and str(topic.project_id) != project_id:
                raise serializers.ValidationError(
                    {'topic': 'Topic does not belong to this project.'}
                )
        return data


class NotificationCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationCampaign
        fields = [
            'id', 'project', 'name', 'title', 'body', 'data', 'image_url',
            'topic', 'target_platforms',
            'status', 'scheduled_at', 'sent_at',
            'total_sent', 'total_failed',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'project',
            'status', 'sent_at',
            'total_sent', 'total_failed',
            'created_at', 'updated_at',
        ]

    def validate_target_platforms(self, value):
        valid = {choice[0] for choice in DeviceToken.PLATFORM_CHOICES}
        for platform in (value or []):
            if platform not in valid:
                raise serializers.ValidationError(
                    f'Invalid platform "{platform}". Must be one of: {", ".join(sorted(valid))}.'
                )
        return value


class SendNotificationSerializer(serializers.Serializer):
    """Input serializer for the ad-hoc send notification endpoint."""

    title = serializers.CharField(max_length=255)
    body = serializers.CharField()
    data = serializers.DictField(required=False, default=dict)
    image_url = serializers.URLField(required=False, allow_blank=True, default='')
    device_token_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    topic_id = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate(self, data):
        if not data.get('device_token_id') and not data.get('topic_id'):
            raise serializers.ValidationError(
                'Either device_token_id or topic_id must be specified.'
            )
        if data.get('device_token_id') and data.get('topic_id'):
            raise serializers.ValidationError(
                'Specify either device_token_id or topic_id, not both.'
            )
        return data
