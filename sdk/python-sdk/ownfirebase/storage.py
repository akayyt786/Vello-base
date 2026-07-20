"""OwnFirebase Storage SDK."""

from typing import Any, BinaryIO, Dict, Optional, Union

import requests

from .client import OwnFirebaseClient
from .errors import APIError


class StorageSDK(OwnFirebaseClient):
    """File storage service."""

    def get_upload_url(
        self,
        path: str,
        content_type: Optional[str] = None,
        size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Request a presigned upload URL from MinIO/S3 for direct upload."""
        return self.request(
            'POST',
            self.project_url('storage/upload-url/'),
            json_data={
                'path': path,
                'content_type': content_type,
                'size': size,
                'metadata': metadata,
            },
        )

    def confirm_upload(self, file_id: str) -> Dict[str, Any]:
        """Confirm a direct upload after PUTting to the presigned URL."""
        return self.request(
            'POST',
            self.project_url('storage/confirm/'),
            json_data={'file_id': file_id},
        )

    def list_files(self, prefix: Optional[str] = None) -> Dict[str, Any]:
        """List files, optionally filtered by prefix. Returns a paginated response."""
        query: Dict[str, str] = {}
        if prefix:
            query['prefix'] = prefix
        return self.request('GET', self.project_url('storage/files/'), query_params=query)

    def get_file(self, path: str) -> Dict[str, Any]:
        """Get metadata for a single file by path."""
        return self.request('GET', self.project_url(f'storage/files/{path}/'))

    def delete_file(self, path: str) -> None:
        """Delete a file by path."""
        return self.request('DELETE', self.project_url(f'storage/files/{path}/'))

    def upload(
        self,
        file: Union[bytes, BinaryIO],
        path: str,
        content_type: Optional[str] = None,
        size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """High-level helper: request an upload URL, PUT the file, then confirm."""
        upload_info = self.get_upload_url(
            path=path, content_type=content_type, size=size, metadata=metadata
        )

        headers = {'Content-Type': content_type} if content_type else None
        put_response = requests.put(
            upload_info['upload_url'], data=file, headers=headers, timeout=30
        )

        if not put_response.ok:
            raise APIError(
                status=put_response.status_code,
                message=f'Upload to presigned URL failed: {put_response.reason}',
                detail=None,
            )

        return self.confirm_upload(upload_info['file_id'])
