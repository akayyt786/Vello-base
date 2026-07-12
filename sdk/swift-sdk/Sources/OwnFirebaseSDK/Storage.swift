import Foundation

public class StorageService: OwnFirebaseClient {
  // MARK: - Upload URL Management

  public func getUploadUrl(
    filename: String,
    contentType: String,
    path: String? = nil
  ) async throws -> StorageUploadUrl {
    let body = GetUploadUrlRequest(
      filename: filename,
      content_type: contentType,
      path: path
    )
    return try await request(
      "POST",
      url: projectUrl("storage/upload-url/"),
      body: body
    )
  }

  public func confirmUpload(objectKey: String) async throws -> StorageObject {
    let body = ConfirmUploadRequest(object_key: objectKey)
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
    filename: String,
    contentType: String,
    path: String? = nil
  ) async throws -> StorageObject {
    // Get upload URL
    let uploadUrlResponse = try await getUploadUrl(
      filename: filename,
      contentType: contentType,
      path: path
    )

    // Upload file to presigned URL
    try await uploadToPresignedUrl(
      url: uploadUrlResponse.upload_url,
      data: data,
      contentType: contentType
    )

    // Confirm upload
    return try await confirmUpload(objectKey: uploadUrlResponse.object_key)
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
  let filename: String
  let content_type: String
  let path: String?
}

private struct ConfirmUploadRequest: Encodable {
  let object_key: String
}
