# OwnFirebase Dart SDK

A comprehensive Dart client library for OwnFirebase, a self-hosted Firebase alternative built on Django + PostgreSQL.

## Features

- **Authentication**: Registration, login, MFA, magic links, social auth, phone OTP
- **Data Management**: Firestore-like collections and documents with subcollection support
- **Analytics**: Event logging, user properties, conversion tracking, advanced queries
- **Push Notifications**: Device token registration, topic-based messaging, batch campaigns
- **Remote Config**: Feature flags, A/B test configurations, conditional parameters
- **A/B Testing**: Experiment assignment, conversion tracking, results analysis
- **Realtime**: Document subscriptions, presence tracking, broadcast messaging

## Installation

Add to your `pubspec.yaml`:

```yaml
dependencies:
  ownfirebase_sdk: ^1.0.0
```

Then run:

```bash
dart pub get
```

## Quick Start

```dart
import 'package:ownfirebase_sdk/ownfirebase_sdk.dart';

void main() async {
  // Initialize SDK
  final app = initOwnFirebase(
    OwnFirebaseConfig(
      baseUrl: 'http://localhost:8000',
      projectId: 'my-project',
    ),
  );

  // Authenticate
  final tokens = await app.auth.login('user@example.com', 'password');
  app.setAccessToken(tokens.access);

  // Create document
  final doc = await app.data.createDocument('users', {
    'name': 'Alice',
    'age': 30,
  });

  // Log analytics event
  await app.analytics.logEvent('user_signup', params: {
    'method': 'email',
  });

  // Get experiment assignment
  final assignment = await app.ab.getAssignment('exp-123', 'user-456');
  print('Variant: ${assignment.variantName}');
}
```

## API Overview

### Authentication

```dart
// Basic auth
final tokens = await app.auth.login(email, password);
app.setAccessToken(tokens.access);

// Social auth
final googleTokens = await app.auth.googleSignIn(idToken);
final githubTokens = await app.auth.githubSignIn(accessToken);

// Passwordless
await app.auth.sendMagicLink(email);
final tokens = await app.auth.verifyMagicLink(token);

// MFA
final mfaEnroll = await app.auth.enrollTOTP();
await app.auth.confirmTOTP(code);
final verifiedTokens = await app.auth.verifyTOTP(code);
```

### Data (Firestore-like)

```dart
// Collections
final collections = await app.data.listCollections();
final col = await app.data.createCollection('users');

// Documents
final doc = await app.data.createDocument('users', {'name': 'Alice'});
final retrieved = await app.data.getDocument('users', docId);
final updated = await app.data.updateDocument('users', docId, {'age': 31});
await app.data.deleteDocument('users', docId);

// Subcollections
final posts = await app.data.listDocuments('users/user-123/posts');

// Batch operations
await app.data.writeBatch([
  {'op': 'set', 'collection': 'users', 'doc_id': 'u1', 'data': {...}},
  {'op': 'delete', 'collection': 'users', 'doc_id': 'u2'},
]);
```

### Analytics

```dart
// Log events
await app.analytics.logEvent('page_view', params: {
  'page': '/home',
}, userId: 'user-123', sessionId: 'session-456');

// User properties
await app.analytics.setUserProperty('subscription_tier', 'premium');

// Conversion events
await app.analytics.markConversionEvent('purchase');

// Query data
final result = await app.analytics.query({
  'metric': 'event_count',
  'dimension': 'event_name',
  'start_date': '2024-01-01',
  'end_date': '2024-01-31',
});
```

### Push Notifications

```dart
// Register device
final token = await app.push.registerToken('device-token', 'ios');

// Send to device
await app.push.sendToDevice(tokenId, {
  'title': 'Hello',
  'body': 'Welcome',
});

// Send to topic
await app.push.sendToTopic('news', {
  'title': 'Breaking News',
  'body': 'Important update',
});

// Topic management
await app.push.subscribeToTopic(tokenId, 'news');
await app.push.unsubscribeFromTopic(tokenId, 'news');
```

### Remote Config

```dart
// List parameters
final params = await app.remoteConfig.listParameters();

// Get specific parameter
final param = await app.remoteConfig.getParameter('feature_new_ui');

// Create/update parameters
await app.remoteConfig.createParameter(
  key: 'max_retry_count',
  defaultValue: '3',
  description: 'Maximum retry count',
  valueType: 'number',
);

// Fetch current config
final config = await app.remoteConfig.fetch();
```

### A/B Testing

```dart
// List experiments
final experiments = await app.ab.listExperiments();

// Get variant assignment
final assignment = await app.ab.getAssignment('exp-123', userId);
print(assignment.variantName); // e.g. "variant_b"
print(assignment.config); // variant-specific config

// Record conversion
await app.ab.recordConversion('exp-123', userId, metadata: {
  'amount': 99.99,
});

// Get results
final results = await app.ab.getResults('exp-123');
```

## Testing

### Running Tests

```bash
# Run all tests
dart test

# Run specific test file
dart test test/unit/auth_test.dart

# Run integration tests only
dart test test/integration/

# Run with verbose output
dart test --verbose

# Run tests matching pattern
dart test --name "auth"
```

### Test Categories

#### Unit Tests (41 tests)
- **auth_test.dart** (15 tests): Auth module initialization, token handling, MFA, social auth
- **data_test.dart** (12 tests): Document parsing, collections, batch operations, nested structures
- **analytics_test.dart** (11 tests): Event parsing, user properties, query structures, batch events
- **push_test.dart** (11 tests): Device tokens, notifications, topics, payloads
- **remoteconfig_test.dart** (10 tests): Parameters, conditions, fetch operations
- **abtesting_test.dart** (11 tests): Variant allocation, assignment, results analysis

Total Unit Tests: **70 tests**

#### Integration Tests (25+ tests per service)
- **auth_integration_test.dart** (15 tests): Full auth flow, endpoints
- **data_integration_test.dart** (12 tests): CRUD operations, batch writes
- **analytics_integration_test.dart** (10 tests): Event logging, batching, queries
- **realtime_integration_test.dart** (12 tests): Subscriptions, presence, broadcasting
- **push_integration_test.dart** (12 tests): Token management, notifications
- **remoteconfig_integration_test.dart** (10 tests): Configuration management
- **abtesting_integration_test.dart** (12 tests): Experiments, assignments

Total Integration Tests: **83 tests**

**Grand Total: 153+ Tests**

### Test Coverage

- **Auth Flow**: Login, registration, token refresh, MFA, social auth, magic links
- **Data CRUD**: Create, read, update, delete, list, batch operations
- **Analytics Batch**: Event logging (1000+ events), user properties, conversions
- **Realtime Subscriptions**: Document changes, presence, multi-collection subscriptions
- **Push Notifications**: Device registration, topic subscriptions, rich notifications
- **Remote Config**: Parameter management, conditional overrides, caching
- **A/B Testing**: Experiment creation, assignment, conversion tracking, results

## Error Handling

```dart
import 'package:ownfirebase_sdk/ownfirebase_sdk.dart';

try {
  await app.data.getDocument('users', 'non-existent');
} catch (err) {
  if (err is APIError) {
    print('Error ${err.status}: ${err.message}');
    print('Details: ${err.detail}');
  }
}
```

## Integration with Backend

Ensure your OwnFirebase backend is running at the configured `baseUrl`:

```bash
# For local development
python manage.py runserver 0.0.0.0:8000

# For production
gunicorn ownfirebase.wsgi
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Ensure all tests pass
4. Submit a pull request

## License

MIT
