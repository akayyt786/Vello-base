"""
S3/MinIO client factory and presigned URL helpers.
Works with any S3-compatible backend (MinIO, AWS S3, DigitalOcean Spaces).

SSRF note: AWS_S3_ENDPOINT_URL must come from server-side settings only — never
from user-controlled request data.  All user-supplied keys (file paths) are
validated by validate_storage_key() before being passed to boto3 to prevent
path traversal attacks (e.g. "../../secret") that could escape the intended
bucket namespace.
"""

import logging
import posixpath
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

PRESIGNED_UPLOAD_TTL = 3600
PRESIGNED_DOWNLOAD_TTL = 900


def validate_storage_key(key: str) -> str:
    """
    Validate and normalise a user-supplied S3 object key.

    Raises ValidationError for:
    - Empty or blank keys
    - Keys that start with '/' (absolute paths)
    - Keys containing '..' segments (directory traversal)
    - Keys containing null bytes or newline characters
    """
    if not key or not key.strip():
        raise ValidationError('Storage path must not be empty.')
    if '\x00' in key or '\n' in key or '\r' in key:
        raise ValidationError('Storage path contains invalid characters.')
    normalized = posixpath.normpath(key)
    if normalized.startswith('/'):
        raise ValidationError('Storage path must not be an absolute path.')
    if normalized.startswith('..') or '/../' in normalized or normalized == '..':
        raise ValidationError('Storage path must not contain directory traversal sequences.')
    return key


def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None),
        aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', 'minioadmin'),
        aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', 'minioadmin'),
        region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1'),
        use_ssl=getattr(settings, 'AWS_S3_USE_SSL', False),
    )


def get_bucket_name(project_slug):
    safe = project_slug.lower().replace('_', '-')[:50]
    return f'ownfb-{safe}'


def ensure_bucket(bucket_name):
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        if e.response['Error']['Code'] in ('404', 'NoSuchBucket'):
            client.create_bucket(Bucket=bucket_name)
        else:
            raise


def presigned_upload_url(bucket, key, content_type):
    key = validate_storage_key(key)
    client = get_s3_client()
    url = client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': bucket,
            'Key': key,
            'ContentType': content_type,
        },
        ExpiresIn=PRESIGNED_UPLOAD_TTL,
    )
    return {'url': url, 'method': 'PUT', 'expires_in': PRESIGNED_UPLOAD_TTL}


def presigned_download_url(bucket, key):
    key = validate_storage_key(key)
    client = get_s3_client()
    return client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=PRESIGNED_DOWNLOAD_TTL,
    )


def get_object_metadata(bucket, key):
    key = validate_storage_key(key)
    client = get_s3_client()
    try:
        resp = client.head_object(Bucket=bucket, Key=key)
        return {
            'size': resp.get('ContentLength'),
            'content_type': resp.get('ContentType'),
            'etag': resp.get('ETag', '').strip('"'),
        }
    except ClientError:
        return {}


def delete_object(bucket, key):
    key = validate_storage_key(key)
    client = get_s3_client()
    try:
        client.delete_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        logger.error(f's3.delete_object error: {e}')
        return False
