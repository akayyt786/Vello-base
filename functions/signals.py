"""
Functions signals: listen to Document post_save/post_delete, dispatch CloudFunction triggers.
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='data.Document')
def on_document_saved_trigger_functions(sender, instance, created, **kwargs):
    trigger_type = 'on_create' if created else 'on_update'
    _dispatch(instance.project_id, instance.collection_path, trigger_type, {
        'event': trigger_type,
        'project_id': str(instance.project_id),
        'collection_path': instance.collection_path,
        'doc_id': instance.doc_id,
        'data': instance.data,
        'version': instance.v,
    })


@receiver(post_delete, sender='data.Document')
def on_document_deleted_trigger_functions(sender, instance, **kwargs):
    _dispatch(instance.project_id, instance.collection_path, 'on_delete', {
        'event': 'on_delete',
        'project_id': str(instance.project_id),
        'collection_path': instance.collection_path,
        'doc_id': instance.doc_id,
        'data': instance.data,
        'version': instance.v,
    })


def _dispatch(project_id, collection_path, trigger_type, payload):
    try:
        from functions.models import CloudFunction
        from functions.tasks import invoke_function_for_event
        fns = CloudFunction.objects.filter(
            project_id=project_id,
            trigger_type=trigger_type,
            collection_path=collection_path,
            is_enabled=True,
        )
        for fn in fns:
            invoke_function_for_event.delay(str(fn.id), payload, str(project_id))
    except Exception as e:
        logger.warning(f'functions signal dispatch error: {e}')
