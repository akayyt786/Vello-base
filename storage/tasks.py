"""
Celery tasks for storage: image thumbnail generation, stale upload cleanup.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)

IMAGE_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
THUMBNAIL_SIZES = [(200, 200), (800, 600)]


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_thumbnails(self, file_id):
    try:
        from storage.models import StorageFile
        f = StorageFile.objects.get(id=file_id)
        if not f.is_image or f.content_type not in IMAGE_CONTENT_TYPES:
            return {'skipped': True, 'reason': 'not_image'}

        f.status = StorageFile.STATUS_PROCESSING
        f.save(update_fields=['status', 'updated_at'])

        try:
            from PIL import Image
        except ImportError:
            logger.warning('Pillow not installed — skipping thumbnail generation')
            f.status = StorageFile.STATUS_READY
            f.save(update_fields=['status', 'updated_at'])
            return {'skipped': True, 'reason': 'pillow_not_installed'}

        import io
        from storage.s3 import get_s3_client

        client = get_s3_client()
        obj = client.get_object(Bucket=f.bucket, Key=f.path)
        img = Image.open(io.BytesIO(obj['Body'].read()))

        thumbnails = {}
        for width, height in THUMBNAIL_SIZES:
            thumb = img.copy()
            thumb.thumbnail((width, height), Image.LANCZOS)
            buf = io.BytesIO()
            fmt = 'JPEG' if f.content_type == 'image/jpeg' else 'PNG'
            thumb.save(buf, format=fmt)
            buf.seek(0)

            ext = f.path.rsplit('.', 1)[-1] if '.' in f.path else 'jpg'
            base = f.path.rsplit('.', 1)[0]
            thumb_key = f'{base}_thumb_{width}x{height}.{ext}'
            client.put_object(
                Bucket=f.bucket,
                Key=thumb_key,
                Body=buf.getvalue(),
                ContentType=f.content_type,
            )
            thumbnails[f'{width}x{height}'] = thumb_key

        f.thumbnails = thumbnails
        f.status = StorageFile.STATUS_READY
        f.save(update_fields=['thumbnails', 'status', 'updated_at'])
        return {'thumbnails': thumbnails}

    except StorageFile.DoesNotExist:
        logger.error(f'generate_thumbnails: file {file_id} not found')
        return {'error': 'not_found'}
    except Exception as exc:
        logger.exception(f'generate_thumbnails error for {file_id}')
        raise self.retry(exc=exc)


@shared_task
def cleanup_pending_uploads():
    """Delete StorageFile records stuck in 'pending' for over 2 hours."""
    from django.utils import timezone
    from datetime import timedelta
    from storage.models import StorageFile

    cutoff = timezone.now() - timedelta(hours=2)
    stale = StorageFile.objects.filter(status='pending', created_at__lt=cutoff)
    count = stale.count()
    stale.delete()
    logger.info(f'cleanup_pending_uploads: deleted {count} stale uploads')
    return {'deleted': count}
