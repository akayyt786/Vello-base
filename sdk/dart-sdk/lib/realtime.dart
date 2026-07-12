import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:web_socket_channel/web_socket_channel.dart';

import 'types.dart';

/// A single realtime change event delivered for an active subscription.
///
/// Mirrors the server's `{"type": "change", ...}` message. `onChange()`
/// streams the raw decoded message as a `Map<String, dynamic>`; this class
/// is provided as a convenience for callers who want a typed view of that
/// same payload (e.g. `RealtimeChange.fromJson(message)`).
class RealtimeChange {
  final String subscriptionId;
  final String event; // 'added' | 'modified' | 'removed'
  final Map<String, dynamic> data;
  final int? version;
  final String? docId;

  RealtimeChange({
    required this.subscriptionId,
    required this.event,
    required this.data,
    this.version,
    this.docId,
  });

  factory RealtimeChange.fromJson(Map<String, dynamic> json) {
    return RealtimeChange(
      subscriptionId: json['subscriptionId'] as String,
      event: json['event'] as String,
      data: Map<String, dynamic>.from(json['data'] as Map? ?? {}),
      version: json['version'] as int?,
      docId: json['docId'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'type': 'change',
        'subscriptionId': subscriptionId,
        'event': event,
        'data': data,
        'version': version,
        'docId': docId,
      };
}

/// Error returned by the realtime server in response to a request (e.g. a
/// `subscribe` that failed with `PERMISSION_DENIED` or `NOT_FOUND`), or
/// raised locally when a request cannot be completed (timeout, disconnect
/// before a response arrived).
class RealtimeException implements Exception {
  final String code;
  final String message;

  RealtimeException({required this.code, required this.message});

  @override
  String toString() => 'RealtimeException($code): $message';
}

class _PendingRequest {
  final Completer<Map<String, dynamic>> completer;
  final Timer timer;

  _PendingRequest(this.completer, this.timer);
}

/// Realtime (WebSocket) SDK for OwnFirebase.
///
/// Unlike the REST-backed services (`PushSDK`, `DataSDK`, ...), this does not
/// extend `OwnFirebaseClient` since it speaks a JSON-over-WebSocket protocol
/// rather than HTTP. It still takes the same [OwnFirebaseConfig] and exposes
/// [setAccessToken]/[setProjectId] so it can be wired into the SDK bundle the
/// same way the other services are.
///
/// Connects to `ws(s)://<host>/ws/v1/projects/{projectId}/listen/?token=...`.
/// The access token is sent as a query parameter because non-browser clients
/// have no session cookie for the server's WebSocket auth middleware to fall
/// back on.
class RealtimeSDK {
  final String baseUrl;
  String? projectId;
  String? accessToken;

  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _streamSubscription;
  Future<void>? _connectingFuture;
  bool _connected = false;
  bool _manualDisconnect = false;

  int _requestIdCounter = 0;
  final Map<String, _PendingRequest> _pendingRequests = {};
  final Map<String, StreamController<Map<String, dynamic>>> _changeControllers = {};

  int _reconnectAttempts = 0;
  Timer? _reconnectTimer;
  final math.Random _random = math.Random();

  static const int _reconnectBaseDelayMs = 1000;
  static const int _maxReconnectAttempts = 10;
  static const Duration _subscribeTimeout = Duration(seconds: 10);

  RealtimeSDK({required OwnFirebaseConfig config})
      : baseUrl = config.baseUrl.replaceAll(RegExp(r'/$'), ''),
        projectId = config.projectId,
        accessToken = config.accessToken;

  void setAccessToken(String token) {
    accessToken = token;
  }

  void setProjectId(String id) {
    projectId = id;
  }

  /// Whether the WebSocket is currently open.
  bool get isConnected => _connected;

  // ─── Connection ──────────────────────────────────────────────────────────────

  /// Opens the WebSocket connection. Completes once the connection is open,
  /// or throws if it could not be established. Safe to call when already
  /// connected (no-op) or while a connection attempt is already in flight
  /// (awaits the same attempt).
  Future<void> connect() async {
    _manualDisconnect = false;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;

    if (_connected) {
      return;
    }
    if (_connectingFuture != null) {
      return _connectingFuture;
    }

    final future = _doConnect();
    _connectingFuture = future;
    try {
      await future;
      _reconnectAttempts = 0;
    } finally {
      _connectingFuture = null;
    }
  }

  /// Closes the socket and clears any pending requests. Does not close
  /// existing `onChange` streams — call [unsubscribe] for those.
  void disconnect() {
    _manualDisconnect = true;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _reconnectAttempts = 0;

    _streamSubscription?.cancel();
    _streamSubscription = null;
    _channel?.sink.close();
    _channel = null;
    _connected = false;

    _failAllPending(
      RealtimeException(code: 'INTERNAL', message: 'Disconnected before a response was received'),
    );
  }

  // ─── Subscriptions ───────────────────────────────────────────────────────────

  /// Subscribes to a document or collection path, auto-connecting first if
  /// necessary. Resolves with the server-assigned `subscriptionId` once the
  /// server responds with a `subscribed` acknowledgement (or throws a
  /// [RealtimeException]/[TimeoutException] if it responds with an error or
  /// never responds within 10 seconds).
  Future<String> subscribe(String path, {Map<String, dynamic>? query}) async {
    if (!isConnected) {
      await connect();
    }

    final requestId = _nextRequestId();
    final responseFuture = _awaitResponse(requestId, _subscribeTimeout);

    _send({
      'type': 'subscribe',
      'requestId': requestId,
      'path': path,
      if (query != null) 'query': query,
    });

    final response = await responseFuture;
    final subscriptionId = response['subscriptionId'] as String;
    _changeControllers.putIfAbsent(
      subscriptionId,
      () => StreamController<Map<String, dynamic>>.broadcast(),
    );
    return subscriptionId;
  }

  /// A broadcast stream of `change` messages for [subscriptionId]. Each
  /// event is the raw decoded server message:
  /// `{"type": "change", "subscriptionId": ..., "event": "added"|"modified"|"removed",
  /// "data": {...}, "version": int, "docId": str}`.
  ///
  /// Safe to call before [subscribe] resolves; the underlying controller is
  /// created lazily and shared between both call sites. Cancel the returned
  /// stream's subscription (`.listen(...).cancel()`) to stop listening, or
  /// call [unsubscribe] to also tear down the subscription server-side.
  Stream<Map<String, dynamic>> onChange(String subscriptionId) {
    final controller = _changeControllers.putIfAbsent(
      subscriptionId,
      () => StreamController<Map<String, dynamic>>.broadcast(),
    );
    return controller.stream;
  }

  /// Sends an `unsubscribe` message (if connected) and closes the local
  /// `onChange` stream for [subscriptionId].
  ///
  /// Note: the server protocol defines no success acknowledgement for
  /// `unsubscribe` (only `subscribe` gets a `subscribed` ack) — an `error`
  /// may still arrive asynchronously (e.g. for an unknown subscriptionId),
  /// but since there's nothing actionable to do about it after the fact,
  /// this does not wait for one. The local stream is always torn down.
  Future<void> unsubscribe(String subscriptionId) async {
    if (isConnected) {
      _send({
        'type': 'unsubscribe',
        'requestId': _nextRequestId(),
        'subscriptionId': subscriptionId,
      });
    }

    final controller = _changeControllers.remove(subscriptionId);
    if (controller != null && !controller.isClosed) {
      await controller.close();
    }
  }

  /// Sends a `ping` to keep the connection alive. No-op if not connected.
  void ping() {
    if (isConnected) {
      _send({'type': 'ping'});
    }
  }

  // ─── Internals ───────────────────────────────────────────────────────────────

  Future<void> _doConnect() async {
    final uri = _buildUri();
    final channel = WebSocketChannel.connect(uri);
    await channel.ready;

    _channel = channel;
    _connected = true;
    _streamSubscription = channel.stream.listen(
      _handleRawMessage,
      onError: (Object _, StackTrace __) {
        // Errors on the stream are followed by onDone, which drives
        // reconnection; nothing else to do with the raw error here.
      },
      onDone: _handleSocketClosed,
      cancelOnError: false,
    );
  }

  void _handleSocketClosed() {
    _connected = false;
    _streamSubscription = null;
    _channel = null;

    _failAllPending(
      RealtimeException(code: 'INTERNAL', message: 'Connection closed before a response was received'),
    );

    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_manualDisconnect) return;
    if (_reconnectAttempts >= _maxReconnectAttempts) return;

    _reconnectAttempts++;
    final baseDelay = _reconnectBaseDelayMs * (1 << (_reconnectAttempts - 1));
    final jitter = baseDelay * 0.1 * (_random.nextDouble() - 0.5);
    final delayMs = (baseDelay + jitter).round();

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(milliseconds: delayMs), () async {
      try {
        await _doConnect();
        _reconnectAttempts = 0;
      } catch (_) {
        _scheduleReconnect();
      }
    });
  }

