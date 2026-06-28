"""
Django signals: Document changes → broadcast to channel layer groups.
This is the CDC (change data capture) layer for Own Firebase realtime.
"""

import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _doc_group(project_id: str, collection_path: str, doc_id: str) -> str:
    safe = lambda s: str(s).replace('/', '__').replace('-', '_')
    return f'p_{safe(project_id)}_d_{safe(collection_path)}_{safe(doc_id)}'


def _col_group(project_id: str, collection_path: str) -> str:
    safe = lambda s: str(s).replace('/', '__').replace('-', '_')
    return f'p_{safe(project_id)}_c_{safe(collection_path)}'


def _broadcast(group_name: str, message: dict) -> None:
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(group_name, {
            'type': 'realtime.event',
            **message,
        })
    except Exception as e:
        logger.warning(f'broadcast error to {group_name}: {e}')


@receiver(post_save, sender='data.Document')
def on_document_saved(sender, instance, created, **kwargs):
    project_id = str(instance.project_id)
    collection_path = instance.collection_path
    doc_id = instance.doc_id
    event = 'added' if created else 'modified'

    payload = {
        'event': event,
        'project_id': project_id,
        'collection_path': collection_path,
        'doc_id': doc_id,
        'data': instance.data,
        'version': instance.v,
    }

    _broadcast(_doc_group(project_id, collection_path, doc_id), payload)
    _broadcast(_col_group(project_id, collection_path), payload)


@receiver(post_delete, sender='data.Document')
def on_document_deleted(sender, instance, **kwargs):
    project_id = str(instance.project_id)
    collection_path = instance.collection_path
    doc_id = instance.doc_id

    payload = {
        'event': 'removed',
        'project_id': project_id,
        'collection_path': collection_path,
        'doc_id': doc_id,
        'data': None,
        'version': instance.v,
    }

    _broadcast(_doc_group(project_id, collection_path, doc_id), payload)
    _broadcast(_col_group(project_id, collection_path), payload)
