"""
Presence system: track connected clients, onDisconnect handlers.
Uses Redis with expiring keys — same pattern as Firebase RTDB presence.
"""

import json
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

PRESENCE_TTL = 30  # seconds; clients must ping to keep alive
PRESENCE_KEY = 'presence:{project_id}:{user_id}'
ON_DISCONNECT_KEY = 'ondisconnect:{project_id}:{user_id}:{channel_name}'


def set_presence(project_id: str, user_id: str, channel_name: str, data: dict) -> None:
    key = PRESENCE_KEY.format(project_id=project_id, user_id=user_id)
    cache.set(key, json.dumps({
        'user_id': user_id,
        'channel_name': channel_name,
        'data': data,
    }), timeout=PRESENCE_TTL)


def remove_presence(project_id: str, user_id: str, channel_name: str) -> None:
    key = PRESENCE_KEY.format(project_id=project_id, user_id=user_id)
    cache.delete(key)


def refresh_presence(project_id: str, user_id: str, channel_name: str) -> None:
    key = PRESENCE_KEY.format(project_id=project_id, user_id=user_id)
    data = cache.get(key)
    if data:
        cache.set(key, data, timeout=PRESENCE_TTL)


def get_online_users(project_id: str) -> list:
    pattern = PRESENCE_KEY.format(project_id=project_id, user_id='*')
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection('default')
        keys = conn.keys(pattern)
        users = []
        for k in keys:
            raw = conn.get(k)
            if raw:
                users.append(json.loads(raw))
        return users
    except Exception as e:
        logger.warning(f'presence.get_online_users error: {e}')
        return []


def register_on_disconnect(project_id: str, user_id: str, channel_name: str,
                           collection_path: str, doc_id: str, data: dict) -> None:
    key = ON_DISCONNECT_KEY.format(
        project_id=project_id, user_id=user_id, channel_name=channel_name
    )
    cache.set(key, json.dumps({
        'collection_path': collection_path,
        'doc_id': doc_id,
        'data': data,
    }), timeout=3600)


def fire_on_disconnect(project_id: str, user_id: str, channel_name: str) -> None:
    key = ON_DISCONNECT_KEY.format(
        project_id=project_id, user_id=user_id, channel_name=channel_name
    )
    payload_raw = cache.get(key)
    if not payload_raw:
        return
    try:
        payload = json.loads(payload_raw)
        from data.models import Document
        from core.models import Project
        project = Project.objects.get(id=project_id)
        doc = Document.objects.get(
            project=project,
            collection_path=payload['collection_path'],
            doc_id=payload['doc_id'],
        )
        doc.data = payload['data']
        doc.save(update_fields=['data', 'updated_at'])  # triggers post_save → CDC broadcast
        logger.info(f'on_disconnect fired for {project_id}/{payload["collection_path"]}/{payload["doc_id"]}')
    except Exception as e:
        logger.error(f'on_disconnect error: {e}')
    finally:
        cache.delete(key)