  Uri _buildUri() {
    final pid = projectId;
    if (pid == null) {
      throw Exception('projectId is required to open a realtime connection');
    }
    final wsBase = baseUrl.replaceFirst(RegExp(r'^http'), 'ws');
    final token = accessToken;
    final tokenQuery = token != null ? '?token=${Uri.encodeQueryComponent(token)}' : '';
    return Uri.parse('$wsBase/ws/v1/projects/$pid/listen/$tokenQuery');
  }

  void _send(Map<String, dynamic> message) {
    final channel = _channel;
    if (channel == null) {
      throw Exception('Realtime WebSocket is not connected');
    }
    channel.sink.add(jsonEncode(message));
  }

  String _nextRequestId() {
    _requestIdCounter += 1;
    return 'req_$_requestIdCounter';
  }

  Future<Map<String, dynamic>> _awaitResponse(String requestId, Duration timeout) {
    final completer = Completer<Map<String, dynamic>>();
    final timer = Timer(timeout, () {
      if (_pendingRequests.remove(requestId) != null && !completer.isCompleted) {
        completer.completeError(
          TimeoutException('Realtime request $requestId timed out after ${timeout.inSeconds}s'),
        );
      }
    });
    _pendingRequests[requestId] = _PendingRequest(completer, timer);
    return completer.future;
  }

