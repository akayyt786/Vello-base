"""
Storage signals: auto-thumbnail on confirm, S3 cleanup on delete, function triggers.
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='storage.StorageFile')
def on_storage_file_saved(sender, instance, created, **kwargs):
    if instance.status == 'confirmed' and instance.is_image:
        from storage.tasks import generate_thumbnails
        generate_thumbnails.delay(str(instance.id), str(instance.project_id))
    _fire_function_triggers(
        instance,
        'storage.object.finalize' if created else 'storage.object.update',
    )


@receiver(post_delete, sender='storage.StorageFile')
def on_storage_file_deleted(sender, instance, **kwargs):
    from storage.s3 import delete_object
    delete_object(instance.bucket, instance.path)
    _fire_function_triggers(instance, 'storage.object.delete')


def _fire_function_triggers(instance, event_type):
    try:
        from functions.tasks import invoke_function_for_event
        from functions.models import CloudFunction
        fns = CloudFunction.objects.filter(
            project=instance.project,
            trigger_type='on_storage',
            is_enabled=True,
        )
        for fn in fns:
            invoke_function_for_event.delay(str(fn.id), {
                'event': event_type,
                'bucket': instance.bucket,
                'path': instance.path,
                'content_type': instance.content_type,
                'size': instance.size,
            }, str(instance.project_id))
    except Exception as e:
        logger.warning(f'storage signal fn trigger error: {e}')
