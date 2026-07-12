"""
Phase 3: Cloud Storage tests.
Covers models, s3 helpers (mocked), serializers, views, tasks, signals.
"""

import uuid
from unittest.mock import MagicMock, patch, PropertyMock
from botocore.exceptions import ClientError

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership, UserProfile
from storage.models import StorageFile
from storage import s3 as storage_s3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client_error(code='NoSuchBucket'):
    err = ClientError(
        error_response={'Error': {'Code': code, 'Message': 'msg'}},
        operation_name='HeadBucket',
    )
    return err


def make_client(user):
    refresh = RefreshToken.for_user(user)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return c


@pytest.fixture
def owner(db):
    u = User.objects.create_user('owner@ex.com', 'owner@ex.com', 'pass123')
    UserProfile.objects.create(user=u, sign_in_provider='password', email_verified=True)
    return u


@pytest.fixture
def viewer(db):
    u = User.objects.create_user('viewer@ex.com', 'viewer@ex.com', 'pass123')
    UserProfile.objects.create(user=u, sign_in_provider='password', email_verified=True)
    return u


@pytest.fixture
def project(db, owner):
    p = Project.objects.create(name='StorageProj', slug='storage-proj', owner=owner, is_active=True)
    ProjectMembership.objects.create(project=p, user=owner, role='owner')
    return p


@pytest.fixture
def project_with_viewer(db, project, viewer):
    ProjectMembership.objects.create(project=project, user=viewer, role='viewer')
    return project


@pytest.fixture
def owner_client(owner):
    return make_client(owner)


@pytest.fixture
def viewer_client(viewer):
    return make_client(viewer)


@pytest.fixture
def storage_file(db, project, owner):
    return StorageFile.objects.create(
        project=project,
        bucket='ownfb-storage-proj',
        path='images/photo.jpg',
        original_name='photo.jpg',
        content_type='image/jpeg',
        size=1024,
        status=StorageFile.STATUS_READY,
        created_by=owner,
        updated_by=owner,
    )


# ---------------------------------------------------------------------------
# StorageFile model tests
# ---------------------------------------------------------------------------

