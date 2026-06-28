"""Serializers for Cloud Functions API."""

import ipaddress
import re
import socket
from urllib.parse import urlparse

from rest_framework import serializers
from .models import CloudFunction, FunctionLog

_BLOCKED_HEADER_RE = re.compile(
    r'^(host|content-length|transfer-encoding|x-forwarded-.*|authorization)$',
    re.IGNORECASE,
)


class CloudFunctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CloudFunction
        fields = [
            'id', 'name', 'description', 'trigger_type', 'collection_path',
            'endpoint_url', 'schedule', 'is_enabled', 'timeout_seconds',
            'retry_count', 'extra_headers', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_endpoint_url(self, value):
        parsed = urlparse(value)
        if parsed.scheme not in ('http', 'https'):
            raise serializers.ValidationError('endpoint_url must use http or https.')
        host = parsed.hostname
        if not host:
            raise serializers.ValidationError('endpoint_url has no hostname.')
        try:
            results = socket.getaddrinfo(host, None)
        except socket.gaierror:
            raise serializers.ValidationError('Cannot resolve endpoint_url hostname.')
        for *_, sockaddr in results:
            ip = ipaddress.ip_address(sockaddr[0])
            if (ip.is_loopback or ip.is_link_local or ip.is_private
                    or ip.is_multicast or ip.is_unspecified):
                raise serializers.ValidationError(
                    'endpoint_url must not resolve to a private, loopback, link-local, '
                    'or multicast address.'
                )
        return value

    def validate_extra_headers(self, value):
        for key in (value or {}):
            if _BLOCKED_HEADER_RE.match(key):
                raise serializers.ValidationError(
                    f'Header "{key}" is not permitted in extra_headers.'
                )
        return value

    def validate(self, data):
        trigger = data.get('trigger_type', getattr(self.instance, 'trigger_type', ''))
        if trigger in ('on_create', 'on_update', 'on_delete'):
            col = data.get('collection_path', getattr(self.instance, 'collection_path', ''))
            if not col:
                raise serializers.ValidationError(
                    {'collection_path': 'Required for document triggers.'}
                )
        if trigger == 'scheduled':
            sched = data.get('schedule', getattr(self.instance, 'schedule', ''))
            if not sched:
                raise serializers.ValidationError(
                    {'schedule': 'Cron expression required for scheduled triggers.'}
                )
        return data


class FunctionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FunctionLog
        # response_body excluded from API: upstream response contents must not be
        # echoed to callers (prevents SSRF data exfiltration via function logs).
        fields = ['id', 'trigger_data', 'status', 'response_status',
                  'duration_ms', 'error', 'created_at']
        read_only_fields = ['id', 'trigger_data', 'status', 'response_status',
                            'duration_ms', 'error', 'created_at']


class InvokeSerializer(serializers.Serializer):
    data = serializers.DictField(required=False, default=dict)
    headers = serializers.DictField(required=False, default=dict)
