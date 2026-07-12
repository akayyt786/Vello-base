# Changelog

All notable changes to the OwnFirebase Swift SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-11

### Added

#### Core Features
- Initial release of OwnFirebase Swift SDK
- Full async/await support for all API operations
- Automatic retry logic with exponential backoff
- Comprehensive error handling with localized messages

#### Authentication Service
- Email/password registration and login
- Anonymous authentication
- Social authentication (Google, GitHub)
- Magic link authentication
- Phone OTP authentication
- Multi-factor authentication (TOTP, SMS)
- Account linking and unlinking
- Password management
- Custom token generation
- Account upgrade (anonymous to verified)

#### Data Service
- CRUD operations (Create, Read, Update, Delete)
- Collection management
- Document listing with filters
- Batch write operations (transactions)
- Security rules management
- Rule testing

#### Storage Service
- File upload with presigned URLs
- Direct uploads to S3/MinIO
- File download
- File listing with prefix support
- File metadata retrieval
- File deletion
- High-level upload helper

#### Analytics Service
- Event logging with parameters
- Batch event logging for efficiency
- Event listing
- User properties management
- Conversion event tracking
- Analytics data querying
- Flexible analytics parameters

#### Remote Configuration Service
- Parameter management (CRUD)
- Built-in caching with configurable TTL
- Condition-based configuration
- Cache invalidation
- List parameters with cache support

#### Crashlytics Service
- Crash report submission
- Batch crash reporting
- Crash group listing and details
- Crash summary statistics
- Performance trace recording
- Network request monitoring
- Crash-free user metrics

#### Realtime Service
- WebSocket-based real-time updates
- Collection subscription
- Filtered subscriptions
- Automatic reconnection with exponential backoff
- Message type handling (create, update, delete)
- Thread-safe message delivery

#### Configuration & Utilities
- Configurable SDK initialization
- Flexible retry configuration
- URL normalization
- Type-safe configuration

#### Type System
- AnyCodable for flexible JSON handling
- Comprehensive type definitions
- Thread-safe type encoding/decoding
- ISO8601 date handling

### Implementation Details

#### Architecture
- Service-based architecture with inheritance from OwnFirebaseClient
- Separation of concerns (auth, data, storage, analytics, etc.)
- Singleton-pattern services for consistent state management

#### Error Handling
- Custom OwnFirebaseError enum with detailed cases
- Automatic error response parsing
- Network error classification
- Localized error messages

#### Retry Logic
- Configurable maximum attempts (default: 3)
- Exponential backoff algorithm
- Customizable retry status codes
- Automatic retry on network failures

#### Threading & Concurrency
- Full Swift async/await support
- Thread-safe batch operations (Analytics, Crashlytics)
- Isolated queue-based state management
- URLSession for network operations

#### Caching
- RemoteConfig parameter caching
- Configurable cache TTL
- Cache invalidation support
- Memory-efficient cache management

#### Batching
- Event batch accumulation (Analytics)
- Crash report batching (Crashlytics)
- Configurable batch sizes
- Automatic flush on batch size exceeded
- Timed flush for small batches

### Supported Platforms
- iOS 14.0+
- macOS 11.0+
- tvOS 14.0+
- watchOS 7.0+

### Dependencies
- None (uses only Foundation framework)

### Testing
- Comprehensive unit tests
- Type decoding/encoding tests
- Configuration tests
- Retry configuration tests

### Documentation
- Comprehensive README with setup instructions
- Quick start guide
- Complete API reference
- 8 detailed usage examples
- Error handling guide
- Thread safety documentation

## Future Releases

### Planned for v1.1.0
- FCM (Firebase Cloud Messaging) integration
- Advanced analytics dashboard
- Offline support with local caching
- Request/response interceptors

### Planned for v1.2.0
- A/B testing service
- Feature flags service
- Advanced search capabilities
- GraphQL support

### Planned for v2.0.0
- Reactive extensions (Combine/AsyncStream)
- SwiftUI view modifiers
- Advanced security features
- Performance improvements

## Migration Guide

### Coming from Other SDKs

#### Firebase SDK
- Similar API structure but more tailored to OwnFirebase
- Async/await instead of completion handlers
- Built-in batching for analytics
- Unified error handling

#### REST API
- Type-safe API with compile-time checks
- Automatic serialization/deserialization
- Built-in retry logic
- Session management
