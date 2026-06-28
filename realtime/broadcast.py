"""
Utility to broadcast data events to all WS clients subscribed to a collection.
Called from data/signals.py after document create/update/delete.
"""
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def broadcast_document_event(project_id, collection_name, event_type, document_data):
    """
    Push event to all WebSocket clients subscribed to this project+collection.
    event_type: 'created' | 'updated' | 'deleted'
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return  # No channel layer configured (e.g., tests without Redis)
    group = f'project_{project_id}_collection_{collection_name}'
    try:
        async_to_sync(channel_layer.group_send)(group, {
            'type': 'document_event',
            'collection': collection_name,
            'event': event_type,
            'document': document_data,
        })
    except Exception as exc:
        logger.warning('broadcast_document_event failed: %s', exc)
