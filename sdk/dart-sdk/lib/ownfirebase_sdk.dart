/// OwnFirebase Dart SDK
///
/// A comprehensive Dart client library for OwnFirebase, a self-hosted Firebase
/// alternative built on Django + PostgreSQL.

export 'types.dart';
export 'client.dart';
export 'auth.dart';
export 'data.dart';
export 'analytics.dart';
export 'push.dart';
export 'remoteconfig.dart';
export 'abtesting.dart';
export 'storage.dart';
export 'crashlytics.dart';
export 'realtime.dart';

import 'types.dart';
import 'auth.dart';
import 'data.dart';
import 'analytics.dart';
import 'push.dart';
import 'remoteconfig.dart';
import 'abtesting.dart';
import 'storage.dart';
import 'crashlytics.dart';
import 'realtime.dart';

/// Main OwnFirebase SDK bundle
class OwnFirebase {
  final AuthSDK auth;
  final DataSDK data;
  final AnalyticsSDK analytics;
  final PushSDK push;
  final RemoteConfigSDK remoteConfig;
  final ABTestingSDK ab;
  final StorageSDK storage;
  final CrashlyticsSDK crashlytics;
  final RealtimeSDK realtime;

  OwnFirebase({required OwnFirebaseConfig config})
      : auth = AuthSDK(config: config),
        data = DataSDK(config: config),
        analytics = AnalyticsSDK(config: config),
        push = PushSDK(config: config),
        remoteConfig = RemoteConfigSDK(config: config),
        ab = ABTestingSDK(config: config),
        storage = StorageSDK(config: config),
        crashlytics = CrashlyticsSDK(config: config),
        realtime = RealtimeSDK(config: config);

  /// Set the access token for all services
  void setAccessToken(String token) {
    auth.setAccessToken(token);
    data.setAccessToken(token);
    analytics.setAccessToken(token);
    push.setAccessToken(token);
    remoteConfig.setAccessToken(token);
    ab.setAccessToken(token);
    storage.setAccessToken(token);
    crashlytics.setAccessToken(token);
    realtime.setAccessToken(token);
  }

  /// Set the project ID for all services
  void setProjectId(String id) {
    auth.setProjectId(id);
    data.setProjectId(id);
    analytics.setProjectId(id);
    push.setProjectId(id);
    remoteConfig.setProjectId(id);
    ab.setProjectId(id);
    storage.setProjectId(id);
    crashlytics.setProjectId(id);
    realtime.setProjectId(id);
  }
}

/// Factory function to initialize the SDK
OwnFirebase initOwnFirebase(OwnFirebaseConfig config) {
  return OwnFirebase(config: config);
}