  void _failAllPending(RealtimeException error) {
    for (final pending in _pendingRequests.values) {
      pending.timer.cancel();
      if (!pending.completer.isCompleted) {
        pending.completer.completeError(error);
      }
    }
    _pendingRequests.clear();
  }

  void _handleRawMessage(dynamic raw) {
    if (raw is! String) return;

    Map<String, dynamic> message;
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map<String, dynamic>) return;
      message = decoded;
    } catch (_) {
      return;
    }

    switch (message['type'] as String?) {
      case 'pong':
        break;
      case 'subscribed':
        _resolvePending(message['requestId'] as String?, message);
        break;
      case 'error':
        _rejectPending(
          message['requestId'] as String?,
          RealtimeException(
            code: message['code'] as String? ?? 'INTERNAL',
            message: message['message'] as String? ?? 'Unknown realtime error',
          ),
        );
        break;
      case 'change':
        _dispatchChange(message);
        break;
      default:
        break;
    }
  }

  void _resolvePending(String? requestId, Map<String, dynamic> message) {
    if (requestId == null) return;
    final pending = _pendingRequests.remove(requestId);
    if (pending == null) return;
    pending.timer.cancel();
    if (!pending.completer.isCompleted) {
      pending.completer.complete(message);
    }
  }

  void _rejectPending(String? requestId, RealtimeException error) {
    if (requestId == null) return;
    final pending = _pendingRequests.remove(requestId);
    if (pending == null) return;
    pending.timer.cancel();
    if (!pending.completer.isCompleted) {
      pending.completer.completeError(error);
    }
  }

  void _dispatchChange(Map<String, dynamic> message) {
    final subscriptionId = message['subscriptionId'] as String?;
    if (subscriptionId == null) return;
    final controller = _changeControllers[subscriptionId];
    if (controller == null || controller.isClosed) return;
    controller.add(message);
  }
}
