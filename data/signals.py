"""Broadcast data document events over WebSocket."""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Document


def _doc_to_dict(doc):
    return {
        'id': str(doc.id),
        'collection': doc.collection_path,
        'doc_id': doc.doc_id,
        'data': doc.data,
        'created_at': doc.created_at.isoformat(),
        'updated_at': doc.updated_at.isoformat(),
    }


@receiver(post_save, sender=Document)
def on_document_save(sender, instance, created, **kwargs):
    from realtime.broadcast import broadcast_document_event
    event = 'created' if created else 'updated'
    broadcast_document_event(
        project_id=str(instance.project_id),
        collection_name=instance.collection_path,
        event_type=event,
        document_data=_doc_to_dict(instance),
    )


@receiver(post_delete, sender=Document)
def on_document_delete(sender, instance, **kwargs):
    from realtime.broadcast import broadcast_document_event
    broadcast_document_event(
        project_id=str(instance.project_id),
        collection_name=instance.collection_path,
        event_type='deleted',
        document_data={
            'id': str(instance.id),
            'collection': instance.collection_path,
            'doc_id': instance.doc_id,
        },
    )