class TestStorageFileModel:
    def test_create_pending_file(self, db, project, owner):
        f = StorageFile.objects.create(
            project=project,
            bucket='ownfb-test',
            path='docs/report.pdf',
            original_name='report.pdf',
            content_type='application/pdf',
            created_by=owner,
            updated_by=owner,
        )
        assert f.status == StorageFile.STATUS_PENDING
        assert f.size is None
        assert f.thumbnails == {}
        assert f.metadata == {}
        assert str(f.id)  # UUID set

    def test_is_image_true_for_jpeg(self, storage_file):
        assert storage_file.is_image is True

    def test_is_image_false_for_pdf(self, db, project, owner):
        f = StorageFile.objects.create(
            project=project, bucket='b', path='doc.pdf',
            original_name='doc.pdf', content_type='application/pdf',
            created_by=owner, updated_by=owner,
        )
        assert f.is_image is False

    def test_extension_extracted(self, storage_file):
        assert storage_file.extension == 'jpg'

    def test_extension_no_dot(self, db, project, owner):
        f = StorageFile.objects.create(
            project=project, bucket='b', path='Makefile',
            original_name='Makefile', content_type='text/plain',
            created_by=owner, updated_by=owner,
        )
        assert f.extension == ''

    def test_status_choices(self):
        choices = dict(StorageFile.STATUS_CHOICES)
        assert 'pending' in choices
        assert 'confirmed' in choices
        assert 'processing' in choices
        assert 'ready' in choices
        assert 'error' in choices

    def test_str_representation(self, storage_file):
        assert 'storage-proj' in str(storage_file)
        assert 'images/photo.jpg' in str(storage_file)

    def test_unique_project_path_constraint(self, db, project, owner):
        StorageFile.objects.create(
            project=project, bucket='b', path='unique/path.txt',
            original_name='path.txt', content_type='text/plain',
            created_by=owner, updated_by=owner,
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            StorageFile.objects.create(
                project=project, bucket='b', path='unique/path.txt',
                original_name='path.txt', content_type='text/plain',
                created_by=owner, updated_by=owner,
            )

    def test_file_status_transitions(self, db, project, owner):
        f = StorageFile.objects.create(
            project=project, bucket='b', path='trans.txt',
            original_name='trans.txt', content_type='text/plain',
            created_by=owner, updated_by=owner,
        )
        assert f.status == 'pending'
        f.status = 'confirmed'
        f.save(update_fields=['status', 'updated_at'])
        f.refresh_from_db()
        assert f.status == 'confirmed'


# ---------------------------------------------------------------------------
# S3 helper tests (mocked boto3)
# ---------------------------------------------------------------------------

class TestS3Helpers:
    def test_get_bucket_name_basic(self):
        assert storage_s3.get_bucket_name('my-project') == 'ownfb-my-project'

    def test_get_bucket_name_underscores_to_hyphens(self):
        assert storage_s3.get_bucket_name('my_project') == 'ownfb-my-project'

    def test_get_bucket_name_uppercase_lowered(self):
        assert storage_s3.get_bucket_name('MyProject') == 'ownfb-myproject'

    def test_get_bucket_name_long_slug_truncated(self):
        long_slug = 'a' * 60
        name = storage_s3.get_bucket_name(long_slug)
        assert len(name) == len('ownfb-') + 50

    @patch('storage.s3.get_s3_client')
    def test_ensure_bucket_creates_when_not_exists(self, mock_factory):
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.head_bucket.side_effect = _client_error('404')
        storage_s3.ensure_bucket('ownfb-new')
        mock_client.create_bucket.assert_called_once_with(Bucket='ownfb-new')

    @patch('storage.s3.get_s3_client')
    def test_ensure_bucket_skips_when_exists(self, mock_factory):
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.head_bucket.return_value = {}
        storage_s3.ensure_bucket('ownfb-exists')
        mock_client.create_bucket.assert_not_called()

    @patch('storage.s3.get_s3_client')
    def test_ensure_bucket_raises_on_other_error(self, mock_factory):
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.head_bucket.side_effect = _client_error('AccessDenied')
        with pytest.raises(ClientError):
            storage_s3.ensure_bucket('ownfb-denied')

    @patch('storage.s3.get_s3_client')
    def test_presigned_upload_url_returns_put(self, mock_factory):
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.generate_presigned_url.return_value = 'https://minio/bucket/key?sig=xxx'
        result = storage_s3.presigned_upload_url('ownfb-test', 'images/a.jpg', 'image/jpeg')
        assert result['method'] == 'PUT'
        assert 'url' in result
        assert result['expires_in'] == storage_s3.PRESIGNED_UPLOAD_TTL
        mock_client.generate_presigned_url.assert_called_once_with(
            'put_object',
            Params={'Bucket': 'ownfb-test', 'Key': 'images/a.jpg', 'ContentType': 'image/jpeg'},
            ExpiresIn=storage_s3.PRESIGNED_UPLOAD_TTL,
        )

    @patch('storage.s3.get_s3_client')
    def test_presigned_download_url(self, mock_factory):
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.generate_presigned_url.return_value = 'https://minio/bucket/key?dl=1'
        url = storage_s3.presigned_download_url('ownfb-test', 'images/a.jpg')
        assert url == 'https://minio/bucket/key?dl=1'

    @patch('storage.s3.get_s3_client')
    def test_get_object_metadata_success(self, mock_factory):
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.head_object.return_value = {
            'ContentLength': 2048,
            'ContentType': 'image/jpeg',
            'ETag': '"abc123"',
        }
        meta = storage_s3.get_object_metadata('ownfb-test', 'images/a.jpg')
        assert meta['size'] == 2048
        assert meta['content_type'] == 'image/jpeg'
        assert meta['etag'] == 'abc123'

    @patch('storage.s3.get_s3_client')
    def test_get_object_metadata_not_found_returns_empty(self, mock_factory):
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.head_object.side_effect = _client_error('NoSuchKey')
        meta = storage_s3.get_object_metadata('ownfb-test', 'missing.jpg')
        assert meta == {}

    @patch('storage.s3.get_s3_client')
    def test_delete_object_success(self, mock_factory):
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.delete_object.return_value = {}
        assert storage_s3.delete_object('ownfb-test', 'a.jpg') is True

    @patch('storage.s3.get_s3_client')
    def test_delete_object_error_returns_false(self, mock_factory):
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        mock_client.delete_object.side_effect = _client_error('AccessDenied')
        assert storage_s3.delete_object('ownfb-test', 'a.jpg') is False


# ---------------------------------------------------------------------------
# Upload URL view tests
# ---------------------------------------------------------------------------

class TestUploadUrlView:
    URL = '/api/projects/{project_id}/storage/upload-url/'

    @patch('storage.views.ensure_bucket')
    @patch('storage.views.presigned_upload_url')
    def test_upload_url_success(self, mock_presigned, mock_ensure, owner_client, project):
        mock_ensure.return_value = None
        mock_presigned.return_value = {
            'url': 'https://minio/upload', 'method': 'PUT', 'expires_in': 3600,
        }
        resp = owner_client.post(
            self.URL.format(project_id=project.id),
            {'path': 'docs/file.pdf', 'content_type': 'application/pdf'},
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert 'file_id' in data
        assert data['upload_url'] == 'https://minio/upload'
        assert data['method'] == 'PUT'
        assert data['path'] == 'docs/file.pdf'

    def test_upload_url_requires_auth(self, api_client, project):
        resp = api_client.post(
            self.URL.format(project_id=project.id),
            {'path': 'x.txt', 'content_type': 'text/plain'},
            format='json',
        )
        assert resp.status_code == 401

    @patch('storage.views.ensure_bucket')
    @patch('storage.views.presigned_upload_url')
    def test_upload_url_viewer_forbidden(self, mock_presigned, mock_ensure, viewer_client, project_with_viewer):
        resp = viewer_client.post(
            self.URL.format(project_id=project_with_viewer.id),
            {'path': 'x.txt', 'content_type': 'text/plain'},
            format='json',
        )
        assert resp.status_code == 403

    @patch('storage.views.ensure_bucket')
    @patch('storage.views.presigned_upload_url')
    def test_upload_url_missing_path_returns_400(self, mock_presigned, mock_ensure, owner_client, project):
        mock_ensure.return_value = None
        resp = owner_client.post(
            self.URL.format(project_id=project.id),
            {'content_type': 'text/plain'},
            format='json',
        )
        assert resp.status_code == 400

    @patch('storage.views.ensure_bucket')
    def test_upload_url_s3_unavailable_returns_503(self, mock_ensure, owner_client, project):
        mock_ensure.side_effect = Exception('Connection refused')
        resp = owner_client.post(
            self.URL.format(project_id=project.id),
            {'path': 'x.txt', 'content_type': 'text/plain'},
            format='json',
        )
        assert resp.status_code == 503

    def test_upload_url_wrong_project_returns_404(self, owner_client):
        resp = owner_client.post(
            self.URL.format(project_id=uuid.uuid4()),
            {'path': 'x.txt', 'content_type': 'text/plain'},
            format='json',
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Confirm upload view tests
# ---------------------------------------------------------------------------

class TestConfirmUploadView:
    URL = '/api/projects/{project_id}/storage/confirm/'

    @patch('storage.tasks.generate_thumbnails')
    @patch('storage.views.get_object_metadata')
    def test_confirm_success(self, mock_meta, mock_thumb, owner_client, project, db, owner):
        mock_meta.return_value = {'size': 2048, 'content_type': 'image/jpeg', 'etag': 'abc'}
        f = StorageFile.objects.create(
            project=project, bucket='ownfb-storage-proj', path='img.jpg',
            original_name='img.jpg', content_type='image/jpeg',
            status=StorageFile.STATUS_PENDING, created_by=owner, updated_by=owner,
        )
        resp = owner_client.post(
            self.URL.format(project_id=project.id),
            {'file_id': str(f.id)},
            format='json',
        )
        assert resp.status_code == 200
        f.refresh_from_db()
        assert f.status == StorageFile.STATUS_CONFIRMED
        assert f.size == 2048

    def test_confirm_requires_auth(self, api_client, project):
        resp = api_client.post(self.URL.format(project_id=project.id), {}, format='json')
        assert resp.status_code == 401

    @patch('storage.views.get_object_metadata')
    def test_confirm_wrong_file_id_returns_404(self, mock_meta, owner_client, project):
        mock_meta.return_value = {}
        resp = owner_client.post(
            self.URL.format(project_id=project.id),
            {'file_id': str(uuid.uuid4())},
            format='json',
        )
        assert resp.status_code == 404

    @patch('storage.views.get_object_metadata')
    def test_confirm_viewer_forbidden(self, mock_meta, viewer_client, project_with_viewer, db, owner):
        f = StorageFile.objects.create(
            project=project_with_viewer, bucket='b', path='v.txt',
            original_name='v.txt', content_type='text/plain',
            created_by=owner, updated_by=owner,
        )
        resp = viewer_client.post(
            self.URL.format(project_id=project_with_viewer.id),
            {'file_id': str(f.id)},
            format='json',
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# File list view tests
# ---------------------------------------------------------------------------

class TestFileListView:
    URL = '/api/projects/{project_id}/storage/files/'

    def test_list_files(self, owner_client, project, storage_file):
        resp = owner_client.get(self.URL.format(project_id=project.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 1
        assert data['files'][0]['path'] == 'images/photo.jpg'

    def test_list_files_with_prefix_filter(self, owner_client, project, storage_file, db, owner):
        StorageFile.objects.create(
            project=project, bucket='b', path='docs/readme.md',
            original_name='readme.md', content_type='text/markdown',
            created_by=owner, updated_by=owner,
        )
        resp = owner_client.get(
            self.URL.format(project_id=project.id) + '?prefix=images/'
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 1
        assert data['files'][0]['path'] == 'images/photo.jpg'

    def test_list_files_pagination(self, owner_client, project, db, owner):
        for i in range(5):
            StorageFile.objects.create(
                project=project, bucket='b', path=f'file{i}.txt',
                original_name=f'file{i}.txt', content_type='text/plain',
                created_by=owner, updated_by=owner,
            )
        resp = owner_client.get(
            self.URL.format(project_id=project.id) + '?limit=2&offset=0'
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['total'] == 5
        assert len(data['files']) == 2

    def test_list_files_viewer_can_read(self, viewer_client, project_with_viewer, storage_file):
        resp = viewer_client.get(self.URL.format(project_id=project_with_viewer.id))
        assert resp.status_code == 200

    def test_list_files_unauthenticated_returns_401(self, api_client, project):
        resp = api_client.get(self.URL.format(project_id=project.id))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# File detail view tests
# ---------------------------------------------------------------------------

class TestFileDetailView:
    def _url(self, project_id, path):
        return f'/api/projects/{project_id}/storage/files/{path}/'

    def test_get_file_detail(self, owner_client, project, storage_file):
        resp = owner_client.get(self._url(project.id, 'images/photo.jpg'))
        assert resp.status_code == 200
        data = resp.json()
        assert data['path'] == 'images/photo.jpg'
        assert data['content_type'] == 'image/jpeg'

    def test_get_file_not_found_returns_404(self, owner_client, project):
        resp = owner_client.get(self._url(project.id, 'nonexistent/file.txt'))
        assert resp.status_code == 404

    @patch('storage.s3.delete_object')
    def test_delete_file_success(self, mock_del, owner_client, project, storage_file):
        mock_del.return_value = True
        resp = owner_client.delete(self._url(project.id, 'images/photo.jpg'))
        assert resp.status_code == 204
        assert not StorageFile.objects.filter(id=storage_file.id).exists()

    @patch('storage.s3.delete_object')
    def test_delete_file_viewer_forbidden(self, mock_del, viewer_client, project_with_viewer, storage_file):
        resp = viewer_client.delete(self._url(project_with_viewer.id, 'images/photo.jpg'))
        assert resp.status_code == 403

    def test_get_file_unauthenticated_returns_401(self, api_client, project, storage_file):
        resp = api_client.get(self._url(project.id, 'images/photo.jpg'))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Storage task tests
# ---------------------------------------------------------------------------

class TestGenerateThumbnailsTask:
    @patch('storage.s3.get_s3_client')
    def test_skips_non_image(self, mock_factory, db, project, owner):
        f = StorageFile.objects.create(
            project=project, bucket='b', path='doc.pdf',
            original_name='doc.pdf', content_type='application/pdf',
            status=StorageFile.STATUS_CONFIRMED, created_by=owner, updated_by=owner,
        )
        from storage.tasks import generate_thumbnails
        result = generate_thumbnails(str(f.id), str(project.id))
        assert result['skipped'] is True
        assert result['reason'] == 'not_image'

    def test_returns_error_for_missing_file(self, db):
        from storage.tasks import generate_thumbnails
        result = generate_thumbnails(str(uuid.uuid4()), str(uuid.uuid4()))
        assert result['error'] == 'not_found'

    @patch('storage.s3.get_s3_client')
    @patch('storage.tasks.Image', create=True)
    def test_thumbnail_generation_with_pillow(self, mock_image_module, mock_factory, db, project, owner):
        import io
        f = StorageFile.objects.create(
            project=project, bucket='ownfb-storage-proj', path='photo.jpg',
            original_name='photo.jpg', content_type='image/jpeg',
            status=StorageFile.STATUS_PENDING, created_by=owner, updated_by=owner,
        )
        # Use update() to skip signals (avoids Celery/Redis call from post_save signal)
        StorageFile.objects.filter(id=f.id).update(status=StorageFile.STATUS_CONFIRMED)
        mock_client = MagicMock()
        mock_factory.return_value = mock_client
        buf = io.BytesIO(b'fake_image_data')
        mock_client.get_object.return_value = {'Body': buf}

        mock_img = MagicMock()
        mock_img.copy.return_value = mock_img
        mock_img.save = lambda b, format=None: b.write(b'thumb_data')
        mock_image_module.open.return_value = mock_img
        mock_image_module.LANCZOS = 1

        with patch.dict('sys.modules', {'PIL': MagicMock(), 'PIL.Image': mock_image_module}):
            with patch('storage.tasks.Image', mock_image_module):
                from storage.tasks import generate_thumbnails
                result = generate_thumbnails(str(f.id), str(project.id))

        f.refresh_from_db()
        assert f.status in (StorageFile.STATUS_READY, StorageFile.STATUS_PROCESSING)


class TestCleanupPendingUploadsTask:
    @patch('storage.s3.delete_object')
    def test_cleanup_deletes_stale_pending(self, mock_del, db, project, owner):
        mock_del.return_value = True
        from django.utils import timezone
        from datetime import timedelta
        old_file = StorageFile.objects.create(
            project=project, bucket='b', path='stale.txt',
            original_name='stale.txt', content_type='text/plain',
            status=StorageFile.STATUS_PENDING, created_by=owner, updated_by=owner,
        )
        StorageFile.objects.filter(id=old_file.id).update(
            created_at=timezone.now() - timedelta(hours=3)
        )
        from storage.tasks import cleanup_pending_uploads
        result = cleanup_pending_uploads()
        assert result['deleted'] >= 1
        assert not StorageFile.objects.filter(id=old_file.id).exists()

    def test_cleanup_keeps_recent_pending(self, db, project, owner):
        f = StorageFile.objects.create(
            project=project, bucket='b', path='fresh.txt',
            original_name='fresh.txt', content_type='text/plain',
            status=StorageFile.STATUS_PENDING, created_by=owner, updated_by=owner,
        )
        from storage.tasks import cleanup_pending_uploads
        cleanup_pending_uploads()
        assert StorageFile.objects.filter(id=f.id).exists()

    def test_cleanup_keeps_confirmed_files(self, db, project, owner):
        from django.utils import timezone
        from datetime import timedelta
        f = StorageFile.objects.create(
            project=project, bucket='b', path='confirmed.txt',
            original_name='confirmed.txt', content_type='text/plain',
            status=StorageFile.STATUS_CONFIRMED, created_by=owner, updated_by=owner,
        )
        StorageFile.objects.filter(id=f.id).update(
            created_at=timezone.now() - timedelta(hours=5)
        )
        from storage.tasks import cleanup_pending_uploads
        cleanup_pending_uploads()
        assert StorageFile.objects.filter(id=f.id).exists()


# ---------------------------------------------------------------------------
# Storage signals tests
# ---------------------------------------------------------------------------

class TestStorageSignals:
    @patch('storage.tasks.generate_thumbnails')
    @patch('storage.s3.delete_object')
    def test_post_save_triggers_thumbnail_for_image(self, mock_del, mock_thumb, db, project, owner):
        f = StorageFile.objects.create(
            project=project, bucket='b', path='pic.jpg',
            original_name='pic.jpg', content_type='image/jpeg',
            status=StorageFile.STATUS_CONFIRMED, created_by=owner, updated_by=owner,
        )
        mock_thumb.delay.assert_called_once_with(str(f.id), str(project.id))

    @patch('storage.tasks.generate_thumbnails')
    @patch('storage.s3.delete_object')
    def test_post_save_skips_thumbnail_for_non_image(self, mock_del, mock_thumb, db, project, owner):
        StorageFile.objects.create(
            project=project, bucket='b', path='doc.pdf',
            original_name='doc.pdf', content_type='application/pdf',
            status=StorageFile.STATUS_CONFIRMED, created_by=owner, updated_by=owner,
        )
        mock_thumb.delay.assert_not_called()

    @patch('storage.s3.delete_object')
    def test_post_delete_calls_s3_delete(self, mock_del, db, project, owner):
        mock_del.return_value = True
        f = StorageFile.objects.create(
            project=project, bucket='ownfb-b', path='del.txt',
            original_name='del.txt', content_type='text/plain',
            created_by=owner, updated_by=owner,
        )
        f.delete()
        mock_del.assert_called_once_with('ownfb-b', 'del.txt')
