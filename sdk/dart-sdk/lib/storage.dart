import 'client.dart';
import 'types.dart';

/// Cloud Storage SDK for OwnFirebase (Firebase Storage-like file storage).
///
/// Files are uploaded directly to the storage backend (MinIO/S3) using a
/// presigned URL: request the URL with [getUploadUrl], PUT the file bytes to
/// `uploadUrl` yourself, then call [confirmUpload] to finalize the file record.
class StorageSDK extends OwnFirebaseClient {
  StorageSDK({required OwnFirebaseConfig config}) : super(config: config);

  // ─── Upload ──────────────────────────────────────────────────────────────────

  /// Request a presigned upload URL for direct client upload.
  ///
  /// [path] is the full destination path (e.g. `"avatars/photo.png"`).
  /// [contentType] is the MIME type of the file being uploaded.
  /// [size] is the optional declared file size in bytes (enforced server-side
  /// against a 100 MB limit).
  /// [metadata] is optional arbitrary metadata to store alongside the file.
  Future<StorageUploadUrl> getUploadUrl({
    required String path,
    required String contentType,
    int? size,
    Map<String, dynamic>? metadata,
  }) async {
    return request<StorageUploadUrl>(
      'POST',
      projectUrl('storage/upload-url/'),
      {
        'path': path,
        'content_type': contentType,
        if (size != null) 'size': size,
        if (metadata != null) 'metadata': metadata,
      },
      fromJson: (json) => StorageUploadUrl.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Confirm that a file has been uploaded to its presigned URL.
  ///
  /// [fileId] is the `file_id` returned by [getUploadUrl].
  Future<StorageObject> confirmUpload(String fileId) async {
    return request<StorageObject>(
      'POST',
      projectUrl('storage/confirm/'),
      {'file_id': fileId},
      fromJson: (json) => StorageObject.fromJson(json as Map<String, dynamic>),
    );
  }

  // ─── Files ───────────────────────────────────────────────────────────────────

  /// List files, optionally filtered by path [prefix] and paginated with
  /// [limit] (server caps at 200, defaults to 50) and [offset] (defaults to 0).
  Future<StorageFileListResponse> listFiles({
    String? prefix,
    int? limit,
    int? offset,
  }) async {
    return request<StorageFileListResponse>(
      'GET',
      projectUrl('storage/files/'),
      null,
      query: {
        if (prefix != null) 'prefix': prefix,
        if (limit != null) 'limit': limit.toString(),
        if (offset != null) 'offset': offset.toString(),
      },
      fromJson: (json) => StorageFileListResponse.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Get a single file's metadata by its [path].
  Future<StorageObject> getFile(String path) async {
    return request<StorageObject>(
      'GET',
      projectUrl('storage/files/$path/'),
      null,
      fromJson: (json) => StorageObject.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Delete a file by its [path].
  Future<void> deleteFile(String path) async {
    return request<void>(
      'DELETE',
      projectUrl('storage/files/$path/'),
      null,
      fromJson: (_) => null,
    );
  }
}

// ─── Models ────────────────────────────────────────────────────────────────────

/// A stored file record (matches the backend's `StorageFileSerializer`).
class StorageObject {
  final String id;
  final String path;
  final String originalName;
  final String contentType;
  final int? size;
  final String status;
  final Map<String, dynamic> metadata;
  final Map<String, dynamic>? thumbnails;
  final String? downloadUrl;
  final String createdAt;
  final String updatedAt;

  StorageObject({
    required this.id,
    required this.path,
    required this.originalName,
    required this.contentType,
    this.size,
    required this.status,
    required this.metadata,
    this.thumbnails,
    this.downloadUrl,
    required this.createdAt,
    required this.updatedAt,
  });

  factory StorageObject.fromJson(Map<String, dynamic> json) {
    return StorageObject(
      id: json['id'] as String,
      path: json['path'] as String,
      originalName: json['original_name'] as String,
      contentType: json['content_type'] as String,
      size: json['size'] as int?,
      status: json['status'] as String,
      metadata: Map<String, dynamic>.from(json['metadata'] as Map? ?? {}),
      thumbnails: json['thumbnails'] == null
          ? null
          : Map<String, dynamic>.from(json['thumbnails'] as Map),
      downloadUrl: json['download_url'] as String?,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'path': path,
    'original_name': originalName,
    'content_type': contentType,
    'size': size,
    'status': status,
    'metadata': metadata,
    'thumbnails': thumbnails,
    'download_url': downloadUrl,
    'created_at': createdAt,
    'updated_at': updatedAt,
  };
}

/// Response from requesting a presigned upload URL.
class StorageUploadUrl {
  final String fileId;
  final String uploadUrl;
  final String method;
  final int expiresIn;
  final String path;
  final String bucket;

  StorageUploadUrl({
    required this.fileId,
    required this.uploadUrl,
    required this.method,
    required this.expiresIn,
    required this.path,
    required this.bucket,
  });

  factory StorageUploadUrl.fromJson(Map<String, dynamic> json) {
    return StorageUploadUrl(
      fileId: json['file_id'] as String,
      uploadUrl: json['upload_url'] as String,
      method: json['method'] as String,
      expiresIn: json['expires_in'] as int,
      path: json['path'] as String,
      bucket: json['bucket'] as String,
    );
  }
}

/// Response from listing files. Note: unlike other OwnFirebase list endpoints,
/// this is NOT the DRF-style count/next/previous/results shape — the storage
/// backend returns files/total/limit/offset instead.
class StorageFileListResponse {
  final List<StorageObject> files;
  final int total;
  final int limit;
  final int offset;

  StorageFileListResponse({
    required this.files,
    required this.total,
    required this.limit,
    required this.offset,
  });

  factory StorageFileListResponse.fromJson(Map<String, dynamic> json) {
    final files = (json['files'] as List?)
            ?.map((item) => StorageObject.fromJson(item as Map<String, dynamic>))
            .toList() ??
        [];

    return StorageFileListResponse(
      files: files,
      total: json['total'] as int? ?? 0,
      limit: json['limit'] as int? ?? 0,
      offset: json['offset'] as int? ?? 0,
    );
  }
}
