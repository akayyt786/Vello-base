import Foundation

public protocol RealtimeDelegate: AnyObject {
  func realtimeDidConnect()
  func realtimeDidDisconnect(error: Error?)
  func realtimeDidReceiveMessage(_ message: RealtimeMessage)
  func realtimeDidEncounterError(_ error: Error)
}

public struct RealtimeMessage: Codable {
  public let type: String // "document_created", "document_updated", "document_deleted"
  public let collection: String
  public let doc_id: String
  public let data: [String: AnyCodable]?
  public let timestamp: String

  public init(
    type: String,
    collection: String,
    doc_id: String,
    data: [String: AnyCodable]? = nil,
    timestamp: String = ISO8601DateFormatter().string(from: Date())
  ) {
    self.type = type
    self.collection = collection
    self.doc_id = doc_id
    self.data = data
    self.timestamp = timestamp
  }
}

public class RealtimeService: OwnFirebaseClient {
  private var webSocket: URLSessionWebSocketTask?
  private let urlSession: URLSession
  private weak var delegate: RealtimeDelegate?
  private var isConnected = false
  private var reconnectAttempts = 0
  private let maxReconnectAttempts = 5
  private let reconnectDelay: TimeInterval = 2
  private var subscriptions: [String: Bool] = [:]

  public init(
    config: OwnFirebaseConfig,
    retryConfig: RetryConfig = RetryConfig(),
    delegate: RealtimeDelegate? = nil
  ) {
    let sessionConfig = URLSessionConfiguration.default
    sessionConfig.timeoutIntervalForRequest = 30
    self.urlSession = URLSession(configuration: sessionConfig)
    self.delegate = delegate

    super.init(config: config, retryConfig: retryConfig)
  }

  // MARK: - Connection Management

  public func connect() async throws {
    guard !isConnected else { return }

    guard let projectId = config.projectId else {
      throw OwnFirebaseError.missingProjectId
    }

    let wsUrl = config.baseUrl
      .replacingOccurrences(of: "http://", with: "ws://")
      .replacingOccurrences(of: "https://", with: "wss://")
      .appending("/ws/v1/projects/\(projectId)/listen/")

    guard let url = URL(string: wsUrl) else {
      throw OwnFirebaseError.invalidURL
    }

    var request = URLRequest(url: url)
    if let token = getAccessToken() {
      request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    }

    webSocket = urlSession.webSocketTask(with: request)
    webSocket?.resume()

    isConnected = true
    reconnectAttempts = 0
    delegate?.realtimeDidConnect()

    await receiveMessages()
  }

  public func disconnect() {
    webSocket?.cancel(with: URLSessionWebSocketTask.CloseCode.goingAway, reason: nil)
    webSocket = nil
    isConnected = false
    subscriptions.removeAll()
  }

  // MARK: - Subscriptions

  public func subscribe(to collection: String) async throws {
    guard isConnected, let webSocket = webSocket else {
      throw OwnFirebaseError.apiError(
        APIError(status: 0, message: "WebSocket not connected")
      )
    }

    let subscription = SubscriptionMessage(
      type: "subscribe",
      collection: collection,
      filters: nil
    )

    let encoder = JSONEncoder()
    let data = try encoder.encode(subscription)
    try await webSocket.send(.data(data))

    subscriptions[collection] = true
  }

  public func subscribeWithFilter(
    to collection: String,
    filters: [String: String]
  ) async throws {
    guard isConnected, let webSocket = webSocket else {
      throw OwnFirebaseError.apiError(
        APIError(status: 0, message: "WebSocket not connected")
      )
    }

    let subscription = SubscriptionMessage(
      type: "subscribe",
      collection: collection,
      filters: filters
    )

    let encoder = JSONEncoder()
    let data = try encoder.encode(subscription)
    try await webSocket.send(.data(data))

    subscriptions[collection] = true
  }

  public func unsubscribe(from collection: String) async throws {
    guard isConnected, let webSocket = webSocket else {
      throw OwnFirebaseError.apiError(
        APIError(status: 0, message: "WebSocket not connected")
      )
    }

    let subscription = SubscriptionMessage(
      type: "unsubscribe",
      collection: collection,
      filters: nil
    )

    let encoder = JSONEncoder()
    let data = try encoder.encode(subscription)
    try await webSocket.send(.data(data))

    subscriptions.removeValue(forKey: collection)
  }

  // MARK: - Message Receiving

  private func receiveMessages() async {
    while isConnected, let webSocket = webSocket {
      do {
        let message = try await webSocket.receive()
        handleMessage(message)
      } catch {
        isConnected = false
        delegate?.realtimeDidDisconnect(error: error)
        await attemptReconnect()
        break
      }
    }
  }

  private func handleMessage(_ message: URLSessionWebSocketTask.Message) {
    switch message {
    case .data(let data):
      do {
        let decoder = JSONDecoder()
        let realtimeMessage = try decoder.decode(RealtimeMessage.self, from: data)
        delegate?.realtimeDidReceiveMessage(realtimeMessage)
      } catch {
        delegate?.realtimeDidEncounterError(error)
      }
    case .string(let string):
      if let data = string.data(using: .utf8) {
        do {
          let decoder = JSONDecoder()
          let realtimeMessage = try decoder.decode(RealtimeMessage.self, from: data)
          delegate?.realtimeDidReceiveMessage(realtimeMessage)
        } catch {
          delegate?.realtimeDidEncounterError(error)
        }
      }
    @unknown default:
      break
    }
  }

  // MARK: - Reconnection Logic

  private func attemptReconnect() async {
    guard reconnectAttempts < maxReconnectAttempts else {
      delegate?.realtimeDidEncounterError(
        OwnFirebaseError.retryExhausted(maxReconnectAttempts)
      )
      return
    }

    reconnectAttempts += 1
    let delay = reconnectDelay * pow(2.0, Double(reconnectAttempts - 1))

    try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))

    do {
      try await connect()
      // Resubscribe to previous subscriptions
      for collection in subscriptions.keys {
        try? await subscribe(to: collection)
      }
    } catch {
      delegate?.realtimeDidEncounterError(error)
      await attemptReconnect()
    }
  }


}

// MARK: - Message Types

struct SubscriptionMessage: Encodable {
  let type: String
  let collection: String
  let filters: [String: String]?
}
