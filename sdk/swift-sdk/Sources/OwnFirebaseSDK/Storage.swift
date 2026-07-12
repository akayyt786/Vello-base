import Foundation

public class StorageService: OwnFirebaseClient {
  // MARK: - Upload URL Management

  public func getUploadUrl(
    path: String,
    contentType: String = "application/octet-stream",
    size: Int? = nil,
    metadata: [String: AnyCodable]? = nil
  ) async throws -> StorageUploadUrl {
    let body = GetUploadUrlRequest(
      path: path,
      content_type: contentType,
      size: size,
      metadata: metadata
    )
    return try await request(
      "POST",
      url: projectUrl("storage/upload-url/"),
      body: body
    )
  }

  public func confirmUpload(fileId: String) async throws -> StorageObject {
    let body = ConfirmUploadRequest(file_id: fileId)
    return try await request(
      "POST",
      url: projectUrl("storage/confirm/"),
      body: body
    )
  }

  // MARK: - File Operations

  public func listFiles(prefix: String? = nil) async throws -> PaginatedResponse<StorageObject> {
    var options = RequestOptions()
    if let prefix = prefix {
      options.query = ["prefix": prefix]
    }

    return try await request(
      "GET",
      url: projectUrl("storage/files/"),
      options: options
    )
  }

  public func getFile(path: String) async throws -> StorageObject {
    return try await request(
      "GET",
      url: projectUrl("storage/files/\(path)/")
    )
  }

  public func deleteFile(path: String) async throws {
    try await requestVoid(
      "DELETE",
      url: projectUrl("storage/files/\(path)/")
    )
  }

  // MARK: - High-Level Upload Helper

  public func upload(
    data: Data,
    path: String,
    contentType: String = "application/octet-stream",
    metadata: [String: AnyCodable]? = nil
  ) async throws -> StorageObject {
    // Get upload URL
    let uploadUrlResponse = try await getUploadUrl(
      path: path,
      contentType: contentType,
      size: data.count,
      metadata: metadata
    )

    // Upload file to presigned URL
    try await uploadToPresignedUrl(
      url: uploadUrlResponse.upload_url,
      data: data,
      contentType: contentType
    )

    // Confirm upload
    return try await confirmUpload(fileId: uploadUrlResponse.file_id)
  }

  private func uploadToPresignedUrl(
    url: String,
    data: Data,
    contentType: String
  ) async throws {
    guard let presignedUrl = URL(string: url) else {
      throw OwnFirebaseError.invalidURL
    }

    var request = URLRequest(url: presignedUrl)
    request.httpMethod = "PUT"
    request.setValue(contentType, forHTTPHeaderField: "Content-Type")
    request.httpBody = data

    let (_, response) = try await URLSession.shared.data(for: request)

    guard let httpResponse = response as? HTTPURLResponse else {
      throw OwnFirebaseError.invalidResponse
    }

    guard httpResponse.statusCode >= 200 && httpResponse.statusCode < 300 else {
      throw OwnFirebaseError.apiError(
        APIError(
          status: httpResponse.statusCode,
          message: HTTPURLResponse.localizedString(forStatusCode: httpResponse.statusCode),
          detail: nil
        )
      )
    }
  }

  // MARK: - Download Helper

  public func downloadFile(url: String) async throws -> Data {
    guard let fileUrl = URL(string: url) else {
      throw OwnFirebaseError.invalidURL
    }

    let (data, response) = try await URLSession.shared.data(from: fileUrl)

    guard let httpResponse = response as? HTTPURLResponse else {
      throw OwnFirebaseError.invalidResponse
    }

    guard httpResponse.statusCode >= 200 && httpResponse.statusCode < 300 else {
      throw OwnFirebaseError.apiError(
        APIError(
          status: httpResponse.statusCode,
          message: HTTPURLResponse.localizedString(forStatusCode: httpResponse.statusCode),
          detail: nil
        )
      )
    }

    return data
  }
}

// MARK: - Request Types

private struct GetUploadUrlRequest: Encodable {
  let path: String
  let content_type: String
  let size: Int?
  let metadata: [String: AnyCodable]?
}

private struct ConfirmUploadRequest: Encodable {
  let file_id: String
}
