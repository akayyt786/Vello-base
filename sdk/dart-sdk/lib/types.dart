/// Types and data models for OwnFirebase SDK

class OwnFirebaseConfig {
  final String baseUrl;
  final String? projectId;
  final String? accessToken;

  OwnFirebaseConfig({
    required this.baseUrl,
    this.projectId,
    this.accessToken,
  });
}

class AuthTokens {
  final String access;
  final String refresh;
  final String userId;
  final String? email;

  AuthTokens({
    required this.access,
    required this.refresh,
    required this.userId,
    this.email,
  });

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      access: json['access'] as String,
      refresh: json['refresh'] as String,
      userId: json['user_id'] as String,
      email: json['email'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'access': access,
    'refresh': refresh,
    'user_id': userId,
    'email': email,
  };
}

class User {
  final String id;
  final String email;
  final String username;
  final String firstName;
  final String lastName;
  final bool isActive;

  User({
    required this.id,
    required this.email,
    required this.username,
    required this.firstName,
    required this.lastName,
    required this.isActive,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as String,
      email: json['email'] as String,
      username: json['username'] as String,
      firstName: json['first_name'] as String,
      lastName: json['last_name'] as String,
      isActive: json['is_active'] as bool,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'email': email,
    'username': username,
    'first_name': firstName,
    'last_name': lastName,
    'is_active': isActive,
  };
}

class DataDocument {
  final String id;
  final String collection;
  final Map<String, dynamic> data;
  final String createdAt;
  final String updatedAt;

  DataDocument({
    required this.id,
    required this.collection,
    required this.data,
    required this.createdAt,
    required this.updatedAt,
  });

  factory DataDocument.fromJson(Map<String, dynamic> json) {
    return DataDocument(
      id: json['id'] as String,
      collection: json['collection'] as String,
      data: (json['data'] ?? {}) as Map<String, dynamic>,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'collection': collection,
    'data': data,
    'created_at': createdAt,
    'updated_at': updatedAt,
  };
}

class DataCollection {
  final String id;
  final String name;
  final int documentCount;

  DataCollection({
    required this.id,
    required this.name,
    required this.documentCount,
  });

  factory DataCollection.fromJson(Map<String, dynamic> json) {
    return DataCollection(
      id: json['id'] as String,
      name: json['name'] as String,
      documentCount: json['document_count'] as int,
    );
  }
}

class AnalyticsEvent {
  final String id;
  final String name;
  final Map<String, dynamic> params;
  final String timestamp;
  final String? userId;
  final String? sessionId;

  AnalyticsEvent({
    required this.id,
    required this.name,
    required this.params,
    required this.timestamp,
    this.userId,
    this.sessionId,
  });

  factory AnalyticsEvent.fromJson(Map<String, dynamic> json) {
    return AnalyticsEvent(
      id: json['id'] as String,
      name: json['name'] as String,
      params: (json['params'] ?? {}) as Map<String, dynamic>,
      timestamp: json['timestamp'] as String,
      userId: json['user_id'] as String?,
      sessionId: json['session_id'] as String?,
    );
  }
}

class UserProperty {
  final String id;
  final String name;
  final String value;
  final String userId;

  UserProperty({
    required this.id,
    required this.name,
    required this.value,
    required this.userId,
  });

  factory UserProperty.fromJson(Map<String, dynamic> json) {
    return UserProperty(
      id: json['id'] as String,
      name: json['name'] as String,
      value: json['value'] as String,
      userId: json['user_id'] as String,
    );
  }
}

class PushDeviceToken {
  final String id;
  final String token;
  final String platform;
  final bool isActive;

  PushDeviceToken({
    required this.id,
    required this.token,
    required this.platform,
    required this.isActive,
  });

  factory PushDeviceToken.fromJson(Map<String, dynamic> json) {
    return PushDeviceToken(
      id: json['id'] as String,
      token: json['token'] as String,
      platform: json['platform'] as String,
      isActive: json['is_active'] as bool,
    );
  }
}

class RemoteConfigParameter {
  final String id;
  final String key;
  final String defaultValue;
  final String description;
  final String valueType;

  RemoteConfigParameter({
    required this.id,
    required this.key,
    required this.defaultValue,
    required this.description,
    required this.valueType,
  });

  factory RemoteConfigParameter.fromJson(Map<String, dynamic> json) {
    return RemoteConfigParameter(
      id: json['id'] as String,
      key: json['key'] as String,
      defaultValue: json['default_value'] as String,
      description: json['description'] as String,
      valueType: json['value_type'] as String,
    );
  }
}

class ExperimentAssignment {
  final String variantName;
  final Map<String, dynamic> config;
  final String experimentName;

  ExperimentAssignment({
    required this.variantName,
    required this.config,
    required this.experimentName,
  });

  factory ExperimentAssignment.fromJson(Map<String, dynamic> json) {
    return ExperimentAssignment(
      variantName: json['variant_name'] as String,
      config: (json['config'] ?? {}) as Map<String, dynamic>,
      experimentName: json['experiment_name'] as String,
    );
  }
}

class PaginatedResponse<T> {
  final int count;
  final String? next;
  final String? previous;
  final List<T> results;

  PaginatedResponse({
    required this.count,
    this.next,
    this.previous,
    required this.results,
  });
}

class APIError implements Exception {
  final int status;
  final String message;
  final dynamic detail;

  APIError({
    required this.status,
    required this.message,
    this.detail,
  });

  @override
  String toString() => 'APIError($status): $message${detail != null ? ' - $detail' : ''}';
}

class MFADevice {
  final String id;
  final String type;
  final String name;
  final bool confirmed;
  final String createdAt;

  MFADevice({
    required this.id,
    required this.type,
    required this.name,
    required this.confirmed,
    required this.createdAt,
  });

  factory MFADevice.fromJson(Map<String, dynamic> json) {
    return MFADevice(
      id: json['id'] as String,
      type: json['type'] as String,
      name: json['name'] as String,
      confirmed: json['confirmed'] as bool,
      createdAt: json['created_at'] as String,
    );
  }
}

class LinkedSocialAccount {
  final String id;
  final String provider;
  final String providerUid;
  final String? email;
  final String linkedAt;

  LinkedSocialAccount({
    required this.id,
    required this.provider,
    required this.providerUid,
    this.email,
    required this.linkedAt,
  });

  factory LinkedSocialAccount.fromJson(Map<String, dynamic> json) {
    return LinkedSocialAccount(
      id: json['id'] as String,
      provider: json['provider'] as String,
      providerUid: json['provider_uid'] as String,
      email: json['email'] as String?,
      linkedAt: json['linked_at'] as String,
    );
  }
}
