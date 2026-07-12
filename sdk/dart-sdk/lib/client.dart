import 'package:http/http.dart' as http;
import 'dart:convert';
import 'types.dart';

/// Base HTTP client for all OwnFirebase SDK services
class OwnFirebaseClient {
  final String baseUrl;
  String? projectId;
  String? accessToken;

  OwnFirebaseClient({
    required OwnFirebaseConfig config,
  })  : baseUrl = config.baseUrl.replaceAll(RegExp(r'/$'), ''),
        projectId = config.projectId,
        accessToken = config.accessToken;

  void setAccessToken(String token) {
    accessToken = token;
  }

  void setProjectId(String id) {
    projectId = id;
  }

  String projectUrl(String path) {
    if (projectId == null) {
      throw Exception('projectId is required for this operation');
    }
    return '$baseUrl/api/projects/$projectId/$path';
  }

  Future<T> request<T>(
    String method,
    String url,
    dynamic body, {
    bool noAuth = false,
    Map<String, String>? query,
    required T Function(dynamic) fromJson,
  }) async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };

    if (!noAuth && accessToken != null) {
      headers['Authorization'] = 'Bearer $accessToken';
    }

    var fullUrl = Uri.parse(url);
    if (query != null && query.isNotEmpty) {
      fullUrl = fullUrl.replace(queryParameters: query);
    }

    late http.Response response;

    try {
      final bodyStr = body != null ? jsonEncode(body) : null;

      switch (method.toUpperCase()) {
        case 'GET':
          response = await http.get(fullUrl, headers: headers);
        case 'POST':
          response = await http.post(fullUrl, headers: headers, body: bodyStr);
        case 'PUT':
          response = await http.put(fullUrl, headers: headers, body: bodyStr);
        case 'PATCH':
          response = await http.patch(fullUrl, headers: headers, body: bodyStr);
        case 'DELETE':
          response = await http.delete(fullUrl, headers: headers, body: bodyStr);
        default:
          throw Exception('Unsupported HTTP method: $method');
      }

      if (!response.statusCode.toString().startsWith('2')) {
        dynamic detail;
        try {
          detail = jsonDecode(response.body);
        } catch (_) {
          detail = response.body;
        }
        throw APIError(
          status: response.statusCode,
          message: response.reasonPhrase ?? 'Unknown error',
          detail: detail,
        );
      }

      if (response.statusCode == 204) {
        return null as T;
      }

      final jsonBody = jsonDecode(response.body);
      return fromJson(jsonBody);
    } catch (e) {
      if (e is APIError) rethrow;
      rethrow;
    }
  }
}
