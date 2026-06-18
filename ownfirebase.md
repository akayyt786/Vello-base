# 🔥 Own Firebase — Build Your Own Firebase on Django

> A complete, self-hosted, open-source Backend-as-a-Service (BaaS) that replicates **every** Google Firebase feature using **Django, PostgreSQL, Redis, Celery, Channels and friends** — so you can build *any* backend, own your data, and never get a surprise five-figure bill.

## Executive Summary

Firebase is not one product — it is ~25 tightly-integrated managed services sitting on top of Google Cloud Platform, fronted by polished client SDKs and a security-rules layer. It removes the need to write a backend by giving you: identity, two NoSQL databases, a SQL database, object storage, serverless functions, hosting/CDN, push messaging, analytics, crash reporting, remote config, A/B testing, on-device + generative AI, and a deep local-emulator + CLI developer experience.

This document is the result of a **14-agent parallel research sweep** across the official Firebase/GCP docs, YouTube, Reddit, Hacker News, engineering blogs, and the open-source clones (Supabase, Appwrite, PocketBase, Parse, Nhost, Convex, Hasura). For **every** Firebase capability it records three things: *(1)* what it does, *(2)* how Firebase implements it under the hood, and *(3)* exactly how to rebuild it yourself on Django — with real package names, data models, and architecture.

## Why Rebuild Firebase on Django?

- **No vendor lock-in & data ownership.** Firestore's data and security model don't port anywhere; a Django/Postgres core is portable forever.
- **Cost control.** Firebase's per-operation billing (esp. Firestore reads from realtime listeners and AI workloads) produces the community's infamous "$50 → $70k overnight" bills. A self-hosted box has flat, predictable cost.
- **Relational power.** Real SQL, joins, transactions, and migrations from day one (Firebase only added this recently with Data Connect).
- **Extensibility.** Django's ecosystem (DRF, Channels, Celery, admin) lets you customise anything Firebase keeps closed.

## Core Philosophy

1. **Postgres is the single source of truth** — documents (JSONB), relations, vectors (pgvector) and auth all live in one ACID database.
2. **Auto-generate the boring parts** — CRUD APIs, client SDKs, and an admin console are generated, mirroring Firebase's "no backend code" DX.
3. **Realtime is a first-class service, not an afterthought** — Django Channels + Redis + Postgres change-capture replaces Firestore/RTDB live listeners.
4. **Everything ships in `docker-compose`** — the whole stack runs locally exactly like the Firebase Emulator Suite.

## Table of Contents

1. [Firebase → Django Master Mapping](#firebase--django-master-mapping)
2. [Target Architecture](#target-architecture)
3. [Recommended Tech Stack](#recommended-tech-stack)
4. [Part II — Feature-by-Feature Deep Dive](#part-ii--feature-by-feature-deep-dive)
    1. Authentication, App Check & Identity
    2. Cloud Firestore (NoSQL Document DB)
    3. Realtime Database
    4. Firebase Data Connect / SQL Connect (PostgreSQL + GraphQL)
    5. Cloud Storage for Firebase
    6. Cloud Functions & Server-Side Compute (incl. App Hosting)
    7. Firebase Hosting & CDN
    8. Realtime Sync Engine for the Django Clone
    9. Cloud Messaging (Push) & In-App Messaging
    10. Analytics, Crashlytics & Performance Monitoring
    11. Remote Config, A/B Testing, Dynamic Links & Predictions
    12. AI: Genkit, Vertex AI in Firebase (AI Logic) & ML Kit
    13. Tooling: CLI, Admin SDK, Emulator Suite, Security Rules, Test Lab, App Distribution & Firebase Studio
    14. Community Wisdom & Open-Source Firebase Alternatives
5. [Build Roadmap](#build-roadmap)


## Firebase → Django Master Mapping

Every Firebase feature mapped to its self-hosted Django equivalent (auto-generated from all 14 research clusters).

| # | Firebase Service | How Firebase Does It | Django Equivalent | Key Libraries |
|---|---|---|---|---|
| 1 | Email/Password Authentication | identitytoolkit.googleapis.com REST API. Bcrypt-hashed passwords stored in Google's CIAM backend. Returns RS256-signed JWT ID token (1h TTL) + opaque refresh token (long-lived). Signing keys rotated daily at securetoken.googleapis.com. | django.contrib.auth + djangorestframework-simplejwt. AbstractUser model. /api/token/ endpoint issues access+refresh JWT pair. RS256 keys configured via SIGNING_KEY/VERIFYING_KEY settings. | djangorestframework-simplejwt, dj-rest-auth, django-allauth |
| 2 | Phone OTP (SMS) Authentication | Client sends phone number; Firebase backend dispatches SMS via Google's SMS aggregator. Client submits OTP code; backend verifies and issues JWT. Phone numbers are sent/stored by Google for spam prevention. reCAPTCHA used to prevent abuse. | Generate TOTP/HOTP code server-side (pyotp), store hashed code+expiry in Redis or DB, send via Twilio/AWS SNS (django-phonenumber-field for normalisation). On verify, issue JWT pair. | pyotp, django-phonenumber-field, twilio, django-ratelimit |
| 3 | Anonymous Authentication | Issues a standard JWT with sign_in_provider=anonymous and a real UID. Data attached to UID persists until account is deleted/signed-out. linkWithCredential() upgrades anonymous to permanent; previous UID is preserved. | On first request without credentials, auto-create an AnonymousUser row with a UUID, issue a short-TTL JWT. Provide /auth/upgrade/ endpoint that links provider credentials to that UUID row, transferring ownership of related data. | djangorestframework-simplejwt, django-uuid (standard) |
| 4 | Custom Tokens | Admin SDK generates a JWT signed with the Firebase service-account private key (RS256). Client exchanges it via signInWithCustomToken() at identitytoolkit — Firebase verifies the SA signature, then issues its own short-lived ID token + refresh token. | Server signs a short-lived JWT (e.g. 5-min TTL) with the app's RS256 private key; expose /auth/custom-token/verify/ that validates the sig and issues a full djangorestframework-simplejwt pair. | PyJWT, djangorestframework-simplejwt |
| 5 | Google / Apple / Facebook / GitHub / Microsoft Social Sign-In | Firebase SDK handles OAuth2 redirect/popup, receives provider tokens, and POSTs to identitytoolkit:signInWithIdp. Firebase verifies the provider ID token, creates/links the Firebase user, and issues its JWT. | django-allauth (headless mode, v65+) or dj-rest-auth[with_social] handles OAuth2 callback; stores SocialAccount linked to User; issues djangorestframework-simplejwt tokens post-callback. | django-allauth[mfa,socialaccount], dj-rest-auth, python-social-auth (alternative) |
| 6 | OIDC / Generic OAuth2 Providers | Identity Platform (paid upgrade to Firebase Auth) allows registering arbitrary OIDC providers. Firebase acts as an RP; it validates the id_token from the IdP, then issues its own JWT. Configured via Firebase console or Admin SDK. | mozilla-django-oidc or django-allauth OIDC provider. Register provider client_id/secret/discovery-URL in DB or settings; allauth handles discovery, code exchange, id_token validation. | mozilla-django-oidc, django-allauth |
| 7 | SAML 2.0 Enterprise SSO | Identity Platform (paid). Firebase registers as SAML SP; ACS URL is https://PROJECT-ID.firebaseapp.com/__/auth/handler. Receives SAMLResponse, validates signature, maps attributes to Firebase user, issues JWT. | djangosaml2 (backed by pysaml2) or django-saml2-auth. Register SP metadata; handle ACS endpoint; map SAML attributes to Django User fields; issue JWT on successful assertion. | djangosaml2, pysaml2, django-saml2-auth (Grafana fork) |
| 8 | Multi-Factor Authentication (SMS + TOTP) | Identity Platform feature. After primary sign-in, if MFA enrolled, Firebase issues a pendingCredential token and requires a second factor (phone OTP or TOTP via Google Authenticator). TOTP uses RFC 6238; secret stored server-side. | django-otp (pluggable framework) + django-otp-twilio for SMS. TOTPDevice model stores base32 secret. After primary JWT issue, set mfa_required=true; client must POST TOTP code to /auth/mfa/verify/; then issue full JWT. | django-otp, django-two-factor-auth, pyotp, django-otp-twilio |
| 9 | Passwordless / Email Link Sign-In | sendSignInLinkToEmail() calls identitytoolkit:sendOobCode which generates a time-limited OOB code, embeds it as a query param in a deep-link URL (Firebase Dynamic Link), and sends via email. Client calls signInWithEmailLink(); Firebase verifies the OOB code and issues JWT. | Generate a cryptographically signed token (using Django's TimestampSigner), email a link to /auth/email-link/verify/?token=X. On GET, verify signature+expiry, create/login user, issue JWT pair. django-allauth headless supports this natively as of v65. | django-allauth (headless), djangorestframework-simplejwt, django.core.signing |
| 10 | JWT ID Token — Structure & Verification | RS256 JWT. Header: {alg:RS256, kid:<key-id>}. Payload: iss=https://securetoken.google.com/<proj>, aud=<proj>, sub=uid, user_id=uid, exp=now+3600, firebase:{sign_in_provider, identities, ...}. Public keys at googleapis.com/robot/v1/metadata/x509/securetoken; rotated daily (Cache-Control header signals refresh time). Admin SDK verifies sig, exp, iss, aud, then checks revocation via user metadata if requested. | djangorestframework-simplejwt with RS256 (ALGORITHM='RS256', SIGNING_KEY=private_pem, VERIFYING_KEY=public_pem). Add custom claims (sub, firebase-equivalent namespace) via a custom TokenObtainPairSerializer. Stateless verification — no DB hit on every request. | djangorestframework-simplejwt, PyJWT |
| 11 | Refresh Tokens | Opaque long-lived token (not a JWT) stored client-side. Client POSTs to securetoken.googleapis.com/v1/token to get a new ID token. Firebase invalidates refresh tokens on: password change, email change, account disable, explicit revoke via Admin SDK, or 270-day inactivity. | djangorestframework-simplejwt rotating refresh tokens (ROTATE_REFRESH_TOKENS=True, BLACKLIST_AFTER_ROTATION=True). Use the blacklist app + Redis/DB-backed token blacklist. Revocation: delete from outstanding tokens or add to blacklist. | djangorestframework-simplejwt[blacklist], django-redis |
| 12 | Session Cookies (Server-Side Web Apps) | Admin SDK createSessionCookie(idToken, {expiresIn}) generates a long-lived Firebase-signed JWT cookie (5min-2weeks). Backend verifies with verifySessionCookie(). Has same custom claims as ID token. Revocable like refresh tokens. | Issue a server-set HttpOnly Secure cookie containing the djangorestframework-simplejwt access token (or a separate session JWT). Use JWTAuthentication in a custom class that reads from cookie. For SSR, couple with Django's session framework or a Redis-backed cookie store. | djangorestframework-simplejwt, django.middleware.csrf, django-cors-headers |
| 13 | Custom Claims / RBAC | Admin SDK setCustomUserClaims(uid, {admin:true, role:'editor'}). Claims written to Firebase's user record; appear in ID token on NEXT token refresh (up to 1h delay). Max 1000 bytes. Enforced in Firestore/RTDB Security Rules via request.auth.token.admin. | Store roles/permissions in Django's built-in auth Groups+Permissions or a custom Profile model. Serialize them into JWT payload via custom TokenObtainPairSerializer. Enforce in DRF via permission classes (IsAdminUser, custom HasRole). Immediate — no propagation delay. | djangorestframework-simplejwt, django.contrib.auth, django-guardian (object-level perms) |
| 14 | User Management (CRUD, List, Import, Export) | Admin SDK: createUser(), getUser(uid), updateUser(), deleteUser(), listUsers(maxResults, pageToken), importUsers() (bulk with hashed passwords). No built-in user search index — must maintain external index. Users stored in Google's CIAM backend, not directly queryable. | Django ORM on PostgreSQL. Full SQL search, indexing, batch ops. Django Admin provides UI. DRF viewsets expose CRUD. django-import-export for bulk CSV import/export. No 1000-byte claims limit. | djangorestframework, django-filter, django-import-export |
| 15 | Token Revocation & Session Invalidation | Admin SDK revokeRefreshTokens(uid) updates tokensValidAfterTime on the user record. During ID token verification, if checkRevoked=true, Admin SDK fetches user metadata and compares token iat against tokensValidAfterTime. Extra network round-trip per request. | djangorestframework-simplejwt blacklist app. On forced logout, call OutstandingToken.objects.filter(user=user).delete() or add to BlacklistedToken. JWTAuthentication checks blacklist on each request (Redis cache recommended for performance). | djangorestframework-simplejwt[blacklist], django-redis |
| 16 | Firebase App Check — Play Integrity (Android) | Client calls Play Integrity API → Google Play returns a signed attestation blob. Client sends blob to Firebase App Check service. Firebase validates the blob with Google Play servers, issues a short-lived App Check JWT (RS256, 30min-7days TTL, configurable). Backend verifies App Check JWT against JWKS at firebaseappcheck.googleapis.com/v1/jwks. | No direct native analog. Approximation: combine certificate pinning + server-side API key rotation + django-ratelimit per client fingerprint. For serious abuse prevention, integrate Google reCAPTCHA Enterprise (server-side verify) as middleware that gates token issuance. | django-ratelimit, django-recaptcha, google-cloud-recaptcha-enterprise |
| 17 | Firebase App Check — DeviceCheck / App Attest (iOS) | On iOS, App Attest (iOS 14+) generates a cryptographic assertion tied to the app's team ID + bundle ID and the device's Secure Enclave. Firebase validates with Apple servers. DeviceCheck (legacy) is similar but weaker. Firebase then issues an App Check JWT. | No direct server-side equivalent in Django without mobile SDK cooperation. Best approach: implement a custom attestation micro-service that verifies Apple's App Attest assertions, then issues a short-lived signed token that your Django middleware validates. | PyJWT, cryptography (for assertion verification), httpx (to call Apple attestation service) |
| 18 | Firebase App Check — reCAPTCHA Enterprise (Web) | Browser loads reCAPTCHA Enterprise script; on action, gets a reCAPTCHA token. Firebase App Check service validates with Google reCAPTCHA API and issues App Check JWT. Protects web endpoints similarly to mobile attestation. | django-recaptcha (wraps reCAPTCHA v3/Enterprise). Add RecaptchaField to sensitive forms/endpoints. For pure API, accept X-Recaptcha-Token header, verify server-side in DRF middleware, reject low-score requests. | django-recaptcha, google-cloud-recaptcha-enterprise |
| 19 | App Check Token Verification on Custom Backend | App sends X-Firebase-AppCheck header with App Check JWT. Backend fetches JWKS from firebaseappcheck.googleapis.com/v1beta/jwks, verifies RS256 signature, checks iss (https://firebaseappcheck.googleapis.com/), aud (projects/<project-number>), exp. Firebase Admin SDK can automate this. | Write a DRF middleware/authentication class that reads X-Firebase-AppCheck (or your own analog header), fetches and caches your attestation service's JWKS, and verifies the JWT. Cache JWKS in Redis with TTL matching Cache-Control. | PyJWT, cryptography, django-redis, djangorestframework |
| 20 | Firebase Installations (FID) | Firebase SDK auto-generates a 22-char base64 Installation ID (FID) per app instance on first run. Registered with Firebase Installations API. Used internally by FCM, Crashlytics, Performance, Remote Config to correlate events to a device instance. Resettable; expires after 270-day inactivity. | Generate a UUID on first app launch, store in device local storage (SharedPreferences/Keychain/localStorage). Send as X-Device-ID header or include in JWT custom claim. Store in a DeviceInstallation model linked (optionally) to User for push targeting. | djangorestframework, django-push-notifications (for FCM integration) |
| 21 | Identity Platform — Multi-Tenancy | Identity Platform (paid upgrade) creates Tenant entities within a project. Each Tenant has isolated user pools, separate IdP configurations, and separate MFA policies. tenantId is embedded in user records and JWTs. SDK routes requests per-tenant. | django-tenant-schemas or django-tenants (schema-per-tenant PostgreSQL). Each tenant schema contains its own auth_user, social accounts, and token tables. Tenant resolved from subdomain or JWT claim. Alternatively, logical multi-tenancy via tenant_id FK on all user/session models. | django-tenants, django-tenant-schemas, djangorestframework |
| 22 | Documents & Collections | Schema-less JSON documents (max 1 MiB, max 20,000 fields) stored one-per-row in a Spanner `Entities` table. Collections are logical groupings derived from the document path; they have no physical representation. Paths alternate collection/document segments (e.g. `users/{uid}/posts/{pid}`). Supported field types: string, number, boolean, null, timestamp, geopoint, bytes, reference, array, map. | PostgreSQL table with `id` (UUID PK), `collection_path` (text), `document_id` (text), `data` (JSONB), `created_at`, `updated_at`. One universal `Document` model or per-collection models with a JSONB `extra` overflow field. | django (built-in JSONField on Postgres), psycopg2 / psycopg3, djangorestframework |
| 23 | Subcollections | Subcollections are collections nested under a document path (depth up to 100). They are stored in the same `Entities` and `IndexEntries` Spanner tables — the full document path is the key. Parent documents do not store subcollection data; subcollection documents are independent rows. A subcollection's existence does not affect parent document size. | The same `Document` model handles subcollections by encoding depth in `collection_path` (e.g. `users/uid123/posts`). A `ltree` or simple text prefix query retrieves all documents under a path. For strong parent-child FK integrity, add an optional `parent_document_id` FK. | django-ltree (pip install django-ltree) for hierarchical path queries; or raw LIKE/prefix queries on collection_path with a btree index |
| 24 | Query model (where / orderBy / limit / startAfter / endBefore) | All queries run exclusively against the `IndexEntries` table — Firestore never scans the `Entities` table. Query cost is O(result set size), not O(collection size). Supported operators: `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `not-in`, `array-contains`, `array-contains-any`. Cursors (`startAfter`, `endBefore`) use document snapshots or field values as positional anchors. Queries within a single collection or across a collection group. | DRF ViewSet with django-filter for `where` clauses against JSONB fields using `__contains`, `__has_key`, KT-expressions (`data__fieldname`). `orderBy` maps to `.order_by('data__field')`. `limit`/`offset` for pagination, or keyset pagination with `django-cursor-pagination`. GIN indexes on JSONB plus partial B-tree indexes on extracted fields. | djangorestframework, django-filter, django-cursor-pagination (pip install django-cursor-pagination) |
| 25 | Composite Indexes | Firestore requires an explicit composite index for any query that filters or sorts on more than one field (except equality-only multi-field `where` chains which can use single-field indexes). Each composite index stores merged (field_value, document_path) tuples in `IndexEntries`, ordered by the composite key, enabling range scans that satisfy the full query in one pass. Up to 500 composite indexes per database (billing-enabled). | Django `Meta.indexes` with `Index(fields=['data__status', 'data__created_at'])` using expression indexes on JSONB paths: `CREATE INDEX ON documents ((data->>'status'), (data->>'created_at'));`. For collection-scoped indexes, add `collection_path` as the first column. Django migrations manage these. | Built-in Django migrations + PostgreSQL expression indexes; django-pgindexes for advanced cases |
| 26 | Collection Group Queries | Queries across ALL collections with the same name regardless of their position in the hierarchy. Requires a collection-group-scoped composite index (as opposed to the default collection-scoped index). SDK: `db.collectionGroup('posts').where('published', '==', true).get()`. Security rules must use wildcard paths to permit collection group access. | Since `collection_path` encodes the full path, a collection group query becomes `Document.objects.filter(collection_path__endswith='/posts', data__published=True)`. Add a partial index on the terminal path segment for performance: `CREATE INDEX ON documents ((split_part(collection_path, '/', -1)))` where the field equals 'posts'. | PostgreSQL expression indexes, built-in Django ORM |
| 27 | Realtime Snapshot Listeners | Clients open a persistent gRPC bidirectional stream (Watch API) to Firestore. On write, Firestore updates `IndexEntries` then fans out diff events (DocumentChange: ADDED/MODIFIED/REMOVED) to all active Watch streams whose registered query is affected. The SDK assembles these into full snapshots locally. The browser JS SDK uses WebChannel (HTTP/1.1 chunked transfer or WebSocket) with optional long-polling fallback. Resume tokens allow streams to reconnect and replay missed events without re-reading the full result set. | Django Channels (ASGI) WebSocket consumers. On write, trigger a `channel_layer.group_send()` call. Use PostgreSQL `NOTIFY` from a Django `post_save` signal (or Celery task) and a background async listener that calls `group_send`. Clients subscribe to a WebSocket endpoint, filtered by collection path + query. The server evaluates whether each document change affects a given client's registered query before sending. | channels (pip install channels), channels-redis (pip install channels-redis), daphne (pip install daphne), psycopg3 async for LISTEN/NOTIFY, redis |
| 28 | Offline Persistence & Local Cache | Web SDK: IndexedDB-backed persistent cache (`persistentLocalCache()`) or memory-only (`memoryLocalCache()`). Mobile SDKs (iOS/Android): enabled by default using LevelDB on device. All reads hit cache first; writes are optimistically applied locally and queued for sync. Multi-tab: a single primary tab owns the network connection and syncs the shared IndexedDB across tabs. On reconnect, the SDK replays queued writes and reconciles cache with server state using resume tokens. | A thin JavaScript client SDK (or a service worker) that caches GET responses in IndexedDB (via idb library) and queues mutations in a pending-writes store. On reconnect, replay pending writes via the REST/WebSocket API. Alternatively, use Workbox (service worker toolkit) for request caching. No Django server changes needed — this is entirely a client-side concern. | idb (npm: idb), workbox (npm: workbox-sw), localforage (npm: localforage) for the JS client layer |
| 29 | Transactions | Firestore transactions use Serializable Snapshot Isolation (SSI) provided by Spanner. A transaction reads documents at a consistent snapshot timestamp, buffers writes, then commits atomically — retrying automatically (up to 5 times) on contention. Transactions can span multiple documents and collections. Maximum duration: 270 seconds. Maximum document reads/writes per transaction: 500. | `django.db.transaction.atomic()` with PostgreSQL's `SERIALIZABLE` isolation level for full SSI, or `REPEATABLE READ` for snapshot isolation. For client-SDK-driven optimistic transactions, implement a version field (`_version` integer) and use `UPDATE ... WHERE _version = expected_version RETURNING *` with retry logic in a DRF view. | Built-in Django transaction.atomic(); django-pgtransaction (pip install django-pgtransaction) for explicit isolation levels |
| 30 | Batched Writes | A `WriteBatch` groups up to 500 set/update/delete operations into a single atomic commit. Unlike transactions, batched writes do not read documents first — they are blind writes. All operations in the batch either succeed or fail together. Each document operation in the batch counts toward billing as a separate write. | `bulk_create`, `bulk_update`, and wrapping multiple `save()`/`delete()` calls inside a single `transaction.atomic()` block. For the REST API, a DRF action endpoint (`@action`) accepts an array of operations and processes them in one atomic block. | Built-in Django ORM + transaction.atomic() |
| 31 | Atomic Increments / ArrayUnion / ArrayRemove / ServerTimestamp | `FieldValue.increment(n)` — server-side atomic increment using Spanner's read-modify-write within a transaction, avoiding the need for a client read-then-write cycle. `FieldValue.arrayUnion([...])` / `arrayRemove([...])` — set union/difference on array fields, also applied server-side. `FieldValue.serverTimestamp()` — replaced with the Spanner commit timestamp, guaranteeing monotonicity and server authority. | `F()` expressions for atomic increments: `Document.objects.filter(pk=id).update(data=Func(F('data'), Value(n), function='jsonb_set', ...))`. For arrayUnion: raw SQL `data = data \|\| jsonb_build_array($1)` with deduplication. For serverTimestamp: `auto_now=True` on a DateTimeField, or `NOW()` in a SQL UPDATE. Custom DRF serializer field types to expose these as `{"_increment": n}` sentinel values. | Built-in Django F() expressions, psycopg2/3 for raw SQL when needed |
| 32 | Data Bundles | Pre-built binary snapshots of query results (Firestore's Protocol Buffer wire format) that can be served from a CDN. Clients load a bundle into the local SDK cache, seeding it without hitting Firestore directly. Named queries embedded in the bundle allow the client to re-execute the same query against cache. Bundles are built server-side (Admin SDK or Cloud Functions) and are read-only snapshots — not live data. | A Django management command or Celery periodic task that serializes a queryset to JSON and uploads it to MinIO/S3 with a CDN-friendly URL and `Cache-Control` header. The JS client fetches this JSON on first load and populates its local cache (IndexedDB). A DRF endpoint returns an ETag so clients can check freshness cheaply. | celery, boto3 / minio (pip install minio), django-storages (pip install django-storages) |
| 33 | TTL Policies | A TTL policy designates a specific field (must be a Timestamp) in a collection group as the expiration time. Firestore's background TTL worker scans for documents where that field is in the past and deletes them — typically within 24 hours after expiry. TTL deletes do NOT count toward write quotas but DO count toward delete billing. Configured per collection group, one TTL field per collection group. | A Celery Beat periodic task (e.g. every hour) that runs `Document.objects.filter(collection_path__startswith='sessions/', data__expires_at__lt=Now()).delete()`. For multiple collection groups, a configurable `TTLPolicy` table maps collection paths to expiry field names. Alternatively, PostgreSQL `pg_partman` for time-based partition pruning on very high-volume collections. | celery, celery-beat (pip install celery django-celery-beat), django-celery-results |
| 34 | Native Mode vs Datastore Mode | Both modes share the same underlying Spanner storage layer. **Native mode** (recommended for all new apps): supports realtime listeners, offline persistence, Firestore v1 API, client SDKs. **Datastore mode**: uses Datastore v1 API, entity-group model, no realtime listeners, no offline persistence, no Firestore client SDKs. Datastore mode was introduced for legacy Datastore users — it removes the old 1-write/sec entity group limit. | The Django rebuild targets only Native mode semantics: all features including realtime. If a Datastore-mode compatibility layer is needed (e.g. for migration), expose a separate URL namespace with Datastore v1 API shape using DRF, but skip Channels/WebSocket for that namespace. | N/A — architectural decision, not a library |
| 35 | Pricing Model | Billed per operation: $0.03/100K reads, $0.09/100K writes, $0.01/100K deletes (Standard edition). Storage: $0.15/GB/month. Egress to internet: $0.12/GB (first 10 TB). Free tier: 50K reads/day, 20K writes/day, 20K deletes/day, 1 GiB storage, 10 GiB/month egress. TTL deletes count as deletes for billing. Listener connections have no per-connection charge but each snapshot delivery counts as a read. | Self-hosted: primary costs are PostgreSQL server (compute + storage), Redis (channel layer), and CDN egress. For metered billing simulation, instrument middleware to count reads/writes per API key and store in Redis counters, then emit to a billing system. | N/A — infrastructure cost model |
| 36 | Scaling Limits & Hotspotting | ~1 sustained write/second per document (a single Spanner row). Firestore auto-shards at the collection level using Spanner's range splits — but a single document's row cannot be split. Sequential document IDs (e.g. timestamps as IDs) cause hotspots because Spanner splits on key ranges and all new writes land on one split. Mitigation: use random/hash IDs, distribute writes across many documents. Queries scale to millions/sec because they fan out across index shards. | PostgreSQL has no built-in per-row write limit but does have row-level lock contention. Use `SELECT FOR UPDATE SKIP LOCKED` for queue-like patterns. For counter aggregation at scale use a sharded counter pattern (N rows summed by a Celery task) or `pg_advisory_lock`-free atomic `F()` increments. Use UUID v4 (random) document IDs to prevent B-tree index hotspots on the `(collection_path, document_id)` index. | Built-in PostgreSQL + Django F() expressions; redis for high-frequency counters |
| 37 | JSON-tree data model | Single hierarchical JSON tree per database instance, stored server-side on Google's proprietary storage (backed by a distributed log/store layer). Accessed via URL paths that map 1-to-1 to JSON keys (e.g., /users/uid123/name). | PostgreSQL JSONB column on a single TreeNode table, or a path-keyed table using PostgreSQL ltree extension. All reads/writes resolve to a path inside a JSONB document. | django-ltree-2 (PyPI: django-ltree-2), psycopg2-binary, PostgreSQL 14+ with ltree extension |
| 38 | .on() / .once() listeners and ref paths | Clients obtain a DatabaseRef pointing to a path, then call .on('value'\|'child_added'\|'child_changed'\|'child_removed'\|'child_moved', cb) to attach persistent listeners, or .once() for a one-shot read. The SDK maintains a single multiplexed WebSocket per app and demultiplexes events by path. | Django Channels AsyncWebsocketConsumer. On connect the client sends a JSON subscribe message with a path; the server adds the consumer to a channel group named after that path (and all ancestor paths). On disconnect it leaves all groups. REST one-shot reads map to standard DRF GET endpoints. | channels (PyPI: channels), channels-redis (PyPI: channels-redis), djangorestframework |
| 39 | SSE / WebSocket diff streaming (put + patch events) | Firebase uses two transport layers: (1) a proprietary WebSocket-based protocol (the native SDK) that multiplexes all listeners over one socket per client and sends minimal diffs; (2) a REST SSE endpoint (Accept: text/event-stream) that emits put (replace subtree) and patch (merge keys) events with a JSON payload of {path, data}. The server sends only the changed subtree to each listener, not the whole tree. | On each write, compute the minimal diff between old and new values at the mutated path using jsonpatch, then call channel_layer.group_send() to every group whose path is a prefix of (or equal to) the written path. Consumers translate this into a put (full replace) or patch (partial merge) message. For SSE fans, add a Django StreamingHttpResponse endpoint using async generators. | jsonpatch (PyPI: jsonpatch), channels, channels-redis, django-sse (PyPI: django-sse) optional |
| 40 | onDisconnect handlers and presence | When a client registers onDisconnect().set(value) or onDisconnect().remove(), the server stores the pending operation server-side. When the TCP connection drops (clean or dirty), the server executes the operation atomically. The /.info/connected read-only path reflects live connection state. Clients typically write online: true and schedule onDisconnect().set({online: false, lastSeen: ServerValue.TIMESTAMP}). | On WS connect: store {channel_name: consumer.channel_name, path: path, value: disconnect_value} in a Redis hash with HSET; set a TTL key redis.setex(f'presence:{channel_name}', 60, 1). The consumer's disconnect() method executes the pending write directly. For dirty disconnects, a Redis keyspace notification (expired event on the TTL key, via CONFIG SET notify-keyspace-events Ex) triggers a Celery task that performs the stored onDisconnect write. Expose a synthetic /.info/connected WebSocket message on connect/disconnect. | redis-py (PyPI: redis), celery (PyPI: celery), django-celery-beat (PyPI: django-celery-beat) |
| 41 | Offline behavior and local persistence | The RTDB SDK caches active listener data in memory; on mobile (iOS/Android) persistence can be enabled to write to disk (LevelDB on mobile clients). Writes are queued locally and replayed on reconnect. The SDK tracks a 'pending writes' queue and applies optimistic updates to the local cache immediately, then confirms with the server. | This is entirely a client-side concern. Implement a JS/TS client SDK (or use a thin wrapper) that stores the last-known tree snapshot in IndexedDB (via idb-keyval or Dexie.js), queues pending mutations in IndexedDB, and replays them as PUT/PATCH messages on WebSocket reconnect. The server must be idempotent (assign client-generated push IDs to writes to detect duplicates). | Client: Dexie.js (IndexedDB), reconnecting-websocket npm package. Server: no extra deps needed beyond idempotent write logic. |
| 42 | Push IDs (auto-generated keys via .push()) | firebase.database().ref('/messages').push(data) generates a 20-char lexicographically-sortable key (e.g., -NxK2z...) based on timestamp + random component, then writes under that key. This guarantees chronological sort order without a sequence number. | Generate a Firebase-compatible push ID server-side: a 17-char base-64 timestamp prefix + 12 random chars, or simply use KSUID (k-sortable unique ID). Return the generated key to the client in the WS ack message. | python-ksuid (PyPI: python-ksuid) or implement Firebase push ID algorithm directly (20 lines of Python) |
| 43 | Shallow queries and query limits | REST GET with ?shallow=true returns only the immediate keys of a JSON node (not values), useful to avoid fetching large subtrees. Standard queries: orderBy child/key/value/priority, limitToFirst(n), limitToLast(n), startAt(v), endAt(v), equalTo(v). Only ONE orderBy per query. Cannot combine shallow + other filters. | REST DRF endpoints accept query params: ?shallow=1 returns only top-level keys of the JSONB field (using jsonb_object_keys in a raw query). Filtering and ordering are implemented via PostgreSQL JSONB path operators (e.g., jsonb_path_query) or extracted columns (index JSONB fields you query on). Index with CREATE INDEX on JSONB expression indexes. | djangorestframework, django-filter (PyPI: django-filter), psycopg2 for raw jsonb_object_keys queries |
| 44 | Multi-path atomic updates | database.ref().update({ '/path/a': val1, '/path/b': val2 }) issues a single atomic write to multiple paths in the tree. Under the hood, this is a single write transaction on the backend — all paths succeed or none do. Exposed over REST as PATCH to the root with a flat map of paths to values. | Wrap all path writes in a single PostgreSQL transaction with SELECT ... FOR UPDATE on the root row. Use jsonb_set() in a loop (or a recursive CTE) to update multiple sub-paths atomically. DRF endpoint accepts { 'updates': {'/a/b': v1, '/c': v2} } and runs a single atomic DB transaction. | django.db.transaction.atomic(), psycopg2 jsonb_set(), no extra packages needed |
| 45 | Database rules (security) | JSON-based security rules (.read, .write, .validate, .indexOn) evaluated server-side on every operation against the path. Rules can access auth.uid, data, newData, and use $ wildcards. Rules are compiled to an expression tree and evaluated per-operation. | DRF permission classes + row-level security. Write a PathPermission class that checks the requesting user against a Django model storing per-path ACL rules (path pattern, read_roles, write_roles). For .validate semantics, use DRF serializers with custom validators. Rule wildcard matching uses regex or fnmatch on the path string. | djangorestframework, django-rules (PyPI: django-rules) for predicate-based permissions |
| 46 | Sharding across multiple database instances | Each RTDB instance is capped at 200,000 concurrent WebSocket connections and 1 GB free / $5/GB stored. Google supports up to 1000 database instances per project. Apps shard by assigning users/sessions to different database URLs (e.g., shard-0.firebaseio.com, shard-1.firebaseio.com). Clients must know which shard they belong to. | Use Django's DATABASE_ROUTERS to route to multiple PostgreSQL instances by shard key (user_id % N). Each shard runs its own Channels worker pool. A thin routing layer (or a consistent-hash Redis key) tells clients which WebSocket endpoint/shard to connect to. Horizontal scaling of the WS tier is handled by adding more Daphne/Uvicorn workers behind an Nginx upstream. | django-db-router (built-in DATABASE_ROUTERS), Nginx upstream, daphne (PyPI: daphne) or uvicorn (PyPI: uvicorn[standard]) |
| 47 | RTDB vs Firestore tradeoffs | RTDB: single JSON tree, low latency (<100ms), limited queries (one orderBy, no compound filters), 200k concurrent connections per instance, $5/GB stored + $1/GB downloaded. Firestore: document/collection model, rich queries (compound indexes, multiple filters), automatic horizontal scaling, slightly higher latency, different pricing. RTDB shines for presence, simple chat, and live counters. | For RTDB-like use cases (presence, counters, simple chat): Django Channels + PostgreSQL JSONB + Redis pub-sub as described here. For Firestore-like use cases (rich queries, collections): use standard Django ORM with PostgreSQL relations, full-text search (pg_trgm), and DRF. The two can coexist in the same Django project on separate URL prefixes. | Same stack — differentiated by data model choice (JSONB tree vs. normalized ORM tables) |
| 48 | Pricing model (per GB stored + downloaded) | Spark (free): 1 GB storage, 10 GB/month download. Blaze (pay-as-you-go): $5/GB/month stored, $1/GB downloaded, beyond the free tier. Connection pricing is implicitly bundled (200k conn limit per instance forces sharding, which costs more instances). | Self-hosted: costs are VPS/Postgres storage (e.g., ~$0.10/GB/month on DigitalOcean), bandwidth (typically $0.01/GB on most cloud providers), and Redis memory. At 10 GB stored: Firebase ~$45/mo vs self-hosted ~$1/mo storage. The break-even vs Firebase is around 5-10 GB if you include ops overhead. | N/A — infrastructure cost comparison |
| 49 | Managed Cloud SQL for PostgreSQL | Firebase provisions and manages a Cloud SQL for PostgreSQL instance (regional, shared or dedicated) per project. Handles provisioning, patching, backups, and connection pooling via the Data Connect service layer. AlloyDB support is community-requested but not yet GA (mid-2026). | Self-managed PostgreSQL (Docker, VM, managed RDS/Cloud SQL/Supabase). Django's DATABASES setting points at it. Add PgBouncer for connection pooling. | psycopg2-binary or psycopg[binary] (Django adapter); pgbouncer (connection pooler); django-db-geographics / PostGIS for spatial; supabase self-hosted as full managed stack |
| 50 | GraphQL SDL Schema → PostgreSQL DDL (schema-first auto-migration) | Developer writes types with @table, @col, @default, @ref directives in .gql files. Firebase CLI compiles these to CREATE TABLE / ALTER TABLE statements and applies them to Cloud SQL on deploy. Implicit FK columns and join-table fields are generated automatically. | Django models.py is the schema source of truth; `makemigrations` + `migrate` generates and applies SQL DDL. Strawberry-Django introspects models to emit a matching GraphQL schema. For pure SDL-first flow use graphene-django or ariadne-django with schema stitching. | strawberry-graphql-django (pip install strawberry-graphql-django); graphene-django (pip install graphene-django); ariadne (pip install ariadne); django-extensions for migration tools |
| 51 | Connectors: bundled named query/mutation operation files (.gql) | A Connector is a directory of .gql operation files scoped to a specific client (e.g., 'web', 'admin'). Each file contains named GraphQL queries and mutations decorated with @auth. The connector is deployed as a unit; only operations defined in a connector can be called from clients — no arbitrary ad-hoc queries. | DRF ViewSets or Strawberry resolvers grouped by Django app. Enforce 'only declared operations' via a whitelist resolver registry or by using persisted-query middleware (graphql-core-3 + custom middleware). Each app = one connector boundary. | strawberry-graphql-django resolvers; djangorestframework (pip install djangorestframework); graphql-core (pip install graphql-core); django-graphql-jwt for auth injection |
| 52 | @auth directive: query-level access control (PUBLIC, USER, NO_ACCESS, ADMIN, custom CEL expressions) | Each query/mutation carries @auth(level: USER) or a CEL expression like @auth(expr: "auth.uid == vars.userId"). The Data Connect server validates Firebase Auth JWT before executing SQL. auth.uid, auth.token.*, request.vars.* are available in CEL. NO_ACCESS = deny all clients; ADMIN = only server SDK. | Strawberry permission classes (BasePermission subclass) or DRF permission_classes. For field-level: strawberry-django's PermissionExtension. For row-level: Django QuerySet filtering by request.user.id, or PostgreSQL RLS policies via django-pgtrigger + manual RLS enablement. | strawberry-graphql-django permissions; djangorestframework permissions; django-rules (pip install rules) for object-level perms; django-pgtrigger for DB-level RLS; PyJWT for Firebase JWT verification |
| 53 | @check directive: mutation-time conditional guard | In a @transaction mutation, @check(expr: "this.wallet >= amount", message: "Insufficient") evaluates a CEL expression against query results mid-transaction. If false, the whole transaction rolls back. Enables optimistic lock patterns without extra round trips. | Django's select_for_update() + database-level CHECK constraints + Django validators in a transaction.atomic() block. Custom GraphQL mutation resolver raises PermissionDenied or ValidationError inside atomic block. | django.db.models.CheckConstraint; django.db.transaction.atomic; select_for_update(); strawberry exception handling |
| 54 | @transaction directive: multi-table atomic mutations | Wrapping a mutation in @transaction groups all its table operations into a single DB transaction. FDC chains auto-generated insert/update calls sequentially inside one SQL transaction. Rollback is automatic on @check failure. | django.db.transaction.atomic() decorator or context manager on mutation resolvers. Nested atomics use savepoints automatically. | django.db.transaction (built-in); django-transaction-hooks (pip install django-transaction-hooks) for post-commit side effects |
| 55 | Auto-generated CRUD mutations (insert, upsert, update, delete, update_many, delete_many) | For every @table type, Data Connect auto-generates movie_insert, movie_upsert, movie_update, movie_delete, movies_update_many, movies_delete_many mutations with full field input types and key-based lookups. No boilerplate required. | strawberry-django auto-generates CRUD mutations from Django models via @strawberry_django.mutation. Graphene-django provides DjangoCreateMutation, DjangoUpdateMutation, DjangoDeleteMutation via graphene-django-extras or relay. | strawberry-graphql-django (auto CRUD); graphene-django-extras (pip install graphene-django-extras); strawberry-django-auth |
| 56 | Relational queries: one-to-one, one-to-many, many-to-many with implicit join table fields | FDC generates traversal fields from FK relationships: movie.actors_on_movies, actor.movies_via_actormovie. Many-to-many uses an explicit join @table with a composite key. GraphQL query traversal compiles to SQL JOINs. @ref directive declares FK; implicit FK columns like movieId are injected. | Django ForeignKey, OneToOneField, ManyToManyField in models.py. Strawberry-django uses select_related() and prefetch_related() under the hood for nested resolvers. Dataloader pattern (strawberry-django DataLoader) prevents N+1. | strawberry-graphql-django (nested types, DataLoader); django-graphql-optimizer (pip install graphene-django-optimizer); strawberry-django-dataloaders |
| 57 | Query filters, ordering, pagination (limit/offset, cursors) | Auto-generated query inputs include where (field filters with _eq, _gt, _lt, _like, _in, isNull), orderBy, limit, offset. Cursor-based pagination via after/before fields. Filter inputs are strongly typed. | Django ORM .filter(), .order_by(), .annotate(). DRF: django-filter backend. GraphQL: strawberry-django FilterLookup for @filter decorator and auto-generated filter input types. Relay connection for cursor pagination. | strawberry-graphql-django filter/ordering/pagination extensions; django-filter (pip install django-filter); graphene-django-connections for relay cursor pagination |
| 58 | Native SQL mode (@sql / _execute directive) for arbitrary SQL | Introduced in SQL Connect (March 2026). _execute(sql: "...", params: [...]) in .gql lets developers embed parameterized raw SQL in mutations/queries. SQL is hardcoded at deploy time (no client-supplied SQL). {_expr: "auth.uid"} injects server-side context into params. Enables CTEs, window functions, PostGIS, etc. Returns Any (JSON) — no compile-time SDK typing. | Django ORM's .raw() queries or cursor.execute() with parameterized queries inside resolvers. db.connection.cursor() + cursor.execute(sql, params) pattern. Full PostGIS, window functions, CTEs available natively. | django.db.connection.cursor() (built-in); django.contrib.gis for PostGIS; psycopg2 for parameterized queries; RawSQL() expression for ORM integration |
| 59 | Typed client SDK generation (Web/TS, Flutter/Dart, iOS/Swift, Android/Kotlin) | firebase dataconnect:sdk:generate reads connector .gql operation files and emits typed client stubs. Web SDK generates TypeScript interfaces + functions that call the Data Connect gRPC endpoint. Flutter SDK generates Dart classes. No manual API client writing. Re-run after any schema/connector change. | graphql-codegen (npm) reads your GraphQL schema + operations and emits typed TypeScript/React hooks. For Dart: ferry codegen or artemis. For Swift/Kotlin: Apollo iOS / Apollo Kotlin. Point codegen at your Django GraphQL schema endpoint or exported schema.graphql. | @graphql-codegen/cli + @graphql-codegen/typescript-operations (npm); ferry_generator (Dart/Flutter); Apollo iOS (Swift); Apollo Kotlin; ariadne-codegen (pip install ariadne-codegen) for Python server-side |
| 60 | Generated Admin SDK (server-side SDK with elevated access) | Announced Nov 2025. `firebase dataconnect:sdk:generate --target=admin` emits a Node.js/Python admin SDK that bypasses @auth(level: NO_ACCESS) guards. Used in Cloud Functions or backend services. Type-safe, same operation definitions as client SDK but with admin context injected. | Django management commands or Celery tasks that call ORM/resolvers directly with superuser context. No auth middleware applied in management layer. Or a separate DRF API endpoint protected by API key / service account auth. | Django management commands (built-in); Celery (pip install celery); djangorestframework API key auth |
| 61 | Event triggers on mutations (via Eventarc / Cloud Functions / Cloud Run) | Announced Nov 2025. After a named mutation executes, Data Connect publishes an Eventarc event. Cloud Functions subscribe via onMutationExecuted trigger. Payload includes mutation args and auth context. Enables send-email-on-signup, webhook-on-order patterns. Supports filter expressions to narrow which mutations trigger. | Django signals (post_save, pre_delete) on model changes for in-process sync triggers. For async/decoupled: django-pgtrigger fires DB-level trigger → Celery task via django-celery-results. Or Postgres LISTEN/NOTIFY → custom consumer. For webhook-style: custom Celery tasks invoked post-mutation. | django.db.models.signals (built-in); django-pgtrigger (pip install django-pgtrigger); Celery + celery[redis] for async task dispatch; django-celery-beat for scheduled triggers; channels for websocket push |
| 62 | Realtime query subscriptions (@refresh directive + CEL conditions) | SQL Connect (April 2026). Clients subscribe to a named query; server pushes updated results when @refresh condition fires. @refresh(onMutationExecuted: {operation: 'UpdateUser', condition: 'mutation.auth.uid == query.auth.uid'}) uses CEL to scope refreshes per user. Or configure @refresh(interval: 30s) for polling-based refresh. Server uses Postgres polling + change detection (not CDC). | Django Channels (ASGI) + WebSocket consumer + GraphQL subscriptions via strawberry-channels. On mutation, resolve side-effects push updated data to subscribed clients via channel layer (Redis). For simpler interval polling: long-polling DRF endpoint or SSE via django-eventstream. | channels[daphne] (pip install channels); strawberry-channels (pip install strawberry-channels); channels-redis (pip install channels-redis); django-eventstream (pip install django-eventstream) for SSE |
| 63 | Offline caching (SDK-level query cache for no/low connectivity) | SQL Connect (April 2026). Client SDKs cache the last query result locally (IndexedDB on Web, SQLite on mobile). On reconnect, the SDK resyncs. Tied to the @refresh subscription mechanism — cached data is the last-known subscription result. | Frontend responsibility: TanStack Query (React) or SWR provide stale-while-revalidate + offline caching patterns against any HTTP/GraphQL endpoint. For mobile: Apollo Client offline cache (InMemoryCache + persistence). No Django server-side change needed. | @tanstack/react-query (npm); apollo-client + apollo3-cache-persist (npm); swr (npm); Hive Gateway or Apollo Router as GraphQL caching layer in front of Django |
| 64 | Custom Resolvers (experimental, backed by Cloud Functions for Firebase) | Announced April 2026 as experimental. Extend a SQL Connect schema with Cloud Function-backed resolvers that can call Stripe, X API, Cloud Storage, BigQuery, etc., then issue Native SQL operations. The custom resolver function is defined in JS and registered in the Data Connect config. Client SDK still gets type-safe stubs for the custom operation. | Django REST Framework custom APIView or Strawberry GraphQL mutation resolver that orchestrates calls to Stripe SDK, requests to external APIs, then writes to the DB in a transaction.atomic() block. This is Django's native pattern — no special framework needed. | requests or httpx (pip install httpx) for external API calls; stripe (pip install stripe); django.db.transaction.atomic; Celery for background orchestration |
| 65 | Firebase Auth integration (auth.uid, auth.token.* in CEL expressions) | Data Connect validates Firebase Auth JWTs on every operation. The decoded token fields (uid, email, custom claims) are available as auth.uid, auth.token.email, auth.token.admin in @auth CEL expressions and in _expr server-side param injection. No JWT parsing code needed in operation files. | Custom Django authentication backend that validates Firebase JWT (PyJWT + Google public keys) and populates request.user. Strawberry resolvers receive request.user via info.context.request. @auth permission class checks user.uid. | PyJWT (pip install PyJWT); python-jose (pip install python-jose); django-firebase-auth (pip install django-firebase-auth); firebase-admin (pip install firebase-admin) for server-side token verification |
| 66 | Supported scalar data types (UUID, Date, Timestamp, Int64, Float, Boolean, String, Any, Vector) | Custom GraphQL scalars map to Postgres types: UUID→uuid, Date→date, Timestamp→timestamptz, Int64→bigint, Any→jsonb, Vector→vector (pgvector). @col(dataType) overrides the column type. @default(expr) supports uuidV4(), request.time, server-side CEL expressions. | Django model fields: UUIDField, DateField, DateTimeField, BigIntegerField, FloatField, JSONField, custom VectorField (pgvector-django). Strawberry auto-maps these to GraphQL scalar types. | pgvector-django (pip install pgvector-django) for Vector/embedding fields; django.db.models (built-in field types); strawberry scalar type mappings |
| 67 | Local emulator + VS Code extension (Data Connect Toolkit) | firebase emulators:start --only dataconnect runs a local Data Connect service + local Postgres. The VS Code extension provides schema editing, connector authoring, SDK generation preview, and GraphQL operation runners directly in the editor. Schema introspection and migration diffing happen locally without hitting production. | Local PostgreSQL (Docker Compose), Django dev server, Django shell, and graphiql-django or Strawberry's built-in /graphql explorer in DEBUG mode. django-extensions provides graph_models for schema visualization. pgAdmin or DBeaver for DB introspection. | graphiql (via strawberry DEBUG view built-in); django-extensions (pip install django-extensions); docker-compose for local Postgres; django-silk (pip install django-silk) for query profiling |
| 68 | Pricing model: operations + Cloud SQL instance cost | Two billable dimensions: (1) Operations: 250,000 free/month on Blaze; then $0.90/million operations (price dropped May 2026 from $4/million). One operation = one query/mutation regardless of tables touched. Network egress: first 10 GiB/month free then premium tier rates. (2) Cloud SQL instance: starts ~$9.37/month for minimal shared instance. Spark plan: 8,300 ops/day limit, free Cloud SQL trial cluster. No-cost trial available without payment info. | Self-hosted cost = VPS/cloud VM + managed PostgreSQL. DigitalOcean: $12/mo Postgres + $6/mo droplet = ~$18/mo. Supabase free tier: 500MB Postgres, unlimited API calls. No per-operation billing — all infrastructure cost. | N/A (infrastructure cost only) |
| 69 | Object/Blob Storage (GCS buckets) | Files stored in GCS buckets; Firebase project IS a GCS project. Exabyte-scale, 11-nines durability, multi-region. Flat namespace with slash-delimited pseudo-paths. All new buckets require Blaze plan as of Oct 2025. | django-storages (S3Boto3Storage) + MinIO or AWS S3/Cloudflare R2 as backend. PostgreSQL StorageObject model as metadata registry and policy table. | django-storages[s3] (pip), boto3 (pip), minio server (Docker: quay.io/minio/minio) |
| 70 | Resumable Uploads | uploadBytesResumable() uses GCS resumable upload protocol: POST to get a session URI, then PUT chunks. Session URI valid 1 week. Auto-retry on network failure. Files >5 MB automatically use resumable path. | Option A: Presigned S3 multipart upload (create_multipart_upload → presign each UploadPart URL → CompleteMultipartUpload). Option B: django-tus server-side tus protocol with tus-js-client on browser. Supabase pattern: map tus chunks to S3 UploadParts server-side. | django-tus (pip, PyPI), boto3 create_multipart_upload, tus-js-client (npm), uppy (npm) |
| 71 | Download URLs (token-based) | UUID stored as firebaseStorageDownloadTokens custom GCS metadata. URL: firebasestorage.googleapis.com/...?alt=media&token=UUID. Firebase proxy checks token matches metadata. Bypasses Security Rules. Permanent until token rotated. | StorageObject.download_token UUID field in PostgreSQL. TokenDownloadView validates token, runs Python access check, then 302-redirects to short-lived S3 presigned GET URL. Rotate token UUID to revoke all outstanding URLs. | django-storages (pip), boto3 generate_presigned_url (pip), DRF APIView |
| 72 | Signed URLs (time-limited) | Admin SDK generates GCS V4 signed URLs using service-account private key. Expire in minutes to 7 days. Bypass Firebase Security Rules. Go directly to GCS. | boto3 generate_presigned_url('get_object', ExpiresIn=N) on server side. DRF view enforces auth/authz before generating URL. Client uses URL directly against MinIO/S3. | boto3 (pip), minio-py (pip, alternative) |
| 73 | Presigned PUT URLs (direct client upload) | Firebase client SDK uploads directly to GCS with user's ID token as auth. Django equivalent needs to replicate no-proxy upload path. | Request-slot → presigned PUT → confirm flow: DRF generates presigned PUT URL, client uploads directly to S3/MinIO, client calls confirm endpoint which verifies via head_object and triggers Celery post-processing. | boto3 generate_presigned_url('put_object') (pip), DRF APIView, Celery (pip) |
| 74 | File Metadata (system + custom) | GCS system metadata: contentType, size, timeCreated, updated, md5Hash, etag, generation. User metadata: customMetadata (string key-value). Settable at upload or via updateMetadata(). Security Rules can read metadata in resource.metadata and request.resource.metadata. | StorageObject.custom_metadata JSONField in PostgreSQL as authoritative store. Sync to S3 object metadata via copy-in-place (s3.copy_object with MetadataDirective=REPLACE). Security rules read from DB, not S3. | django JSONField (built-in), boto3 copy_object (pip) |
| 75 | Security Rules (declarative access control DSL) | CEL-based DSL evaluated server-side on Firebase's proxy before request reaches GCS. Matches paths with wildcards. Variables: request.auth (JWT claims), request.resource (incoming write), resource (existing object). Cross-service: firestore.get() and firestore.exists(). Does NOT apply to Admin SDK, GCS direct calls, or download token URLs. | Python evaluate_storage_access() function per-request in DRF views. StorageObjectPermission class for DRF has_object_permission hook. For cross-service: query PostgreSQL instead of Firestore. For declarative teams: OPA (Open Policy Agent) sidecar with Rego policies. | djangorestframework (pip), python-opa-client (pip, optional), django-rules (pip, optional) |
| 76 | File Listing (listAll / list with pagination) | Maps to GCS list-objects with prefix and delimiter. listAll() buffers everything in memory (up to 1000 per page internally). list() returns pageToken for cursor pagination. Prefixes simulate folders. Requires Security Rules v2. | Query StorageObject table with object_path__startswith=prefix and cursor-based pagination (object_path__gt=cursor). Returns items and pseudo-folder prefixes by string-splitting paths. | Django ORM (built-in), DRF ListAPIView (pip) |
| 77 | Image Resize Extension | Cloud Function triggered on object.finalize event. Uses Sharp (Node.js) to resize to configured dimensions (preserving aspect ratio). Uploads variants to same bucket with suffix (e.g., photo_200x200.jpg). Copies safe metadata. Optionally deletes original. Publishes EventArc events onSuccess/onError/onCompletion. | Celery task process_uploaded_file() triggered from ConfirmUploadView. Uses Pillow (PIL) Image.thumbnail() for aspect-ratio-preserving resize. Uploads variants via s3.put_object(). Creates StorageObject records for each variant. Chain with virus scan task. Alternatively use django-imagekit ImageSpecField for ORM-level spec definitions. | Pillow (pip), django-imagekit (pip), Celery (pip), Redis (broker), python-clamd (pip, optional) |
| 78 | Client SDK (web/iOS/Android/Flutter) | Unified SDK handles: auto-attach ID token to all requests, retry on failure, upload/download progress callbacks, offline queue on mobile, getDownloadURL() after upload. SDK speaks GCS API but routes through Firebase's proxy. | Thin JS wrapper class (OwnStorageClient) handling: token attachment, presigned-URL upload flow, progress callbacks via axios onUploadProgress, confirm step. For mobile offline: use tus-js-client (stores upload offset in localStorage/IndexedDB). No equivalent to Firebase's offline mobile queue without additional work. | axios (npm), tus-js-client (npm), uppy (npm, full-featured drop-in), @aws-sdk/client-s3 (npm, for direct multipart) |
| 79 | CORS Configuration | Configured on the GCS bucket via gsutil or gcloud CLI with a JSON policy file. Firebase client SDK does NOT bypass CORS — bucket CORS must match your app's origin. Common gotcha for new Firebase users. | Set CORS policy on MinIO bucket via mc (MinIO Client) or via S3 PutBucketCors API. Nginx handles CORS for Django API responses. django-cors-headers for DRF endpoints. | django-cors-headers (pip), MinIO mc CLI (Docker), boto3 put_bucket_cors (pip) |
| 80 | Pricing (storage + egress + operations) | Spark free: 5 GB storage, 1 GB/day download. Blaze: $0.026/GB/month storage, $0.12-0.15/GB egress, $0.005/1K Class A ops (writes), $0.0004/1K Class B ops (reads). All buckets require Blaze from Oct 2025. Egress costs are the primary bill driver at scale. | MinIO self-hosted: $0 storage (hardware cost), $0 egress internal. Cloudflare R2: $0.015/GB storage, $0 egress (vs Firebase's $0.15/GB). AWS S3: $0.023/GB storage, $0.09/GB egress. Operations are free with MinIO; S3 Class A $0.005/1K, Class B $0.0004/1K (same as Firebase). | MinIO (Docker, free), Cloudflare R2 (managed, free egress), AWS S3 (managed) |
| 81 | HTTP Functions (onRequest) | Deploys as a Cloud Run container (2nd gen) or Cloud Functions v1 (1st gen). Any HTTP method, plain HTTPS URL. 2nd gen supports up to 32 MB request body, 60-minute timeout, up to 1000 concurrent requests/instance. | DRF @api_view or Django Ninja operation on any URL. Served by Gunicorn/Uvicorn behind Nginx in Docker. No cold starts — workers are long-lived. | djangorestframework, gunicorn, uvicorn |
| 82 | Callable Functions (onCall) | Special HTTPS Cloud Run endpoint. Firebase client SDK auto-attaches Authorization Bearer token, Firebase-Instance-ID-Token, and X-Firebase-AppCheck header. Request body is always {"data": ...}, response is {"result": ...} or {"error": ...}. Auth token validated server-side automatically. | DRF POST view with JWT authentication. Same JSON envelope convention implemented manually. Client shim function replicates the SDK convenience. djangorestframework-simplejwt handles token validation. | djangorestframework, djangorestframework-simplejwt, django-ninja |
| 83 | Firestore Triggers (onDocumentCreated/Updated/Deleted/Written) | Firestore writes publish CloudEvents to Eventarc. Eventarc delivers to Cloud Run service via HTTP POST. Event payload includes before/after DocumentSnapshot and wildcard-captured path params. At-least-once delivery. | django-pgtrigger defines PostgreSQL triggers that fire pg_notify() on INSERT/UPDATE/DELETE (including bulk ORM, raw SQL). django-pgpubsub LISTEN worker receives notifications and dispatches Celery tasks. Outbox pattern (SELECT FOR UPDATE SKIP LOCKED) for zero-loss fan-out. | django-pgtrigger, django-pgpubsub, celery[redis] |
| 84 | Realtime Database Triggers (onValueWritten/Created/Updated/Deleted) | RTDB write events publish to Firebase internal event bus → Eventarc → Cloud Run. Path patterns with wildcards (e.g. users/{uid}/messages/{msgId}). DataSnapshot before/after provided in event. | RTDB replaced by PostgreSQL + Django Channels for realtime. Same pgtrigger/pgpubsub stack handles DB-change events. Path-based routing implemented via channel name conventions or Celery task routing keys. | django-pgtrigger, django-pgpubsub, celery[redis], channels |
| 85 | Auth Triggers (onUserCreated, onUserDeleted) | Non-blocking: Firebase Auth events (new user account, federated login first-time, Admin SDK create) publish to Eventarc, invoke Cloud Run asynchronously. Admin SDK bulk delete does NOT fire onDelete per user. | Django post_save signal (created=True) and post_delete signal on the User model. Signals dispatch Celery tasks for heavyweight work. For blocking behavior (reject signup), override DRF serializer or use middleware. | celery[redis], djangorestframework |
| 86 | Blocking Auth Functions (beforeUserCreated, beforeUserSignedIn) | Firebase Identity Platform calls Cloud Run synchronously before completing the auth operation. Function can reject with an error to block signup/signin. Adds latency to auth flow. | DRF serializer validate_* methods or custom authentication backends reject invalid registrations/logins synchronously. Django middleware intercepts all requests including login endpoints. | djangorestframework |
| 87 | Cloud Storage Triggers (onObjectFinalized, onObjectDeleted, onObjectArchived, onObjectMetadataUpdated) | Cloud Storage (GCS) publishes Pub/Sub notifications on bucket events. Eventarc delivers CloudEvents to Cloud Run. Event contains bucket name, object path, content type, generation, size, metadata. | MinIO (S3-compatible self-hosted storage) sends HTTP webhook events to a Django endpoint on bucket events (configured via mc event add). Endpoint dispatches Celery tasks for processing (thumbnail generation, virus scan, etc.). | celery[redis], djangorestframework, MinIO |
| 88 | Scheduled Functions (onSchedule / Cloud Scheduler) | onSchedule creates a Cloud Scheduler job that publishes to Pub/Sub at the given cron interval. Pub/Sub triggers the Cloud Run function via Eventarc. Supports Unix-cron and App Engine cron syntax, timezone, and retry count. | Celery Beat with django-celery-beat stores schedules in the Django database (PeriodicTask model). Admin UI allows adding/editing/disabling schedules without restarting the beat process. Supports crontab, interval, solar, and clocked schedules with timezone. | celery[redis], django-celery-beat, django-celery-results |
| 89 | Pub/Sub Triggers (onMessagePublished) | Cloud Functions subscribes to a Pub/Sub topic. When a message is published (from any GCP service, Firebase Admin SDK, or external publisher), Eventarc delivers it to the Cloud Run service. Message body is base64-encoded in event.data.message.data. | Redis Streams (xadd/xread) for lightweight pub/sub. RabbitMQ with fanout exchanges for true multi-consumer fan-out. A Django management command or Celery consumer reads the stream/queue and dispatches handlers. | redis-py, celery[redis] or pika (RabbitMQ) |
| 90 | Eventarc Custom Events | Firebase Admin SDK publishes CloudEvents-formatted messages to named Eventarc channels. Firebase creates a default channel 'firebase' in us-central1. Functions subscribe with onCustomEventPublished(). Used by Firebase Extensions to expose events to user functions. | Redis Streams with CloudEvents JSON envelope. Publisher calls r.xadd('eventarc:custom', {...}) with type, subject, source, data fields. Consumer management command reads stream and routes to handlers by event type. | redis-py |
| 91 | Firebase App Hosting (managed SSR hosting) | CI/CD pipeline (Cloud Build) triggered by GitHub push. Runs next build / ng build. Static assets deployed to Google CDN. SSR bundle deployed as Cloud Run revision. apphosting.yaml configures minInstances, maxInstances, CPU, memory, env vars (with Cloud Secret Manager references). FirebaseServerApp enables SSR code to call Firestore with user credentials from the request. | Gunicorn (WSGI) or Uvicorn (ASGI) behind Nginx in Docker. GitHub Actions CI/CD for build and deploy. Nginx serves static files with long-cache headers (CDN equivalent) and proxies dynamic requests to Django. Secrets via environment variables or HashiCorp Vault. Django's built-in request.user provides auth context in views. | gunicorn, uvicorn[standard], nginx (Docker), GitHub Actions |
| 92 | 1st Gen vs 2nd Gen Cloud Functions | 1st gen: Cloud Functions v1, 1 req/instance, 8 GB/2 vCPU max, 540s timeout, 10 MB HTTP body. 2nd gen: Cloud Run backed, up to 1000 req/instance, 16 GiB/4 vCPU max, 3600s HTTP timeout, 32 MB body, Eventarc triggers, container-level deployment. | Django has no generation concept. Gunicorn worker count and Celery worker concurrency are tuned per deployment. WSGI (sync) vs ASGI (async) is the architectural equivalent of the scaling model difference between gen 1 and gen 2. | gunicorn, uvicorn, celery |
| 93 | Cold Start Mitigation (minInstances / provisioned instances) | minInstances keeps N Cloud Run instances warm at all times, paying for idle CPU/memory. Reduces cold start from 1-12 seconds (depending on dependencies) to ~0. 2nd gen concurrency means N instances serve up to N*1000 requests before needing to scale out. | No cold starts exist in the Gunicorn/Docker model — worker processes are persistent. The analog is ensuring at least 1 container replica is running (replicas: 1 in Docker Swarm, or minReplicas: 1 in Kubernetes HPA). Worker process count controls throughput, not startup latency. | gunicorn (--workers flag), Docker/Kubernetes replica config |
| 94 | Idempotency and At-Least-Once Delivery | Firebase Cloud Functions (both gen) guarantee at-least-once execution. A single Firestore write can trigger multiple function invocations. Retry on failure configurable. No exactly-once guarantee. | Celery defaults to at-least-once. Use get_or_create for writes, track event IDs in a processed_events table, or use Celery's task_id as idempotency key. Transactional outbox pattern prevents dual-write problem for critical events. | celery, django-celery-beat |
| 95 | Static file hosting + global CDN | Files are stored in a GCS-backed object store. On deploy, the Firebase CLI uploads only changed files (hash deduplication). Every file is pushed to Google Cloud CDN SSD edge nodes worldwide, served over HTTPS with auto Brotli/gzip negotiation. Cache-Control: public, max-age=31536000 is set for fingerprinted assets; HTML gets no-cache. | WhiteNoise (dev/simple) or Nginx + S3/MinIO + django-storages + CloudFront/Cloudflare (prod). collectstatic + ManifestStaticFilesStorage generates content-hashed filenames. Cloudflare CDN fronts the origin. | whitenoise, django-storages[s3], boto3, django-minio-backend, Nginx, Cloudflare |
| 96 | Atomic deploys | Hosting REST API creates a new Version object, uploads files to it (by SHA256 hash), then creates a Release that atomically points the live channel to that Version. Old versions remain stored for rollback. The CDN is instructed to purge all cached content the moment the release pointer switches. | Build a new Docker image tagged with git-sha, push it to a registry. Use Kamal (or a blue-green nginx upstream swap) to switch traffic atomically after health checks pass. Store DeployVersion records in Postgres pointing to image tags. Trigger Cloudflare Cache Purge API on each deploy. | Docker, Kamal (basecamp/kamal), Cloudflare Cache Purge API, PostgreSQL |
| 97 | One-click rollback | Each Release points to an immutable Version. Rolling back creates a new Release pointing to a previous Version — the CDN pointer switches instantly and the cache is purged. | Rollback = re-deploy a previous Docker image tag via kamal deploy --version=<sha>. The DeployRelease model records which image tag each channel currently points to. A management command or API endpoint triggers the re-point + cache purge. | Kamal, custom Django admin action, Cloudflare API (cloudflare Python SDK) |
| 98 | Preview channels | firebase hosting:channel:deploy <name> creates an isolated Channel with its own URL (https://<channel>--<project>-<hash>.web.app). Each channel tracks its own Release history. Channels can be set to auto-expire (max 30 days). GitHub Action creates per-PR channels automatically, posts URL as PR comment. | Per-PR Docker Compose stack (app + Caddy) deployed to a staging VPS. Caddy on-demand TLS issues a Let's Encrypt cert for pr-123.preview.yourservice.com. A DeployChannel model tracks channel name, subdomain, expiry, and current image tag. GitHub Actions workflow calls a Django API to provision/deprovision. Coolify automates this entirely. | Caddy (on-demand TLS), Docker Compose, Coolify, GitHub Actions, django-background-tasks or Celery for cleanup |
| 99 | Custom domains + auto SSL | User adds domain in Firebase Console. Firebase presents a DNS TXT record (ACME challenge) to prove ownership. Once verified, Firebase provisions a Let's Encrypt cert via ACME DNS-01 challenge. SSL is renewed automatically. Supports www + apex. CAA records should be cleared. | Caddy with on-demand TLS: an /ask endpoint in Django verifies the domain is in the HostingDomain table before authorizing cert issuance. Caddy issues a cert on first TLS handshake via Let's Encrypt (DNS-01 via Cloudflare plugin for wildcards, HTTP-01 for custom CNAME domains). Cert storage in Docker volume or distributed via Redis. | Caddy (caddy-dns/cloudflare plugin), acme.sh, certbot with cloudflare plugin (alternative), HostingDomain Django model |
| 100 | Rewrites (SPA fallback, Cloud Functions/Cloud Run proxy) | firebase.json rewrites array: glob patterns matched in order; unmatched URLs can be rewritten to a Cloud Function or Cloud Run service URL. SPA rewrite: source='**' destination='/index.html'. Processing order: exact file > redirect > rewrite. | Nginx location blocks or Caddy handle blocks with try_files for SPA fallback. For function-style dynamic endpoints, Nginx proxies /api/** to Django/Gunicorn. Rules stored in a HostingRewrite model, rendered into Nginx config template on deploy (via Jinja2 + nginx -s reload), or use Caddy's JSON API for hot-reload without restart. | Nginx, Caddy, Jinja2 for config templating, django-ninja or DRF for API, Celery for async config reload |
| 101 | Redirects (301/302, glob patterns) | firebase.json redirects array: source glob, destination URL, HTTP status code (301/302). Capture groups supported (:segment, *). Evaluated before rewrites. Firebase's Superstatic library implements the routing logic. | django-redirects (fabiocaccamo/django-redirects) for DB-backed redirects with admin UI. For high-volume / edge redirects, Nginx map + return directives generated from a HostingRedirect model. Celery task regenerates nginx.conf and reloads on redirect CRUD operations. | django-redirects, Nginx map directives, Caddy redir directive |
| 102 | Custom response headers (per-URL glob) | firebase.json headers array: source glob matched to an array of {key, value} header objects. Applied to both static files and rewrites. Commonly used for HSTS, X-Frame-Options, Content-Security-Policy, CORS, Cache-Control overrides. | Django SecurityMiddleware covers HSTS, X-Frame-Options, X-Content-Type-Options. For per-URL glob header rules, store in HostingHeader model and render to Nginx add_header directives or Caddy header blocks. CORS handled by django-cors-headers. CSP by django-csp. | django-cors-headers, django-csp, SecurityMiddleware (built-in), Nginx add_header, Caddy header |
| 103 | cleanUrls (drop .html extension) | Superstatic strips .html from served URLs — /about.html is served at /about. Controlled by cleanUrls: true in firebase.json. | Nginx try_files $uri $uri.html $uri/ = 404; or WhiteNoise WHITENOISE_INDEX_FILE = True + custom middleware that strips .html and 301-redirects. Django's CommonMiddleware handles APPEND_SLASH similarly. | WhiteNoise (WHITENOISE_INDEX_FILE), Nginx try_files, Django CommonMiddleware |
| 104 | trailingSlash normalization | Superstatic trailingSlash: true\|false\|undefined. true always appends slash, false always removes it, undefined = smart mode (directory -> add slash, file -> remove). | Django APPEND_SLASH = True (default) + CommonMiddleware handles the trailing slash append case. For removal, custom middleware or Nginx rewrite rule: rewrite ^/(.*)/$ /$1 permanent; | Django CommonMiddleware (APPEND_SLASH), Nginx rewrite |
| 105 | i18n rewrites (Accept-Language / country routing) | firebase.json i18n.root points to a directory of language/country sub-folders. Firebase reads Accept-Language and x-country-code headers to serve the best-matching locale folder transparently, with fallback to the root. | Django i18n middleware (LocaleMiddleware) + django.conf.urls.i18n.i18n_patterns() for URL-prefix routing. For header-based (no URL change) routing, custom middleware reading Accept-Language to serve locale-specific content from S3 prefix or template directory. | django.middleware.locale.LocaleMiddleware, django-localflavor (country data), Django i18n built-in |
| 106 | Cloud Run / Functions integration for dynamic content | firebase.json rewrite with run.serviceId routes matched URLs to a Cloud Run service via a Google-internal service mesh. The CDN can cache Cloud Run responses if they set appropriate Cache-Control headers (s-maxage). No cold start penalty when fronted by CDN cache hits. | Nginx upstream block pointing to Gunicorn/Uvicorn container. For serverless-style isolation, Django app runs in Cloud Run / Fly.io with Caddy fronting it. Cache Cloud Run-equivalent responses using Varnish or Cloudflare Cache Rules keyed on URL + headers. | Gunicorn, Uvicorn, Nginx upstream, Varnish, Cloudflare Cache Rules |
| 107 | CDN cache management (purge on deploy, manual PURGE) | On every firebase deploy, Firebase issues a global CDN cache purge for all paths on the site. An undocumented PURGE HTTP method allows per-URL manual purge. Static file fingerprinting means most files never need purging (URL changes = new cache entry). HTML gets purged fully on deploy. | Cloudflare Cache Purge API (POST /zones/{zone}/purge_cache) called from a post-deploy hook. For per-file purge, store a mapping of URL -> cache tag in Redis and call Cloudflare's cache-tag purge. django-cloudflare-push or a custom Celery task handles this. | cloudflare (PyPI: cloudflare), Celery, Redis (cache tag store) |
| 108 | Hosting REST API (programmatic deploy) | Full REST API: POST /sites/{site}/versions, POST /versions/{version}/populateFiles (SHA256 hash list), POST /upload/{upload_url} (file bodies for new hashes only), PATCH /versions/{version} status=FINALIZED, POST /sites/{site}/releases {versionName}. Hash-based deduplication means only changed files are uploaded. | DRF or django-ninja API endpoints mirroring the same flow: POST /api/hosting/versions/, POST /api/hosting/versions/{id}/files/ (with SHA256 dedup against MinIO), PATCH /api/hosting/versions/{id}/finalize/, POST /api/hosting/releases/. File storage in MinIO with object-level versioning. | django-ninja or djangorestframework, django-minio-backend, MinIO (SHA256-keyed objects) |
| 109 | Multiple sites per project | One Firebase project can host multiple sites (e.g., app.example.com + docs.example.com). Each site has independent channels, versions, releases, and custom domains. firebase.json can target a specific site with firebase use --add. | HostingSite model (FK to Project). Each site gets its own Caddy virtual host config block. Channels and custom domains are site-scoped. Admin UI groups resources by site. Nginx/Caddy server_name per site. | Django multi-tenancy via FK scoping, Caddy dynamic JSON config API, Nginx virtual hosts |
| 110 | Firestore realtime listeners (onSnapshot) | gRPC bidirectional streaming (ListenRequest/ListenResponse) from client to Firestore frontend servers. Server-side reverse query matcher registers the live query, receives change events from an internal changelog/fan-out bus, evaluates Security Rules, and pushes DocumentChange / QueryResultSnapshot deltas back to the client. | Django Channels AsyncWebsocketConsumer per connection; per-document or per-query group in Redis channel layer; Postgres LISTEN/NOTIFY or CDC triggers fire into a bridge worker that calls group_send. | django-channels>=4.0, channels-redis>=4.2, psycopg[async]>=3.1, daphne>=4.1 (ASGI server) |
| 111 | Firestore fan-out (reverse query matching) | When a document write lands, Firestore's subscription service runs a reverse query match: it searches all registered live queries to find those that match the mutated document, then fans out the delta to the relevant frontend servers which push to subscribed clients. Runs across replicated components for HA. | On each document change event, look up all active subscription records in Redis (key: `subs:{collection}:{doc_id}` → set of channel group names), then call channel_layer.group_send for each matching group. For query subscriptions, maintain a subscription registry with filter metadata and evaluate filters in Python before fanning out. | redis-py>=5.0, channels-redis, custom SubscriptionRegistry in Redis HSET/SADD structures |
| 112 | RTDB realtime sync (WebSocket JSON protocol) | RTDB uses a single persistent WebSocket per client. The wire protocol is a proprietary JSON framing (`t: 'd'` for data, `t: 'c'` for control). The server is a stateful cluster (not Firestore's shared-nothing model) where each node owns a shard of the tree. All reads/writes for a path route to the owning node. Mutations are logged and fanned out to subscribed clients synchronously within that shard. | Simpler to replicate than Firestore: single Django Channels consumer per client, subscribe to Redis groups keyed by path prefix. Writes go through DRF API → save to Postgres → pg_notify → async bridge → Redis group_send → all consumers listening on that path. | django-channels>=4.0, channels-redis>=4.2, psycopg[async]>=3.1 |
| 113 | Connection management, reconnect & exponential backoff | RTDB and Firestore SDKs both maintain a persistent connection with automatic reconnection. RTDB uses truncated binary exponential backoff (1s → 2s → 4s … max 30s) with jitter. Firestore's gRPC channel uses CHANNEL_IDLE timeout and reconnects with the same strategy. The SDK re-establishes subscriptions transparently after reconnect. | Client-side JS/mobile SDK must implement reconnect with backoff. On the server side, Django Channels handles dropped WebSocket connections automatically (the consumer's websocket_disconnect fires). On reconnect the client sends its last-seen cursor/token; the server replays missed events from a Postgres-backed event log or rehydrates from current DB state. | Client: reconnecting-websocket (npm) or native retry loop. Server: no special library needed — Channels handles it. For event replay: custom EventLog model in Postgres with cursor field. |
| 114 | Presence system (RTDB .info/connected + onDisconnect) | RTDB: /.info/connected is a synthetic boolean updated by the server when the WebSocket handshake completes or drops. onDisconnect() registers server-side hooks that fire atomically when TCP drops. Server timestamps via ServerValue.TIMESTAMP prevent clock skew. Firestore has no native presence — Google's own docs recommend bridging through RTDB + Cloud Functions. | On WebSocket connect: write presence record to Redis HSET `presence:{room}` with TTL (e.g. 30s). Extend TTL via heartbeat every 20s. On Channels disconnect (websocket_disconnect): delete key and broadcast a `user.left` event to the room group. For server-authoritative timestamps use Django's timezone.now() on the server side. Use Redis EXPIRE for dead-client cleanup. | redis-py>=5.0 (HSET/EXPIRE/HDEL), channels-redis, django-channels. Optional: django-presence (thin wrapper) or custom PresenceManager class. |
| 115 | Optimistic local writes + server reconciliation | Firestore SDK applies writes immediately to the local cache (IndexedDB on web, SQLite on mobile) and marks them with `hasPendingWrites: true`. The mutation is queued in an outbox. On server ACK, the pending flag clears. On server rejection or conflict, the SDK raises an error and reverts local state. Snapshots include a `fromCache` metadata flag. Multiple pending writes to the same document are applied as a single ordered batch. | Client SDK maintains a local IndexedDB/SQLite store (or use RxDB / WatermelonDB as the local cache layer). Writes are applied locally immediately and enqueued in a local outbox table. On reconnect/flush the client POSTs the batch to the Django API; the server processes and returns the canonical state. Client merges server response over local state. Expose `pending: true` in the local document model. | Client: RxDB (rxdb, npm) or WatermelonDB for local persistence. Server: standard Django REST Framework, no special library. Celery (celery>=5.3) for async mutation processing at scale. |
| 116 | Offline queue + conflict resolution (last-write-wins / CRDT) | Firebase's default is last-write-wins (LWW): the final mutation received by the server wins, regardless of when it was generated on the client. For RTDB transactions use optimistic concurrency (read-hash compare-and-swap). For Firestore transactions, reads are snapshotted and the transaction retries up to 5 times on contention. There is no built-in CRDT support — developers must implement merge logic in Cloud Functions or client code. | Implement LWW with a `updated_at` + `client_version` (Lamport clock or monotonic integer per device) column. On conflict (server version > client version), return 409 with canonical state; client re-applies or discards. For true CRDT use `python-crdt` (pure-Python) or store CRDT state blobs (Yjs Y.Doc via y-py). Django signal or DRF serializer validates version before save. | py-crdt>=0.4 (pure Python CRDT), ypy>=0.6.2 (Yjs CRDT bindings for Python), django-concurrency>=2.5 (optimistic locking), djangorestframework>=3.15 |
| 117 | Change Data Capture (CDC) / server-side change propagation | Firestore uses an internal changelog (Google Spanner's change log / TrueTime ordering). When a document is committed, the change event flows through an internal pub/sub bus to subscription handlers. There is no user-visible Kafka or WAL — it's all proprietary. Supabase Realtime replicates this pattern using Postgres logical replication WAL slot polling. | Option A (simple): Postgres LISTEN/NOTIFY via trigger — on INSERT/UPDATE/DELETE fire pg_notify('doc_changes', json_build_object('id', NEW.id, 'collection', TG_TABLE_NAME)::text). An async Python listener (psycopg3 async connection) picks up notifications and calls channel_layer.group_send. Option B (scalable): Debezium Server (no Kafka dependency, supports HTTP/Redis/SQS sinks) reads Postgres WAL and posts change events to Redis Streams; a Django Channels worker consumes the stream and fans out. Option C (lightest): Django post_save/post_delete signals call async_to_sync(channel_layer.group_send) directly. | Option A: psycopg[async]>=3.1. Option B: Debezium Server 2.7+ (JVM, Docker), redis-py Streams. Option C: django-channels, asgiref. All options: channels-redis>=4.2 |
| 118 | Per-query subscriptions (not just per-document) | Firestore's reverse query matcher runs registered queries (with where/orderBy/limit clauses) against each incoming document change to determine which live queries are affected. This is the hardest part of Firestore to replicate — a single document write may match thousands of registered queries across millions of clients. | Store active query subscriptions in Redis as serialized filter specs (HSET `query_subs:{collection}` field=`{sub_id}` value=`{filters_json, group_name}`). On each document change event, load all query_subs for the collection and evaluate each filter spec in Python (using a small DSL or Django Q objects against a dict). Fan out to matching group names. For high scale: shard by collection, use Lua scripts in Redis for atomic lookup, or offload to a dedicated matching worker. | redis-py>=5.0 (HSET, HSCAN), channels-redis, custom QueryMatcher class. For complex filters: pyparsing>=3.1 to build a query DSL parser. |
| 119 | Firestore metadata: hasPendingWrites, fromCache, snapshotListenOptions | Every Firestore snapshot has a SnapshotMetadata object: `hasPendingWrites` (true if local mutations not yet ACKed by server), `fromCache` (true if data came from local cache, not server). includeMetadataChanges option lets you receive snapshots that only differ in metadata (e.g. when a pending write is confirmed). | Include a `_meta` field in every WebSocket message payload: `{"pending": bool, "from_cache": bool, "server_time": ISO8601}`. On the client, track which document IDs are in the local outbox to compute `pending`. `from_cache` is true when the client is disconnected and returning stale local data. Expose `includeMetadataChanges` equivalent as a subscribe option. | No special library — implement as part of the WebSocket message envelope schema. |
| 120 | FCM — Android push (data & notification messages) | App server sends HTTP v1 POST to FCM backend (OAuth2 bearer token auth). FCM holds a persistent TCP connection to Android devices via Google Play Services (GMS). HIGH-priority messages wake the device from Doze. Stores messages up to 28 days TTL. Returns per-token success/failure synchronously. | firebase-admin SDK (`send_each_for_multicast`) or raw HTTP v1 with google-auth tokens. Celery task fans out to device tokens in 500-token chunks. PushDevice model stores registration_id + platform. Invalid tokens (UNREGISTERED error) deactivated immediately. | firebase-admin>=6.5, google-auth>=2.29, celery[redis]>=5.4 |
| 121 | FCM → APNs routing for iOS | FCM accepts an iOS registration token + ApnsConfig payload. Internally, FCM signs a JWT with your Apple .p8 key and POSTs to APNs HTTP/2 endpoint (api.push.apple.com:443). APNs delivers via its persistent TLS connection to the device. FCM never directly touches iOS devices; APNs is the last-mile carrier. Certificate-based APNs auth deprecated 2024 — JWT token auth is mandatory. | aioapns async HTTP/2 APNs client called from a Celery task via asyncio.run(). Requires Apple Developer account, .p8 AuthKey file, Team ID, Key ID, and bundle ID. Token-based auth (JWT) only — no certificate path needed. | aioapns>=3.2, celery[redis]>=5.4 |
| 122 | Web Push (browsers) | FCM supports Web Push via the webpush config block. Client calls pushManager.subscribe() with VAPID public key → gets PushSubscription (endpoint + p256dh + auth). FCM encrypts payload per RFC 8291, signs VAPID JWT per RFC 8292, POSTs to browser vendor endpoint (Chrome→FCM, Firefox→Mozilla Autopush, Safari→Apple). Service worker receives push event and shows notification. | pywebpush sends encrypted VAPID-signed POST to the browser's push endpoint. VAPID keys generated once with py-vapid. PushDevice model stores endpoint + p256dh + auth. 410/404 responses mean subscription expired — deactivate device. | pywebpush>=2.0, py-vapid>=1.9, celery[redis]>=5.4 |
| 123 | FCM Topics (pub/sub) | Devices call subscribeToTopic() on the client SDK → FCM backend stores topic→[tokens] mapping. Server sends to /topics/weather. FCM fans out asynchronously, not instantaneous. Limits: 2,000 topics/device, 1,000 concurrent fan-outs/project, 3,000 QPS topic subscription management. Topic fan-out optimized for throughput not latency. | TopicSubscription model (topic + device FK, unique together). subscribe/unsubscribe via DRF action endpoint. dispatch_to_topic() queries subscriptions, groups by platform, splits into 500-token Celery task chunks, dispatches as a Celery group for parallel execution. | celery[redis]>=5.4, djangorestframework>=3.15 |
| 124 | FCM Conditions (boolean topic expressions) | FCM supports condition strings like "'dogs' in topics \|\| 'cats' in topics" evaluated server-side against topic subscription store. Allows cross-topic targeting without pre-computing audience lists. | Parse condition string server-side (regex/parser), query TopicSubscription for matching topic names with Q objects (OR/AND logic), union device sets, dispatch fan-out. No native condition DSL — implement simple OR/AND parser over topic names. | django ORM Q objects, no extra pip dependency |
| 125 | Device token management & stale token cleanup | Client SDK auto-refreshes tokens on reinstall/data clear and fires onTokenRefresh callback. FCM marks tokens stale after 60 days inactivity, expired at 270 days. Returns UNREGISTERED error on send to invalid token. | PushDevice.registration_id unique; update_or_create on register to handle token rotations. Celery Beat daily task deactivates devices with last_used_at older than 60 days. Synchronous deactivation on UNREGISTERED/BadDeviceToken/410 responses during send. | django-celery-beat>=2.6, celery[redis]>=5.4 |
| 126 | Collapse keys & message deduplication | collapse_key groups messages; FCM keeps only the latest per collapse key per device when offline (max 4 distinct collapse keys simultaneously). Notification messages are always collapsible. Data messages need explicit collapse_key. | Pass collapse_key to FCM via AndroidConfig.collapse_key. For APNs use apns-collapse-id header. For WebPush use Topic header. No Django-level deduplication needed — pass through to platform APIs. | firebase-admin, aioapns, pywebpush (pass-through platform params) |
| 127 | FCM message priority & TTL | HIGH priority wakes device immediately (counts against Android battery optimization quota). NORMAL deferred. TTL 0 = discard if device unreachable. TTL max = 2,419,200s (28 days). Per-platform override in ApnsConfig (apns-priority header) and WebpushConfig. | Set priority='high' in AndroidConfig, apns-priority: '10' in APNs headers, TTL header in WebPush. Expose as optional params in dispatch API. | firebase-admin AndroidConfig/ApnsConfig/WebpushConfig classes |
| 128 | Notifications Composer (Firebase Console campaign builder) | Visual UI in Firebase console: compose notification, pick target (topic/segment/A-B test), schedule (immediate/timezone-local), add analytics tracking. Integrates with Firebase Analytics audiences and Firebase A/B Testing. Sends via same FCM HTTP v1 API internally. | Django Admin with NotificationCampaign model + custom admin actions. Alternatively, build a simple React/Vue admin frontend consuming the DRF API. Celery Beat handles scheduling. No built-in A/B testing — integrate with a feature-flag service (Waffle, Flagsmith) for variants. | django.contrib.admin, django-celery-beat>=2.6 |
| 129 | Firebase In-App Messaging (FIAM) — triggered UI campaigns | SDK polls Firebase backend once per 24h using Firebase Installation ID (not FCM token). Downloads active campaigns list. On each Analytics event, SDK checks local campaign list for trigger match. If match found and frequency cap not hit, renders message (card/banner/modal/image-only) as a native overlay. Reports impressions/clicks back to Firebase. SDK suppresses display when another message is showing. | NotificationCampaign model with trigger_event, message_type, frequency cap fields. GET /api/inam/campaigns/?event=app_open returns eligible campaigns (server filters by status, schedule, frequency cap). Client SDK (mobile/web) caches and evaluates triggers locally. POST /api/inam/impressions/ records shown/clicked events. Django Admin = campaign composer. | djangorestframework>=3.15, django ORM (no extra push deps needed — FIAM is poll-based) |
| 130 | FIAM message types (Card, Modal, Banner, ImageOnly) | Firebase ships a default display SDK that renders 4 native message layouts. Developers can also implement a custom display by providing their own rendering library conforming to the Firebase FIAM display protocol. | message_type field on NotificationCampaign ('card','banner','modal','image_only'). Rendering is 100% client-side — the mobile/web app renders the appropriate component based on message_type. Django only serves the campaign JSON payload. Ship a React Native / Flutter / Web component library that reads the payload and renders the layout. | No backend library needed — client-side rendering |
| 131 | FIAM frequency capping & suppression | Per-campaign impression limits configurable in the console. Global cap: one message per 24h per user by default. Programmatic suppression: call setMessageDisplaySuppressed(true) to prevent display (e.g., during onboarding, checkout). Suppression resets on app restart. | CampaignImpression model tracks shown_at per user per campaign. GET /api/inam/campaigns/ server-side excludes campaigns where impression count in last cooldown_seconds exceeds max_impressions_per_user. Client-side suppression flag stored in local state/AsyncStorage and reset on app open. | django ORM annotations (Count, filter by date range) |
| 132 | FCM Device Groups (legacy) | Server-managed groups of tokens identified by a notification_key. Sending to the group reaches all tokens in it. Largely superseded by topics. Managed via a separate Instance ID server API (itself deprecated in favor of HTTP v1). | Model a device group as a named tag/label on PushDevice (ManyToMany). Use the same topic fan-out dispatch logic. No need to reimplement the notification_key concept — topics cover the same use case cleanly. | django ORM ManyToMany, existing dispatch infrastructure |
| 133 | Google Analytics for Firebase — Event Collection & SDK | Client SDK batches events (~1 hr) into SQLite, uploads to Firebase ingestion endpoints. DebugView bypasses batching in dev mode. Events are GA4-schema: event_name + up to 25 typed params + user_properties. Auto-collected events (app_open, session_start, first_open, screen_view) are fired by SDK hooks. | DRF ingest endpoint (POST /v1/events/batch) + Redis Stream or Kafka topic + Celery consumer batch-writing to ClickHouse. Client SDKs can be thin wrappers reusing the same JSON payload shape. | djangorestframework, clickhouse-connect, django-clickhouse-backend, celery, redis, confluent-kafka-python |
| 134 | Google Analytics for Firebase — Audiences & Funnels | Audiences are server-side computed cohorts over user property + event sequences (up to 10 steps). Evaluated periodically; audience membership gates Remote Config personalisation and FCM targeting. Funnels built in the Firebase/GA4 console over BigQuery-backed aggregations. | Materialized queries in ClickHouse (funnels via window functions or ClickHouse funnel functions). Audience membership stored in Postgres and cached in Redis. PostHog (self-hosted) ships all of this out of the box. | clickhouse-connect, celery (periodic audience computation), posthog (self-hosted, OSS) |
| 135 | BigQuery Export (Analytics) | Daily shard tables events_YYYYMMDD + real-time events_intraday_YYYYMMDD via BigQuery streaming inserts. Schema: event_date, event_timestamp, event_name, event_params (REPEATED RECORD with {key, value: {string_value, int_value, float_value, double_value}}), user_properties (same shape), user_pseudo_id, device, geo, app_info, traffic_source. 1M event/day cap on free tier; GA360 unlimited. | ClickHouse is the direct equivalent: columnar, compressed, millisecond-latency on billions of rows. events table with Nullable typed columns replaces the nested BigQuery RECORD type. Grafana or Metabase sits on top for dashboards. | clickhouse-connect, django-clickhouse-backend, metabase (Docker), grafana |
| 136 | Firebase Crashlytics — Crash & ANR Reporting | SDK wraps JVM/ObjC/NDK exception handlers. On crash: captures stack trace, device metadata, custom keys/logs, breadcrumbs; writes to on-disk cache. On next launch, uploads protobuf payload to Firebase ingestion endpoint. Server-side symbolication service maps obfuscated frames back to source using uploaded ProGuard/dSYM/symbol files. ANRs detected via Android ANRWatchdog or system signals. | GlitchTip (Django + Postgres + Celery + Redis, 4 containers, 512 MB RAM) or self-hosted Sentry (20+ container stack with Kafka + ClickHouse + Symbolicator). Both speak the Sentry SDK wire protocol — change DSN URL only. Mobile apps use sentry-java / sentry-cocoa / sentry-dart pointing at your instance. | glitchtip (Docker Compose), sentry-sdk (Python), sentry-java, sentry-cocoa, sentry-dart, sentry-javascript |
| 137 | Firebase Crashlytics — Symbolication (ProGuard / dSYM / NDK) | Gradle plugin task uploadCrashlyticsSymbolFile uploads stripped ELF symbols and ProGuard mapping files to Firebase symbol server. Firebase's server-side Symbolicator resolves frame addresses. 2025 enhancement: also ingests Android tombstones for richer native crash context, shows symbolicated + raw views side-by-side. | Sentry Symbolicator (open-source Rust service by Sentry). Accepts minidumps, Apple crash reports, source maps. Self-hosted Sentry includes it; GlitchTip has basic symbolication, outsources heavy lifting to sentry-cli upload. Upload ProGuard/dSYM via sentry-cli or CI step. | getsentry/symbolicator (Docker), sentry-cli, sentry-java Gradle plugin |
| 138 | Firebase Crashlytics — BigQuery Export | Dataset firebase_crashlytics; per-app tables named by package (com_example_app_ANDROID). Columns: platform, bundle_identifier, version, os_version, device_model, error_type (CRASH/ANR/NON_FATAL), issue_id, issue_title, issue_subtitle, exception.type, exception.object, exception.frames (REPEATED RECORD: file, line, symbol), breadcrumbs, custom_keys, sessions.  _REALTIME suffix tables for streaming export. | Sentry / GlitchTip already persists all this in Postgres. For BigQuery-parity analytics, forward Sentry issues via Sentry's webhook/integration to ClickHouse or directly query Sentry's Postgres via read replica. | sentry-sdk, psycopg2 (read replica queries), clickhouse-connect (forwarding) |
| 139 | Firebase Performance Monitoring — Automatic Traces | SDK instruments app lifecycle via reflection/bytecode (Gradle transform plugin on Android). Auto traces: _app_start (cold/warm/hot), _app_in_foreground, _app_in_background, _screen_rendering (per Activity: slow_rendering >16 ms, frozen_frames >700 ms). Traces uploaded in batches every ~30 s. Each trace: name, start_time, duration_us, custom_attributes (up to 5), custom_metrics. | opentelemetry-instrumentation-django auto-instruments HTTP views. For mobile, Sentry's performance SDK (sentry-java / sentry-cocoa) captures app start and screen transitions as transactions. For backend Django services: spans map directly to Firebase traces. | opentelemetry-instrumentation-django, opentelemetry-sdk, opentelemetry-exporter-otlp, sentry-java (mobile perf) |
| 140 | Firebase Performance Monitoring — Network Request Traces | Gradle plugin adds OkHttp interceptor and NSURLSession swizzle on iOS. Captures: URL pattern, HTTP method, response_code, request_payload_bytes, response_payload_bytes, response_time_ms. Groups by URL pattern (manual or auto-detected). Custom network traces for libraries not auto-intercepted. | OpenTelemetry opentelemetry-instrumentation-requests or opentelemetry-instrumentation-httpx for outbound; for inbound DRF requests opentelemetry-instrumentation-django captures all automatically. Export to Grafana Tempo (traces) + Prometheus (metrics) + Loki (logs). | opentelemetry-instrumentation-requests, opentelemetry-instrumentation-httpx, opentelemetry-instrumentation-django, grafana-tempo, prometheus |
| 141 | Firebase Performance Monitoring — Custom Traces & Metrics | Developer wraps code with startTrace()/stopTrace() API; can call putMetric(name, value) and putAttribute(key, value) within a trace. Custom traces visible in Performance console with attribute-based filtering (app_version, country, device). Max 5 custom metrics per trace, 5 custom attributes. | OpenTelemetry manual spans: tracer.start_as_current_span('my-operation'). Custom metrics via opentelemetry-sdk metrics API (Counter, Histogram). Prometheus remote_write or OTLP exporter forwards to Grafana. | opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp, prometheus-client |
| 142 | Firebase Performance Monitoring — BigQuery Export | Separate dataset from Analytics export. Tables per app. Each row = one performance event: trace_type (DURATION_TRACE / NETWORK_TRACE / SCREEN_TRACE), trace_name, start_time, duration_us, country, app_version, os_version, sdk_version, custom_attributes (REPEATED key-value), for network traces: url_pattern, http_method, http_response_code, request_payload_bytes, response_payload_bytes. | Grafana Tempo stores all spans; query via TraceQL. For BigQuery-style dumps, export from Tempo or from OTLP collector to ClickHouse (opentelemetry-collector ClickHouse exporter). SigNoz bundles ClickHouse as trace store natively. | grafana/tempo, signoz/signoz (Docker), otel-collector-contrib (clickhouse exporter) |
| 143 | Firebase DebugView | Enable on Android: adb shell setprop debug.firebase.analytics.app <pkg>. On iOS: launch arg -FIRAnalyticsDebugEnabled. SDK switches from 1-hour batching to near-instant upload. Firebase console DebugView shows: Seconds column (last 60 s), Minutes column (last 30 min), right panel (top events + current user properties). Identifies a single device by installation ID for filtering. | DRF ingest endpoint accepts a X-Debug-Mode: true header → events skip Kafka/Celery and write synchronously to a debug_events ClickHouse table or Redis list. A lightweight Django Channels WebSocket view streams events in real time to a browser dashboard. | channels, channels-redis, djangorestframework, clickhouse-connect |
| 144 | Remote Config — server-controlled parameters | Cloud key-value store (JSON template, up to 3 000 params). Client SDKs fetch the full resolved template over HTTPS, cache locally with a default 12-hour TTL (fetch throttled to 5 fetches / hour in debug mode), then activate on next launch or explicit activate() call. Server-side SDK downloads the raw template and evaluates conditions in-process per request. | DRF endpoint returning a JSON key-value map per client; PostgreSQL stores parameters + conditions; Redis caches the resolved template per-environment; clients poll with ETag/If-None-Match or receive real-time push via Django Channels WebSocket. | djangorestframework, django-redis, channels, psycopg2-binary; or deploy Flagsmith (pip install flagsmith) as a sidecar |
| 145 | Remote Config — conditions & targeting (app version, OS, language, country, audience, custom signals, random-percentile) | Conditions are ordered expressions evaluated top-to-bottom; first TRUE condition wins. Rule atoms: app.version (semver comparisons), app.audiences (GA4 audience membership), app.userProperty (Analytics user property), device.os, device.language, device.country, app.firebaseInstallationId (allowlist), app.customSignal (client-supplied key-value), percent (HMAC seed hashed to 0–100 float, supports named seeds for independent bucketing). All evaluated server-side on each fetch. | Condition rows in PostgreSQL: type enum (version_match \| language \| country \| user_property \| custom_signal \| random_percent \| segment), operator, value. Evaluation function in Python: for random_percent, use HMAC-SHA256(seed + installation_id) % 100; for segments, join against a precomputed UserSegment table. Flagsmith's identity+trait system covers custom signals natively. | Flagsmith (Django API, BSD-3); or custom: hmac (stdlib), django-countries, user_agents |
| 146 | Remote Config — real-time config (instant push on publish) | Client opens a persistent WebSocket (or long-poll HTTP/2) to the Remote Config real-time backend. When a new template is published, the server sends an invalidation message; the client SDK auto-fetches and calls the registered listener callback, bypassing the normal fetch cache/TTL. Enabled via addOnConfigUpdateListener() (iOS/Android) or realtime listener (Web). | Django Channels consumer: client connects via WebSocket (ws://config/stream). On template publish (admin save signal), call channel_layer.group_send('config', {'type': 'config.updated', 'version': v}); consumer forwards the nudge; client re-fetches over REST. For mobile, a push notification (FCM/APNs) can serve as the invalidation signal. | channels>=4, channels-redis, daphne (ASGI server); or Server-Sent Events via django-eventstream |
| 147 | Remote Config — percent-rollouts (gradual feature release with control group) | A rollout is a named Remote Config condition using the percent operator with a named seed. Firebase assigns equal-sized control and enabled groups; if you expand the rollout %, users in prior groups stay in their original assignment. Max 50% for enabled group unless rolling to 100%. Monitored via Crashlytics crash rates and GA4 conversion metrics side-by-side. Counts against the 24 simultaneous A/B-test+rollout limit. | A Rollout model (name, seed_key, enabled_pct, control_pct, status). evaluate(installation_id) returns 'enabled' \| 'control' \| 'holdout' via HMAC bucketing. A Celery periodic task computes Crashlytics-equivalent crash rates from error events and flags the rollout for review. django-waffle's percent field does the same thing with cookies; Flagsmith's percentage split strategy is a direct equivalent. | django-waffle (pip install django-waffle); Flagsmith; or custom + celery + django-dramatiq for async metric computation |
| 148 | A/B Testing — Remote Config experiments | Experiment defines: targeting (app version, country, language, GA4 audience, user property, % exposure), variants (control + up to N treatment arms each with Remote Config overrides), primary goal metric (GA4 event or predefined: purchase revenue, retention, crash-free users, ad revenue), up to 5 secondary metrics. Variant assignment: HMAC(experiment_id + firebase_installation_id) mod 100 mapped to variant buckets by weight. Assignment is sticky for experiment lifetime even if user properties change. Stats: frequentist (p-value < 0.05 significance) plus Bayesian (probability-to-beat-baseline, credible intervals). Results refresh daily. Up to 300 total experiments per project, 24 running at once. | Experiment → Variant → Assignment tables in PostgreSQL. Assignment on first encounter: HMAC(experiment_id + user_id) % 100 → variant bucket. Events logged to ExperimentEvent(experiment, variant, user, event_name, value, ts). Celery Beat task runs nightly stats: scipy.stats.ttest_ind for frequentist, or Bayesian Beta-Binomial conjugate via pymc / scipy. GrowthBook self-hosted is the full-featured OSS replacement (REST API, Python SDK, React SDK, warehouse queries). | GrowthBook (docker-compose, MIT); or custom: scipy, pymc, numpy + django-rest-framework + celery |
| 149 | Firebase Dynamic Links (shut down 25 Aug 2025) | DEAD SERVICE as of 25 Aug 2025 — all page.link and custom-domain Firebase Dynamic Links return HTTP 404. Was a URL shortener + smart router: on click, server detected platform (iOS/Android/web), redirected to App Store / Play Store / fallback URL, and passed the deep-link payload as a query param. Deferred deep linking stored the payload server-side keyed to a click ID, matched to the install via Play Install Referrer (Android, deterministic) or probabilistic fingerprinting (IP+UA+screen-res, iOS). | 1) Platform-native: serve /.well-known/assetlinks.json (Android App Links) and /.well-known/apple-app-site-association (iOS Universal Links) from a Django view — no app install needed for already-installed users. 2) Smart redirect: a Django view inspects User-Agent, redirects to Play Store / App Store / web fallback with deep-link param. 3) Deferred deep link: generate a click_id, store payload in Redis/PG, return it to Android via Play Install Referrer callback or iOS via clipboard paste on first launch. | django (views + TemplateResponse), whitenoise or nginx for .well-known static files; no extra pip packages required; Dub (open-source, MIT) or 1link.io as a hosted alternative |
| 150 | Deferred deep linking (post-install payload delivery) | Android: Play Install Referrer API gives the app the exact referrer URL string that was in the Play Store link — deterministic, ~98% match rate. iOS: no deterministic equivalent since iOS 14.5 ATT; probabilistic matching uses IP address + user-agent + screen resolution hashed server-side to a fingerprint, matched against click records within a time window. Both platforms can also use a clipboard paste approach (app checks clipboard on first launch for a magic token). | Click record endpoint: POST /links/click → store {click_id, deep_link_path, payload, ip, ua, screen_res, ts} in PostgreSQL, set Redis TTL 15min. Match endpoint: POST /links/match?method=referrer → lookup by click_id (Android) or POST /links/match?method=fingerprint → fuzzy match on ip+ua within 15min window (iOS fallback). Return payload JSON to app. Clipboard method: generate a short token, put it in the redirect URL's fragment, app reads clipboard and calls GET /links/token/{token}. | django, djangorestframework, django-redis, psycopg2-binary, python-ipware (for real IP extraction) |
| 151 | Firebase Predictions (legacy / effectively deprecated) | Applied Google's ML models to GA4 event streams to produce daily-refreshed user segments: will_churn (active last 7d, predicted to stop), will_spend (likely to make IAP), will_not_spend, top_spenders, predicted_ltv_bucket. Segments were available as Remote Config conditions and FCM targeting audiences. The 'new' Predictions product merged into GA4 Predictive Audiences (churn probability, purchase probability, predicted revenue — computed by Google's AutoML on GA4 data). Legacy Predictions can still be selected in the Firebase console but is deprecated and may be removed. | Celery Beat task (daily): query event aggregation tables → feature-engineer per-user engagement vectors → run scikit-learn LogisticRegression / XGBoostClassifier for churn / purchase propensity → write scores to UserPrediction table → upsert into Flagsmith identity traits or custom segment table for Remote Config-equivalent targeting. Light version: use simple heuristics (last_active_days, purchase_count, session_count) as a proxy. | celery, scikit-learn, xgboost (optional), pandas, psycopg2-binary; results fed back into Flagsmith traits or the custom RemoteConfig condition engine |
| 152 | Firebase Genkit — Flows | Strongly-typed, streamable server functions (defineFlow) that wrap LLM logic with Zod schemas, streaming via sendChunk, deployed as HTTP endpoints to Cloud Functions for Firebase or Cloud Run. Traces stored in Cloud Trace / Firestore. GA for Node.js (Feb 2025), Go (Sep 2025), Python alpha (Apr 2025). | Django async view or DRF APIView wrapping a Celery task; StreamingHttpResponse + django-async-sse for streaming chunks; Pydantic schemas for I/O validation; trace storage in PostgreSQL. | celery, redis, django-async-sse, pydantic, anthropic, litellm, opentelemetry-sdk |
| 153 | Firebase Genkit — Dotprompt | Prompt-as-code file format (.prompt) with YAML frontmatter declaring model, temperature, tools, input/output Picoschema, and Handlebars body. Prompts stored in the repo alongside code. | Prompt templates stored as Django model rows (or YAML files in a prompts/ directory), rendered with Jinja2 or Django templates, versioned via migrations or Git. | jinja2, django (Template engine), PyYAML |
| 154 | Firebase Genkit — Tool Calling / Agents | defineTool() registers typed tools; Genkit's generate() loop automatically calls tools when the model requests them. Middleware (May 2026) intercepts the model/tool/generate cycle for retries, approvals, logging. Multi-agent via ai.generate() calling other flows as tools. | Tool registry as Python dict of callables; Celery task chain for multi-step execution; anthropic SDK tool_use block for Claude's native function-calling loop; Django Channels for human-in-the-loop approval webhooks. | anthropic, celery, channels, pydantic |
| 155 | Firebase Genkit — RAG (Retrieval-Augmented Generation) | defineIndexer / defineRetriever / ai.retrieve() abstractions; plugins for pgvector, Pinecone, Chroma, Firestore, Vertex AI Vector Search; embedding via Vertex AI / Google AI embedder plugins. Two-stage retrieval with optional reranker. | pgvector extension on PostgreSQL; pgvector-python + Django ORM VectorField; embedding via anthropic (voyage-3) or google-generativeai embeddings; chunking + indexing as Celery tasks; retriever as a DRF utility function. | pgvector, pgvector-python, anthropic, google-generativeai, celery, langchain-text-splitters |
| 156 | Firebase Genkit — Observability & Dev UI | Traces exported to Cloud Trace / Firestore; Firebase Console AI monitoring dashboard; local Developer UI (web app) showing flow traces, model call inputs/outputs, latency. Genkit CLI for running/testing flows from terminal. | OpenTelemetry traces to Jaeger or Grafana Tempo; LiteLLM's built-in /ui admin panel for spend/request monitoring; django-silk or django-debug-toolbar for local inspection; management commands for CLI-style flow execution. | opentelemetry-sdk, opentelemetry-instrumentation-django, litellm, django-silk |
| 157 | Firebase AI Logic (Vertex AI in Firebase) — LLM Proxy Gateway | Firebase AI Logic API (firebasevertexai.googleapis.com) acts as a proxy: client SDK sends request → Firebase server validates App Check token → forwards to Vertex AI Gemini API or Google AI Gemini Developer API (with Firebase holding all API keys). Supports Gemini and Imagen models, multimodal input, streaming, function calling, grounding with Google Search, Live API (audio streaming), URL context, explicit context caching (April 2026). | A Django view that validates a client attestation token, then calls Anthropic or Gemini on the server, streaming the response back via StreamingHttpResponse. LiteLLM as the multi-provider backend (supports Claude claude-opus-4-8, claude-sonnet-4-6, claude-haiku-4-5, Gemini, etc.) with spend tracking and virtual keys. | litellm, anthropic, google-generativeai, djangorestframework, django-async-sse |
| 158 | Firebase AI Logic — App Check Attestation (incl. replay-attack protection May 2026) | Client SDK attaches an App Check token (generated by Play Integrity on Android, DeviceCheck on iOS, reCAPTCHA Enterprise on web) to every request. Firebase proxy validates it before forwarding. As of May 2026, tokens are single-use (replay-attack protection): each token is consumed on first use and rejected on any subsequent attempt. Token TTL configurable 5 min–7 days. | Custom DRF middleware: mobile clients obtain attestation receipts from Play Integrity / DeviceCheck / Apple App Attest, send them with requests; Django validates via pyattest / google-play-integrity library, then issues a short-lived signed HMAC token (or JWT with jti nonce tracked in Redis for single-use enforcement). | pyattest, djangorestframework-simplejwt, redis, cryptography |
| 159 | Firebase AI Logic — Server Prompt Templates (April 2026) | Prompt templates (Dotprompt format with {{history}} placeholder for chat) defined in Firebase Console server-side; client just passes templateId + parameter values. Templates can include tool schemas, model config, system instructions — never exposed to client. Supports chat sessions and function calling through templates. | PromptTemplate Django model with version, body (Jinja2), model_slug, config JSON, tool_schemas JSON; client sends template_id + params; Django renders and calls LLM. Allows hot-editing without redeploy. | jinja2, djangorestframework, anthropic, litellm |
| 160 | Firebase AI Logic — Hybrid On-Device / Cloud Inference (Sep 2025) | Firebase JS SDK auto-detects Gemini Nano availability in Chrome (via ML Kit Prompt API), falls back to cloud Gemini if unavailable. Developer sets preference; SDK switches transparently. | Client-side only: ship WebLLM / Chrome Prompt API detection logic in the JS client; Django backend is the fallback. No server-side Django component needed for on-device path. | N/A (client-side: @mlc-ai/web-llm or Chrome Prompt API) |
| 161 | ML Kit — On-Device Vision APIs (text recognition, face detection, barcode scanning, image labeling, object detection, pose detection, selfie segmentation) | Standalone Google ML Kit SDK (no Firebase project required since 2020); fully on-device, no network call, no cost. Uses TensorFlow Lite models bundled in the SDK. Separate bundled (model in APK/app) and unbundled (model downloaded on demand via Google Play Services) variants. SDK size reduced ~65% in recent releases. | Pure mobile-client concern: integrate google-mlkit-* packages on Android / MLKitVision on iOS. For server-side equivalents: Google Cloud Vision API or pytesseract (OCR), face_recognition, pyzbar (barcodes), TensorFlow Serving or ONNX Runtime with a pre-trained model. | pytesseract, Pillow, face_recognition, pyzbar, tensorflow-serving, onnxruntime (server-side); google-mlkit-* (mobile) |
| 162 | ML Kit — On-Device Language APIs (translation, language ID, smart reply) | On-device translation (100 language pairs), language ID, and smart reply via TFLite models. Models downloaded lazily via Google Play Services. Smart Reply generates contextual short suggestions for chat without any server call. | Server-side: argostranslate or LibreTranslate (self-hosted) for translation; langdetect / lingua-py for language ID; no direct Django equivalent for smart reply (train a custom model or prompt a small LLM). On-device: keep using ML Kit in the mobile client. | argostranslate, langdetect, lingua-py, transformers (for smart-reply fine-tune) |
| 163 | ML Kit — GenAI APIs (Gemini Nano on-device: Prompt API, Image Description, Proofreading, Rewriting, Summarization) | Uses on-device Gemini Nano via Chrome's built-in AI APIs or Android Gemini Nano. ML Kit Prompt API (Android) lets apps send natural language requests to Gemini Nano without network. Launched 2025. | Not a Django concern — purely client-side (Chrome Built-in AI / Android AICore). Django provides the fallback cloud endpoint using the same Anthropic/Gemini proxy pattern from Firebase AI Logic above. | N/A (client-side); fallback: anthropic, litellm on Django side |
| 164 | Firebase ML (deprecated) — Cloud Vision APIs & Custom TFLite Model Hosting | Older product; proxied Cloud Vision API calls and hosted TFLite models for OTA delivery to devices. Deprecated, shutting down June 15, 2027. Migration path: use Firebase AI Logic for cloud vision, Cloud Storage for TFLite model hosting. | Google Cloud Vision API directly (via google-cloud-vision) or open-source server-side inference (torchvision, onnxruntime). TFLite model hosting: MinIO or S3 presigned URL for OTA model delivery; version tracked in a Django model. | google-cloud-vision, onnxruntime, torchvision, minio (boto3) |
| 165 | Firebase CLI (`firebase init`, `deploy`, `emulators:start`) | Node.js CLI (`firebase-tools` npm package). `firebase init` scaffolds `firebase.json` + `.firebaserc`; `firebase deploy` reads `firebase.json`, calls Firebase Management REST API to upload Hosting assets to GCS CDN, push Firestore/Storage/RTDB rules via Rules Management API, deploy Cloud Functions via Cloud Build, and update indexes. `emulators:start` spawns Java JARs (Firestore, RTDB) and Node processes (Auth, Functions, Storage, Pub/Sub), wiring them via a central Emulator Hub on port 4400. | Python CLI built with `typer` (`pip install typer`) + `django-typer` (`pip install django-typer`) for management-command integration. `ownfb init` scaffolds `ownfirebase.json`; `ownfb deploy` calls DRF admin endpoints to upload static assets to S3/MinIO, push permission policies, and trigger Celery task deployments; `ownfb emulators:start` runs `docker-compose up` to spin up the full local dev stack. | typer, django-typer, click, rich, python-dotenv, boto3 (S3/MinIO), requests |
| 166 | Firebase Admin SDK (Node/Python/Java/Go server-side privileged access) | Initialized with a Google service-account JSON (or ADC). Signs custom JWTs using IAM `signBlob` API. Calls Firebase Auth, Firestore, RTDB, Storage, FCM, Remote Config REST APIs using an OAuth2 access token derived from the service account — bypasses Security Rules entirely. Key ops: `verifyIdToken(token)`, `createCustomToken(uid, claims)`, `setCustomUserClaims(uid, claims)`, Firestore admin writes, FCM batch send. Custom tokens are signed JWTs (RS256) whose private key belongs to the service account. | A Django app (`ownfb_admin`) exposing a Python SDK class `AdminSDK` initialized with a service-account-equivalent Django API key (stored in DB, scoped to bypass row-level permissions). The SDK calls internal DRF endpoints with `X-Admin-Key` header that sets `request.is_admin = True`, short-circuiting all object-level permission checks. Key ops: `verify_id_token()` (validates JWT via `PyJWT`/`djangorestframework-simplejwt`), `create_custom_token()`, `set_custom_user_claims()`, direct ORM access. | djangorestframework-simplejwt, PyJWT, cryptography, django-api-key (pip: djangorestframework-api-key), django-guardian |
| 167 | Local Emulator Suite (Auth, Firestore, RTDB, Functions, Storage, Hosting, Pub/Sub + Emulator UI) | Central Emulator Hub (Node.js, port 4400) coordinates service emulators. Firestore and RTDB emulators are Java JARs (~100MB each, cached in `~/.cache/firebase/emulators/`) requiring JDK 11+. Auth, Functions, Storage, Hosting, and Pub/Sub emulators are Node.js processes. The Hub exposes a discovery endpoint; client SDKs detect it via `FIREBASE_EMULATOR_HUB` env var and redirect all calls. Web UI on port 4000 provides a React dashboard for all emulators. Emulators share a project ID for cross-emulator triggers (e.g., Firestore write → Cloud Functions trigger). | A `docker-compose.yml` with named services matching each Firebase emulator: `postgres` (Firestore/RTDB), `redis` (Pub/Sub / session), `minio` (Storage), `mailhog` (Auth email), `django` (API + Auth + Functions), `celery` (async triggers), `channels` (WebSocket realtime). A custom Django management command `ownfb_emulators_ui` serves a React admin panel at port 4000. All services advertise their ports via `.env.local`; client SDKs read `OWNFB_EMULATOR_HOST` to redirect calls. | docker-compose, postgres:16-alpine, redis:7-alpine, minio/minio, mailhog/mailhog, django-channels, celery, django-environ |
| 168 | Security Rules Language & Engine (Firestore/Storage/RTDB rules, `request.auth`, `get()`/`exists()`) | Firebase Security Rules use a CEL (Common Expression Language) superset. Rules are declared in `.rules` files with `match` path patterns and `allow` statements. The rules engine runs server-side inside Firestore/Storage/RTDB before any read/write completes. `request.auth` contains the verified JWT payload; `resource.data` is the existing document; `request.resource.data` is the incoming write. `get()` and `exists()` perform cross-document lookups inside the rule evaluation. Rules are stateless, evaluated per-request, and cannot call external services. Deployed via `firebase deploy --only firestore:rules` (calls the Firebase Rules Management REST API which stores rules as immutable rulesets with versioned releases). | Three-layer approach: (1) **DRF object-level permissions** using `django-rules` (`pip install rules`) + `drf-rules` (`pip install drf-rules`) for predicate-based per-object checks in viewsets. (2) **PostgreSQL Row-Level Security** (`django-pgtrigger`, `django-pgpolicies`) for database-enforced data isolation. (3) **OPA (Open Policy Agent)** sidecar via HTTP for complex cross-document policy evaluation equivalent to `get()`/`exists()`. Rules are declared as Python predicates or Rego policies stored in a `policies/` directory, version-controlled and hot-reloaded. A `ownfb deploy --only rules` command uploads Rego bundles to the OPA sidecar. | rules (django-rules), drf-rules, django-guardian, opa (sidecar binary), requests (OPA HTTP), django-pgtrigger, psycopg2 |
| 169 | Firebase Test Lab (cloud device farm, Robo tests, instrumented tests, Game Loop tests) | Backed by Google's Cloud Testing API (`testing.googleapis.com`). Real Android/iOS hardware in Google data centers. Test matrices run APK/IPA + test APK across device × OS version × locale combinations in parallel. Robo test uses ML-driven UI crawler; instrumentation tests use Espresso/XCTest. Results (video, logcat, screenshots, coverage) stored in GCS. Quota: free tier = 10 virtual device hours/day; Blaze = pay per device-minute. Accessible via Firebase console, `gcloud firebase test android run`, or REST API. | Not a Django backend concern — this is mobile CI infrastructure. **Self-hosted alternative**: `OpenTestLabAndroid` (GitHub: `oianmol/OpenTestLabAndroid`) for Android; Appium Grid (`pip install Appium-Python-Client`) + Android Emulator (`emulator -avd`) running in Docker for automated UI tests; `pytest-appium` for test orchestration. For iOS, use macOS CI runners (GitHub Actions `macos-latest`) with XCTest. A Django management command `ownfb test:run --apk build.apk` submits to the Appium Grid and polls for results, storing them in PostgreSQL and serving a React test results dashboard. | Appium-Python-Client, pytest-appium, selenium, docker (android-emulator image), celery (test job queue) |
| 170 | Firebase App Distribution (beta APK/IPA hosting, tester management, install links, CI integration) | Firebase App Distribution API (`firebaseappdistribution.googleapis.com`) accepts APK/AAB/IPA uploads. Generates tester invitation emails with one-tap install links (Android: custom install page + `android.permission.REQUEST_INSTALL_PACKAGES`; iOS: OTA manifest via HTTPS). Tester groups managed via console or REST API. Integrates with Fastlane plugin (`fastlane-plugin-firebase_app_distribution`), Gradle plugin, and GitHub Actions. Completely free, no limits on builds/testers. Release notes attached per build. Tester feedback SDK (`FirebaseAppDistribution.checkForUpdate()`) in-app. | A Django app (`ownfb_distribution`) with: S3/MinIO for APK/IPA binary storage; a `Release` model (app, version, build_number, binary_url, release_notes, uploaded_at); a `TesterGroup` + `Tester` model with email invitations via Django email (`django-anymail`); an OTA install page (Android: serve `application/vnd.android.package-archive`; iOS: serve `.plist` manifest + signed IPA over HTTPS); and a DRF REST API (`/api/v1/distribution/releases/`) for CI upload. A `ownfb appdistribution:distribute --app myapp --apk build.apk --groups beta-testers` CLI command wraps the upload. | boto3, django-storages, django-anymail, Pillow (app icon extraction), djangorestframework, celery (email dispatch) |
| 171 | Firebase Studio / Project IDX (cloud VS Code IDE, Nix environments, Android/iOS emulators, Gemini AI, sunset March 2027) | VS Code fork running on dedicated Google Cloud VMs (one VM per workspace). Uses Nix for reproducible environment definitions (`idx/dev.nix`). Built-in Android emulator (QEMU-based) and iOS simulator (via macOS worker pool). Gemini AI integration for code completion and chat. Git-based project import. Sunset announced March 19 2026, full shutdown March 22 2027. Google recommends migrating to Google Antigravity (agent-first platform) or Google AI Studio for prototyping. | **Coder** (`pip install coder` for CLI; deploy with Helm/Docker) is the closest self-hosted equivalent — Terraform-templated workspaces running VS Code in the browser on any cloud/on-prem. Alternatively, **Gitpod** (self-hosted, open source CE) or **Eclipse Che** (Kubernetes-native). For the Django BaaS context: ship a `devcontainer.json` + `docker-compose.yml` so any Gitpod/Codespaces/Coder instance gets the full OwnFirebase stack in one click. A `ownfb studio:open` command generates a Gitpod/Coder launch URL for the project. | Coder (open source), Gitpod (open source CE), Eclipse Che, devcontainer spec, docker-compose |
| 172 | Firebase Management API (REST API for programmatic project/app management) | REST API at `https://firebase.googleapis.com/v1beta1/`. Endpoints: `projects.list`, `projects.get`, `projects.addFirebase`, `projects.webApps.create`, `projects.androidApps.create`, `projects.iosApps.create`, `projects.webApps.getConfig` (returns `firebaseConfig` JSON). Operations are long-running (`Operation` objects polled via `operations.get`). Auth: OAuth2 Bearer token with `firebase` or `cloudplatformprojects` scope. Used by `firebase init` under the hood to link local project to Firebase backend. | A DRF API (`/api/v1/management/`) with endpoints: `POST /projects/` (create project/tenant), `GET /projects/{id}/apps/` (list apps), `POST /projects/{id}/apps/web/` (register web app, returns SDK config JSON). Multi-tenancy via `django-tenants` (`pip install django-tenants`) or schema-per-tenant PostgreSQL isolation. `GET /projects/{id}/sdkconfig` returns the equivalent of Firebase's `firebaseConfig`: `{"apiUrl": "https://...", "projectId": "...", "authDomain": "..."}`. Used by the `ownfb init` CLI command. | djangorestframework, django-tenants, django-organizations, drf-spectacular |
| 173 | Client SDKs (Web/iOS/Android/Flutter/Unity — auto-synced, offline-capable, realtime listeners) | Firebase JS SDK uses modular tree-shakeable ESM packages (`firebase/app`, `firebase/auth`, `firebase/firestore`). Offline persistence: IndexedDB (web) / SQLite (mobile) as local cache; writes queued to an in-memory/on-disk WAL; sync via long-polling or WebSocket gRPC streams. Flutter SDK (`cloud_firestore` package) uses platform channels. Unity SDK uses REST polling. SDKs are hand-crafted per platform but share protobuf-based wire format. Firebase Data Connect (2025) auto-generates typed client SDKs from GraphQL schema. | Auto-generate typed client SDKs from the DRF OpenAPI schema using `drf-spectacular` (`pip install drf-spectacular`) + `openapi-generator-cli` (npm: `@openapitools/openapi-generator-cli`). Generates: TypeScript (web), Dart (Flutter), Swift (iOS), Kotlin (Android), Python (server-side). For realtime/offline: web client uses `@tanstack/react-query` with WebSocket subscription via Django Channels; mobile uses `drift` (Flutter SQLite) with delta sync. Publish generated SDKs to npm/pub.dev/PyPI as `@ownfb/client-js`, `ownfb_flutter`, etc. | drf-spectacular, openapi-generator-cli (npm), @tanstack/react-query, django-channels, drift (Flutter), retrofit (Android/Kotlin) |
| 174 | Firestore per-operation billing model (Blaze plan) | Charges per document read, write, and delete on GCP Firestore. Free Spark tier: 50K reads/day, 20K writes/day, 1 GB storage. Blaze is pay-as-you-go with no hard spending cap by default. Every query scans and charges for each document touched, including index entries. | PostgreSQL with flat-rate infrastructure pricing. Self-hosted = pay for VMs/storage, not per query. Expose budget controls at infra layer (reserved instances, database connection pooling via PgBouncer). | psycopg2-binary, django-db-geventpool, pgbouncer (infra) |
| 175 | Read amplification billing trap | Real-time listeners on large collections charge for every document in the result set on each refresh. Query offsets charge for skipped docs. AI pipelines re-reading the same docs multiply costs. A DoS or crawl spike → unbounded bill (documented $70k/day incidents on HN, Jan 2025). | Django ORM queries do not charge per row — only infra CPU/IO. Use Django's select_related/prefetch_related to minimise queries. Add rate limiting (django-ratelimit) and throttling (DRF throttle classes) to prevent DoS-driven cost spikes. | django-ratelimit, djangorestframework throttling, django-silk (query profiling) |
| 176 | Vendor lock-in / data portability | Firestore data lives exclusively on GCP in a proprietary format. Export via gcloud CLI produces Avro-like LevelDB snapshots, not standard SQL. Firebase SDKs tightly couple client code to Google's servers. No self-hosting option. Auth tokens are Firebase-specific JWTs tied to Google's issuer. | PostgreSQL is a fully open standard. pg_dump produces portable SQL. Django migrations document the full schema. JWT tokens are standard (RFC 7519) — swap issuers without client SDK rewrites. Everything runs on any cloud, on-prem, or local Docker. | psycopg2, djangorestframework-simplejwt, python-jose |
| 177 | Supabase architectural blueprint (PostgREST auto-REST API) | Supabase runs PostgREST — a standalone Go server that introspects the Postgres schema and auto-generates a full REST API: GET /users, POST /orders, PATCH /items?id=eq.5. Zero code required. Kong API gateway sits in front routing to PostgREST, GoTrue, Realtime, Storage, pg_graphql, and pg_meta. | DRF ModelViewSet + router auto-generates CRUD endpoints from Django models. For zero-code auto-generation, django-auto-api or djangorestframework with automatic router registration matches PostgREST's DX. Kong → nginx + gunicorn. | djangorestframework, drf-spectacular (OpenAPI), django-filter, django-cors-headers |
| 178 | Supabase GoTrue authentication (JWT + Postgres RLS) | GoTrue (Go, MIT) manages user identities stored directly in Postgres (auth.users table). Issues JWTs containing user ID and role. Postgres RLS policies read the JWT claim via current_setting('request.jwt.claims') to enforce row-level security without any app-layer filtering. 20+ OAuth providers. | django-allauth (social OAuth), djangorestframework-simplejwt (JWT issuance), Postgres RLS via raw SQL migrations. Set the JWT user_id into a postgres session variable in a middleware and write RLS policies that reference it for multi-tenant row isolation. | django-allauth, djangorestframework-simplejwt, psycopg2 (for SET LOCAL claims), social-auth-app-django |
| 179 | Supabase Realtime (Broadcast, Presence, Postgres Changes via WebSocket) | Elixir/Phoenix cluster (github.com/supabase/realtime). Three channels: Broadcast (ephemeral pub/sub), Presence (CRDT-based online tracking), Postgres Changes (WAL logical decoding → Phoenix PubSub → authorized client WebSocket). WAL reader checks RLS before forwarding each change. | Django Channels (ASGI) + Redis channel layer. For Postgres Changes: use a pgoutput logical replication slot, decode WAL in a Celery worker or asyncio process, push to Django Channels groups keyed by table/row. For Presence: store presence in Redis with TTL. Broadcast: Channels group_send. | channels, channels-redis, daphne, psycopg2 (replication API), celery, redis-py |
| 180 | Appwrite microservices-in-Docker architecture | Appwrite (PHP/Go, BSD-3) is a Docker Compose stack: appwrite (PHP API), mariadb (collections), redis (queues/cache), influxdb (usage metrics), telegraf, traefik, appwrite-realtime, appwrite-worker-* (separate worker containers per task). Each service scales independently. Single docker compose up -d deploys the whole BaaS. | Django + PostgreSQL + Redis + Celery workers in Docker Compose. Split workers by queue (celery_beat, celery_worker_email, celery_worker_storage) just like Appwrite's worker containers. Use Traefik or nginx for routing. | celery, django-celery-beat, redis-py, docker-compose (infra) |
| 181 | PocketBase — single-binary minimalist BaaS | Go binary (~15 MB) embedding SQLite, REST API, WebSocket realtime, auth, and file storage. Zero dependencies. Ships with a built-in admin UI. API Rules per collection (listRule, viewRule, createRule, updateRule, deleteRule) expressed as filter expressions, e.g. @request.auth.id = user_id. | A single Django app with SQLite backend is the closest analog for small/internal deployments. For the PocketBase DX (admin UI + auto-REST), combine Django admin + DRF routers + WhiteNoise. For a truly single-file deploy target, use Django with dj-database-url pointed at SQLite. | dj-database-url, whitenoise, djangorestframework, django-guardian (object permissions) |
| 182 | Parse Platform — mature OSS Node.js BaaS | Node.js/Express server (github.com/parse-community/parse-server) backed by MongoDB or PostgreSQL. Provides REST + GraphQL APIs, Cloud Code (serverless JS hooks), Live Queries (WebSocket subscriptions), push notifications (APNs/FCM), Parse Dashboard. Originally open-sourced by Facebook (2016). MIT license. | Django mirrors Parse almost 1:1: DRF = REST API, Django Signals / post_save hooks = Cloud Code triggers, Django Channels Live Queries = WebSocket subscriptions, django-push-notifications = push. Parse's schema-on-write → Django migrations. | djangorestframework, django-push-notifications, channels, celery |
| 183 | Nhost — GraphQL-first Postgres BaaS (Hasura + GoTrue + Storage) | Nhost stacks: Hasura (GraphQL engine over Postgres), nhost-auth (GoTrue fork), nhost-storage (S3-compatible), nhost-functions (Node.js serverless). Self-hostable via Docker. Provides real-time GraphQL subscriptions (Hasura polls Postgres CDC). CLI tooling for local dev with git-based deploys. | Add Strawberry or graphene-django for GraphQL, django-channels for subscriptions, django-storages+MinIO for storage. Or bolt Hasura on top of the Django Postgres DB as a GraphQL sidecar (Hasura works on any Postgres DB). | strawberry-graphql-django, graphene-django, django-storages, boto3 |
| 184 | Hasura — GraphQL engine with Postgres RLS and event triggers | Hasura (Go) introspects Postgres schema and auto-generates a full GraphQL API with subscriptions. Permissions are role+session-variable-based, translated to SQL WHERE clauses before query execution. Event Triggers use Postgres triggers to capture INSERT/UPDATE/DELETE and POST to any webhook with at-least-once delivery guarantee. Horizontally scalable. | Postgres triggers + Django Celery tasks via pg_notify/LISTEN: write a Postgres trigger that calls pg_notify('events_channel', row_data::text); a Django management command runs asyncio LISTEN and enqueues Celery tasks. RLS in Postgres replicates Hasura's permission model exactly. | celery, psycopg2 (LISTEN/NOTIFY), strawberry-graphql-django (GraphQL), django-pgpubsub |
| 185 | Convex — reactive database with TypeScript functions | Convex (open-sourced 2024, github.com/get-convex/convex-backend) is a document store where backend logic is TypeScript queries/mutations running inside the database. Query functions track which documents they read; any mutation touching those documents marks the query dirty and pushes a delta to all subscribed clients. No manual cache invalidation. ACID transactions. | Django ORM with django-pgpubsub or custom WAL consumer: when a model saves, broadcast the affected row IDs to Channels groups that have subscribed to those records. Clients receive push diffs. This replicates Convex's reactive query model with Django+Postgres+Channels. | django-pgpubsub, channels, channels-redis, djangorestframework |
| 186 | Firebase Security Rules (Firestore document-level ACL DSL) | Firebase Security Rules are a custom DSL evaluated server-side on every Firestore read/write. Rules can inspect request.auth (JWT claims), resource.data (document fields), and call get() to fetch other documents for cross-collection checks. Rules live in firestore.rules, deployed via CLI. | PostgreSQL Row Level Security (RLS) policies enforced at the DB engine level — identical security guarantee as Firebase Rules but in standard SQL. Combined with DRF permission classes and django-guardian for object-level permissions. Define RLS policies in Django migrations. | django-guardian, djangorestframework (IsAuthenticated, IsOwner), raw SQL RLS in migrations, django-rules |
| 187 | Firebase Auth mobile SDK migration complexity | Firebase Auth SDKs for iOS/Android are deeply integrated. Migration requires: shipping a new binary with new SDK, dual-issuer period (60–90 days) where backend accepts both Firebase JWTs and new-provider JWTs, waiting for old binary adoption to fall below 5% MAU. Phone SMS metered at $0.06/SMS after 10K/month. | djangorestframework-simplejwt issues standard JWTs. For migration from Firebase: implement a dual-issuer middleware that validates Firebase RS256 tokens (fetch Google's JWKS) OR local HS256/RS256 tokens. Cut Firebase issuer validation after adoption drops. | djangorestframework-simplejwt, python-jose, cryptography (JWKS validation) |
| 188 | Firebase offline persistence (client-side cache) | Firestore SDK caches all read documents in IndexedDB (web) or LevelDB (mobile). Queries can be served from cache when offline. Writes queue locally and sync when reconnected. This is a flagship Firebase differentiator — available out of the box with firestore().enablePersistence(). | Not a server-side concern — must be implemented in the client SDK. For a Django BaaS: provide a JavaScript/TypeScript client lib that wraps IndexedDB (via idb or Dexie.js) and Django Channels WebSocket. On reconnect, sync pending writes via DRF. Service Worker + Cache API for offline HTTP fallback. | Server-side: channels, djangorestframework. Client-side: idb (npm), dexie (npm), workbox (Service Worker) |
| 189 | Community-documented pitfalls: query offsets, listener scope, missing indexes | Documented in Firebase docs and community: (1) Query offsets charge for skipped documents — use cursors (startAfter/startAt). (2) Attaching collection-level real-time listeners on large collections charges on every document on every change. (3) Composite queries without matching indexes fall back to full-collection scans. (4) Re-opening the same onSnapshot listener triggers another full read. | Django ORM avoids all these: cursor pagination via .filter(id__gt=last_id), queryset lazy evaluation, database indexes declared in Meta class. For Django Channels subscriptions, scope groups to specific object PKs (not entire model tables) to minimise fanout. | djangorestframework (CursorPagination), django-silk (N+1 detection), django-debug-toolbar |
| 190 | Cost comparison: Firebase vs OSS alternatives at scale | Independent benchmarks (2025–2026): 10M reads/day on Firebase Blaze ≈ $500–1,500/month. Same workload on Supabase Pro ≈ $50–100/month (3–5x cheaper). Firebase Auth 500K MAU + 200K SMS ≈ $13,600/month; alternatives $3,000–6,000/month. Firebase has no self-hosting option so the minimum is always the Blaze metered bill. | A self-hosted Django BaaS on a $20/month VPS handles thousands of requests/second (Postgres + Redis + gunicorn + nginx). Infrastructure is predictable. Add Celery workers per need. No per-read billing. Total cost for 10M reads/day: $50–200/month all-in on a mid-range VPS. | gunicorn, uvicorn, nginx (infra), Prometheus + django-prometheus (metrics) |

## Target Architecture

"Own Firebase" is a set of cooperating Django/Python services behind a single API gateway, all multi-tenant by **project**. A client app talks to one base URL with a project API key + a user JWT; the gateway routes to the right service and every request is evaluated against a **Security-Rules-equivalent policy engine** before touching data.

```
                          ┌──────────────────────────────────────────────┐
   Web / iOS / Android /  │   Auto-generated Client SDKs (JS/Dart/Swift)  │
   Flutter clients        │   REST + WebSocket + gRPC-web                 │
                          └───────────────────┬──────────────────────────┘
                                              │  HTTPS / WSS (project key + user JWT)
                                  ┌───────────▼────────────┐
                                  │   API Gateway / Edge    │  Nginx / Caddy / Traefik
                                  │  TLS, routing, rate-limit, App-Check verify
                                  └───────────┬────────────┘
            ┌───────────────┬─────────────────┼───────────────┬────────────────┐
            ▼               ▼                 ▼               ▼                ▼
     ┌────────────┐  ┌────────────┐   ┌──────────────┐ ┌────────────┐  ┌─────────────┐
     │ Auth svc   │  │ Data API   │   │ Realtime svc │ │ Storage svc│  │ Functions / │
     │ JWT, OAuth │  │ DRF auto-  │   │ Channels(ASGI)│ │ presigned  │  │ Tasks       │
     │ MFA, claims│  │ CRUD+query │   │ WS sub/pub    │ │ S3/MinIO   │  │ Celery+Beat │
     └─────┬──────┘  └─────┬──────┘   └──────┬───────┘ └─────┬──────┘  └──────┬──────┘
           │               │                 │               │                │
           └───────────────┴───────┬─────────┴───────┬───────┴────────────────┘
                                   ▼                 ▼
                        ┌────────────────────┐  ┌──────────────────┐
                        │  PostgreSQL        │  │  Redis           │
                        │  rows + JSONB docs │  │  channel layer,  │
                        │  pgvector, RLS     │  │  cache, presence,│
                        │  LISTEN/NOTIFY +   │  │  Celery broker   │
                        │  logical replication│ │                  │
                        └─────────┬──────────┘  └──────────────────┘
                                  │ WAL / CDC (LISTEN-NOTIFY or Debezium)
                                  ▼
                        ┌────────────────────┐
                        │ Push (FCM/APNs/Web),│  Analytics sink (ClickHouse),
                        │ Messaging, AI proxy │  Crash (Sentry), Metrics (Prom)
                        └────────────────────┘

      Cross-cutting: Admin Console (Django admin / React) · CLI (Typer) ·
      Local Emulator (docker-compose) · Security-Rules policy engine · App Check attestation
```

### Key architectural decisions

- **Multi-tenant by project.** Every table carries a `project_id`; Postgres **Row-Level Security (RLS)** + a per-request `SET app.current_project / app.current_user` enforces isolation — this is also how the security-rules engine is implemented (Supabase uses the same RLS trick).
- **Documents on Postgres.** Firestore-style collections become Postgres tables with a `data JSONB` column + GIN indexes; collection-group queries become partial indexes. You get document ergonomics *and* joins/transactions.
- **Change Data Capture drives realtime.** A Postgres trigger emits `pg_notify` (or Debezium streams the WAL) → a Channels consumer fans the change out to every subscribed WebSocket, replicating Firestore's snapshot listeners.
- **Security Rules → policy DSL + RLS.** Firebase's `allow read: if request.auth...` compiles to Postgres RLS policies plus an optional declarative YAML/JSON policy layer evaluated in the Data API.
- **Stateless app tier, scale horizontally.** Gunicorn/Uvicorn workers + a Channels (ASGI) layer behind the gateway; Redis is the shared channel/cache/broker; Postgres is the single source of truth.


## Recommended Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Web framework | **Django + Django REST Framework** | Batteries-included ORM, auth, admin, migrations; DRF auto-generates CRUD/query APIs (the Firestore-without-code DX). |
| Realtime | **Django Channels (ASGI) + Redis channel layer** | WebSocket consumers + pub/sub replicate Firestore/RTDB live listeners & presence. |
| Database | **PostgreSQL 16** (JSONB + GIN, `pgvector`, RLS, `LISTEN/NOTIFY`, logical replication) | One ACID store for documents, relations, vectors, auth, and change-capture. |
| Cache / broker / presence | **Redis** | Channel layer, cache, Celery broker, `onDisconnect`/presence sets. |
| Background & scheduled | **Celery + Celery Beat** (or Dramatiq) | Cloud Functions triggers, scheduled jobs, fan-out work. |
| Object storage | **MinIO** (S3-compatible) via **django-storages + boto3** | Self-hosted GCS-equivalent with presigned/resumable uploads. |
| Auth | **djangorestframework-simplejwt + django-allauth / social-auth** | JWT ID/refresh tokens, social login, MFA, custom claims. |
| AI | **Anthropic Claude** (`claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5`) + `pgvector` RAG | Server-protected LLM proxy = Vertex-AI-in-Firebase / Genkit analog. |
| Edge / hosting | **Nginx or Caddy** (auto-TLS) + Cloudflare CDN + **Whitenoise** | Hosting, custom domains, atomic deploy + rollback via image tags. |
| Push | **FCM HTTP v1 + aioapns + pywebpush** (`django-push-notifications`) | Cross-platform push without depending on Firebase. |
| Analytics / crash / perf | **ClickHouse/TimescaleDB + Sentry/GlitchTip + OpenTelemetry + Prometheus/Grafana** | Event ingest, crash reporting, traces & metrics. |
| Feature flags / config | **Flagsmith / Unleash / django-waffle** | Remote Config + A/B testing. |
| Packaging / local emulator | **Docker + docker-compose**, **Typer** CLI | One-command local stack = Firebase Emulator Suite + CLI. |
| Admin console | **Django admin** (fast) → custom **React** console (polished) | The Firebase Console equivalent. |
| Client SDKs | **OpenAPI Generator / custom codegen** | Auto-generated typed SDKs per platform. |


---

# Part II — Feature-by-Feature Deep Dive (Firebase → Django)

_Each section: what the feature does · how Firebase implements it under the hood · how to rebuild it on Django · gotchas & how the OSS clones solve them._

## Authentication, App Check & Identity

This section covers every sub-feature of Firebase Authentication, Firebase App Check, Firebase Installations, and the enterprise Identity Platform layer, along with concrete Django rebuild strategies for each.

---

### Overview: Firebase Auth Architecture

Firebase Authentication is a hosted CIAM (Customer Identity and Access Management) service built on top of Google Cloud's **Identity Platform** (GCIP). Under the hood, the two are the same backend; Firebase Auth is the consumer/developer tier and Identity Platform is the enterprise tier with additional features gated behind a paid upgrade.

**Token flow at a glance:**

```
Client SDK ──► identitytoolkit.googleapis.com/v1/accounts:signIn* ──► Issues ID Token (JWT, RS256, 1h TTL)
                                                                    └──► Issues Refresh Token (opaque, long-lived)
Client ──► securetoken.googleapis.com/v1/token (POST refresh_token) ──► New ID Token
Backend ──► verifyIdToken(idToken) ──► Fetches public keys from:
           https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com
           (Cache-Control response header tells you when to rotate the cached keys)
```

**Firebase ID Token payload (canonical shape):**

```json
{
  "iss": "https://securetoken.google.com/<project-id>",
  "aud": "<project-id>",
  "sub": "<firebase-uid>",
  "user_id": "<firebase-uid>",
  "iat": 1716995000,
  "exp": 1716998600,
  "email": "user@example.com",
  "email_verified": true,
  "firebase": {
    "identities": {
      "google.com": ["108512345"],
      "email": ["user@example.com"]
    },
    "sign_in_provider": "google.com"
  },
  "admin": true,
  "role": "editor"
}
```

Custom claims (the `admin`, `role` fields above) are set server-side via `admin.auth().setCustomUserClaims(uid, {...})` and appear in the token after the user's next token refresh (up to 1-hour delay). Max size: **1000 bytes** across all custom claims.

---

### 1. Email / Password Authentication

**What it does:** Lets users register and sign in with email + password. Passwords are hashed with scrypt (Firebase's tuned variant) on Google's servers.

**Firebase REST API shape:**
```
POST https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=<API_KEY>
Body: { "email": "...", "password": "...", "returnSecureToken": true }
→ { "idToken": "<JWT>", "refreshToken": "<opaque>", "expiresIn": "3600", "localId": "<uid>" }

POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=<API_KEY>
```

**Django rebuild:**

```python
# pip install djangorestframework-simplejwt dj-rest-auth django-allauth

# settings.py
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "dj_rest_auth",
    "allauth",
    "allauth.account",
    "dj_rest_auth.registration",
]

SIMPLE_JWT = {
    "ALGORITHM": "RS256",
    "SIGNING_KEY": open("keys/private.pem").read(),
    "VERIFYING_KEY": open("keys/public.pem").read(),
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# urls.py
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view()),
    path("auth/token/refresh/", TokenRefreshView.as_view()),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    path("auth/", include("dj_rest_auth.urls")),
]
```

**Custom claims in the JWT** (mirrors Firebase's `setCustomUserClaims`):

```python
# serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Embed custom claims — available immediately, no propagation delay
        token["email"] = user.email
        token["email_verified"] = user.profile.email_verified
        token["role"] = user.profile.role
        token["firebase"] = {
            "sign_in_provider": user.profile.sign_in_provider or "password",
            "identities": {},
        }
        return token

# settings.py
SIMPLE_JWT["TOKEN_OBTAIN_SERIALIZER"] = "myapp.serializers.CustomTokenSerializer"
```

**Gotchas:** Django's default `AbstractUser` uses PBKDF2. Scrypt is available via `django.contrib.auth.hashers.ScryptPasswordHasher` (Django 4.0+) — add it to `PASSWORD_HASHERS` if you need Firebase password migration.

---

### 2. Phone OTP / SMS Authentication

**What it does:** User enters phone number; Firebase sends an SMS OTP via Google's carrier aggregator. User submits OTP; Firebase verifies and issues JWT. reCAPTCHA verification gates the SMS send to prevent abuse.

**Django rebuild:**

```python
# pip install pyotp twilio django-phonenumber-field django-ratelimit

# models.py
import pyotp
from django.db import models

class PhoneOTPRequest(models.Model):
    phone_e164 = models.CharField(max_length=20, db_index=True)
    hashed_otp = models.CharField(max_length=128)  # bcrypt of 6-digit code
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

# views.py
import pyotp, bcrypt
from datetime import timedelta
from django.utils import timezone
from twilio.rest import Client as TwilioClient

class SendOTPView(APIView):
    throttle_classes = [AnonRateThrottle]  # Abuse prevention

    def post(self, request):
        phone = request.data["phone"]  # Must be E.164
        otp = str(pyotp.random_base32())[:6]  # 6-digit numeric OTP
        # Store hashed OTP; never store plaintext
        hashed = bcrypt.hashpw(otp.encode(), bcrypt.gensalt())
        PhoneOTPRequest.objects.create(
            phone_e164=phone,
            hashed_otp=hashed.decode(),
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        TwilioClient(SID, TOKEN).messages.create(
            body=f"Your code is {otp}",
            from_=TWILIO_NUMBER,
            to=phone,
        )
        return Response({"detail": "OTP sent"})

class VerifyOTPView(APIView):
    def post(self, request):
        phone = request.data["phone"]
        code = request.data["code"]
        record = PhoneOTPRequest.objects.filter(
            phone_e164=phone, used=False, expires_at__gt=timezone.now()
        ).last()
        if not record or not bcrypt.checkpw(code.encode(), record.hashed_otp.encode()):
            raise AuthenticationFailed("Invalid or expired OTP")
        record.used = True
        record.save()
        user, _ = User.objects.get_or_create(username=phone)
        return Response({"token": str(RefreshToken.for_user(user).access_token)})
```

**Gotchas:** Firebase uses Google's own SMS infrastructure with spam scoring. Self-hosting means you pay Twilio/AWS SNS rates per SMS. Rate-limit aggressively: per-phone-number (1 SMS/60s) and per-IP.

---

### 3. Anonymous Authentication

**What it does:** Creates a real Firebase UID with `sign_in_provider=anonymous` instantly. Allows data to accumulate before a user commits to an account. `linkWithCredential()` upgrades the anonymous account, preserving the UID and associated data.

**Django rebuild:**

```python
# views.py
import uuid
from rest_framework_simplejwt.tokens import RefreshToken

class AnonymousSignInView(APIView):
    permission_classes = []  # No auth required

    def post(self, request):
        # Create a real but uncommitted user
        user = User.objects.create(
            username=f"anon_{uuid.uuid4().hex}",
            is_active=True,
        )
        user.profile.sign_in_provider = "anonymous"
        user.profile.save()
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})

class UpgradeAnonymousView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Attach email/password or social account to the existing anonymous user
        # The UID (user.pk) is preserved — related data stays intact
        user = request.user
        serializer = UpgradeSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Account upgraded"})
```

**Gotcha:** Implement a cleanup Celery beat task to delete anonymous users older than N days with no associated data, matching Firebase's 270-day inactivity threshold.

---

### 4. Custom Tokens

**What it does:** Server mints a short-lived signed JWT; client SDK exchanges it at Firebase for a full ID token + refresh token. Used for server-controlled auth flows (e.g., post-SAML assertion, custom IDP).

**Firebase shape:**
```python
# Firebase Admin SDK (Python)
custom_token = auth.create_custom_token(uid, {"premium": True})
# Returns a JWT signed with the Firebase service-account private key
# Client: firebase.auth().signInWithCustomToken(token)
```

**Django rebuild:**

```python
# pip install PyJWT cryptography

import jwt, datetime
from cryptography.hazmat.primitives import serialization

PRIVATE_KEY = serialization.load_pem_private_key(open("keys/private.pem","rb").read(), password=None)

def create_custom_token(uid: str, additional_claims: dict = {}) -> str:
    now = datetime.datetime.utcnow()
    payload = {
        "iss": "https://yourservice.com",
        "sub": str(uid),
        "aud": "https://yourservice.com/auth/custom-token",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=5),  # Short-lived — exchange immediately
        **additional_claims,
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

# Exchange endpoint
class CustomTokenExchangeView(APIView):
    def post(self, request):
        token = request.data.get("custom_token")
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"],
                             audience="https://yourservice.com/auth/custom-token")
        user = User.objects.get(pk=payload["sub"])
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
```

---

### 5. Social Sign-In (Google, Apple, Facebook, GitHub, Microsoft)

**What it does:** Firebase SDK handles OAuth2 popup/redirect. On callback, Firebase verifies the provider's ID token at `identitytoolkit:signInWithIdp`, creates or links a Firebase user, and issues a JWT.

**Django rebuild with django-allauth (headless, recommended for APIs):**

```python
# pip install "django-allauth[mfa,socialaccount]" dj-rest-auth

# settings.py
INSTALLED_APPS += [
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    "allauth.socialaccount.providers.github",
    "allauth.socialaccount.providers.facebook",
    "allauth.socialaccount.providers.microsoft",
]
HEADLESS_ONLY = True  # No template-rendered views; pure API
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": "https://yourapp.com/auth/verify-email/{key}",
    "account_reset_password_from_key": "https://yourapp.com/auth/reset/{key}",
}

# Database: register social apps in SocialApp model or use settings
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {"client_id": "...", "secret": "..."},
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    },
    "apple": {
        "APP": {"client_id": "com.yourapp.service", "secret": "<p8 key>"},
    },
}

# urls.py
urlpatterns += [path("auth/", include("allauth.headless.urls"))]
# allauth headless exposes: POST /_allauth/app/v1/auth/provider/token
#   Body: {"provider": "google", "token": {"id_token": "..."}}
```

**Flow:** Client gets provider token (e.g. Google ID token from Google Sign-In SDK), POSTs it to allauth headless endpoint, allauth validates with the provider, creates/finds User + SocialAccount, returns session. Wrap with djangorestframework-simplejwt: override allauth's login signal to also issue JWT.

**Apple Sign-In gotcha:** Apple only returns name on first sign-in. Allauth handles this correctly if you store it on the first callback. Sign-in with Apple requires a JWT signed with your Apple private key as the client_secret — allauth generates this automatically when configured.

---

### 6. OIDC / Generic OAuth2 Providers (Identity Platform)

**What it does:** Available only in Identity Platform (paid). Register any OIDC-compliant provider with discovery URL, client_id, client_secret. Firebase validates the `id_token`, extracts claims, and issues a Firebase JWT.

**Django rebuild:**

```python
# pip install mozilla-django-oidc
# Or: django-allauth has native OIDC via allauth.socialaccount.providers.openid_connect

INSTALLED_APPS += ["allauth.socialaccount.providers.openid_connect"]

SOCIALACCOUNT_PROVIDERS = {
    "openid_connect": {
        "SERVERS": [
            {
                "id": "okta",
                "name": "Okta",
                "server_url": "https://myorg.okta.com/.well-known/openid-configuration",
                "APP": {"client_id": "...", "secret": "..."},
            },
            {
                "id": "azure-ad",
                "name": "Azure AD",
                "server_url": "https://login.microsoftonline.com/<tenant>/v2.0/.well-known/openid-configuration",
                "APP": {"client_id": "...", "secret": "..."},
            },
        ]
    }
}
```

For **mozilla-django-oidc** (simpler, single-provider focus):
```python
OIDC_RP_CLIENT_ID = "..."
OIDC_RP_CLIENT_SECRET = "..."
OIDC_OP_AUTHORIZATION_ENDPOINT = "..."
OIDC_OP_TOKEN_ENDPOINT = "..."
OIDC_OP_JWKS_ENDPOINT = "..."
OIDC_RP_SIGN_ALGO = "RS256"
```

---

### 7. SAML 2.0 Enterprise SSO (Identity Platform)

**What it does:** Identity Platform registers as SAML SP. ACS URL is `https://PROJECT-ID.firebaseapp.com/__/auth/handler`. Validates SAMLResponse XML signature, maps attributes to user record, issues JWT.

**Django rebuild:**

```python
# pip install djangosaml2 pysaml2
# Or: pip install django-saml2-auth (Grafana fork, simpler API)

# settings.py (djangosaml2)
INSTALLED_APPS += ["djangosaml2"]
AUTHENTICATION_BACKENDS += ["djangosaml2.backends.Saml2Backend"]

SAML_CONFIG = {
    "entityid": "https://yourservice.com/saml2/metadata/",
    "service": {
        "sp": {
            "endpoints": {
                "assertion_consumer_service": [
                    ("https://yourservice.com/saml2/acs/", saml2.BINDING_HTTP_POST),
                ],
            },
            "allow_unsolicited": False,
            "authn_requests_signed": True,
            "want_assertions_signed": True,
        },
    },
    "metadata": {
        "remote": [{"url": "https://idp.example.com/metadata.xml"}],
    },
    "key_file": "keys/saml_private.pem",
    "cert_file": "keys/saml_cert.pem",
}

# urls.py
urlpatterns += [path("saml2/", include("djangosaml2.urls"))]
# After successful ACS assertion, issue JWT from djangosaml2's login signal
```

**Gotcha:** SAML XML signature validation requires exact certificate management. For multi-tenant (per-tenant IdP), store IdP metadata per-tenant in DB and dynamically build SAML_CONFIG from it.

---

### 8. Multi-Factor Authentication (Phone SMS + TOTP)

**What it does:** Identity Platform (paid). After primary sign-in, if MFA enrolled, Firebase halts with a `pendingCredential` and requires a second factor. TOTP uses RFC 6238 (Google Authenticator compatible). SMS MFA uses same phone OTP infrastructure.

**Django rebuild:**

```python
# pip install django-otp pyotp qrcode

# models.py
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice  # Backup codes

# Enroll TOTP:
class EnrollTOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import pyotp, qrcode, io, base64
        secret = pyotp.random_base32()
        device = TOTPDevice.objects.create(
            user=request.user,
            name="Authenticator App",
            key=secret,
            confirmed=False,
        )
        uri = pyotp.TOTP(secret).provisioning_uri(
            name=request.user.email,
            issuer_name="YourApp",
        )
        # Return QR code for scanning
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response({"qr_code": base64.b64encode(buf.getvalue()).decode(), "secret": secret})

# MFA verification middleware pattern:
class TokenObtainPairWithMFAView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        user = User.objects.get(username=request.data["username"])
        if user.totpdevice_set.filter(confirmed=True).exists():
            # Downgrade: return a partial token requiring MFA
            partial_token = create_partial_token(user)  # Short-lived, MFA-gated
            return Response({"mfa_required": True, "mfa_token": partial_token}, status=202)
        return response

class VerifyMFAView(APIView):
    def post(self, request):
        user = verify_partial_token(request.data["mfa_token"])
        device = user.totpdevice_set.filter(confirmed=True).first()
        if not device.verify_token(request.data["code"]):
            raise AuthenticationFailed("Invalid MFA code")
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
```

**SMS MFA:** Use the Phone OTP flow from §2, gated behind the partial token.

---

### 9. Passwordless / Email Link Sign-In

**What it does:** `sendSignInLinkToEmail()` generates a time-limited OOB code, wraps it in a Firebase Dynamic Link, emails it. `signInWithEmailLink()` submits the OOB code; Firebase verifies and issues JWT. Dynamic Links are **deprecated as of August 2025** — Firebase now uses direct links with `?apiKey=&oobCode=&mode=signIn`.

**Django rebuild:**

```python
# pip install django-allauth  (headless v65+ has native support)
# Or implement manually:

from django.core.signing import TimestampSigner, SignatureExpired, BadSignature

class SendEmailLinkView(APIView):
    def post(self, request):
        email = request.data["email"]
        signer = TimestampSigner()
        token = signer.sign(email)
        link = f"https://yourapp.com/auth/email-link/verify/?token={token}"
        send_mail("Sign in to YourApp", f"Click: {link}", "noreply@yourapp.com", [email])
        return Response({"detail": "Link sent"})

class VerifyEmailLinkView(APIView):
    def get(self, request):
        try:
            signer = TimestampSigner()
            email = signer.unsign(request.query_params["token"], max_age=3600)  # 1h
        except (SignatureExpired, BadSignature):
            raise AuthenticationFailed("Link expired or invalid")
        user, created = User.objects.get_or_create(email=email, defaults={"username": email})
        if created:
            user.profile.sign_in_provider = "emailLink"
            user.profile.save()
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
```

**django-allauth headless** (v65.3.1+) provides this natively via `ACCOUNT_LOGIN_METHODS = {"email"}` and passwordless flow endpoints.

---

### 10. JWT ID Token: Verification Architecture

**Firebase under the hood:**
1. Token signing: Google rotates RSA key pairs on `securetoken@system.gserviceaccount.com` service account. Public keys served at `googleapis.com/robot/v1/metadata/x509/securetoken@...` (X.509 cert format) and also as JWKS at `googleapis.com/service_accounts/v1/jwk/securetoken@...`.
2. `Cache-Control: max-age=<N>` on the public key response tells SDKs when to refresh. Default rotation cycle is ~24h.
3. Verification checks (in order): RS256 signature → `exp` not passed → `iat` in past → `aud` = project ID → `iss` = `https://securetoken.google.com/<project>` → optional revocation check (network round-trip to fetch `tokensValidAfterTime`).

**Django rebuild — stateless verification (no DB hit):**

```python
# pip install PyJWT cryptography django-redis

import jwt
import requests
from django.core.cache import cache

class FirebaseTokenBackend:
    """Drop-in for verifying Firebase ID tokens on a Django backend
    that still uses Firebase Auth client-side."""

    JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"

    def _get_public_key(self, kid: str):
        cache_key = f"firebase_jwk_{kid}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        resp = requests.get(self.JWKS_URL, timeout=5)
        max_age = int(resp.headers.get("Cache-Control", "max-age=3600").split("max-age=")[-1])
        jwks = resp.json()
        for key_data in jwks["keys"]:
            from jwt.algorithms import RSAAlgorithm
            pub = RSAAlgorithm.from_jwk(key_data)
            cache.set(f"firebase_jwk_{key_data['kid']}", pub, timeout=max_age)
        return cache.get(cache_key)

    def verify(self, id_token: str, project_id: str):
        header = jwt.get_unverified_header(id_token)
        pub_key = self._get_public_key(header["kid"])
        return jwt.decode(
            id_token,
            pub_key,
            algorithms=["RS256"],
            audience=project_id,
            issuer=f"https://securetoken.google.com/{project_id}",
        )
```

**For your own-issued JWTs (the primary path), djangorestframework-simplejwt handles all of this transparently** — JWKS endpoint can be exposed via `rest_framework_simplejwt.views.TokenVerifyView`.

---

### 11. Refresh Tokens & Revocation

**Firebase mechanism:**
- Refresh token is an opaque string (not a JWT). Stored client-side (localStorage / Secure storage).
- Exchange at `https://securetoken.googleapis.com/v1/token` (grant_type=refresh_token).
- Invalidated when: password changed, email changed, account disabled, `revokeRefreshTokens(uid)` called, 270-day inactivity.
- `verifyIdToken(token, { checkRevoked: true })` does an extra network call to fetch `tokensValidAfterTime` from the user record and compares against token's `iat`.

**Django rebuild:**

```python
# settings.py
SIMPLE_JWT = {
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,  # Requires rest_framework_simplejwt.token_blacklist in INSTALLED_APPS
}

# Force-revoke all tokens for a user (e.g., password change, stolen device)
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

def revoke_all_tokens(user):
    tokens = OutstandingToken.objects.filter(user=user)
    for token in tokens:
        BlacklistedToken.objects.get_or_create(token=token)

# Performance: cache the blacklist check in Redis
# Use django-redis and set CACHES to Redis; simplejwt's blacklist app queries the DB by default.
# For high-throughput: maintain a Redis Set of blacklisted jti values, check in middleware.
```

**Revocation on security events (mirrors Firebase):**
```python
# signals.py
from django.contrib.auth.signals import user_logged_out
from django.db.models.signals import post_save

@receiver(post_save, sender=User)
def revoke_on_password_change(sender, instance, **kwargs):
    if instance.tracker.has_changed("password"):
        revoke_all_tokens(instance)
```

---

### 12. Session Cookies (Server-Side Web Apps)

**Firebase mechanism:** `admin.auth().createSessionCookie(idToken, { expiresIn: 14 * 24 * 60 * 60 * 1000 })` returns a Firebase-signed JWT cookie (valid 5min–2 weeks). The cookie carries the same custom claims as the ID token. `verifySessionCookie(cookie, checkRevoked=True)` validates it on each server-rendered request.

**Django rebuild:**

```python
# views.py — issue a cookie-based session after JWT login
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse

class SessionLoginView(APIView):
    def post(self, request):
        # Expect a short-lived "exchange token" or credentials
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        response = JsonResponse({"detail": "logged in"})
        response.set_cookie(
            key="session",
            value=access,
            httponly=True,
            secure=True,
            samesite="Strict",
            max_age=60 * 60 * 24 * 14,  # 14 days
        )
        return response

# authentication.py — read JWT from cookie
class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get("session")
        if raw_token is None:
            return None
        validated = self.get_validated_token(self.get_raw_token_from_header(request)
                                             or raw_token.encode())
        return self.get_user(validated), validated
```

---

### 13. Custom Claims / RBAC

**Firebase mechanism:** `admin.auth().setCustomUserClaims(uid, { admin: true, role: "editor" })`. Claims appear in the token on next refresh (up to 1-hour delay). Enforced in Firestore Security Rules via `request.auth.token.admin`. Max 1000 bytes.

**Django rebuild — no propagation delay:**

```python
# models.py
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=50, default="viewer")
    is_premium = models.BooleanField(default=False)
    sign_in_provider = models.CharField(max_length=50, default="password")
    email_verified = models.BooleanField(default=False)

# Claims injected at token-issue time (no delay)
class CustomTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.profile.role
        token["is_premium"] = user.profile.is_premium
        return token

# permissions.py
class HasRole(BasePermission):
    def __init__(self, required_role):
        self.required_role = required_role

    def has_permission(self, request, view):
        return request.auth and request.auth.get("role") == self.required_role

# Object-level permissions: pip install django-guardian
from guardian.shortcuts import assign_perm
assign_perm("edit_document", user, document_instance)
```

**Key advantage over Firebase:** Custom claims take effect on the NEXT request — zero propagation delay, no 1-hour wait, no 1000-byte limit.

---

### 14. User Management (CRUD, List, Import, Export)

**Firebase capabilities:**
- `createUser()`, `updateUser()`, `deleteUser()`, `getUser()`, `getUserByEmail()`, `getUserByPhoneNumber()`
- `listUsers(maxResults=1000, pageToken)` — paginated, no SQL-style filtering
- `importUsers()` — bulk import with password hash configs (scrypt, bcrypt, argon2)
- No built-in search; must export to external search index

**Django rebuild:**

```python
# Full SQL power: search, filter, sort, paginate natively
# pip install djangorestframework django-filter django-import-export

# views.py
class UserViewSet(ModelViewSet):
    queryset = User.objects.select_related("profile").all()
    serializer_class = UserSerializer
    filterset_fields = ["email", "profile__role", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["date_joined", "email"]

    @action(detail=True, methods=["post"])
    def set_custom_claims(self, request, pk=None):
        user = self.get_object()
        user.profile.role = request.data.get("role", user.profile.role)
        user.profile.is_premium = request.data.get("is_premium", user.profile.is_premium)
        user.profile.save()
        # Optionally: revoke existing tokens to force re-login with new claims
        revoke_all_tokens(user)
        return Response({"detail": "Claims updated"})

# Bulk import (mirrors importUsers())
# pip install django-import-export
from import_export.admin import ImportExportModelAdmin
# Admin UI + REST endpoint for CSV/JSON bulk import
```

**Password hash migration from Firebase:**
```python
# settings.py — support Firebase's scrypt variant during migration
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.ScryptPasswordHasher",  # New default
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",  # Django legacy
    # Custom hasher for Firebase scrypt: implement check_password() using
    # hashlib.scrypt with Firebase's parameters (N=14, r=8, p=1 + salt separator)
]
```

---

### 15. Firebase App Check

Firebase App Check proves that a request originates from your genuine app binary running on a legitimate device — not a bot, emulator script, or malicious server using your API keys.

#### How the full token flow works

```
Mobile App
    │
    ├─(Android)─► Google Play Integrity API ──► Returns signed attestation blob
    ├─(iOS 14+)─► Apple App Attest / Secure Enclave ──► Returns assertion
    └─(Web)─────► reCAPTCHA Enterprise ──► Returns reCAPTCHA token
         │
         ▼
Firebase App Check Service
    │  Validates attestation with Google Play / Apple / reCAPTCHA servers
    │  Issues App Check JWT (RS256, configurable TTL 30min–7days)
    │
    ▼
Your App ──► X-Firebase-AppCheck: <App Check JWT> ──► Your Backend
                                                           │
                                               Verify via JWKS at:
                                    firebaseappcheck.googleapis.com/v1/jwks
                                    (iss: firebaseappcheck.googleapis.com,
                                     aud: projects/<project-number>)
```

**App Check JWT payload:**
```json
{
  "iss": "https://firebaseappcheck.googleapis.com/<project-number>",
  "sub": "<app-id>",
  "aud": ["projects/<project-number>"],
  "exp": 1716998600,
  "iat": 1716995000
}
```

#### Django analog for App Check

There is no true hardware-attestation analog that you can self-host without Apple/Google involvement. The pragmatic self-hosted approximation uses a defense-in-depth layered approach:

**Layer 1 — reCAPTCHA Enterprise (Web, closest analog):**
```python
# pip install django-recaptcha google-cloud-recaptcha-enterprise

# views.py
from django.conf import settings
from google.cloud import recaptchaenterprise_v1

class RecaptchaProtectedView(APIView):
    def post(self, request):
        token = request.META.get("HTTP_X_RECAPTCHA_TOKEN")
        client = recaptchaenterprise_v1.RecaptchaEnterpriseServiceClient()
        assessment = client.create_assessment(
            parent=f"projects/{settings.GOOGLE_CLOUD_PROJECT}",
            assessment=recaptchaenterprise_v1.Assessment(
                event=recaptchaenterprise_v1.Event(token=token, site_key=settings.RECAPTCHA_SITE_KEY),
            ),
        )
        if not assessment.token_properties.valid or assessment.risk_analysis.score < 0.5:
            raise PermissionDenied("Bot detected")
        # Proceed with request
```

**Layer 2 — App Attest (iOS) custom verification:**
```python
# Standalone micro-service or Django view that verifies Apple App Attest assertions
# Apple's attestation service: https://data.appattest.apple.com (no Python SDK — use httpx)

# Verification steps (CBOR-decoded assertion):
# 1. Verify the credential certificate chain against Apple's root CA
# 2. Verify the clientDataHash (SHA256 of challenge you issued)
# 3. Verify the rpId hash matches your app's bundle ID
# 4. Verify the counter and risk metadata
# On success, issue your own short-lived "attestation token" (JWT, 5min TTL)

# pip install cbor2 cryptography httpx PyJWT
```

**Layer 3 — Django middleware gating all sensitive endpoints:**
```python
# middleware.py
class AppAttestationMiddleware:
    PROTECTED_PATHS = ["/api/auth/", "/api/sensitive/"]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in self.PROTECTED_PATHS):
            attestation_token = request.META.get("HTTP_X_APP_ATTESTATION")
            if not attestation_token or not self._verify(attestation_token):
                return JsonResponse({"error": "App attestation required"}, status=403)
        return self.get_response(request)

    def _verify(self, token: str) -> bool:
        try:
            payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"],
                                 audience="com.yourapp.bundle")
            return True
        except jwt.InvalidTokenError:
            return False
```

**Layer 4 — Rate limiting and abuse signals (django-ratelimit):**
```python
# pip install django-ratelimit

from django_ratelimit.decorators import ratelimit

@ratelimit(key="ip", rate="10/m", block=True)
@ratelimit(key="user_or_ip", rate="100/h", block=True)
def sensitive_endpoint(request):
    pass
```

#### OSS alternatives approach:
- **Supabase Auth:** No App Check equivalent; relies on API key + RLS + rate limiting.
- **Appwrite:** No native attestation; uses API keys + rate limiting + abuse detection.
- **SuperTokens:** No attestation; focuses on session security (rotating tokens, anti-CSRF, device fingerprinting via IP+User-Agent).

**Conclusion for self-hosting:** True hardware attestation (Play Integrity, App Attest) requires the Apple/Google attestation services — you cannot replace them. Build a verification service that calls those same Google/Apple endpoints directly, validates the result, and issues your own short-lived attestation JWT. Your Django backend then only needs to verify that JWT (stateless, fast).

---

### 16. Firebase Installations (FID)

**What it does:** Auto-generated 22-char base64 ID per app instance. Used by FCM, Crashlytics, Performance Monitoring, Remote Config to correlate events to a device. Resettable; different per-app on same device. Expires after 270 days of inactivity.

**Django rebuild:**

```python
# models.py
import uuid

class DeviceInstallation(models.Model):
    installation_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    platform = models.CharField(max_length=20)  # ios, android, web
    app_version = models.CharField(max_length=20)
    push_token = models.TextField(blank=True)  # FCM/APNs token for push notifications
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "platform"])]

# Cleanup task (Celery beat)
@app.task
def purge_stale_installations():
    cutoff = timezone.now() - timedelta(days=270)
    DeviceInstallation.objects.filter(last_seen_at__lt=cutoff).delete()
```

Client generates the installation ID on first launch, stores it (SharedPreferences / Keychain / localStorage), and sends it as `X-Installation-ID` header. Backend upserts the `DeviceInstallation` record on each authenticated request.

---

### 17. Identity Platform — Multi-Tenancy

**What it does:** Creates isolated user pools (Tenants) within a single project. Each Tenant has its own IdP configs, MFA policy, and user namespace. `tenantId` is embedded in JWTs. Enterprise SaaS / B2B pattern.

**Django rebuild options:**

| Approach | Library | Isolation Level | When to use |
|---|---|---|---|
| Schema-per-tenant | `django-tenants` | Strong (separate PostgreSQL schemas) | Strict data isolation requirement |
| Row-level multi-tenancy | `tenant_id` FK on all models | Moderate (shared schema, filtered queries) | Simpler ops, most SaaS cases |
| Separate deployments | Docker per tenant | Complete | Extreme isolation (regulated industries) |

```python
# pip install django-tenants

# models.py (schema-per-tenant approach)
from django_tenants.models import TenantMixin, DomainMixin

class Tenant(TenantMixin):
    name = models.CharField(max_length=100)
    idp_config = models.JSONField(default=dict)  # SAML/OIDC config per tenant
    mfa_required = models.BooleanField(default=False)
    auto_create_schema = True

class Domain(DomainMixin):
    pass

# JWT includes tenant context
class TenantAwareTokenSerializer(CustomTokenSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        from django_tenants.utils import get_current_db_name
        token["tenant_id"] = get_current_db_name()
        return token

# Middleware resolves tenant from subdomain or JWT before routing
```

---

### Architecture Summary: Django Auth Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (Web / iOS / Android)              │
│   django-allauth JS / your custom SDK                        │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼────────────────────────────────────┐
│                       NGINX (TLS termination)                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     DJANGO APPLICATION                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ django-allauth (headless)  │  dj-rest-auth            │   │
│  │ Social: Google/Apple/GH/FB │  Registration/Login/Pass │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ djangorestframework-simplejwt (RS256)                 │   │
│  │ Access Token (1h) + Refresh Token (30d, rotating)     │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ django-otp  (TOTP + SMS MFA)                         │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ djangosaml2 / mozilla-django-oidc (Enterprise SSO)   │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ django-ratelimit + django-recaptcha (App Check ≈)    │   │
│  └──────────────────────────────────────────────────────┘   │
└──────┬──────────────────────────────────────────┬───────────┘
       │                                          │
┌──────▼────────┐                      ┌──────────▼──────────┐
│  PostgreSQL   │                      │    Redis             │
│  - auth_user  │                      │  - Token blacklist  │
│  - profiles   │                      │  - OTP codes        │
│  - social     │                      │  - JWKS cache       │
│  - otp devices│                      │  - Rate limit state │
│  - tenants    │                      └─────────────────────┘
└───────────────┘
       │
┌──────▼──────────────┐
│  Celery (async)     │
│  - Send SMS / Email │
│  - Purge stale FIDs │
│  - Token cleanup    │
└─────────────────────┘
```

---

### Key Packages Reference

| Purpose | Package | pip install |
|---|---|---|
| JWT auth (access + refresh) | djangorestframework-simplejwt | `djangorestframework-simplejwt` |
| Token blacklist / revocation | simplejwt blacklist app | included above |
| Social OAuth2 + passwordless | django-allauth (headless) | `django-allauth[mfa,socialaccount]` |
| REST auth endpoints | dj-rest-auth | `dj-rest-auth[with_social]` |
| TOTP / HOTP MFA | django-otp | `django-otp django-two-factor-auth` |
| TOTP logic | pyotp | `pyotp` |
| SMS OTP via Twilio | twilio | `twilio` |
| SAML 2.0 SSO | djangosaml2 | `djangosaml2 pysaml2` |
| OIDC SSO | mozilla-django-oidc / allauth | `mozilla-django-oidc` |
| Rate limiting | django-ratelimit | `django-ratelimit` |
| reCAPTCHA (App Check ≈) | django-recaptcha | `django-recaptcha` |
| reCAPTCHA Enterprise | google client | `google-cloud-recaptcha-enterprise` |
| Phone number validation | django-phonenumber-field | `django-phonenumber-field` |
| Object-level permissions | django-guardian | `django-guardian` |
| Schema-per-tenant | django-tenants | `django-tenants` |
| JWT (low-level) | PyJWT | `PyJWT[crypto]` |
| Cryptography | cryptography | `cryptography` |
| Scrypt password hashing | Built-in Django 4.0+ | n/a |

---

### Gotchas & Hard Parts

| Problem | Firebase handles it | Self-hosted mitigation |
|---|---|---|
| Key rotation for JWT signing | Google rotates automatically; clients fetch new public keys via Cache-Control | Use a secrets manager (Vault, AWS Secrets Manager); automate key rotation; expose JWKS endpoint; cache keys in Redis |
| SMS flood / OTP abuse | Google's internal spam scoring + reCAPTCHA | django-ratelimit (per-phone + per-IP) + Twilio Verify (built-in rate limits) |
| Token revocation at scale | Firebase RTDB stores `tokensValidAfterTime`; Admin SDK fetches it | Redis-backed blacklist; accept eventual consistency (blacklist miss window = Redis TTL) |
| Custom claims propagation delay | Up to 1h in Firebase | Zero delay in Django (claims at token-issue time); invalidate old tokens immediately |
| Mobile hardware attestation | Firebase calls Apple/Google servers internally | Call Apple App Attest / Google Play Integrity directly; issue your own attestation JWT |
| Anonymous user accumulation | Firebase has auto-cleanup toggle | Celery beat task: delete inactive anonymous users older than 270 days |
| SAML certificate rotation | Firebase console; managed by Google | djangosaml2 supports multiple certs; script rotation via cron; test SP metadata update |
| Multi-tenancy user isolation | Identity Platform tenant objects | django-tenants (schema isolation) or row-level `tenant_id` + composite indexes |
| Email deliverability (OTP, magic link) | Google's email infrastructure | SendGrid / AWS SES with DKIM/SPF/DMARC; monitor bounce rates |

## Cloud Firestore (NoSQL Document DB)

Cloud Firestore is Google's flagship serverless NoSQL document database, powering apps from solo-dev prototypes to New York Times scale. This section covers every sub-feature and maps each to a concrete Django/PostgreSQL implementation.

---

### Architecture Overview: What Firestore Actually Is Under the Hood

Firestore launched in 2019 as a reimplementation of the older Cloud Datastore, replacing its Megastore storage engine with **Google Cloud Spanner**. This is the most important architectural fact: Firestore is a document-model API layer sitting on top of a globally distributed, strongly consistent, relational storage system.

**Physical storage (per the VLDB 2024 paper "Transparent Migration from Datastore to Firestore"):**

- Each Firestore database maps to a **directory** within pre-initialized Spanner databases in the project's region.
- That directory contains exactly **two tables**:
  - `Entities` — one row per document, primary key = full document path, single column = document content (Protocol Buffer, max 1 MiB).
  - `IndexEntries` — one row per (field, value, document_path) tuple; all auto and composite indexes live here.
- Firestore manages its **own query engine** on top of Spanner because Firestore's query semantics (automatic indexing, collection-scoped queries, array operators) differ from Spanner SQL.
- Indexes in Firestore are stored as **inverted indexes** — i.e., each `IndexEntries` row maps `(collection_group, field_path, field_value, document_path)` to nothing (the row's existence is the index entry).
- **Every query is an index-only scan** of `IndexEntries`. Firestore never scans `Entities` directly. Query latency scales with the result set size, not the collection size.
- Firestore is **multi-tenant** with a fair-scheduler keyed on database ID to prevent noisy-neighbor effects.

---

### 1. Documents & Collections

#### What it does

A **document** is a key-value map of typed fields stored under a path like `users/alice`. A **collection** is a logical grouping of documents (e.g. `users`). Collections have no physical representation — they exist only as a common prefix in document paths.

**Supported field types:** string, integer, float, boolean, null, timestamp, geopoint, bytes, document reference, array (heterogeneous), map (nested object).

**Document limits:** 1 MiB max, 20,000 fields max (including nested), subcollection depth max 100.

```js
// Firebase JS SDK v9 (modular)
import { doc, setDoc, getDoc } from "firebase/firestore";

await setDoc(doc(db, "users", "alice"), {
  name: "Alice",
  age: 30,
  tags: ["admin", "beta"],
  address: { city: "NYC", zip: "10001" },
  createdAt: serverTimestamp(),
});

const snap = await getDoc(doc(db, "users", "alice"));
console.log(snap.data());
```

#### Django Rebuild

Use a single `Document` model with a JSONB `data` column. This mirrors Firestore's `Entities` table exactly.

```python
# models.py
import uuid
from django.db import models
from django.contrib.postgres.indexes import GinIndex

class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Full path: "users/alice/posts/post1"
    collection_path = models.TextField(db_index=True)  # "users/alice/posts"
    document_id = models.TextField()                    # "post1"
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("collection_path", "document_id")]
        indexes = [
            GinIndex(fields=["data"], name="document_data_gin"),
        ]

    @property
    def full_path(self):
        return f"{self.collection_path}/{self.document_id}"
```

```python
# serializers.py
from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "collection_path", "document_id", "data",
                  "created_at", "updated_at"]
```

```python
# views.py — auto-CRUD matching Firestore's REST shape
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from .models import Document
from .serializers import DocumentSerializer

class DocumentViewSet(ViewSet):
    def retrieve(self, request, collection_path, document_id):
        doc = Document.objects.get(
            collection_path=collection_path, document_id=document_id
        )
        return Response({"fields": doc.data})

    def update(self, request, collection_path, document_id):
        doc, created = Document.objects.update_or_create(
            collection_path=collection_path,
            document_id=document_id,
            defaults={"data": request.data.get("fields", {})}
        )
        return Response(status=status.HTTP_200_OK)
```

**URL pattern** mirrors Firestore's REST API shape:
```
GET/PUT /documents/{collection_path}/{document_id}
```

---

### 2. Subcollections

#### What it does

A subcollection lives under a document path: `users/alice/posts/post1`. It is independent of the parent document — writing to a subcollection does not touch the parent document row. Subcollection documents have no size impact on the parent. Depth limit: 100 levels.

```js
// Writing to a subcollection
await setDoc(doc(db, "users", "alice", "posts", "post1"), {
  title: "Hello World",
  published: true,
});
```

#### Django Rebuild

The same `Document` model handles subcollections — `collection_path` encodes the full hierarchy.

```python
# Subcollection write: collection_path="users/alice/posts", document_id="post1"
Document.objects.update_or_create(
    collection_path="users/alice/posts",
    document_id="post1",
    defaults={"data": {"title": "Hello World", "published": True}}
)

# List all documents in a subcollection
Document.objects.filter(collection_path="users/alice/posts")

# List all subcollections under a document (collection discovery)
Document.objects.filter(
    collection_path__startswith="users/alice/"
).values_list("collection_path", flat=True).distinct()
```

For deep hierarchical queries, add a `django-ltree` column as a secondary index:

```python
# pip install django-ltree
from ltree_fields.fields import LtreeField

class Document(models.Model):
    ...
    path_ltree = LtreeField(null=True)  # e.g. "users.alice.posts.post1"
```

---

### 3. Query Model (where / orderBy / limit / Cursors)

#### What it does

Firestore queries are **always collection-scoped** (or collection-group-scoped). All queries run against `IndexEntries` exclusively — no collection scans. Cost = O(result set size).

**Operators:** `==`, `!=`, `<`, `<=`, `>`, `>=`, `in` (max 30 values), `not-in` (max 10), `array-contains`, `array-contains-any` (max 30).

**Pagination** uses document snapshots as cursors (`startAfter`, `endBefore`, `startAt`, `endAt`), not integer offsets.

```js
import { collection, query, where, orderBy, limit, startAfter, getDocs } from "firebase/firestore";

// Simple filter + sort
const q = query(
  collection(db, "cities"),
  where("country", "==", "USA"),
  where("population", ">", 1_000_000),
  orderBy("population", "desc"),
  limit(10)
);
const snapshot = await getDocs(q);

// Cursor-based next page
const lastDoc = snapshot.docs[snapshot.docs.length - 1];
const nextPage = query(
  collection(db, "cities"),
  where("country", "==", "USA"),
  orderBy("population", "desc"),
  startAfter(lastDoc),
  limit(10)
);
```

#### Django Rebuild

```python
# views.py — DRF ViewSet with query support
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from django.db.models import Q
from .models import Document

class CollectionQueryView(ViewSet):
    def list(self, request, collection_path):
        qs = Document.objects.filter(collection_path=collection_path)

        # WHERE clauses from query params: ?where[status][eq]=active
        filters = request.query_params.get("where", {})
        for field, ops in filters.items():
            for op, val in ops.items():
                jsonb_field = f"data__{field}"
                if op == "eq":
                    qs = qs.filter(**{jsonb_field: val})
                elif op == "gt":
                    qs = qs.filter(**{f"{jsonb_field}__gt": val})
                elif op == "lt":
                    qs = qs.filter(**{f"{jsonb_field}__lt": val})
                elif op == "array_contains":
                    qs = qs.filter(**{f"{jsonb_field}__contains": [val]})

        # ORDER BY
        order_field = request.query_params.get("orderBy", "created_at")
        direction = request.query_params.get("direction", "asc")
        prefix = "" if direction == "asc" else "-"
        qs = qs.order_by(f"{prefix}data__{order_field}")

        # Keyset pagination (cursor-based, not offset)
        after_id = request.query_params.get("startAfter")
        if after_id:
            pivot = Document.objects.get(pk=after_id)
            qs = qs.filter(
                **{f"data__{order_field}__gt": pivot.data.get(order_field)}
            )

        page_size = int(request.query_params.get("limit", 20))
        qs = qs[:page_size]

        return Response([{"id": d.document_id, "fields": d.data} for d in qs])
```

**Indexes for JSONB query fields** (run via Django migration):

```python
# migrations/0002_jsonb_indexes.py
from django.db import migrations, models
from django.contrib.postgres.indexes import GinIndex

class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            # Expression index on a commonly filtered field
            "CREATE INDEX doc_data_status ON documents ((data->>'status'), collection_path);",
            reverse_sql="DROP INDEX IF EXISTS doc_data_status;"
        ),
        migrations.RunSQL(
            "CREATE INDEX doc_data_created_at ON documents ((data->>'created_at'));",
            reverse_sql="DROP INDEX IF EXISTS doc_data_created_at;"
        ),
    ]
```

**Gotcha:** Firestore's inequality filter + orderBy rule (you must `orderBy` the inequality field first) has no equivalent constraint in PostgreSQL — but you should still put the most selective indexed column first for performance.

---

### 4. Composite Indexes

#### What it does

Firestore requires a manually created composite index for any query combining:
- A range/inequality filter on one field + any orderBy or filter on another field
- Any `array-contains` + another condition
- Two or more `orderBy` fields

Firestore throws an error at query time if the required composite index doesn't exist — and helpfully includes a direct link to create it in the Firebase console.

**Auto-index (single-field):** Firestore automatically creates ASC + DESC indexes for every non-array, non-map field in every document, plus an array-contains index for every array field. This happens on write, not on schema creation — it's schema-less index fan-out.

**Composite index limit:** 500 per database (billing enabled), 200 without billing.

#### Django Rebuild

Composite indexes are PostgreSQL expression indexes on JSONB paths:

```python
# models.py Meta
class Meta:
    indexes = [
        # Composite: filter on status, order by created_at (collection-scoped)
        models.Index(
            fields=["collection_path"],
            name="idx_collection_path",  # already covered by unique_together
        ),
        # Expression index: (collection_path, data->>'status', data->>'created_at')
        # Must be created via RunSQL:
    ]
```

```sql
-- migrations/0003_composite_indexes.sql
-- Equivalent to Firestore composite index on (status ASC, createdAt DESC)
-- for collection "orders"
CREATE INDEX idx_orders_status_created
ON documents (collection_path, (data->>'status'), (data->>'created_at') DESC)
WHERE collection_path LIKE 'orders%';
```

**Auto-index equivalent:** Firestore's auto-indexing of every field is impractical to replicate fully (and unnecessary in PostgreSQL). Use the GIN index for ad-hoc containment queries during development, then add targeted expression indexes for production query patterns as they emerge. A management command can introspect slow queries from `pg_stat_statements` and suggest new indexes.

---

### 5. Collection Group Queries

#### What it does

Query across ALL collections with the same name, anywhere in the document hierarchy.

```js
// Returns all "comments" subcollections across all parent documents
const q = query(
  collectionGroup(db, "comments"),
  where("approved", "==", true),
  orderBy("createdAt", "desc")
);
```

Requires a **collection-group-scoped** composite index (separate from the collection-scoped default). Security rules must use wildcard paths: `match /{path=**}/comments/{id}`.

#### Django Rebuild

Since `collection_path` encodes full hierarchy, a collection group query is a LIKE/suffix filter:

```python
# All "comments" subcollections anywhere in the tree
Document.objects.filter(
    collection_path__regex=r'(^|/)comments$',
    data__approved=True
).order_by("-data__created_at")
```

Add an expression index on the terminal path component for performance:

```sql
-- Index on the last path segment (the collection name)
CREATE INDEX idx_terminal_collection
ON documents (split_part(collection_path, '/', -1));
-- Note: -1 is PostgreSQL 14+ feature for last element; use regexp_replace on older versions
```

---

### 6. Realtime Snapshot Listeners

#### What it does

The most differentiated Firestore feature. Clients register a query or document reference and receive immediate push updates whenever matching data changes — without polling.

```js
// Document listener
const unsub = onSnapshot(doc(db, "users", "alice"), (snap) => {
  console.log("Updated:", snap.data());
});

// Query listener — fires when ANY matching document changes
const unsub2 = onSnapshot(
  query(collection(db, "orders"), where("status", "==", "pending")),
  (snapshot) => {
    snapshot.docChanges().forEach((change) => {
      if (change.type === "added") console.log("New order:", change.doc.data());
      if (change.type === "modified") console.log("Changed:", change.doc.data());
      if (change.type === "removed") console.log("Removed:", change.doc.id);
    });
  }
);
```

**Under the hood:**
1. Client opens a gRPC bidirectional stream (Watch API) to Firestore servers.
2. The stream carries `AddTarget` messages (one per registered query/document).
3. On any write to `Entities`/`IndexEntries`, Firestore evaluates all active Watch targets to find matches.
4. Affected targets receive `DocumentChange` events (ADDED/MODIFIED/REMOVED) plus a new **resume token**.
5. If the stream drops, the client reconnects using the last resume token — Firestore replays only the delta since that token.
6. **Browser transport:** WebChannel (chunked HTTP/1.1 response or WebSocket). Long-polling fallback via `experimentalForceLongPolling`. **Server SDKs:** native gRPC streaming.

#### Django Rebuild

Django Channels + Redis channel layer + PostgreSQL NOTIFY:

```python
# pip install channels channels-redis daphne
# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from .routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
```

```python
# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Document

class FirestoreConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.subscriptions = {}  # target_id -> {collection_path, filters}
        await self.accept()

    async def disconnect(self, code):
        for group_name in self.subscriptions.values():
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive(self, text_data):
        msg = json.loads(text_data)
        if msg["type"] == "subscribe":
            target_id = msg["targetId"]
            collection_path = msg["collectionPath"]
            # Group name encodes the collection
            group_name = f"collection_{collection_path.replace('/', '_')}"
            self.subscriptions[target_id] = group_name
            await self.channel_layer.group_add(group_name, self.channel_name)

            # Send current snapshot immediately
            docs = await self._get_documents(collection_path, msg.get("filters", {}))
            await self.send(json.dumps({
                "type": "snapshot",
                "targetId": target_id,
                "docs": docs,
            }))

        elif msg["type"] == "unsubscribe":
            target_id = msg["targetId"]
            group_name = self.subscriptions.pop(target_id, None)
            if group_name:
                await self.channel_layer.group_discard(group_name, self.channel_name)

    async def document_change(self, event):
        """Called by channel layer when a document in a subscribed collection changes."""
        await self.send(json.dumps({
            "type": "documentChange",
            "changeType": event["changeType"],  # ADDED/MODIFIED/REMOVED
            "documentId": event["documentId"],
            "data": event.get("data"),
        }))

    @database_sync_to_async
    def _get_documents(self, collection_path, filters):
        qs = Document.objects.filter(collection_path=collection_path)
        return [{"id": d.document_id, "fields": d.data} for d in qs]
```

```python
# signals.py — broadcast on every save/delete
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Document

channel_layer = get_channel_layer()

@receiver(post_save, sender=Document)
def broadcast_document_change(sender, instance, created, **kwargs):
    group_name = f"collection_{instance.collection_path.replace('/', '_')}"
    async_to_sync(channel_layer.group_send)(group_name, {
        "type": "document.change",
        "changeType": "ADDED" if created else "MODIFIED",
        "documentId": instance.document_id,
        "data": instance.data,
    })

@receiver(post_delete, sender=Document)
def broadcast_document_delete(sender, instance, **kwargs):
    group_name = f"collection_{instance.collection_path.replace('/', '_')}"
    async_to_sync(channel_layer.group_send)(group_name, {
        "type": "document.change",
        "changeType": "REMOVED",
        "documentId": instance.document_id,
    })
```

```python
# settings.py additions
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("redis", 6379)]},
    }
}
```

**Resume token equivalent:** Store a `last_event_id` (auto-increment or timestamp) on the server. On WebSocket reconnect, the client sends its last seen ID; the server replays all Document changes since that ID from a lightweight `DocumentChangeLog` table.

```python
class DocumentChangeLog(models.Model):
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True)
    collection_path = models.TextField(db_index=True)
    document_id = models.TextField()
    change_type = models.CharField(max_length=10)  # ADDED/MODIFIED/REMOVED
    data_snapshot = models.JSONField(null=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

**Alternative — PostgreSQL LISTEN/NOTIFY (no Redis needed for single-node):**

```python
# async listener using psycopg3
import asyncio, psycopg, json

async def listen_for_changes():
    async with await psycopg.AsyncConnection.connect(DSN, autocommit=True) as conn:
        await conn.execute("LISTEN document_changes")
        async for notify in conn.notifies():
            payload = json.loads(notify.payload)
            await channel_layer.group_send(
                f"collection_{payload['collection_path'].replace('/', '_')}",
                {"type": "document.change", **payload}
            )
```

```sql
-- PostgreSQL trigger to fire NOTIFY on document changes
CREATE OR REPLACE FUNCTION notify_document_change() RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify(
    'document_changes',
    json_build_object(
      'collection_path', COALESCE(NEW.collection_path, OLD.collection_path),
      'document_id',     COALESCE(NEW.document_id, OLD.document_id),
      'change_type',     TG_OP,
      'data',            row_to_json(NEW)
    )::text
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER document_change_trigger
AFTER INSERT OR UPDATE OR DELETE ON documents
FOR EACH ROW EXECUTE FUNCTION notify_document_change();
```

**Query-scoped listeners (hard part):** Firestore evaluates whether a changed document matches a registered query on the server. In the Django rebuild, you must either: (a) send all changes for a collection to all subscribers and let the client filter, or (b) implement server-side query evaluation against each subscriber's registered filter set before calling `group_send`. Option (b) is more correct but requires maintaining in-memory subscriber state per Channels worker — solvable with a shared Redis hash keyed by channel name.

---

### 7. Offline Persistence & Local Cache

#### What it does

- **Mobile (iOS/Android):** Enabled by default. Uses LevelDB on-device. All reads serve from cache first; writes are queued locally and synced when online.
- **Web:** Opt-in. Uses IndexedDB (`persistentLocalCache()`) or memory (`memoryLocalCache()`). Multi-tab mode: one primary tab owns the network connection, shares IndexedDB with other tabs.
- On reconnect: queued writes are replayed in order; cache is reconciled with server state using resume tokens.

```js
// Web — enable persistent cache
import { initializeFirestore, persistentLocalCache } from "firebase/firestore";

const db = initializeFirestore(app, {
  localCache: persistentLocalCache()
});
```

#### Django Rebuild

Offline persistence is **entirely a client-side concern** — no Django changes needed.

**Recommended approach: a thin JS client SDK with IndexedDB caching**

```js
// client-sdk/firestore-client.js (vanilla JS, no framework dependency)
import { openDB } from "idb"; // npm: idb

const DB_NAME = "ownfirestore";
const STORE_NAME = "documents";
const PENDING_STORE = "pending_writes";

async function getDB() {
  return openDB(DB_NAME, 1, {
    upgrade(db) {
      db.createObjectStore(STORE_NAME, { keyPath: "fullPath" });
      db.createObjectStore(PENDING_STORE, { keyPath: "id", autoIncrement: true });
    },
  });
}

export async function getDocument(collectionPath, documentId) {
  const db = await getDB();
  const fullPath = `${collectionPath}/${documentId}`;
  // Try cache first
  const cached = await db.get(STORE_NAME, fullPath);
  if (cached && navigator.onLine) {
    // Return cache immediately, refresh in background
    fetchAndCache(collectionPath, documentId);
    return cached.data;
  }
  if (cached) return cached.data; // offline, return stale
  // Cache miss — fetch from server
  return fetchAndCache(collectionPath, documentId);
}

async function fetchAndCache(collectionPath, documentId) {
  const res = await fetch(`/api/documents/${collectionPath}/${documentId}`);
  const json = await res.json();
  const db = await getDB();
  await db.put(STORE_NAME, {
    fullPath: `${collectionPath}/${documentId}`,
    data: json.fields,
    cachedAt: Date.now(),
  });
  return json.fields;
}

export async function setDocument(collectionPath, documentId, data) {
  // Optimistic local write
  const db = await getDB();
  const fullPath = `${collectionPath}/${documentId}`;
  await db.put(STORE_NAME, { fullPath, data, cachedAt: Date.now() });

  if (!navigator.onLine) {
    // Queue for later sync
    await db.add(PENDING_STORE, { collectionPath, documentId, data, op: "set" });
    return;
  }
  await syncWrite(collectionPath, documentId, data);
}

async function flushPendingWrites() {
  const db = await getDB();
  const pending = await db.getAll(PENDING_STORE);
  for (const write of pending) {
    await syncWrite(write.collectionPath, write.documentId, write.data);
    await db.delete(PENDING_STORE, write.id);
  }
}

window.addEventListener("online", flushPendingWrites);
```

**Service Worker approach (for PWA):** Use Workbox (`workbox-strategies`) to cache `/api/documents/**` responses with a `StaleWhileRevalidate` strategy.

---

### 8. Transactions

#### What it does

Firestore transactions use **Serializable Snapshot Isolation** (SSI), inherited from Spanner.

- Transaction reads documents at a consistent snapshot timestamp.
- All reads must come before any writes.
- Transaction is committed atomically; retried automatically (up to 5 times) on contention.
- **Limits:** 270-second max duration, 500 document reads/writes per transaction.

```js
import { runTransaction, doc } from "firebase/firestore";

await runTransaction(db, async (txn) => {
  const sfRef = doc(db, "cities", "SF");
  const sfDoc = await txn.get(sfRef);
  if (!sfDoc.exists()) throw new Error("Document does not exist");
  txn.update(sfRef, { population: sfDoc.data().population + 1 });
});
// Automatically retried on contention up to 5 times
```

#### Django Rebuild

```python
# For server-side transactions: Django's transaction.atomic() with explicit isolation
from django.db import transaction
import psycopg2

def transfer_tokens(from_id, to_id, amount):
    with transaction.atomic():
        # Use SELECT FOR UPDATE to lock rows (equivalent to Firestore's snapshot read)
        from_doc = Document.objects.select_for_update().get(
            collection_path="wallets", document_id=from_id
        )
        to_doc = Document.objects.select_for_update().get(
            collection_path="wallets", document_id=to_id
        )

        if from_doc.data["balance"] < amount:
            raise ValueError("Insufficient balance")

        from_doc.data["balance"] -= amount
        to_doc.data["balance"] += amount
        from_doc.save()
        to_doc.save()
```

For **SERIALIZABLE** isolation (full SSI, closest to Firestore/Spanner):

```python
# pip install django-pgtransaction
import django_pgtransaction

@django_pgtransaction.atomic(isolation_level="SERIALIZABLE")
def safe_increment(document_id):
    doc = Document.objects.get(document_id=document_id)
    doc.data["counter"] = doc.data.get("counter", 0) + 1
    doc.save()
```

**Client-initiated optimistic transactions** (matching Firestore's client SDK pattern):

```python
# DRF view: client sends expected version, server validates
class TransactionView(APIView):
    def post(self, request):
        ops = request.data.get("operations", [])  # [{path, data, expectedVersion}]
        with transaction.atomic():
            for op in ops:
                doc = Document.objects.select_for_update().get(
                    collection_path=op["collectionPath"],
                    document_id=op["documentId"]
                )
                if doc.data.get("_version") != op.get("expectedVersion"):
                    raise serializers.ValidationError("Version conflict — retry")
                doc.data.update(op["data"])
                doc.data["_version"] = doc.data.get("_version", 0) + 1
                doc.save()
        return Response({"status": "committed"})
```

---

### 9. Batched Writes

#### What it does

Group up to **500** set/update/delete operations into a single atomic commit, with no reads. All succeed or all fail. Each operation billed individually. No automatic retry (unlike transactions).

```js
import { writeBatch, doc } from "firebase/firestore";

const batch = writeBatch(db);
batch.set(doc(db, "cities", "NYC"), { name: "New York City" });
batch.update(doc(db, "cities", "SF"), { population: 900000 });
batch.delete(doc(db, "cities", "LA"));
await batch.commit();
```

#### Django Rebuild

```python
# DRF batch endpoint
class BatchWriteView(APIView):
    def post(self, request):
        operations = request.data.get("writes", [])
        if len(operations) > 500:
            return Response({"error": "Max 500 operations per batch"},
                            status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            for op in operations:
                col = op["collectionPath"]
                doc_id = op["documentId"]
                if op["type"] == "set":
                    Document.objects.update_or_create(
                        collection_path=col, document_id=doc_id,
                        defaults={"data": op["data"]}
                    )
                elif op["type"] == "update":
                    doc = Document.objects.get(collection_path=col, document_id=doc_id)
                    doc.data.update(op["data"])
                    doc.save(update_fields=["data", "updated_at"])
                elif op["type"] == "delete":
                    Document.objects.filter(
                        collection_path=col, document_id=doc_id
                    ).delete()
        return Response({"status": "ok"})
```

For very large batches, use `bulk_create` and `bulk_update` for performance:

```python
# Bulk upsert using PostgreSQL ON CONFLICT
from django.db import connection

def bulk_upsert(documents: list[dict]):
    """documents: [{collection_path, document_id, data}]"""
    with connection.cursor() as cursor:
        args = [(d["collection_path"], d["document_id"], json.dumps(d["data"]))
                for d in documents]
        cursor.executemany("""
            INSERT INTO documents (id, collection_path, document_id, data, created_at, updated_at)
            VALUES (gen_random_uuid(), %s, %s, %s::jsonb, NOW(), NOW())
            ON CONFLICT (collection_path, document_id)
            DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
        """, args)
```

---

### 10. Atomic Increments / ArrayUnion / ArrayRemove / ServerTimestamp

#### What it does

Server-side atomic field transforms — no read-then-write round trip needed.

```js
import { doc, updateDoc, FieldValue } from "firebase/firestore";

await updateDoc(doc(db, "cities", "SF"), {
  population:  FieldValue.increment(1),           // atomic +1
  tags:        FieldValue.arrayUnion("featured"),  // add to set
  oldTags:     FieldValue.arrayRemove("draft"),    // remove from set
  lastUpdated: FieldValue.serverTimestamp(),        // server clock
});
```

#### Django Rebuild

```python
# DRF serializer recognizes sentinel values in the payload
class FieldTransformSerializer(serializers.Serializer):
    def process_transforms(self, document: Document, data: dict) -> dict:
        result = dict(document.data)
        for key, value in data.items():
            if isinstance(value, dict):
                if "_increment" in value:
                    result[key] = result.get(key, 0) + value["_increment"]
                elif "_arrayUnion" in value:
                    existing = set(result.get(key, []))
                    existing.update(value["_arrayUnion"])
                    result[key] = list(existing)
                elif "_arrayRemove" in value:
                    existing = result.get(key, [])
                    result[key] = [x for x in existing
                                   if x not in value["_arrayRemove"]]
                elif "_serverTimestamp" in value:
                    from django.utils import timezone
                    result[key] = timezone.now().isoformat()
                else:
                    result[key] = value
            else:
                result[key] = value
        return result
```

For **true atomic increments** (no read needed, concurrent-safe):

```python
# Using PostgreSQL's JSONB arithmetic — atomic, no SELECT needed
from django.db import connection

def atomic_increment(collection_path, document_id, field, delta):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE documents
            SET data = jsonb_set(
                data,
                %s::text[],
                (COALESCE((data #>> %s::text[])::numeric, 0) + %s)::text::jsonb
            ),
            updated_at = NOW()
            WHERE collection_path = %s AND document_id = %s
        """, (
            [field], [field], delta,
            collection_path, document_id
        ))
```

---

### 11. Data Bundles

#### What it does

Pre-packaged binary snapshots of query results, servable from a CDN. Clients load the bundle into local cache and get initial data without hitting Firestore. Bundles embed **named queries** — stored query shapes clients can re-run against cache. Reduces cold-start latency and Firestore read billing.

```js
// Server-side: build bundle (Admin SDK)
const bundle = db.bundle("latest-cities");
const query = db.collection("cities").where("population", ">", 1_000_000);
await bundle.add("big-cities", query);
const bundleBuffer = await bundle.build();
// Upload bundleBuffer to CDN

// Client-side: load bundle
const res = await fetch("https://cdn.example.com/bundles/latest-cities.bundle");
await db.loadBundle(res.body);
// Now query against cache with the named query
const snap = await db.namedQuery("big-cities");
```

#### Django Rebuild

A Celery periodic task builds a JSON snapshot and uploads to MinIO/S3:

```python
# tasks.py
import json, io
from celery import shared_task
from django.utils import timezone
from .models import Document
import boto3

@shared_task
def build_bundle(collection_path: str, bundle_name: str, filters: dict = None):
    """Build a data bundle for a collection and upload to S3/MinIO."""
    qs = Document.objects.filter(collection_path=collection_path)
    if filters:
        for field, value in filters.items():
            qs = qs.filter(**{f"data__{field}": value})

    bundle = {
        "name": bundle_name,
        "createdAt": timezone.now().isoformat(),
        "documents": [
            {"id": d.document_id, "fields": d.data}
            for d in qs
        ],
        "namedQueries": {
            bundle_name: {
                "collectionPath": collection_path,
                "filters": filters or {}
            }
        }
    }

    s3 = boto3.client("s3", endpoint_url="http://minio:9000",
                      aws_access_key_id="minioadmin",
                      aws_secret_access_key="minioadmin")
    body = json.dumps(bundle).encode()
    s3.put_object(
        Bucket="bundles",
        Key=f"{bundle_name}.json",
        Body=body,
        ContentType="application/json",
        CacheControl="public, max-age=300",
    )
    return f"Bundle {bundle_name} uploaded ({len(bundle['documents'])} docs)"
```

```python
# Schedule bundle rebuilds with Celery Beat
# celery_config.py
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    "rebuild-cities-bundle": {
        "task": "myapp.tasks.build_bundle",
        "schedule": crontab(minute="*/5"),
        "args": ("cities", "latest-cities", {"population__gt": 1_000_000}),
    },
}
```

**Client-side bundle loading:**
```js
// Load bundle from CDN into local IndexedDB cache
async function loadBundle(bundleName) {
  const res = await fetch(`https://cdn.example.com/bundles/${bundleName}.json`);
  const bundle = await res.json();
  const db = await getDB();
  for (const doc of bundle.documents) {
    await db.put("documents", {
      fullPath: `${bundle.namedQueries[bundleName].collectionPath}/${doc.id}`,
      data: doc.fields,
      cachedAt: Date.now(),
    });
  }
}
```

---

### 12. TTL Policies

#### What it does

Designate a **Timestamp field** in a collection group as the document's expiration time. Firestore's background worker deletes expired documents within ~24 hours. TTL deletes do not count against write quotas but do count as **delete billing**. One TTL policy per collection group.

```bash
# Configure via gcloud CLI
gcloud firestore fields ttls update expiry_time \
  --collection-group=sessions \
  --enable-ttl
```

```js
// Write a document with a TTL field
await setDoc(doc(db, "sessions", sessionId), {
  userId: "alice",
  data: { ... },
  expiry_time: Timestamp.fromDate(new Date(Date.now() + 24 * 60 * 60 * 1000))
});
```

#### Django Rebuild

```python
# models.py — TTL policy configuration table
class TTLPolicy(models.Model):
    collection_group = models.TextField(unique=True)  # e.g. "sessions"
    expiry_field = models.TextField()                 # e.g. "expiry_time"
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

# tasks.py — Celery Beat task
from celery import shared_task
from django.utils import timezone
from .models import Document, TTLPolicy

@shared_task
def run_ttl_deletes():
    """Run TTL deletions for all active TTL policies."""
    now = timezone.now().isoformat()
    policies = TTLPolicy.objects.filter(is_active=True)
    total_deleted = 0
    for policy in policies:
        # Find documents where expiry_field < now
        expired = Document.objects.filter(
            collection_path__regex=fr'(^|/)({policy.collection_group})$',
            **{f"data__{policy.expiry_field}__lt": now}
        )
        count, _ = expired.delete()
        total_deleted += count
    return f"TTL deleted {total_deleted} documents"
```

```python
# celery_config.py
CELERYBEAT_SCHEDULE = {
    "ttl-deletes": {
        "task": "myapp.tasks.run_ttl_deletes",
        "schedule": crontab(minute="0"),  # hourly
    },
}
```

**Management command for one-off TTL runs:**
```python
# management/commands/run_ttl.py
from django.core.management.base import BaseCommand
from myapp.tasks import run_ttl_deletes

class Command(BaseCommand):
    help = "Run TTL document deletions"
    def handle(self, *args, **options):
        result = run_ttl_deletes()
        self.stdout.write(result)
```

---

### 13. Native Mode vs Datastore Mode

| Feature | Native Mode | Datastore Mode |
|---|---|---|
| Data model | Documents & collections | Entities & kinds |
| Realtime listeners | Yes | No |
| Offline persistence (mobile/web SDK) | Yes | No |
| API | Firestore v1 API | Datastore v1 API |
| Client libraries | Firestore SDKs | Datastore SDKs |
| Write limit per entity group | N/A | Removed (was 1/sec in legacy Datastore) |
| Strong consistency | Yes (always) | Yes (since Datastore mode on Spanner) |
| Ancestor queries required in transactions | No | No (removed in Datastore mode) |

**Django rebuild targets Native mode only.** If you need a Datastore-compatibility layer for migration, expose a separate URL namespace with the Datastore v1 REST API shape via DRF — but skip Channels/WebSocket for that namespace.

---

### 14. Pricing Model

| Operation | Firestore Standard | Self-hosted (reference infra) |
|---|---|---|
| Document reads | $0.03 / 100K | PostgreSQL SELECT (compute cost) |
| Document writes | $0.09 / 100K | PostgreSQL INSERT/UPDATE |
| Document deletes | $0.01 / 100K | PostgreSQL DELETE |
| Storage | $0.15 / GB / month | Disk cost (~$0.10/GB on commodity) |
| Egress (internet) | $0.12 / GB (first 10 TB) | CDN/bandwidth cost |
| TTL deletes | Billed as deletes | Celery worker compute time |
| Listener connections | No per-connection charge | Redis channel layer overhead |
| **Free tier** | 50K reads/day, 20K writes/day, 1 GiB storage | N/A |

**Billing simulation in Django:** Instrument a DRF middleware that increments per-API-key counters in Redis for reads, writes, and deletes — then emit to your billing system hourly via Celery.

---

### 15. Scaling Limits & Hotspotting

#### What Firestore does

- **~1 sustained write/second per document.** A single `Entities` row lives on one Spanner replica set; high sustained writes to one document hit a wall.
- **No hard limit on collection size** — Firestore auto-shards the `IndexEntries` table by key range.
- **Hotspotting** occurs when document IDs are sequential (timestamps, integers) — Spanner range splits mean all new documents land on the same shard until Spanner detects the hotspot and re-splits (which takes minutes). Solution: use random/hash IDs.
- **Ramp up write rate gradually** on new collections — avoid sudden bursts to new key ranges.

#### Django Rebuild

PostgreSQL has no equivalent per-row write limit, but there are analogous concerns:

```python
# 1. Use UUID4 document IDs (random) to prevent B-tree hotspots
import uuid
document_id = str(uuid.uuid4())  # random, avoids sequential insert hotspot

# 2. For high-frequency counters: sharded counter pattern
class ShardedCounter(models.Model):
    collection_path = models.TextField()
    document_id = models.TextField()
    field_name = models.TextField()
    shard = models.IntegerField()  # 0..N_SHARDS-1
    value = models.BigIntegerField(default=0)

    class Meta:
        unique_together = [("collection_path", "document_id", "field_name", "shard")]

import random
def increment_sharded(collection_path, doc_id, field, delta=1, n_shards=10):
    shard = random.randint(0, n_shards - 1)
    ShardedCounter.objects.update_or_create(
        collection_path=collection_path,
        document_id=doc_id,
        field_name=field,
        shard=shard,
        defaults={"value": 0}
    )
    ShardedCounter.objects.filter(
        collection_path=collection_path,
        document_id=doc_id,
        field_name=field,
        shard=shard
    ).update(value=models.F("value") + delta)

def get_sharded_total(collection_path, doc_id, field):
    from django.db.models import Sum
    result = ShardedCounter.objects.filter(
        collection_path=collection_path,
        document_id=doc_id,
        field_name=field
    ).aggregate(total=Sum("value"))
    return result["total"] or 0

# 3. For row-level contention: SELECT FOR UPDATE SKIP LOCKED (queue pattern)
from django.db import transaction
with transaction.atomic():
    job = Document.objects.select_for_update(skip_locked=True).filter(
        collection_path="job_queue",
        data__status="pending"
    ).first()
```

---

### Complete Infrastructure Stack for Django Firestore Rebuild

```yaml
# docker-compose.yml
version: "3.9"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ownfirestore
      POSTGRES_USER: django
      POSTGRES_PASSWORD: secret
    volumes:
      - postgres_data:/var/lib/postgresql/data
    command: >
      postgres
        -c wal_level=logical
        -c max_replication_slots=5
        -c max_wal_senders=5

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

  daphne:
    build: .
    command: daphne -b 0.0.0.0 -p 8000 myproject.asgi:application
    depends_on: [postgres, redis]
    environment:
      DATABASE_URL: postgres://django:secret@postgres/ownfirestore
      REDIS_URL: redis://redis:6379/0

  celery:
    build: .
    command: celery -A myproject worker --loglevel=info --concurrency=4
    depends_on: [postgres, redis]

  celery-beat:
    build: .
    command: celery -A myproject beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    depends_on: [postgres, redis]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    depends_on: [daphne]

volumes:
  postgres_data:
  minio_data:
```

---

### OSS Alternatives — Implementation Lessons

| Alternative | Realtime mechanism | Document store | Key lesson for DIY |
|---|---|---|---|
| **Supabase** | PostgreSQL WAL → logical decoding → Realtime server (Elixir Phoenix) → WebSocket | PostgreSQL rows (not JSONB-native) | WAL-based CDC is more reliable than trigger-based NOTIFY for high-throughput; Elixir handles 1M+ concurrent WebSockets |
| **PocketBase** | SSE (Server-Sent Events) per collection subscription | SQLite with JSON columns | SSE is simpler than WebSocket for unidirectional push; SQLite is surprisingly capable for single-node |
| **Appwrite** | WebSocket via Swoole PHP | MariaDB | Separate realtime service from the API service — don't mix them |
| **Parse Platform** | MongoDB change streams or LiveQuery WebSocket server | MongoDB | LiveQuery server is a separate process — same pattern as Channels |
| **Nhost** | Hasura GraphQL subscriptions over WebSocket | PostgreSQL | GraphQL subscriptions compile to SQL `FOR UPDATE` poll or `LISTEN/NOTIFY` |

**Key takeaway for Django build:** Supabase's architecture (PostgreSQL WAL → separate Elixir realtime process → WebSocket) is the most battle-tested pattern. The Django equivalent: PostgreSQL trigger → `pg_notify` → async Python listener (psycopg3 `AsyncConnection`) → Channels Redis group_send → WebSocket consumers. This is the pattern to follow for production scale.

---

### Gotchas & Hard Parts When Self-Hosting

| Problem | Firestore's solution | Django/Postgres workaround |
|---|---|---|
| **Index fan-out on write** | Spanner atomically updates `Entities` + all `IndexEntries` in one transaction | PostgreSQL triggers update expression index entries implicitly — add indexed computed columns for critical fields |
| **Query-scoped live listener evaluation** | Server maintains watch targets per stream, evaluates them at write time inside the storage layer | Must implement in application layer; evaluate each subscriber's filter against changed doc before `group_send` |
| **Resume tokens / missed events on reconnect** | Built into the Watch API | Implement `DocumentChangeLog` table with timestamp cursor; replay on reconnect |
| **1 write/sec per document** | Spanner architecture limit; mitigate with sharded counters pattern | Not a hard limit in PostgreSQL but row-level locks can bottleneck; use `SELECT FOR UPDATE SKIP LOCKED` and F() expressions |
| **Index explosion on deeply nested JSONB** | Firestore indexes each map subfield recursively | Only index JSONB paths you actually query; use GIN for ad-hoc, expression indexes for known-hot paths |
| **Auto-composite-index suggestions** | SDK throws error with a console link to create the index | Log slow queries via `pg_stat_statements`; build a management command to suggest `CREATE INDEX` statements |
| **Multi-region strong consistency** | Free — Spanner is globally consistent | Requires PostgreSQL synchronous replication or Citus; complex to self-host |
| **Security rules** | Declarative CEL-based rules evaluated server-side per operation | DRF permissions classes + django-rules (pip install rules) for attribute-based access control |

## Realtime Database

Firebase Realtime Database (RTDB) is the original Firebase product — a cloud-hosted, single JSON tree synchronized in real time to every connected client over a persistent WebSocket. It predates Firestore and remains the go-to choice for presence systems, live counters, and simple chat where sub-100 ms latency matters more than rich queries. This section covers every sub-feature exhaustively, its internal mechanics, and the concrete Django rebuild.

---

### 1. JSON-Tree Data Model

#### What It Does

Every RTDB instance is a single JSON tree stored at `https://<project>.firebaseio.com/`. Paths in the URL map 1-to-1 to JSON keys:

```
/users/uid123/name      → "Alice"
/users/uid123/online    → true
/chats/room1/messages/  → { "-NxK2z...": { text: "hi", ts: 1700000000000 } }
```

All values are JSON primitives or objects. There are no collections, documents, or schemas. **Denormalization is required** — the same data is often duplicated at multiple paths to enable efficient fan-out reads (e.g., `/user-posts/uid` and `/posts/pid` both hold post metadata).

#### Under the Hood

Google has not published the full internal storage architecture, but from public signals: the tree is stored in Google's proprietary distributed storage layer (likely a derivative of Bigtable's log-structured merge tree or a custom in-memory store with a durable write-ahead log). The unit of distribution is the **database instance** (one URL = one shard). A client always talks to one instance; there is no transparent cross-instance query. All mutations are written to a durable log first, then the in-memory state is updated and the diff is broadcast to subscribers.

#### Django Rebuild

Use a single PostgreSQL table with a `JSONB` column to store the entire tree for a given "database instance":

```python
# models.py
from django.db import models

class RealtimeTree(models.Model):
    """One row = one logical RTDB instance / shard."""
    db_name = models.SlugField(unique=True)
    data = models.JSONField(default=dict)  # the full JSON tree
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # GIN index for JSONB containment queries
            models.Index(fields=["data"], name="rtree_data_gin",
                         condition=models.Q())  # use GinIndex from django.contrib.postgres
        ]
```

For path access, write a utility that walks the JSONB tree using PostgreSQL's `jsonb_set()` and `#>` / `#>>` operators:

```python
# utils/tree.py
from django.db import connection

def get_at_path(db_name: str, path: list[str]):
    """Retrieve subtree at path, e.g. ['users', 'uid123']."""
    selector = "{" + ",".join(path) + "}" if path else None
    with connection.cursor() as cur:
        if selector:
            cur.execute(
                "SELECT data #> %s FROM rtdb_realtimetree WHERE db_name = %s",
                [selector, db_name]
            )
        else:
            cur.execute(
                "SELECT data FROM rtdb_realtimetree WHERE db_name = %s",
                [db_name]
            )
        row = cur.fetchone()
    return row[0] if row else None

def set_at_path(db_name: str, path: list[str], value, conn=None):
    """Atomically set value at path using jsonb_set."""
    import json
    selector = "{" + ",".join(path) + "}"
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE rtdb_realtimetree SET data = jsonb_set(data, %s, %s::jsonb, true), "
            "updated_at = NOW() WHERE db_name = %s",
            [selector, json.dumps(value), db_name]
        )
```

**Install:** `pip install psycopg2-binary django` (PostgreSQL 14+ required; enable `CREATE EXTENSION IF NOT EXISTS "pg_trgm";` for future text search).

For hierarchical path queries with ltree-style ancestors, also consider `django-ltree-2` (`pip install django-ltree-2`), but for a pure JSON-tree clone the JSONB approach above is simpler and sufficient.

---

### 2. `.on()` / `.once()` Listeners and Ref Paths

#### What They Do

```javascript
// JavaScript SDK — Firebase RTDB client
const db = getDatabase(app);
const messagesRef = ref(db, 'chats/room1/messages');

// Persistent listener — fires on initial data + every change
const unsub = onValue(messagesRef, (snapshot) => {
  console.log(snapshot.val());
});

// One-shot read
const snap = await get(messagesRef);

// Child-granular listeners
onChildAdded(messagesRef, (snap) => { /* new child */ });
onChildChanged(messagesRef, (snap) => { /* changed child */ });
onChildRemoved(messagesRef, (snap) => { /* removed child */ });
```

Event types:
- `value` — full snapshot of the path (fires immediately + on any descendant change)
- `child_added` — once per existing child on attach, then per new child
- `child_changed` — when a direct child's value changes
- `child_removed` — when a direct child is deleted
- `child_moved` — when a child's priority/order changes

All listeners on a single app instance share **one multiplexed WebSocket connection**. The SDK de-multiplexes incoming diffs by path.

#### Under the Hood

On connect the SDK sends a `listen` message for each ref path over the shared WS. The server maintains a per-connection subscription table. When a write hits path `/a/b/c`, the server fans out to all clients subscribed to `/a`, `/a/b`, `/a/b/c`, or any descendent of `/a/b/c` — sending the appropriate diff to each.

#### Django Rebuild

```python
# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .utils.tree import get_at_path

class RTDBConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.subscriptions: dict[str, str] = {}  # path_str -> group_name
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        msg = json.loads(text_data)
        action = msg.get("action")

        if action == "subscribe":
            path = msg["path"].strip("/")
            path_parts = path.split("/") if path else []
            group = "rtdb_" + path.replace("/", "__")
            self.subscriptions[path] = group
            await self.channel_layer.group_add(group, self.channel_name)
            # Send current value immediately (like Firebase's initial fire)
            value = await database_sync_to_async(get_at_path)(
                msg.get("db", "default"), path_parts
            )
            await self.send(json.dumps({
                "event": "put",
                "path": "/" + path,
                "data": value
            }))

        elif action == "unsubscribe":
            path = msg["path"].strip("/")
            group = self.subscriptions.pop(path, None)
            if group:
                await self.channel_layer.group_discard(group, self.channel_name)

    async def disconnect(self, close_code):
        for group in self.subscriptions.values():
            await self.channel_layer.group_discard(group, self.channel_name)
        await self._run_on_disconnect_ops()

    # Handler for group_send messages
    async def rtdb_event(self, event):
        await self.send(json.dumps({
            "event": event["event_type"],   # "put" or "patch"
            "path": event["path"],
            "data": event["data"],
        }))

    async def _run_on_disconnect_ops(self):
        """Execute any registered onDisconnect operations."""
        import redis.asyncio as aioredis
        r = aioredis.from_url("redis://localhost")
        ops_raw = await r.hget(f"ondisconnect:{self.channel_name}", "ops")
        if ops_raw:
            ops = json.loads(ops_raw)
            for op in ops:
                await database_sync_to_async(_apply_write)(
                    op["db"], op["path"], op["value"], op["op_type"]
                )
        await r.delete(f"ondisconnect:{self.channel_name}")
        await r.aclose()
```

**ASGI routing** (`routing.py`):

```python
from django.urls import re_path
from .consumers import RTDBConsumer

websocket_urlpatterns = [
    re_path(r"ws/rtdb/(?P<db_name>[^/]+)/$", RTDBConsumer.as_asgi()),
]
```

**Settings** (`settings.py`):

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.pubsub.RedisPubSubChannelLayer",
        "CONFIG": { "hosts": [("127.0.0.1", 6379)] },
    }
}
```

**Install:** `pip install channels channels-redis daphne`

---

### 3. SSE / WebSocket Diff Streaming — the Core Protocol

#### What It Does (Wire Format)

Firebase exposes two transport options:

**Option A — Native SDK WebSocket:** A proprietary multiplexed binary-ish JSON protocol. Not publicly documented. The JS SDK opens one WS per app, sends `{t:"d", d:{r:1, a:"l", b:{p:"/path"}}}` style frames.

**Option B — REST SSE (public spec):** Any HTTP client can stream changes:

```bash
curl -N \
  -H "Accept: text/event-stream" \
  "https://<project>.firebaseio.com/chats/room1.json?auth=TOKEN"
```

Server responds with an SSE stream:

```
event: put
data: {"path":"/","data":{"messages":{"-NxK":{"text":"hi","ts":1700000000000}}}}

event: patch
data: {"path":"/messages/-NxK2","data":{"text":"hello"}}

event: keep-alive
data: null

event: cancel
data: null

event: auth_revoked
data: null
```

- `put` — replace the entire subtree at `path` with `data` (used on initial subscribe and for large writes)
- `patch` — merge `data` into the subtree at `path` (used for incremental updates; only changed keys are sent)
- `keep-alive` — null payload, keeps the HTTP connection alive through proxies
- `cancel` — permission denied; stop listening
- `auth_revoked` — token expired; re-authenticate

**This is the key diff streaming mechanism**: Firebase computes the delta between old and new state at the written path and sends only the changed keys as a `patch` event (or a `put` if the entire node was replaced).

#### Under the Hood

When a write arrives at the server:
1. The server locks the relevant tree node.
2. It computes `oldValue` and `newValue` at the path.
3. For each subscriber whose listened path is an ancestor-or-equal of the written path: send `put` with `path = writtenPath` and `data = newValue` (or `patch` if only some keys changed under a node the client is listening to at a higher level).
4. For each subscriber whose listened path is a descendant of the written path: send `put` with `path = "/"` (relative to their listen root) and `data = newValue[descendantSuffix]`.
5. The server does NOT send unchanged sibling data.

#### Django Rebuild

The write handler computes the diff and broadcasts to all affected groups:

```python
# services/write.py
import json
import jsonpatch          # pip install jsonpatch
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .tree import get_at_path, set_at_path
from django.db import transaction

channel_layer = get_channel_layer()

def write_to_tree(db_name: str, path: str, new_value, op="set"):
    """
    Perform an atomic write and broadcast diffs to all subscribers.
    op: "set" (replaces subtree), "update" (merges keys at path), "delete"
    """
    path_parts = [p for p in path.strip("/").split("/") if p]

    with transaction.atomic():
        old_value = get_at_path(db_name, path_parts)

        if op == "set":
            set_at_path(db_name, path_parts, new_value)
            event_type = "put"
            event_data = new_value
        elif op == "update":
            # Merge: apply each key from new_value into the subtree
            merged = {**(old_value or {}), **new_value}
            set_at_path(db_name, path_parts, merged)
            event_type = "patch"
            event_data = new_value  # only the changed keys
        elif op == "delete":
            delete_at_path(db_name, path_parts)
            event_type = "put"
            event_data = None

    # Fan-out: notify subscribers of this path AND all ancestor paths
    _broadcast_to_subscribers(db_name, path, event_type, event_data, path_parts)


def _broadcast_to_subscribers(db_name, written_path, event_type, event_data, path_parts):
    """Notify groups for the written path and every ancestor path."""
    # Notify the exact path group
    segments = [""] + path_parts  # ["", "a", "b", "c"]
    for i in range(len(segments)):
        ancestor_path = "/" + "/".join(segments[1:i+1])
        group = "rtdb_" + ancestor_path.strip("/").replace("/", "__")
        async_to_sync(channel_layer.group_send)(group, {
            "type": "rtdb.event",
            "event_type": event_type,
            "path": written_path,   # relative path from listener root
            "data": event_data,
        })
```

For **multi-path atomic writes** (the `.update()` with multiple paths):

```python
def multi_path_update(db_name: str, updates: dict):
    """
    updates = { "/users/uid/name": "Alice", "/user-index/Alice": "uid" }
    All applied atomically inside one DB transaction.
    """
    with transaction.atomic():
        for path, value in updates.items():
            path_parts = [p for p in path.strip("/").split("/") if p]
            set_at_path(db_name, path_parts, value)
    # Broadcast each changed path
    for path, value in updates.items():
        path_parts = [p for p in path.strip("/").split("/") if p]
        _broadcast_to_subscribers(db_name, path, "put", value, path_parts)
```

**REST SSE endpoint** (for non-WS clients):

```python
# views.py
import asyncio
import json
from django.http import StreamingHttpResponse

async def sse_stream(request, db_name, path):
    from channels.layers import get_channel_layer
    cl = get_channel_layer()
    group = "rtdb_" + path.replace("/", "__")
    channel_name = f"sse.{request.META.get('REMOTE_ADDR')}.{id(request)}"
    await cl.group_add(group, channel_name)

    async def event_generator():
        yield "event: put\ndata: {}\n\n".format(
            json.dumps({"path": "/" + path, "data": get_at_path(db_name, path.split("/"))})
        )
        while True:
            # Poll the channel layer for messages (simplified — use proper async receive)
            msg = await cl.receive(channel_name)
            yield "event: {}\ndata: {}\n\n".format(
                msg["event_type"],
                json.dumps({"path": msg["path"], "data": msg["data"]})
            )
            await asyncio.sleep(0)  # yield to event loop

    response = StreamingHttpResponse(
        event_generator(), content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # disable Nginx buffering
    return response
```

**Install:** `pip install jsonpatch channels channels-redis`

---

### 4. onDisconnect Handlers and Presence

#### What Firebase Does

```javascript
const presenceRef = ref(db, `/presence/${uid}`);

// Register what to write when this client disconnects
onDisconnect(presenceRef).set({ online: false, lastSeen: serverTimestamp() });

// Mark online immediately
set(presenceRef, { online: true });
```

The server stores the pending operation **server-side** as soon as `onDisconnect()` is registered. When the TCP connection drops — cleanly or dirty — the server executes the operation. A second security check is performed at execution time to ensure the rule still permits the write.

Special read-only paths:
- `/.info/connected` — `true` when connected, `false` otherwise
- `/.info/serverTimeOffset` — milliseconds to add to local time to get server time

#### Under the Hood

Firebase servers maintain an in-memory map of `{connectionId → [pendingDisconnectOps]}`. On clean close (WS close frame) or on server-detected TCP timeout, all ops for that connection are executed atomically. This is why onDisconnect is reliable even during crashes — the server owns the ops, not the client.

#### Django Rebuild

**On WS connect**, store the onDisconnect ops in Redis and start a heartbeat TTL key:

```python
# In RTDBConsumer.receive() when action == "on_disconnect":
async def _register_on_disconnect(self, db_name, path, value, op_type):
    import redis.asyncio as aioredis
    r = aioredis.from_url("redis://localhost")
    ops_key = f"ondisconnect:{self.channel_name}"
    existing = await r.hget(ops_key, "ops")
    ops = json.loads(existing) if existing else []
    ops.append({"db": db_name, "path": path, "value": value, "op_type": op_type})
    await r.hset(ops_key, "ops", json.dumps(ops))
    # Heartbeat key — TTL kept alive by client pings
    await r.setex(f"presence:hb:{self.channel_name}", 90, "1")
    await r.aclose()
```

**Client must send periodic pings** (every 30s). The consumer renews the TTL on each ping:

```python
elif action == "ping":
    import redis.asyncio as aioredis
    r = aioredis.from_url("redis://localhost")
    await r.setex(f"presence:hb:{self.channel_name}", 90, "1")
    await r.aclose()
    await self.send(json.dumps({"event": "pong"}))
```

**On clean disconnect**, `RTDBConsumer.disconnect()` calls `_run_on_disconnect_ops()` (shown earlier) directly.

**On dirty disconnect** (TCP drop, no close frame), the heartbeat TTL expires. Configure Redis keyspace notifications and a Celery consumer:

```python
# celery_tasks.py  — triggered by Redis keyspace notification
from celery import shared_task
import redis, json

@shared_task
def handle_heartbeat_expiry(channel_name: str):
    r = redis.from_url("redis://localhost")
    ops_raw = r.hget(f"ondisconnect:{channel_name}", "ops")
    if ops_raw:
        ops = json.loads(ops_raw)
        for op in ops:
            # import and call your write function
            from .services.write import write_to_tree
            write_to_tree(op["db"], op["path"], op["value"], op["op_type"])
    r.delete(f"ondisconnect:{channel_name}")
```

**Redis keyspace notification subscriber** (run as a separate management command or Celery beat task):

```python
# management/commands/watch_presence.py
import redis, json
from django.core.management.base import BaseCommand
from myapp.celery_tasks import handle_heartbeat_expiry

class Command(BaseCommand):
    def handle(self, *args, **options):
        r = redis.from_url("redis://localhost")
        r.config_set("notify-keyspace-events", "Ex")  # expired events
        pubsub = r.pubsub()
        pubsub.psubscribe("__keyevent@0__:expired")
        for msg in pubsub.listen():
            if msg["type"] == "pmessage":
                key = msg["data"].decode()
                if key.startswith("presence:hb:"):
                    channel_name = key[len("presence:hb:"):]
                    handle_heartbeat_expiry.delay(channel_name)
```

**Synthetic `/.info/connected`** — send on WS connect:

```python
# In RTDBConsumer.connect():
await self.send(json.dumps({
    "event": "put",
    "path": "/.info/connected",
    "data": True
}))
```

**Install:** `pip install redis celery django-celery-beat`

---

### 5. Offline Behavior and Local Persistence

#### What Firebase Does

The RTDB SDK caches all active listener data in memory. On mobile (iOS/Android), calling `setPersistenceEnabled(true)` writes the cache to disk using LevelDB. On web, `enableIndexedDbPersistence()` writes to IndexedDB. Pending writes are queued locally and applied optimistically (the local cache reflects the write immediately, before server confirmation). On reconnect, the queue is replayed, and the server's authoritative state is merged.

#### Django Rebuild — Client-Side Concern

This is implemented in the **client SDK**, not the server. Build a thin JS/TS client that wraps the WebSocket connection:

```typescript
// client/rtdb-client.ts (conceptual)
import Dexie from "dexie";  // npm install dexie

const localDb = new Dexie("RTDBOfflineCache");
localDb.version(1).stores({
  cache: "path, value, updatedAt",
  pendingWrites: "++id, path, value, opType, ts"
});

class RTDBClient {
  private ws: WebSocket | null = null;
  private listeners = new Map<string, Set<(val: unknown) => void>>();

  onValue(path: string, cb: (v: unknown) => void) {
    if (!this.listeners.has(path)) this.listeners.set(path, new Set());
    this.listeners.get(path)!.add(cb);
    // Return cached value immediately from IndexedDB
    localDb.table("cache").get(path).then(row => { if (row) cb(row.value); });
    this.ws?.send(JSON.stringify({ action: "subscribe", path }));
  }

  async set(path: string, value: unknown) {
    // Optimistic local update
    await localDb.table("cache").put({ path, value, updatedAt: Date.now() });
    const pending = await localDb.table("pendingWrites").add(
      { path, value, opType: "set", ts: Date.now() }
    );
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: "set", path, data: value }));
      await localDb.table("pendingWrites").delete(pending);
    }
    // If offline, replayed on reconnect
  }
}
```

On reconnect, the client replays all rows in `pendingWrites` in timestamp order, then subscribes to all active paths and merges the server's authoritative state.

The server must be idempotent: assign **client-generated push IDs** to writes so retries don't create duplicates.

---

### 6. Push IDs (Auto-Generated Lexicographic Keys)

#### What Firebase Does

```javascript
const newRef = push(ref(db, '/messages'));
// newRef.key => "-NxK2zABCDEFGHIJKL"
set(newRef, { text: "hello", uid: "user1" });
```

Push IDs are 20-character base-64 strings: 8 chars of millisecond timestamp (big-endian) + 12 random chars. They sort lexicographically in chronological order, enabling `orderByKey()` to return messages in insertion order without a sequence number.

#### Django Rebuild

```python
# utils/pushid.py
import time, random, string

PUSH_CHARS = "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"

_last_push_time = 0
_last_rand_chars = [0] * 12

def generate_push_id() -> str:
    global _last_push_time, _last_rand_chars
    now = int(time.time() * 1000)
    duplicate_time = now == _last_push_time
    _last_push_time = now

    time_stamp_chars = [""] * 8
    for i in range(7, -1, -1):
        time_stamp_chars[i] = PUSH_CHARS[now % 64]
        now //= 64

    result = "".join(time_stamp_chars)

    if not duplicate_time:
        _last_rand_chars = [random.randint(0, 63) for _ in range(12)]
    else:
        for i in range(11, -1, -1):
            if _last_rand_chars[i] == 63:
                _last_rand_chars[i] = 0
            else:
                _last_rand_chars[i] += 1
                break

    result += "".join(PUSH_CHARS[c] for c in _last_rand_chars)
    return result
```

Alternatively, use `pip install python-ksuid` for KSUID (also lexicographic + time-sortable, simpler).

---

### 7. Shallow Queries and Query Parameters

#### What Firebase Does

```bash
# Shallow: return only the immediate child keys (values replaced with true)
GET /users.json?shallow=true
# → { "uid1": true, "uid2": true }

# Ordered + filtered query
GET /messages.json?orderBy="ts"&limitToLast=50&startAt=1700000000000
```

Supported query params (REST):
| Parameter | Meaning |
|---|---|
| `shallow=true` | Return only immediate keys, values become `true` |
| `orderBy="$key"` | Sort by push ID key |
| `orderBy="$value"` | Sort by primitive value |
| `orderBy="childKey"` | Sort by a child property |
| `limitToFirst=N` | First N results |
| `limitToLast=N` | Last N results |
| `startAt=val` | Inclusive lower bound |
| `endAt=val` | Inclusive upper bound |
| `equalTo=val` | Exact match |

**Constraints:** Only ONE `orderBy` per query. Cannot combine `limitToFirst` + `limitToLast`. Shallow cannot be combined with filters. The REST API returns an unsorted JSON object (ordering is a client-side re-sort).

#### Django Rebuild

```python
# views.py (DRF ViewSet excerpt)
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import connection
import json

class TreeViewSet(viewsets.ViewSet):

    def retrieve(self, request, db_name=None, path=""):
        path_parts = [p for p in path.strip("/").split("/") if p]
        shallow = request.query_params.get("shallow") == "true"
        order_by = request.query_params.get("orderBy")
        limit_first = request.query_params.get("limitToFirst")
        limit_last = request.query_params.get("limitToLast")
        start_at = request.query_params.get("startAt")
        end_at = request.query_params.get("endAt")
        equal_to = request.query_params.get("equalTo")

        value = get_at_path(db_name, path_parts)

        if shallow and isinstance(value, dict):
            return Response({k: True for k in value.keys()})

        if order_by and isinstance(value, dict):
            items = list(value.items())

            if order_by == "$key":
                items.sort(key=lambda x: x[0])
            elif order_by == "$value":
                items.sort(key=lambda x: x[1] if not isinstance(x[1], dict) else "")
            else:
                # orderBy child key
                items.sort(key=lambda x: (x[1] or {}).get(order_by, "") if isinstance(x[1], dict) else "")

            # Apply filters
            if start_at:
                sv = json.loads(start_at)
                items = [(k, v) for k, v in items
                         if (v.get(order_by, "") if isinstance(v, dict) else v) >= sv]
            if end_at:
                ev = json.loads(end_at)
                items = [(k, v) for k, v in items
                         if (v.get(order_by, "") if isinstance(v, dict) else v) <= ev]
            if equal_to:
                etv = json.loads(equal_to)
                items = [(k, v) for k, v in items
                         if (v.get(order_by, "") if isinstance(v, dict) else v) == etv]
            if limit_first:
                items = items[:int(limit_first)]
            if limit_last:
                items = items[-int(limit_last):]

            value = dict(items)

        return Response(value)
```

**Gotcha:** For production query performance, extract frequently-queried child fields into separate indexed PostgreSQL columns, or use `jsonb_path_query` with GIN indexes. Pure JSONB path queries without indexes will full-scan.

---

### 8. Multi-Path Atomic Updates

#### What Firebase Does

```javascript
// Atomically update denormalized copies in one transaction
const updates = {
  `/posts/${postId}/title`: "New Title",
  `/user-posts/${uid}/${postId}/title`: "New Title",
  `/feed/${followerId}/${postId}/title`: "New Title",
};
update(ref(db), updates);  // all-or-nothing
```

If any path fails (permission denied, validation error), none are applied.

#### Django Rebuild

Shown in §3 above (`multi_path_update`). The key is `django.db.transaction.atomic()`:

```python
def multi_path_update(db_name: str, updates: dict):
    with transaction.atomic():
        # Lock the row for the duration of all updates
        tree_row = RealtimeTree.objects.select_for_update().get(db_name=db_name)
        for path, value in updates.items():
            path_parts = [p for p in path.strip("/").split("/") if p]
            set_at_path(db_name, path_parts, value)
    # Broadcast after commit
    for path, value in updates.items():
        path_parts = [p for p in path.strip("/").split("/") if p]
        _broadcast_to_subscribers(db_name, path, "put", value, path_parts)
```

`SELECT FOR UPDATE` on the `RealtimeTree` row serializes concurrent writes within a shard. For cross-shard atomic updates (not supported natively by RTDB either), you would need a distributed transaction or a saga pattern.

---

### 9. Security Rules

#### What Firebase Does

```json
{
  "rules": {
    "users": {
      "$uid": {
        ".read": "$uid === auth.uid",
        ".write": "$uid === auth.uid",
        ".validate": "newData.hasChildren(['name', 'email'])"
      }
    },
    "public": {
      ".read": true,
      ".write": "auth != null"
    }
  }
}
```

Rules are evaluated server-side on every operation. `$uid` is a wildcard that captures the path segment. Rules **cascade downward** — a `.read: true` at `/public` grants read on all descendants. Rules do NOT filter data — if a client reads `/users`, the entire node is returned or denied, not partially filtered.

#### Django Rebuild

Use DRF permission classes with a path-ACL model:

```python
# models.py
class PathACL(models.Model):
    db_name = models.SlugField()
    path_pattern = models.CharField(max_length=512)  # e.g. "/users/$uid"
    read_authenticated = models.BooleanField(default=False)
    read_owner = models.BooleanField(default=False)   # $uid == request.user.id
    write_authenticated = models.BooleanField(default=False)
    write_owner = models.BooleanField(default=False)

# permissions.py
from rest_framework.permissions import BasePermission
import re, fnmatch

class RTDBPathPermission(BasePermission):
    def has_permission(self, request, view):
        path = view.kwargs.get("path", "")
        user = request.user
        acl = self._match_acl(path)
        if request.method in ("GET", "HEAD"):
            return (acl.read_authenticated and user.is_authenticated) or \
                   (acl.read_owner and self._is_owner(path, user))
        return (acl.write_authenticated and user.is_authenticated) or \
               (acl.write_owner and self._is_owner(path, user))
```

For `.validate` semantics, use DRF serializer validators that inspect `newData` shape before committing.

**Install:** `pip install django-rules` (predicate-based permission system that composes well).

---

### 10. Sharding Across Multiple Database Instances

#### What Firebase Does

Each RTDB instance is capped at:
- **200,000 concurrent WebSocket connections**
- **1 GB free storage** (then $5/GB/month)
- **Up to 1,000 instances per project**

Sharding is explicit: the app assigns each user/session to a database URL. There is no transparent cross-shard query — the client must know which shard it belongs to.

```javascript
const db = getDatabase(app, "https://shard-3.firebaseio.com");
```

#### Django Rebuild

```python
# settings.py — multiple database shards
DATABASES = {
    "default": {"ENGINE": "django.db.backends.postgresql", "NAME": "rtdb_shard0", ...},
    "shard1":  {"ENGINE": "django.db.backends.postgresql", "NAME": "rtdb_shard1", ...},
    "shard2":  {"ENGINE": "django.db.backends.postgresql", "NAME": "rtdb_shard2", ...},
}

# utils/shard.py
import hashlib

SHARD_NAMES = ["default", "shard1", "shard2"]

def get_shard(db_name: str) -> str:
    h = int(hashlib.md5(db_name.encode()).hexdigest(), 16)
    return SHARD_NAMES[h % len(SHARD_NAMES)]
```

For WebSocket horizontal scaling:
- Deploy N Daphne/Uvicorn workers behind Nginx with `upstream` block using `ip_hash` (sticky sessions per client, or let channels-redis handle fan-out across workers).
- Each Channels worker uses the same channels-redis layer, so `group_send` reaches all consumers regardless of which worker they live on.

```nginx
upstream rtdb_ws {
    least_conn;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    location /ws/ {
        proxy_pass http://rtdb_ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

---

### 11. RTDB vs Firestore Tradeoffs

| Dimension | RTDB | Firestore | Django Equivalent |
|---|---|---|---|
| Data model | Single JSON tree | Collections + Documents | JSONB tree | Normalized ORM tables |
| Query power | One orderBy, no compound filters | Rich: multiple where/orderBy, compound indexes | JSONB path queries | Full SQL with indexes |
| Scaling unit | 200k connections/instance, shard manually | Automatic horizontal scaling | Django workers + Redis; shard by DB | N workers auto-scale |
| Latency | ~10-50 ms (WebSocket, in-memory) | ~50-200 ms (RPC + Bigtable) | ~5-20 ms local | ~10-50 ms |
| Offline | LevelDB (mobile), IndexedDB (web) | Automatic multi-tab IndexedDB | Custom client SDK + IndexedDB | Supabase-style client |
| Pricing | $5/GB/mo stored, $1/GB downloaded | $0.06/100k reads, $0.18/100k writes, $0.18/GB/mo | VPS storage ~$0.10/GB/mo | PostgreSQL storage |
| Best for | Presence, simple chat, live counters | Collections with rich queries, multi-field filters | Presence/pubsub use cases | General app backend |

**Verdict for new projects:** Use the Firestore-style approach (normalized Django ORM) for most features. Use the RTDB-style JSONB tree only for presence, live cursors, and counters where the JSON tree model is a natural fit and you need sub-50 ms fan-out.

---

### 12. Pricing Model

| Tier | Storage | Downloads | Connections |
|---|---|---|---|
| Firebase Spark (free) | 1 GB | 10 GB/month | 100 simultaneous (Spark limit) |
| Firebase Blaze | $5/GB/month | $1/GB | 200,000 per instance |
| Self-hosted (DigitalOcean) | ~$0.10/GB/month | ~$0.01/GB (bandwidth) | Limited by Nginx/Redis/worker tuning |

At 10 GB stored + 100 GB/month downloaded: Firebase Blaze = ~$145/mo. Self-hosted (2 vCPU VPS + managed Redis) = ~$25-40/mo. Firebase wins on ops overhead; self-hosted wins on cost at scale.

---

### Infrastructure Summary (Docker Compose)

```yaml
# docker-compose.yml (RTDB service slice)
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: rtdb
      POSTGRES_USER: rtdb
      POSTGRES_PASSWORD: rtdb_secret
    volumes:
      - postgres_data:/var/lib/postgresql/data
    command: >
      postgres -c "shared_buffers=512MB"
               -c "work_mem=16MB"
               -c "max_connections=500"

  redis:
    image: redis:7-alpine
    command: >
      redis-server
        --notify-keyspace-events Ex
        --maxmemory 1gb
        --maxmemory-policy allkeys-lru

  daphne:
    build: .
    command: daphne -b 0.0.0.0 -p 8000 myproject.asgi:application
    depends_on: [db, redis]
    environment:
      DATABASE_URL: postgres://rtdb:rtdb_secret@db/rtdb
      REDIS_URL: redis://redis:6379/0

  celery:
    build: .
    command: celery -A myproject worker -l info -Q ondisconnect
    depends_on: [db, redis]

  presence_watcher:
    build: .
    command: python manage.py watch_presence
    depends_on: [redis]

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on: [daphne]

volumes:
  postgres_data:
```

---

### Gotchas and Hard Parts

| Problem | Firebase solution | Django self-hosted solution |
|---|---|---|
| Fan-out to 200k connections | Google's proprietary infrastructure, in-memory subscriptions | `channels-redis` pub-sub; add more Daphne workers + Redis Cluster for >50k concurrent |
| Dirty disconnect detection | Server owns the TCP stack; knows immediately | Redis heartbeat TTL + keyspace notifications; ~90s lag on dirty disconnect (tunable) |
| Ordering without compound index | `.priority` field or push IDs | Add a `GENERATED ALWAYS AS` PostgreSQL column for extracted sort keys + B-tree index |
| Cross-shard queries | Not supported natively | Not supported; document this as a design constraint |
| Offline queue deduplication | Firebase SDK handles client-side | Require clients to send client-generated idempotency keys (push IDs) |
| Security rule expressiveness | Declarative JSON with `auth.uid`, `data`, `newData` | DRF permission classes are imperative; more code but also more powerful |
| WebSocket scalability beyond one Redis instance | Managed by Google | Redis Cluster or use `channels-redis` with `RedisPubSubChannelLayer` (supports Cluster) |

### OSS Alternative Approaches

- **Supabase Realtime** (Elixir + Phoenix Channels + PostgreSQL logical replication): excellent model to study. Uses `pg_logical` to stream WAL changes; presence via CRDT-like maps. Source: `github.com/supabase/realtime`.
- **PocketBase** (Go + SQLite + SSE): single binary, uses SQLite WAL mode + SSE for real-time. Proves that a single-process tree-store + SSE can handle moderate load (~5k concurrent) without Redis.
- **Appwrite Realtime** (PHP + Redis pub-sub + WebSockets): closest architecture to the Django approach described here. MariaDB stores data; Redis handles pub-sub; a dedicated realtime container fans out WS messages.
- **RxDB** (client-side): for the offline-first client SDK layer, RxDB's replication protocol (push/pull/live with EventSource) is a ready-to-use open-source implementation that can sync against the Django backend described here.

## Firebase Data Connect (PostgreSQL + GraphQL)

> **Naming note (2026):** Firebase Data Connect reached GA in April 2025 and was rebranded to **Firebase SQL Connect** in April 2026. All features described here apply to both names; the product is identical. "FDC" is used throughout as a shorthand.

---

### What it is

FDC is a managed GraphQL-over-PostgreSQL Backend-as-a-Service layer built on **Cloud SQL for PostgreSQL**. It is Firebase's answer to the question "what if Firebase felt like a relational database?" — and it is the closest Firebase product to a Django + Postgres backend. Developers define a GraphQL SDL schema, write named query/mutation operation files, and Firebase generates:

1. PostgreSQL DDL (tables, FK constraints, indexes)
2. A secured GraphQL API endpoint
3. Fully-typed client SDKs for Web (TypeScript), Flutter (Dart), iOS (Swift), Android (Kotlin)

The three conceptual pillars are **Services** (one per Firebase project, wraps a Cloud SQL instance), **Schemas** (the SDL .gql files), and **Connectors** (directories of named operation .gql files scoped per client/role).

---

### Sub-feature inventory

#### 1. Managed Cloud SQL for PostgreSQL

**What it does:** Firebase provisions and manages a Cloud SQL for PostgreSQL instance per project. Connection pooling, backups, patching, and scaling are handled by Google. Developers never write a connection string in client code.

**Under the hood:** Runs on standard Cloud SQL Enterprise or Enterprise Plus tier. The Data Connect service layer manages connections via a Google-internal proxy (similar to Cloud SQL Auth Proxy). AlloyDB support was community-requested as of mid-2026 but not yet GA — FDC is tightly coupled to Cloud SQL because it manages schema migrations, IAM, and the connection lifecycle itself.

**Django rebuild:**

```python
# settings.py — point Django at your own Postgres
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": "5432",
        "CONN_MAX_AGE": 60,  # persistent connections
    }
}
```

Add **PgBouncer** in transaction mode in front of PostgreSQL for connection pooling at scale. Use Docker Compose locally:

```yaml
# docker-compose.yml (excerpt)
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: myapp
      POSTGRES_PASSWORD: secret
  pgbouncer:
    image: edoburu/pgbouncer:latest
    environment:
      DATABASE_URL: "postgres://myapp:secret@db/myapp"
      POOL_MODE: transaction
```

**Packages:** `psycopg[binary]` (Django adapter, replaces `psycopg2-binary` for Postgres 16+), PgBouncer container for pooling. For spatial: `django.contrib.gis` + PostGIS.

---

#### 2. GraphQL SDL Schema → PostgreSQL DDL

**What it does:** You write `.gql` schema files using standard GraphQL SDL + FDC-specific directives. On `firebase deploy`, the CLI diffs the schema against the live database and applies migrations.

**Key directives:**

| Directive | Purpose | Postgres equivalent |
|---|---|---|
| `@table(name, key)` | Maps type to table, declares PK | `CREATE TABLE`, `PRIMARY KEY` |
| `@col(name, dataType)` | Renames column, sets type | Column alias, `varchar(n)` |
| `@default(expr)` | Server-side default | `DEFAULT` / `gen_random_uuid()` |
| `@ref` | Declares FK relationship | `FOREIGN KEY REFERENCES` |
| `@unique` | Unique constraint | `UNIQUE` |
| `@index` | Adds index | `CREATE INDEX` |

**Example schema:**

```graphql
# schema.gql
type Movie @table(name: "movie", key: "id") {
  id: UUID! @col(name: "movie_id") @default(expr: "uuidV4()")
  title: String!
  releaseYear: Int
  genre: String @col(dataType: "varchar(20)")
  rating: Int
  description: String
}

type Actor @table {
  id: UUID! @default(expr: "uuidV4()")
  name: String! @col(dataType: "varchar(30)")
}

# Explicit many-to-many join table
type MovieActor @table(key: ["movie", "actor"]) {
  movie: Movie!    # implicitly adds movieId: UUID! FK column
  actor: Actor!    # implicitly adds actorId: UUID! FK column
  role: String!
}
```

**Under the hood:** The FDC compiler translates these types to `CREATE TABLE` / `ALTER TABLE` SQL. It also generates auto-traversal fields on each type (`actor.movies_via_actormovie`, `movie.actors_on_movies`) that become SQL JOINs at query time.

**Django rebuild:** Django models are the schema source of truth. `makemigrations` + `migrate` handles DDL.

```python
# models.py
import uuid
from django.db import models

class Movie(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    release_year = models.IntegerField(null=True)
    genre = models.CharField(max_length=20, null=True)
    rating = models.IntegerField(null=True)
    description = models.TextField(null=True)

    class Meta:
        db_table = "movie"

class Actor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30)

class MovieActor(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="actor_links")
    actor = models.ForeignKey(Actor, on_delete=models.CASCADE, related_name="movie_links")
    role = models.CharField(max_length=50)

    class Meta:
        unique_together = [["movie", "actor"]]
```

Strawberry-Django introspects these models to produce a matching GraphQL schema:

```python
# types.py
import strawberry_django
from strawberry_django import auto
from . import models

@strawberry_django.type(models.Movie)
class MovieType:
    id: auto
    title: auto
    release_year: auto
    genre: auto
    rating: auto
    description: auto
    actor_links: list["MovieActorType"]
```

**Packages:** `strawberry-graphql-django` (primary), `graphene-django` (alternative), `ariadne` (schema-first SDL approach matching FDC's mental model most closely).

---

#### 3. Connectors: Named Operations with Access Control

**What it does:** A Connector is a directory of `.gql` operation files. Each file contains named queries and mutations. Clients can only call operations defined in a connector — no arbitrary ad-hoc GraphQL allowed. Each connector is deployed independently and maps to a generated SDK bundle.

**The `@auth` directive** enforces access control per operation:

| Level | Meaning |
|---|---|
| `PUBLIC` | No auth required |
| `USER` | Valid Firebase Auth JWT required |
| `USER_ANON` | Authenticated or anonymous user |
| `NO_ACCESS` | Only callable from Admin SDK (server-side) |
| Custom CEL | `@auth(expr: "auth.uid == vars.userId")` |

**Example connector:**

```graphql
# connector/queries.gql

query ListMovies @auth(level: PUBLIC) {
  movies {
    id
    title
    imageUrl
    genre
  }
}

query MyReviews @auth(level: USER) {
  user(key: { id_expr: "auth.uid" }) {
    reviews: reviews_on_user {
      movie { name }
      rating
    }
  }
}
```

```graphql
# connector/mutations.gql

mutation CreateNewPost($title: String!, $content: String!) @auth(level: USER) {
  post_insert(data: {
    author_id_expr: "auth.uid",
    title: $title,
    content: $content,
    status: "draft"
  })
}

# Multi-table atomic with @check guard
mutation SponsorAuthor($authorId: UUID!, $tipAmount: Int!) @auth(level: USER) @transaction {
  reader_update(id_expr: "auth.uid", data: {
    wallet_coins_update: { inc: -$tipAmount }
  }) @check(expr: "this.wallet_coins >= $tipAmount", message: "Insufficient coins")

  author_update(id: $authorId, data: {
    earned_coins_update: { inc: $tipAmount }
  })
}
```

**Under the hood:** The connector config maps to a gRPC service endpoint. Each connector has a fixed set of operations registered at deploy time. The server validates the auth JWT, evaluates CEL expressions, and routes to auto-generated SQL resolvers.

**Django rebuild:**

```python
# schema.py — Strawberry GraphQL with permission classes

import strawberry
import strawberry_django
from strawberry.permission import BasePermission
from strawberry.types import Info

class IsAuthenticated(BasePermission):
    message = "User is not authenticated"
    def has_permission(self, source, info: Info, **kwargs) -> bool:
        return info.context.request.user.is_authenticated

@strawberry.type
class Query:
    @strawberry.field
    def list_movies(self) -> list[MovieType]:
        return Movie.objects.all()  # PUBLIC — no permission class

    @strawberry.field(permission_classes=[IsAuthenticated])
    def my_reviews(self, info: Info) -> list[ReviewType]:
        return Review.objects.filter(user=info.context.request.user)

@strawberry.type
class Mutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def create_post(self, info: Info, title: str, content: str) -> PostType:
        return Post.objects.create(
            author=info.context.request.user,
            title=title,
            content=content,
            status="draft"
        )

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def sponsor_author(self, info: Info, author_id: uuid.UUID, tip_amount: int) -> bool:
        from django.db import transaction
        with transaction.atomic():
            reader = Reader.objects.select_for_update().get(user=info.context.request.user)
            if reader.wallet_coins < tip_amount:
                raise ValueError("Insufficient coins")
            reader.wallet_coins -= tip_amount
            reader.save()
            Author.objects.filter(id=author_id).update(earned_coins=F("earned_coins") + tip_amount)
        return True
```

To enforce connector-style operation whitelisting (no arbitrary queries), add persisted-query middleware that only allows registered operation names.

**Packages:** `strawberry-graphql-django`, `django-graphql-jwt` or `firebase-admin` for JWT validation, `djangorestframework` for REST connector equivalent.

---

#### 4. Relational Queries: Joins, Traversal, N+1 prevention

**What it does:** FDC auto-generates traversal fields from FK relationships. `movie.actors_on_movies` and `actor.movies_via_actormovie` are available without writing any join logic. GraphQL query traversal compiles to SQL JOINs automatically.

**Example:**

```graphql
query GetMovieWithActors($id: UUID!) @auth(level: PUBLIC) {
  movie(id: $id) {
    title
    releaseYear
    actors_on_movies {
      actor { name }
      role
    }
  }
}
```

**Django rebuild:** Strawberry-Django handles nested types via `select_related()` and `prefetch_related()`. Use DataLoader to prevent N+1:

```python
# dataloaders.py
from strawberry_django.optimizer import DjangoOptimizerExtension

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[DjangoOptimizerExtension],  # auto-optimizes related queries
)
```

**Packages:** `strawberry-graphql-django` with `DjangoOptimizerExtension` (built-in, handles select_related + prefetch_related automatically), `graphene-django-optimizer` for Graphene.

---

#### 5. Query Filters, Ordering, Pagination

**What it does:** Auto-generated filter input types on every query field with operators: `_eq`, `_gt`, `_lt`, `_gte`, `_lte`, `_like`, `_ilike`, `_in`, `isNull`. Ordering via `orderBy: [{field: ASC/DESC}]`. Pagination via `limit`, `offset`, or cursor-based `after`/`before`.

```graphql
query FilteredMovies($genre: String, $minRating: Int) @auth(level: PUBLIC) {
  movies(
    where: { genre: { _eq: $genre }, rating: { _gte: $minRating } }
    orderBy: [{ releaseYear: DESC }]
    limit: 20
    offset: 0
  ) {
    id
    title
    rating
  }
}
```

**Django rebuild:**

```python
# filters.py
import django_filters
from .models import Movie

class MovieFilter(django_filters.FilterSet):
    min_rating = django_filters.NumberFilter(field_name="rating", lookup_expr="gte")
    genre = django_filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = Movie
        fields = ["genre", "min_rating"]
```

With Strawberry: use `strawberry_django.filter` decorator which auto-generates filter input types from model fields including all lookup variants.

**Packages:** `strawberry-graphql-django` (filters/ordering/pagination built-in), `django-filter`, relay connection for cursor pagination.

---

#### 6. Auto-generated CRUD Mutations

**What it does:** For every `@table` type, FDC generates: `movie_insert`, `movie_upsert`, `movie_update`, `movie_delete`, `movies_update_many`, `movies_delete_many`. These accept strongly-typed input objects. No boilerplate.

**Django rebuild:** `strawberry-graphql-django` provides `@strawberry_django.mutation` with `create`, `update`, `delete` helpers:

```python
@strawberry.type
class Mutation:
    create_movie: MovieType = strawberry_django.mutations.create(MovieInput)
    update_movie: MovieType = strawberry_django.mutations.update(MoviePartialInput)
    delete_movie: MovieType = strawberry_django.mutations.delete()
```

**Packages:** `strawberry-graphql-django` (CRUD mutations), `graphene-django-extras` for Graphene equivalent.

---

#### 7. Native SQL Mode (`_execute` / `@sql` directive)

**What it does** (SQL Connect, March 2026): Developers embed parameterized raw SQL directly in `.gql` operation files using `_execute(sql: "...", params: [...])`. SQL is server-hardcoded at deploy time — clients cannot inject SQL. `{_expr: "auth.uid"}` injects server-side context. Enables CTEs, window functions, PostGIS, `RANK()`, `PARTITION BY`, bulk operations, and any Postgres extension without fighting GraphQL type constraints. Returns `Any` (JSON) — no compile-time SDK typing.

```graphql
# Conditional update with auth-injected param
mutation UpdatePostTitle($postId: Int!, $newTitle: String!) @auth(level: USER) {
  _execute(
    sql: """
      UPDATE posts
      SET title = $2
      WHERE id = $1 AND author_id = $3
    """,
    params: [$postId, $newTitle, {_expr: "auth.uid"}]
  )
}

# CTE for atomic delete + reassign
mutation DeleteAccountAndAnonymizePosts() @auth(level: USER) {
  _execute(
    sql: """
      WITH deleted_user AS (
        DELETE FROM users WHERE id = $1 RETURNING id
      )
      UPDATE posts
      SET author_id = 'system-anon'
      WHERE author_id IN (SELECT id FROM deleted_user)
    """,
    params: [{_expr: "auth.uid"}]
  )
}
```

**Security model:** SQL strings are hardcoded in deployed `.gql` files (validated at deploy time). Params are bound via positional placeholders — no string concatenation. `{_expr: "auth.uid"}` is resolved server-side only.

**Django rebuild:** This is Django's native mode. `cursor.execute()` with parameterized queries:

```python
@strawberry.mutation(permission_classes=[IsAuthenticated])
def delete_account_and_anonymize(self, info: Info) -> bool:
    user_id = info.context.request.user.id
    with connection.cursor() as cursor:
        cursor.execute("""
            WITH deleted_user AS (
                DELETE FROM users WHERE id = %s RETURNING id
            )
            UPDATE posts
            SET author_id = 'system-anon'
            WHERE author_id IN (SELECT id FROM deleted_user)
        """, [user_id])
    return True
```

Django provides this natively — no extra packages needed. PostGIS spatial queries, window functions, and any Postgres extension work identically.

**Packages:** `django.db.connection.cursor()` (built-in), `django.contrib.gis` for PostGIS, `psycopg` for advanced Postgres types.

---

#### 8. Typed Client SDK Generation

**What it does:** `firebase dataconnect:sdk:generate` reads connector `.gql` files and emits typed client code. Web → TypeScript interfaces + async functions. Flutter → Dart classes. iOS → Swift structs. Android → Kotlin data classes. Re-run after any schema/connector change. Also supports `--target=admin` for a server-side Node.js/Python SDK with elevated access (bypasses NO_ACCESS guards).

**Generated Web SDK shape:**

```typescript
// Auto-generated — do not edit
import { executeQuery } from 'firebase/data-connect';
import { connectorConfig } from './connector';

export interface Movie { id: string; title: string; genre: string | null }
export interface ListMoviesResponse { movies: Movie[] }

export function listMovies(): QueryRef<ListMoviesResponse, undefined> {
  return executeQuery(connectorConfig, 'ListMovies', undefined);
}
```

**Django rebuild:** Use `graphql-codegen` (npm) pointing at your Django GraphQL endpoint:

```yaml
# codegen.yml
schema: "http://localhost:8000/graphql"
documents: "src/**/*.graphql"
generates:
  src/generated/graphql.ts:
    plugins:
      - typescript
      - typescript-operations
      - typescript-react-query   # or typescript-urql
    config:
      fetcher: fetch
```

For Dart/Flutter: `ferry_generator` or `artemis`. For Swift: Apollo iOS. For Kotlin: Apollo Kotlin. The key difference: you maintain separate `.graphql` operation files client-side (same pattern as FDC connectors).

**Packages (client-side npm):** `@graphql-codegen/cli`, `@graphql-codegen/typescript`, `@graphql-codegen/typescript-operations`, `@graphql-codegen/typescript-react-query`

**Packages (Python server, for admin SDK analog):** `ariadne-codegen` (pip) generates typed Python clients from a schema + operations.

---

#### 9. Event Triggers on Mutations (via Eventarc)

**What it does** (Nov 2025): After a named mutation executes, Data Connect publishes an Eventarc event. Cloud Functions subscribe via `onMutationExecuted`. Filter expressions narrow which mutations fire a trigger. Payload includes mutation args and auth context. Enables: send email on signup, charge Stripe on subscription mutation, index data in Algolia on upsert.

```javascript
// Cloud Function (Node.js)
const { onMutationExecuted } = require('firebase-functions/v2/dataconnect');

exports.onMovieCreated = onMutationExecuted({
  operation: 'CreateMovie',
  filters: [{ field: 'genre', operator: '==', value: 'Horror' }]
}, (event) => {
  const { args, auth } = event.data;
  // Send notification, update search index, etc.
});
```

**Django rebuild:** Django signals + Celery for decoupled async triggers:

```python
# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Movie
from .tasks import on_movie_created

@receiver(post_save, sender=Movie)
def movie_post_save(sender, instance, created, **kwargs):
    if created:
        on_movie_created.delay(instance.id)  # Celery async task

# tasks.py
from celery import shared_task

@shared_task
def on_movie_created(movie_id):
    movie = Movie.objects.get(id=movie_id)
    # Send email, call Stripe, update Algolia, etc.
```

For DB-level triggers (fires even on bulk ORM operations): `django-pgtrigger` creates Postgres triggers that enqueue Celery tasks via `NOTIFY`.

**Packages:** `celery[redis]` (pip), `django-celery-results`, `django-pgtrigger` (pip install django-pgtrigger), `celery-once` for deduplication.

---

#### 10. Realtime Query Subscriptions (`@refresh` directive)

**What it does** (SQL Connect, April 2026): Clients subscribe to a named query. The server pushes updated results when a CEL-bound condition fires. `@refresh(onMutationExecuted: {operation: "UpdateUser", condition: "mutation.auth.uid == query.auth.uid"})` triggers per-user updates. Also supports `@refresh(interval: "30s")` for periodic polling. Server uses Postgres polling + change detection (not CDC/logical replication).

```graphql
query UserProfile @auth(level: USER)
@refresh(
  onMutationExecuted: {
    operation: "UpdateUser"
    condition: "mutation.auth.uid == query.auth.uid"
  }
) {
  user(id_expr: "auth.uid") {
    id
    name
    avatarUrl
  }
}
```

**Django rebuild:** Django Channels + Strawberry subscriptions:

```python
# subscriptions.py
import strawberry
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def user_profile(self, info: Info) -> AsyncGenerator[UserType, None]:
        user = info.context.request.user
        channel_layer = get_channel_layer()
        # subscribe to user-specific channel
        async with channel_layer.listen(f"user_{user.id}") as events:
            async for event in events:
                yield await UserType.from_id(user.id)

# In mutation resolver — push update after profile change:
def update_user(self, info: Info, **kwargs) -> UserType:
    user = info.context.request.user
    # ... update ...
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user.id}",
        {"type": "profile.updated"}
    )
    return updated_user
```

**Packages:** `channels[daphne]` (pip), `strawberry-channels` (pip install strawberry-channels), `channels-redis` (pip install channels-redis), Django ASGI deployment via Daphne or Uvicorn.

---

#### 11. Offline Caching

**What it does** (SQL Connect, April 2026): Client SDKs cache the last subscription result locally (IndexedDB on Web, SQLite on mobile). Apps display cached data on reconnect with a stale indicator. Tied to the `@refresh` subscription system.

**Django rebuild:** This is entirely a client-side concern — your Django backend needs no changes:

- **React/Web:** TanStack Query (`@tanstack/react-query`) + `react-query-persist-client` with IndexedDB adapter. stale-while-revalidate pattern gives identical UX to FDC offline cache.
- **Flutter:** Apollo Flutter or Ferry with SQLite persistence.
- **React Native:** Apollo Client + `apollo3-cache-persist`.

**Packages (npm):** `@tanstack/react-query`, `@tanstack/query-persist-client-core`, `@tanstack/query-async-storage-persister`

---

#### 12. Custom Resolvers (Experimental, April 2026)

**What it does:** Extend SQL Connect schema with Cloud Function-backed resolvers that integrate external APIs (Stripe, X/Twitter, BigQuery, Cloud Storage) alongside database operations. The custom resolver function returns data that can then be written to Cloud SQL via Native SQL. Client SDK still gets typed stubs.

```javascript
// Custom resolver example: verify tweet then award coins
resolvers: {
  mutation: {
    async boostFromTweet(_parent, args, context) {
      const tweet = await fetch(`https://api.x.com/2/tweets/${args.tweetId}`);
      if (!tweet.text.includes('#myapp')) throw new Error('Invalid tweet');
      // Then execute Native SQL to update DB
      await context.dataconnect.execute(
        'UPDATE users SET coins = coins + 10 WHERE id = $1',
        [context.auth.uid]
      );
    }
  }
}
```

**Django rebuild:** This is Django's natural mode — no special framework needed:

```python
@strawberry.mutation(permission_classes=[IsAuthenticated])
def boost_from_tweet(self, info: Info, tweet_url: str) -> bool:
    import httpx
    user = info.context.request.user
    response = httpx.get(f"https://api.x.com/2/tweets/{tweet_id}",
                         headers={"Authorization": f"Bearer {settings.X_TOKEN}"})
    if "#myapp" not in response.json()["data"]["text"]:
        raise ValueError("Tweet must include #myapp")
    with transaction.atomic():
        User.objects.filter(id=user.id).update(coins=F("coins") + 10)
    return True
```

**Packages:** `httpx` (pip install httpx) for async HTTP, `stripe` (pip install stripe), `google-cloud-bigquery` for BigQuery integration.

---

#### 13. Supported Scalar Types and pgvector

**FDC scalars → Postgres → Django field mapping:**

| FDC Scalar | Postgres Type | Django Field |
|---|---|---|
| `UUID` | `uuid` | `UUIDField` |
| `String` | `text` / `varchar` | `CharField`, `TextField` |
| `Int` | `int` | `IntegerField` |
| `Int64` | `bigint` | `BigIntegerField` |
| `Float` | `double precision` | `FloatField` |
| `Boolean` | `boolean` | `BooleanField` |
| `Date` | `date` | `DateField` |
| `Timestamp` | `timestamptz` | `DateTimeField` |
| `Any` | `jsonb` | `JSONField` |
| `Vector` | `vector` (pgvector) | `VectorField` (pgvector-django) |

```python
# pgvector example in Django
from pgvector.django import VectorField

class Document(models.Model):
    content = models.TextField()
    embedding = VectorField(dimensions=1536)  # OpenAI ada-002
    
# Semantic search query
from pgvector.django import CosineDistance
Document.objects.order_by(CosineDistance("embedding", query_embedding))[:10]
```

**Packages:** `pgvector-django` (pip install pgvector-django).

---

#### 14. Firebase Data Connect vs Firestore: When to Use Which

| Dimension | Firestore | Data Connect / SQL Connect |
|---|---|---|
| Data model | Document/collection, schema-free | Relational tables, strict schema |
| Real-time | Native (websocket CDC) | Added in 2026 via `@refresh` |
| Joins / relations | Fan-out queries, denormalization | Native SQL JOINs |
| ACID transactions | Single-doc atomic; multi-doc via batches | Full multi-table ACID transactions |
| Query flexibility | Limited (no full-text, no window functions) | Full SQL via Native SQL mode |
| Schema migrations | No schema, no migrations | Explicit SDL schema + CLI migrations |
| Auth integration | Security Rules (document-level) | `@auth` CEL on every operation |
| Offline | First-class, built-in | Client SDK cache (2026) |
| Best for | Mobile-first, realtime, schemaless | Relational apps, analytics, complex queries |

**Django analog:** Django + Postgres covers 100% of Data Connect's use cases. Firestore's document model has no direct Django equivalent — use Django + MongoDB (djongo/mongoengine) if you need that.

---

#### 15. Local Development and Emulator

**What it does:** `firebase emulators:start --only dataconnect` runs a local Data Connect service with an embedded Postgres instance. The VS Code Data Connect Toolkit extension adds schema editing, operation authoring, SDK generation preview, and an in-editor GraphQL explorer. Schema migrations are diffed and applied locally before hitting production.

**Django rebuild:**

```bash
# docker-compose up spins the full local stack
docker compose up -d

# Explore GraphQL schema interactively
# http://localhost:8000/graphql (Strawberry's built-in GraphiQL, DEBUG=True)

# Visualize Django model relationships
python manage.py graph_models myapp | dot -Tpng > schema.png

# Profile queries
# Add django-silk middleware and hit /silk/ for query timing
```

**Packages:** `django-extensions` (pip, for `graph_models`), `django-silk` (pip, for query profiling), `graphiql` (built into Strawberry in DEBUG mode).

---

### Pricing and Gotchas

**Firebase pricing (as of May 2026):**

| Dimension | Spark (free) | Blaze (pay-as-you-go) |
|---|---|---|
| Operations | 8,300/day | 250,000/month free, then **$0.90/million** |
| Cloud SQL instance | Free trial cluster (no payment info required) | From ~$9.37/month |
| Network egress | First 10 GiB/month free | Premium tier rates after |

One operation = one query or mutation regardless of how many tables it touches. A 10-table JOIN is still one operation.

**Key gotchas when using Firebase:**

1. **Schema migrations are irreversible by default.** FDC will refuse destructive migrations (column drops) unless you explicitly acknowledge. Django gives you full migration control.
2. **No arbitrary queries from clients.** Only connector-defined operations are callable — this is a security feature but limits dynamic query building. Django lets you expose a full GraphQL introspection endpoint in DEBUG mode.
3. **Native SQL returns `Any` (JSON).** No compile-time SDK type safety for `_execute` operations — you must validate JSON client-side. Django has the same trade-off when using raw SQL, but Python type hints + Pydantic can validate the response server-side.
4. **AlloyDB not yet supported.** FDC is locked to Cloud SQL. For AlloyDB (4x faster OLTP, 100x faster analytics), you need to self-host — which Django makes trivial.
5. **Connection limits.** Cloud SQL has hard connection limits per instance tier. PgBouncer (connection pooler) is not managed by FDC — you need to configure it separately. Django + PgBouncer solves this cleanly.
6. **Custom resolvers are experimental.** Integrating external APIs requires Cloud Functions overhead. Django resolvers call any SDK natively in-process.

---

### OSS Alternatives and Inspiration

| Tool | Approach | Relevance |
|---|---|---|
| **Supabase** | PostgREST (REST) + pg_graphql (extension) over Postgres | Closest managed OSS analog; fully self-hostable |
| **Nhost** | Hasura (GraphQL engine) + Postgres + Auth + Storage | GraphQL-first, self-hostable, closest to FDC DX |
| **Hasura v2/v3** | Schema introspection → instant GraphQL + subscriptions | Direct FDC competitor; self-hostable; v2 now legacy |
| **PostGraphile** | Postgres-first GraphQL schema generation | Lightest alternative; pure schema introspection |
| **Strawberry-Django** | Python-native GraphQL from Django models | Best Django-native DX; what this rebuild uses |
| **graphql-codegen** | Client SDK generation from any GraphQL schema | Replaces FDC's `sdk:generate` for any language |

**Recommended Django stack to match FDC DX end-to-end:**

```
Backend:    Django 5.x + PostgreSQL 16 + Strawberry-Django (GraphQL)
Auth:       django-firebase-auth (validate Firebase JWTs) OR dj-rest-auth + SimpleJWT
Realtime:   Django Channels + strawberry-channels + Redis channel layer
SDK gen:    graphql-codegen (Web/TS), ferry (Flutter), Apollo (iOS/Android)
Admin SDK:  Django management commands / Celery workers (bypass auth middleware)
Events:     Celery + Redis + django-pgtrigger for DB-level triggers
Offline:    TanStack Query (React) or Apollo offline cache (mobile)
Local dev:  docker-compose (Postgres + Redis + pgAdmin) + Strawberry GraphiQL
```

```bash
pip install django strawberry-graphql-django channels[daphne] strawberry-channels \
            channels-redis django-pgtrigger celery[redis] firebase-admin \
            pgvector-django django-filter django-extensions django-silk httpx
```

## Cloud Storage for Firebase

### Overview and Architecture

Cloud Storage for Firebase is not a separate storage system — it is **Google Cloud Storage (GCS) with a Firebase authentication + security-rules proxy bolted in front**. When you create a Firebase project you also create a GCS bucket; the two share the same underlying object store. Firebase's value-add is:

1. **Client SDK** — A JavaScript/iOS/Android/Flutter SDK that speaks the GCS JSON and XML APIs but automatically attaches the user's Firebase ID token as a Bearer token on every request.
2. **Rule evaluation layer** — Before any upload/download/delete reaches the underlying GCS bucket, Firebase evaluates your declarative Security Rules on its servers. Authorized requests are forwarded to GCS; denied requests get a 403.
3. **Download token system** — A UUID stored as custom object metadata (`firebaseStorageDownloadTokens`) that lets anyone with the token download the file without a Firebase session. This is separate from GCS signed URLs.
4. **Admin SDK** — Server-side SDK that bypasses Security Rules and talks directly to GCS via a service-account credential, with helpers for generating signed URLs and managing objects.

From an infrastructure standpoint, files live in GCS, metadata lives in GCS object metadata, and Firebase adds nothing to the storage path — it is purely a **policy enforcement point and SDK convenience layer**.

---

### Feature-by-Feature Breakdown

#### 1. Object/Blob Storage (built on GCS buckets)

**What it does.** Stores arbitrary binary objects (files, blobs) in a flat namespace with path-like names (e.g., `users/{uid}/avatars/photo.jpg`). There are no real directories; the slash is a naming convention that the List API treats as a delimiter.

**Under the hood.** Each Firebase project has one or more GCS buckets (the default bucket is `<project-id>.appspot.com` for legacy projects or `<project-id>.firebasestorage.app` for projects created after Sept 2024). Objects are stored with GCS's standard multi-region or regional durability guarantees (11 nines durability). As of October 2025 all buckets require the Blaze (pay-as-you-go) plan.

**Pricing.**

| Dimension | Free (Spark) | Paid (Blaze) |
|-----------|-------------|--------------|
| Storage | 5 GB/month | $0.026/GB/month after free tier |
| Downloads (egress) | 1 GB/day | $0.12–$0.15/GB (region-dependent) |
| Class A ops (uploads, writes) | 20K/day | $0.0050/1,000 ops |
| Class B ops (reads, metadata) | 50K/day | $0.0004/1,000 ops |

**Django rebuild.** Use `django-storages` with either MinIO (self-hosted S3-compatible) or AWS S3/Cloudflare R2 as the raw object store. Track every uploaded object in a PostgreSQL `StorageObject` model so you have a queryable metadata registry — GCS itself doesn't give you a searchable DB.

```python
# pip install django-storages[s3] boto3
# settings.py
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_STORAGE_BUCKET_NAME = "my-app-media"
AWS_S3_ENDPOINT_URL = "http://minio:9000"   # omit for real S3
AWS_S3_REGION_NAME = "us-east-1"
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_DEFAULT_ACL = None                       # keep bucket private; use presigned URLs
AWS_QUERYSTRING_AUTH = True                  # default: presigned URLs on .url()
AWS_QUERYSTRING_EXPIRE = 3600               # 1-hour presigned URL lifetime
```

```python
# models.py
import uuid
from django.db import models

class StorageObject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bucket = models.CharField(max_length=255)
    object_path = models.CharField(max_length=1024, db_index=True)
    owner = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL)
    content_type = models.CharField(max_length=255)
    size = models.BigIntegerField(default=0)
    custom_metadata = models.JSONField(default=dict)
    download_token = models.UUIDField(default=uuid.uuid4)  # mirrors Firebase token
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("bucket", "object_path")
        indexes = [
            models.Index(fields=["owner", "created_at"]),
            models.Index(fields=["download_token"]),
        ]
```

---

#### 2. Resumable Uploads

**What it does (Firebase).** The Firebase client SDK uses GCS's resumable upload protocol transparently. When you call `uploadBytesResumable()`, the SDK:
1. POSTs to GCS to initiate the session, receiving a session URI (valid for 1 week).
2. Sends the file in chunks via PUT requests to that session URI.
3. Can pause/resume by re-using the session URI. The SDK stores the session URI in memory and restarts automatically on transient network failures.

```javascript
// Firebase client SDK (modular v9+)
import { getStorage, ref, uploadBytesResumable, getDownloadURL } from "firebase/storage";

const storage = getStorage();
const storageRef = ref(storage, `users/${uid}/photo.jpg`);

const uploadTask = uploadBytesResumable(storageRef, file, {
  contentType: "image/jpeg",
  customMetadata: { originalName: file.name },
});

uploadTask.on("state_changed",
  (snapshot) => {
    const pct = (snapshot.bytesTransferred / snapshot.totalBytes) * 100;
    console.log(`Progress: ${pct.toFixed(1)}%`);
  },
  (error) => console.error(error),
  async () => {
    const url = await getDownloadURL(uploadTask.snapshot.ref);
    console.log("Download URL:", url);
  }
);
// pause/resume/cancel
uploadTask.pause();
uploadTask.resume();
uploadTask.cancel();
```

**Under the hood.** GCS resumable uploads use the XML API. Files above 5 MB automatically use the resumable path; smaller files use a single multipart request. The session URI is an opaque authentication token — anyone with it can upload data without further auth, so Firebase treats it as a server secret and the client SDK never exposes the raw URI.

**Django rebuild — Option A: Presigned Multipart (S3 native).** Best for files up to 5 GB with a modern browser.

```python
# pip install boto3
# views.py — DRF endpoint to initiate a multipart upload
import boto3
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

s3 = boto3.client(
    "s3",
    endpoint_url=settings.AWS_S3_ENDPOINT_URL,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    config=boto3.session.Config(signature_version="s3v4"),
)

class InitiateMultipartUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        object_path = f"users/{request.user.id}/{request.data['filename']}"
        resp = s3.create_multipart_upload(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=object_path,
            ContentType=request.data.get("content_type", "application/octet-stream"),
        )
        upload_id = resp["UploadId"]
        # Pre-sign each part URL (up to 10,000 parts supported)
        part_urls = []
        for part_num in range(1, int(request.data["num_parts"]) + 1):
            url = s3.generate_presigned_url(
                "upload_part",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": object_path,
                    "UploadId": upload_id,
                    "PartNumber": part_num,
                },
                ExpiresIn=3600,
            )
            part_urls.append({"part_number": part_num, "url": url})
        return Response({"upload_id": upload_id, "object_path": object_path, "parts": part_urls})


class CompleteMultipartUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s3.complete_multipart_upload(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=request.data["object_path"],
            UploadId=request.data["upload_id"],
            MultipartUpload={"Parts": request.data["parts"]},  # [{PartNumber, ETag}]
        )
        # Register in DB
        obj = StorageObject.objects.create(
            bucket=settings.AWS_STORAGE_BUCKET_NAME,
            object_path=request.data["object_path"],
            owner=request.user,
            content_type=request.data.get("content_type", "application/octet-stream"),
            size=request.data.get("size", 0),
        )
        return Response({"id": obj.id, "download_token": obj.download_token})
```

**Django rebuild — Option B: tus protocol server.** Better for very large files, offline-first clients, and when you want true byte-range resumability with server-side state.

```python
# pip install django-tus
# settings.py
TUS_DESTINATION_DIR = "/tmp/tus-uploads/"   # staging area before S3 move
TUS_FILE_NAME_FORMAT = "keep"
TUS_MAX_FILE_SIZE = 50 * 1024 * 1024 * 1024  # 50 GB

# urls.py
from django.urls import path, include
urlpatterns = [
    path("api/storage/tus/", include("django_tus.urls")),
]
# After tus completes, a django_tus.signals.tus_upload_finished signal fires.
# Connect it to a Celery task that moves the file to S3 and creates StorageObject.
```

Supabase's approach (tus → S3 multipart under the hood) is worth studying: they map each tus chunk to an S3 `UploadPart`, accumulate the ETags server-side, then call `CompleteMultipartUpload` when the tus upload finalizes. This is the most production-ready pattern for large files.

---

#### 3. Download URLs and Signed URLs

**What Firebase does.** Firebase has two URL types:

| Type | How generated | Lifetime | Auth required |
|------|---------------|---------- |---------------|
| **Download token URL** | Auto-created at upload; stored as `firebaseStorageDownloadTokens` custom metadata | Permanent (until revoked) | None — public by token |
| **Signed URL** | Admin SDK / GCS signing with service account private key | Minutes to 7 days | None — public for duration |

A download token URL looks like:
```
https://firebasestorage.googleapis.com/v0/b/BUCKET/o/ENCODED_PATH?alt=media&token=UUID
```
Firebase's proxy verifies the token matches the `firebaseStorageDownloadTokens` metadata on the object and streams the bytes. Security Rules do NOT apply to token URLs — if you know the token, you can download regardless of rules.

A signed URL goes directly to GCS with a V4 HMAC signature and bypasses Firebase entirely.

**Django rebuild.** Mirror the two patterns exactly:

```python
# Pattern 1: Download token URL (long-lived, revocable via DB)
# views.py
class TokenDownloadView(APIView):
    """
    GET /api/storage/download/<token>/
    Validates token against DB, checks permissions, then redirects to presigned S3 URL.
    """
    authentication_classes = []  # public endpoint; token IS the auth
    permission_classes = []

    def get(self, request, token):
        try:
            obj = StorageObject.objects.get(download_token=token)
        except StorageObject.DoesNotExist:
            return Response(status=404)
        # Evaluate access rules (see Security Rules section below)
        if not _evaluate_access(request, obj, operation="read"):
            return Response(status=403)
        # Generate short-lived presigned URL and redirect; never expose bucket directly
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": obj.bucket, "Key": obj.object_path},
            ExpiresIn=300,  # 5-minute presigned redirect
        )
        return redirect(url)


# Pattern 2: Short-lived signed URL (for server-trusted clients)
class SignedURLView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        obj = get_object_or_404(StorageObject, id=request.data["object_id"])
        if obj.owner != request.user:
            return Response(status=403)
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": obj.bucket, "Key": obj.object_path},
            ExpiresIn=int(request.data.get("expires_in", 3600)),
        )
        return Response({"url": url, "expires_in": 3600})
```

**Gotcha.** Firebase's download token is truly permanent until you revoke it by deleting or regenerating the `firebaseStorageDownloadTokens` metadata. In the Django model above, you get the same revocability by calling `obj.download_token = uuid.uuid4(); obj.save()` — all old token URLs immediately 404.

---

#### 4. Presigned PUT URLs (Direct Client Upload without Proxy)

**What Firebase does.** Firebase SDKs upload directly to GCS — the Django server is never in the upload path. For small files (`uploadBytes`), a single multipart POST. For large files, the resumable session.

**Django rebuild.** Implement a "request upload slot" → "upload directly" → "confirm" flow to match this pattern.

```python
# Step 1: Client requests a presigned PUT URL
class RequestUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        filename = request.data["filename"]
        content_type = request.data.get("content_type", "application/octet-stream")
        object_path = f"users/{request.user.id}/{uuid.uuid4()}/{filename}"

        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": object_path,
                "ContentType": content_type,
            },
            ExpiresIn=900,  # 15 minutes to complete upload
        )
        # Create a pending record
        obj = StorageObject.objects.create(
            bucket=settings.AWS_STORAGE_BUCKET_NAME,
            object_path=object_path,
            owner=request.user,
            content_type=content_type,
            custom_metadata=request.data.get("metadata", {}),
            size=0,  # unknown until confirmed
        )
        return Response({"upload_url": presigned_url, "object_id": str(obj.id)})


# Step 2: Client PUTs file bytes directly to S3 (no Django involvement)
# Step 3: Client confirms completion so server can finalize record
class ConfirmUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        obj = get_object_or_404(StorageObject, id=request.data["object_id"], owner=request.user)
        # Verify object actually landed in S3
        try:
            head = s3.head_object(Bucket=obj.bucket, Key=obj.object_path)
            obj.size = head["ContentLength"]
            obj.save(update_fields=["size", "updated_at"])
        except s3.exceptions.NoSuchKey:
            return Response({"error": "Upload not found in storage"}, status=400)
        # Trigger post-processing (thumbnails, virus scan, etc.)
        process_uploaded_file.delay(str(obj.id))
        return Response({"id": str(obj.id), "download_token": str(obj.download_token)})
```

---

#### 5. File Metadata

**What Firebase does.** Every GCS object carries system metadata (`contentType`, `size`, `timeCreated`, `updated`, `md5Hash`, `etag`, `generation`, `metageneration`) plus user-defined `customMetadata` (string key-value pairs). The Firebase SDK exposes these via `getMetadata()` and allows updating mutable fields with `updateMetadata()`.

```javascript
// Set metadata at upload time
const metadata = {
  contentType: "image/jpeg",
  cacheControl: "public, max-age=31536000",
  customMetadata: {
    originalName: file.name,
    uploadedBy: auth.currentUser.uid,
    tags: "avatar,profile",
  },
};
await uploadBytesResumable(storageRef, file, metadata);

// Update metadata after the fact
await updateMetadata(storageRef, { customMetadata: { processed: "true" } });

// Delete a metadata field
await updateMetadata(storageRef, { customMetadata: { tags: null } });
```

**Security Rules can read metadata:**
```
// Only allow images under 5 MB
allow write: if request.resource.size < 5 * 1024 * 1024
             && request.resource.contentType.matches("image/.*");

// Check existing metadata on read
allow read: if resource.metadata.visibility == "public"
            || request.auth.uid == resource.metadata.ownerId;
```

**Django rebuild.** The `StorageObject.custom_metadata` JSONField already covers this. Expose a metadata update endpoint:

```python
class ObjectMetadataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, object_id):
        obj = get_object_or_404(StorageObject, id=object_id)
        if not _can_read(request.user, obj):
            return Response(status=403)
        return Response(ObjectMetadataSerializer(obj).data)

    def patch(self, request, object_id):
        obj = get_object_or_404(StorageObject, id=object_id, owner=request.user)
        # Merge patch — set key to None to delete
        current = obj.custom_metadata or {}
        patch = request.data.get("custom_metadata", {})
        merged = {k: v for k, v in {**current, **patch}.items() if v is not None}
        obj.custom_metadata = merged
        obj.save(update_fields=["custom_metadata", "updated_at"])
        # Optionally propagate to S3 object metadata via copy-in-place
        _sync_s3_metadata(obj)
        return Response(ObjectMetadataSerializer(obj).data)
```

```python
def _sync_s3_metadata(obj: StorageObject):
    """Propagate custom_metadata to S3 object via server-side copy."""
    s3.copy_object(
        Bucket=obj.bucket,
        CopySource={"Bucket": obj.bucket, "Key": obj.object_path},
        Key=obj.object_path,
        Metadata={k: str(v) for k, v in obj.custom_metadata.items()},
        MetadataDirective="REPLACE",
        ContentType=obj.content_type,
    )
```

---

#### 6. Security Rules (Access Control Gating)

**What Firebase does.** Firebase Security Rules for Cloud Storage are a declarative DSL evaluated server-side. They match on path patterns, operate on `request` (incoming request) and `resource` (existing object), and can call `firestore.get()` since September 2022 for cross-service authorization.

```
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Private user files
    match /users/{userId}/{allPaths=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }

    // Public read, authenticated write, size+type validation
    match /public/{fileName} {
      allow read;
      allow write: if request.auth != null
                   && request.resource.size < 10 * 1024 * 1024
                   && request.resource.contentType.matches("image/.*");
    }

    // Cross-service: check Firestore for group membership
    match /groups/{groupId}/{allPaths=**} {
      allow read, write: if request.auth != null
        && firestore.get(/databases/(default)/documents/groups/$(groupId)/members/$(request.auth.uid)).data.role in ["admin", "editor"];
    }
  }
}
```

**Under the hood.** Firebase runs a rules evaluation engine (CEL-based) on its own servers. Every SDK upload/download includes the Firebase ID token; Firebase's proxy validates the JWT signature against Firebase Auth's public keys, populates `request.auth`, then evaluates the rules tree. If a rule grants access, the request is proxied to GCS with service-account credentials that have full bucket access. The client never holds GCS credentials. Security Rules do NOT apply to Admin SDK calls or direct GCS API calls using a GCS credential.

**Important caveat.** Firebase Storage Security Rules are evaluated *only* for requests via the Firebase client SDK (which route through `firebasestorage.googleapis.com`). Direct GCS API calls bypass rules entirely. Download token URLs (`?token=UUID`) also bypass rules — the token is sufficient.

**Django rebuild — per-request access control middleware.**

```python
# access_control.py
# Replaces Firebase's declarative rules with a Python evaluation function.
# Call this in every DRF view that touches StorageObject.

from functools import reduce
from typing import Literal

Operation = Literal["read", "write", "delete", "list"]

class StorageAccessDenied(Exception):
    pass

def evaluate_storage_access(user, obj: StorageObject, operation: Operation) -> bool:
    """
    Evaluate whether `user` may perform `operation` on `obj`.
    This is the Django equivalent of Firebase Storage Security Rules.
    Rules are Python; they live in code, not a DSL file.
    """
    # Rule 1: owners always have full access
    if obj.owner_id and user.is_authenticated and obj.owner_id == user.id:
        return True

    # Rule 2: admins always have full access
    if user.is_staff:
        return True

    # Rule 3: public objects are readable by anyone
    if operation == "read" and obj.custom_metadata.get("visibility") == "public":
        return True

    # Rule 4: group membership check (mirrors firestore.get() cross-service rule)
    group_id = obj.custom_metadata.get("group_id")
    if group_id and user.is_authenticated:
        from myapp.models import GroupMembership
        role = GroupMembership.objects.filter(
            group_id=group_id, user=user
        ).values_list("role", flat=True).first()
        if operation in ("read",) and role in ("admin", "editor", "viewer"):
            return True
        if operation in ("write", "delete") and role in ("admin", "editor"):
            return True

    return False


# DRF permission class that wraps the evaluator
from rest_framework.permissions import BasePermission

class StorageObjectPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            op = "read"
        elif request.method == "DELETE":
            op = "delete"
        else:
            op = "write"
        return evaluate_storage_access(request.user, obj, op)
```

**What OSS alternatives do:**
- **Supabase Storage**: uses PostgreSQL Row-Level Security (RLS) policies — the `objects` table has `auth.uid()` checks just like any other Postgres table. Arguably more flexible and testable than Firebase's DSL.
- **Appwrite Storage**: uses its own permission model with JSON arrays on each object (`read("any")`, `write("user:<id>")`).
- **PocketBase**: each collection has a rules string (a Go expression) evaluated per-request.

**Recommendation for Django rebuild**: use Python functions (as above) for simple projects; for teams that want declarative rules, adopt a small `StorageRule` DB model with a JSON-encoded condition tree evaluated by a CEL/OPA sidecar.

---

#### 7. File Listing (List API)

**What Firebase does.** The `list()` and `listAll()` SDK methods map to the GCS list-objects API with `prefix` and `delimiter` parameters, emulating directory-like navigation.

```javascript
// List top-level "folders" under users/uid/
const listRef = ref(storage, `users/${uid}/`);
const result = await listAll(listRef);
result.prefixes.forEach((folderRef) => console.log("Folder:", folderRef.name));
result.items.forEach((itemRef) => console.log("File:", itemRef.name));

// Paginated (use for large buckets)
const pageResult = await list(listRef, { maxResults: 100, pageToken: cursor });
// pageResult.nextPageToken for next page
```

**Requires Rules version 2.** The List API is blocked by default in Security Rules v1 buckets.

**Django rebuild.**

```python
class ListObjectsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefix = request.query_params.get("prefix", f"users/{request.user.id}/")
        limit = min(int(request.query_params.get("limit", 100)), 1000)
        cursor = request.query_params.get("cursor")

        qs = StorageObject.objects.filter(
            bucket=settings.AWS_STORAGE_BUCKET_NAME,
            object_path__startswith=prefix,
            owner=request.user,
        ).order_by("object_path")

        if cursor:
            qs = qs.filter(object_path__gt=cursor)

        page = list(qs.values("id", "object_path", "size", "content_type", "created_at")[:limit + 1])
        has_more = len(page) > limit
        items = page[:limit]
        next_cursor = items[-1]["object_path"] if has_more else None

        return Response({"items": items, "next_cursor": next_cursor})
```

---

#### 8. Image Resize Extension

**What Firebase does.** The `storage-resize-images` Firebase Extension deploys a Cloud Function that triggers on the `object.finalize` event (every new upload to the bucket). If the object's `contentType` is an image, the function:
1. Downloads the original from GCS.
2. Uses Sharp (Node.js image processing) to resize to one or more configured dimensions (e.g., `200x200,400x400,800x800`) while preserving aspect ratio.
3. Uploads the resized variants to the same bucket with a naming suffix (e.g., `photo_200x200.jpg`).
4. Optionally deletes the original.
5. Copies safe metadata fields (`Cache-Control`, `Content-Type`, `Content-Disposition`, `Content-Language`, `Content-Encoding`) to the resized variants.
6. Publishes EventArc events: `onSuccess`, `onError`, `onCompletion`.

Configuration is done via Firebase console/CLI; no code required. The extension is a managed Cloud Function with a service account that has read/write access to the bucket.

**Django rebuild — Celery post-processing worker.**

```python
# pip install Pillow django-imagekit celery
# tasks.py
from celery import shared_task
from PIL import Image
import io, boto3
from myapp.models import StorageObject

THUMBNAIL_SIZES = [
    (200, 200, "thumb"),
    (800, 800, "medium"),
    (1920, 1080, "large"),
]

@shared_task(bind=True, max_retries=3)
def process_uploaded_file(self, object_id: str):
    obj = StorageObject.objects.get(id=object_id)
    if not obj.content_type.startswith("image/"):
        return  # skip non-images

    s3 = boto3.client("s3", endpoint_url=settings.AWS_S3_ENDPOINT_URL, ...)
    raw = s3.get_object(Bucket=obj.bucket, Key=obj.object_path)["Body"].read()

    with Image.open(io.BytesIO(raw)) as img:
        img = img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img
        for max_w, max_h, suffix in THUMBNAIL_SIZES:
            variant = img.copy()
            variant.thumbnail((max_w, max_h), Image.LANCZOS)  # preserves aspect ratio
            buf = io.BytesIO()
            variant.save(buf, format="JPEG", quality=85, optimize=True)
            buf.seek(0)

            base, ext = obj.object_path.rsplit(".", 1) if "." in obj.object_path else (obj.object_path, "jpg")
            variant_path = f"{base}_{suffix}.jpg"

            s3.put_object(
                Bucket=obj.bucket,
                Key=variant_path,
                Body=buf,
                ContentType="image/jpeg",
                CacheControl="public, max-age=31536000",
            )
            StorageObject.objects.create(
                bucket=obj.bucket,
                object_path=variant_path,
                owner=obj.owner,
                content_type="image/jpeg",
                custom_metadata={**obj.custom_metadata, "variant": suffix, "source_id": str(obj.id)},
            )

    # Mark original as processed
    obj.custom_metadata["processed"] = "true"
    obj.save(update_fields=["custom_metadata", "updated_at"])
```

**Using django-imagekit for model-level spec fields** (better for ORM-driven use cases):

```python
# pip install django-imagekit Pillow
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit

class UserProfile(models.Model):
    avatar = models.ImageField(upload_to="avatars/", storage=S3Boto3Storage())
    avatar_thumb = ImageSpecField(
        source="avatar",
        processors=[ResizeToFit(200, 200)],
        format="JPEG",
        options={"quality": 85},
    )
    # Access: profile.avatar_thumb.url → presigned S3 URL of the generated thumbnail
```

**Virus scanning addition.** Production deployments should integrate `python-clamd` (ClamAV) as a second Celery task chained after upload:

```python
process_uploaded_file.si(object_id) | scan_for_viruses.si(object_id)
```

---

#### 9. Client SDK Integration and Developer Experience

**What Firebase provides.** A unified SDK for web, iOS, Android, Flutter with:
- Automatic retry on network failure.
- Upload/download progress observables.
- Offline queue (mobile SDKs cache uploads and retry when back online).
- Automatic Firebase Auth token refresh and attachment.
- `getDownloadURL()` convenience method.

**Django rebuild — JavaScript client utility.**

```javascript
// storage-client.js — thin wrapper that mirrors Firebase SDK DX
class OwnStorageClient {
  constructor(baseUrl, authToken) {
    this.baseUrl = baseUrl;
    this.authToken = authToken;
  }

  async uploadFile(file, path, options = {}) {
    // Step 1: request upload slot
    const { data: { upload_url, object_id } } = await axios.post(
      `${this.baseUrl}/api/storage/upload/request/`,
      { filename: file.name, content_type: file.type, metadata: options.metadata },
      { headers: { Authorization: `Bearer ${this.authToken}` } }
    );

    // Step 2: direct PUT to S3 (no Django in the hot path)
    await axios.put(upload_url, file, {
      headers: { "Content-Type": file.type },
      onUploadProgress: (evt) => options.onProgress?.(evt.loaded / evt.total),
    });

    // Step 3: confirm
    const { data } = await axios.post(
      `${this.baseUrl}/api/storage/upload/confirm/`,
      { object_id },
      { headers: { Authorization: `Bearer ${this.authToken}` } }
    );
    return data; // { id, download_token }
  }

  getDownloadURL(token) {
    return `${this.baseUrl}/api/storage/download/${token}/`;
  }
}
```

For mobile / offline support, wrap this in a service worker or use the tus-js-client for true resumable uploads with local state persistence.

---

#### 10. Supporting Infrastructure Architecture

Below is the full infra stack for the Django self-hosted Firebase Storage replacement:

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT (Browser/Mobile)               │
│  OwnStorageClient (JS) / tus-js-client                  │
└────────────┬──────────────────────────┬─────────────────┘
             │ REST API calls           │ Direct PUT (presigned)
             ▼                          ▼
┌──────────────────────┐    ┌──────────────────────────────┐
│  Nginx (reverse proxy)│    │  MinIO / AWS S3 / R2         │
│  - TLS termination   │    │  (private bucket)            │
│  - Rate limiting     │    │  - Stores raw bytes          │
│  - CORS headers      │    │  - S3 multipart API          │
└────────────┬─────────┘    └──────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────┐
│  Django (Gunicorn / uvicorn)                             │
│  - DRF views for: upload slot, confirm, metadata,        │
│    list, delete, token download, signed URL              │
│  - StorageObjectPermission (replaces Security Rules)     │
│  - JWT auth (djangorestframework-simplejwt)              │
└───────────┬──────────────────────────┬────────────────────┘
            │                          │
            ▼                          ▼
┌──────────────────┐       ┌──────────────────────────────┐
│  PostgreSQL       │       │  Redis                        │
│  - StorageObject │       │  - Celery broker              │
│  - Auth tables   │       │  - Rate limit counters        │
└──────────────────┘       └──────────────┬───────────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │  Celery Workers       │
                               │  - Image resize       │
                               │  - Virus scan         │
                               │  - Metadata sync      │
                               │  - Webhook dispatch   │
                               └──────────────────────┘
```

**Docker Compose services:**
```yaml
services:
  django: { build: ., depends_on: [postgres, redis, minio] }
  celery: { build: ., command: celery -A myproject worker -Q storage -c 4 }
  minio:
    image: quay.io/minio/minio  # MinIO community via Chainguard
    command: server /data --console-address ":9001"
    volumes: [minio_data:/data]
  postgres: { image: postgres:16 }
  redis: { image: redis:7-alpine }
  nginx: { image: nginx:alpine }
```

---

### Gotchas and Hard Parts

| Problem | Firebase behavior | Django self-hosted solution |
|---------|-------------------|----------------------------|
| **Security Rules bypass via token URL** | Download token URLs bypass rules entirely | Mirror this: `TokenDownloadView` skips Python rules if token is valid; document clearly |
| **Rules don't apply to Admin/GCS SDK** | Documented but surprising | Your DRF views ARE the policy boundary; anything with boto3/s3 credentials skips them — restrict boto3 to server processes only |
| **Resumable upload state** | Firebase/GCS session URI server-side | For tus: `django-tus` stores state on disk/Redis; for multipart: UploadId + Parts in Redis or DB |
| **CORS on MinIO** | Firebase handles CORS via its proxy; you configure bucket CORS via gsutil | Set MinIO bucket CORS policy; for token-download proxy pattern, CORS is handled by Nginx/Django |
| **Metadata on S3 objects vs DB** | GCS is the single source of truth | Two sources of truth; keep PostgreSQL as authoritative, sync to S3 metadata asynchronously |
| **Image resize race condition** | Extension triggers on finalize event; original remains until confirmed | Use Celery chord: `resize_task | mark_processed`; never show variants until parent Celery task succeeds |
| **Large file upload timeouts** | Firebase SDK retries automatically for weeks | tus-js-client stores offset in localStorage; retries on page reload; no server timeout on tus PATCH |
| **Cross-service rules (Storage + Firestore)** | Two-document Firestore query per rules eval, cached | Equivalent: Python function that queries PostgreSQL; same performance, full ORM power, no 2-doc limit |
| **Download URL revocation** | Regenerate `firebaseStorageDownloadTokens` metadata | Rotate `StorageObject.download_token`; all old token URLs immediately fail |
| **Egress costs** | Firebase charges $0.12-0.15/GB | MinIO self-hosted: $0 egress; Cloudflare R2: $0 egress to internet (huge advantage over S3) |

### OSS Alternatives: What They Teach Us

- **Supabase Storage**: The best implementation to study. PostgreSQL RLS as the access policy engine is more composable than Firebase's DSL. Their tus-over-S3-multipart architecture (tus chunks mapped to S3 UploadParts) is the gold standard for large-file resumable uploads. Note: MinIO is deprecated in their stack (Chainguard images, or RustFS replacement) as of 2025.
- **Appwrite**: Uses its own metadata DB (MariaDB) + bucket abstraction over local disk or S3. Permission system uses string arrays on each resource. Good reference for object-level permission grants.
- **PocketBase**: Single binary with file storage on local disk + optional S3. Too simple for production use but the code is readable Go and shows a clean minimal implementation.
- **Minio Operator (Kubernetes)**: For production self-hosted, MinIO Operator with distributed mode (4+ nodes) gives erasure-coded object storage with no single point of failure — comparable to GCS durability.

## Cloud Functions & Server-Side Compute (incl. App Hosting)

This cluster covers every mechanism Firebase provides for running server-side code: callable and HTTP endpoints, background event triggers tied to database/auth/storage changes, scheduled jobs, custom event routing via Eventarc/Pub/Sub, and managed full-stack SSR hosting. The Django rebuild maps each piece onto DRF views, Celery workers, PostgreSQL triggers + LISTEN/NOTIFY, Celery Beat, and Gunicorn/Uvicorn behind Nginx in Docker.

---

### 1. Cloud Functions for Firebase — Overview and Generations

#### What it does (developer-facing)

Cloud Functions for Firebase is a serverless execution environment. Developers write Node.js (or Python) functions and deploy them; Google manages infrastructure, scaling, and runtime lifecycle. There are two execution generations:

| Feature | 1st Gen | 2nd Gen (GA as of 2023) |
|---|---|---|
| Underlying infra | Google Cloud Functions v1 | Cloud Run (container-per-service) |
| Max memory | 8 GB / 2 vCPU | 16 GiB / 4 vCPU |
| Max timeout (HTTP) | 540 s | 3600 s (60 min) |
| Concurrency per instance | 1 | Up to 1 000 (default 80) |
| Min instances | Yes | Yes (provisioned instances) |
| Cold start reduction | Per-request spin-up | Concurrency absorbs bursts |
| Request size (HTTP) | 10 MB | 32 MB |
| Event system | Firebase-managed | Eventarc (CloudEvents) |
| Max instances (HTTP) | Unlimited | 100 default / 1 000 max |

**2nd gen is the current default and recommended path.** 1st gen remains in maintenance mode; new projects should use 2nd gen exclusively.

#### Under the hood

When you run `firebase deploy --only functions`, the CLI:
1. Zips source code and uploads to a Cloud Storage staging bucket.
2. Cloud Build compiles a container image and pushes it to Artifact Registry (repository `gcf-artifacts`).
3. Firebase creates or updates a **Cloud Run service** for each function (2nd gen) or a Cloud Functions v1 deployment (1st gen).
4. Traffic is routed to the Cloud Run revision; Eventarc wires background triggers.

For 2nd gen, each deployed function **is** a Cloud Run service. The Firebase tooling just wraps the Cloud Run API with higher-level trigger abstractions.

#### Django rebuild — DRF Service Layer

The equivalent of a "deployed Cloud Functions project" is a **Django application** packaged as a Docker image and deployed to any container runtime (Kubernetes, Fly.io, Railway, bare VPS). There is no separate "functions" process — all endpoints and background workers run from the same codebase, separated into Django apps by concern.

```
# Minimal project layout
mybackend/
  mybackend/          # Django project
    settings.py
    celery.py         # Celery app instance
    urls.py
  functions/          # replaces Cloud Functions src/
    http.py           # HTTP / callable endpoints (DRF views)
    triggers.py       # DB-change handlers (signals + pgtrigger)
    scheduled.py      # Celery Beat periodic tasks
  manage.py
  docker-compose.yml
```

---

### 2. HTTP Functions & Callable Functions

#### Firebase: HTTP functions

```js
// 2nd gen — Node.js
const { onRequest } = require("firebase-functions/v2/https");

exports.helloWorld = onRequest({ region: "us-central1" }, (req, res) => {
  res.send("Hello from Firebase!");
});
```

Any HTTP method works; the function URL is a plain HTTPS endpoint.

#### Firebase: Callable functions

Callable functions are the recommended way to invoke functions from client SDKs. They differ from plain HTTP functions in three critical ways:

1. **Automatic auth propagation** — the Firebase client SDK sends `Authorization: Bearer <id_token>` automatically.
2. **Structured protocol** — request body is always `{"data": <payload>}`; response is `{"result": <payload>}` or `{"error": {...}}`.
3. **App Check & FCM token forwarding** — additional headers (`X-Firebase-AppCheck`, `Firebase-Instance-ID-Token`) are validated server-side transparently.

```js
// 2nd gen callable
const { onCall, HttpsError } = require("firebase-functions/v2/https");

exports.addMessage = onCall({ enforceAppCheck: true }, async (request) => {
  if (!request.auth) throw new HttpsError("unauthenticated", "Login required");
  const uid  = request.auth.uid;
  const text = request.data.text;
  // ... write to Firestore
  return { messageId: "abc123" };
});
```

Client invocation (JS SDK):
```js
const addMessage = httpsCallable(functions, "addMessage");
const result = await addMessage({ text: "Hello" });
```

The wire protocol is a POST to `https://<region>-<project>.cloudfunctions.net/<name>` with `Content-Type: application/json` and an optional `Authorization: Bearer <token>` header. The body is `{"data": {...}}` and success response is `{"result": {...}}`.

#### Django rebuild — DRF callable-equivalent

Replace callable functions with **DRF `@api_view` actions** or **Django Ninja operations** that implement the same conventions:

```python
# functions/http.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_message(request):
    """
    Mirrors Firebase callable: expects {"data": {...}}, returns {"result": {...}}
    Authentication handled by DRF JWT (djangorestframework-simplejwt)
    """
    payload = request.data.get("data", {})
    text = payload.get("text", "")
    if not text:
        return Response(
            {"error": {"status": "INVALID_ARGUMENT", "message": "text required"}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    msg = Message.objects.create(author=request.user, text=text)
    return Response({"result": {"messageId": str(msg.pk)}})
```

Client SDK shim (TypeScript, mirrors Firebase callable DX):
```typescript
// client/lib/callable.ts
export async function callFunction<T>(name: string, data: unknown): Promise<T> {
  const token = await getAuthToken(); // from your auth layer
  const res = await fetch(`/api/functions/${name}/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ data }),
  });
  const json = await res.json();
  if (json.error) throw new Error(json.error.message);
  return json.result as T;
}
```

**Key packages:**
- `djangorestframework` — DRF core
- `djangorestframework-simplejwt` — JWT auth (replaces Firebase ID tokens)
- `django-ninja` — alternative to DRF with OpenAPI auto-generation, faster for pure JSON APIs

---

### 3. Background Triggers — Firestore / RTDB / Storage / Auth

Firebase's background triggers are the hardest feature to replicate cleanly. Firebase uses a proprietary event bus where writes to Firestore, RTDB, Storage, or Auth automatically publish structured events, and Cloud Run picks them up via Eventarc.

#### Firebase: Firestore triggers (2nd gen)

```js
const { onDocumentCreated, onDocumentUpdated, onDocumentDeleted } =
  require("firebase-functions/v2/firestore");

exports.onUserCreated = onDocumentCreated("users/{userId}", async (event) => {
  const snapshot = event.data;           // DocumentSnapshot (new doc)
  const userId   = event.params.userId;  // wildcard captured
  await sendWelcomeEmail(snapshot.data().email);
});

exports.onOrderUpdated = onDocumentUpdated("orders/{orderId}", async (event) => {
  const before = event.data.before.data(); // pre-write snapshot
  const after  = event.data.after.data();  // post-write snapshot
  if (before.status !== after.status) {
    await notifyStatusChange(event.params.orderId, after.status);
  }
});
```

**Events available:** `onDocumentCreated`, `onDocumentUpdated`, `onDocumentDeleted`, `onDocumentWritten` (all three). RTDB equivalents: `onValueCreated`, `onValueUpdated`, `onValueDeleted`, `onValueWritten`.

**Under the hood:** Firestore writes publish CloudEvents to Eventarc. Eventarc delivers to the Cloud Run service backing the function via HTTP POST. At-least-once delivery — write idempotent functions.

#### Firebase: Auth triggers

```js
const { beforeUserCreated, beforeUserSignedIn } =
  require("firebase-functions/v2/identity");
const { onUserCreated, onUserDeleted } =
  require("firebase-functions/v2/identity"); // blocking vs non-blocking

exports.onUserCreated = onUserCreated((event) => {
  const user = event.data; // UserRecord
  // provision user profile, send welcome email, etc.
});
```

Note: Auth v2 `onUserCreated` / `onUserDeleted` are **non-blocking** (fire-and-forget after the auth event). Blocking functions (`beforeUserCreated`, `beforeUserSignedIn`) can reject the operation — equivalent to Django middleware on login/registration.

#### Firebase: Storage triggers

```js
const { onObjectFinalized, onObjectDeleted } =
  require("firebase-functions/v2/storage");

exports.onImageUpload = onObjectFinalized(async (event) => {
  const { bucket, name, contentType } = event.data;
  if (!contentType.startsWith("image/")) return;
  await generateThumbnail(bucket, name);
});
```

#### Django rebuild — DB-change event triggers

The canonical self-hosted solution is a **three-layer stack**:

```
Layer 1: PostgreSQL trigger (fires on every write path, including bulk ORM, raw SQL, admin)
    ↓  NOTIFY channel with JSON payload
Layer 2: Django LISTEN worker (django-pgpubsub) — receives NOTIFY, dispatches handler
    ↓  or publishes to Redis/RabbitMQ for fan-out
Layer 3: Celery worker (optional) — heavyweight async processing
```

**Layer 1 — PostgreSQL triggers via `django-pgtrigger`:**

```python
# pip install django-pgtrigger
import pgtrigger
from django.db import models

class Order(models.Model):
    status     = models.CharField(max_length=50)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        triggers = [
            pgtrigger.Trigger(
                name="notify_on_status_change",
                operation=pgtrigger.Update,
                when=pgtrigger.After,
                condition=pgtrigger.Q(old__status__df=pgtrigger.F("status")),
                func="""
                    PERFORM pg_notify(
                        'order_status_changed',
                        json_build_object(
                            'order_id', NEW.id,
                            'old_status', OLD.status,
                            'new_status', NEW.status
                        )::text
                    );
                    RETURN NEW;
                """,
            )
        ]
```

This fires for ORM saves, bulk updates, admin writes, raw SQL — unlike Django `post_save` signals which miss `bulk_update`, `update()` QuerySet calls, etc.

**Layer 2 — LISTEN consumer via `django-pgpubsub`:**

```python
# pip install django-pgpubsub django-pgtrigger
# functions/triggers.py
import pgpubsub
from pgpubsub.channel import TriggerChannel
from dataclasses import dataclass

@dataclass
class OrderStatusChanged:
    order_id:   int
    old_status: str
    new_status: str

channel = TriggerChannel(
    name="order_status_changed",
    model=Order,
    payload_model=OrderStatusChanged,
)

@pgpubsub.post_save_receiver(channel)
def handle_order_status_changed(old, new, payload: OrderStatusChanged, **kwargs):
    # Runs in the listener process — keep it fast
    # For heavy work, dispatch a Celery task:
    from functions.scheduled import send_order_notification
    send_order_notification.delay(payload.order_id, payload.new_status)
```

Run the listener process:
```bash
python manage.py pgpubsub_listen --channel order_status_changed
```

This process uses PostgreSQL's `LISTEN` — zero CPU polling, no extra infrastructure beyond your existing DB.

**Layer 2 alternative — Outbox pattern + RabbitMQ/Kafka (for fan-out, durability):**

For higher-volume or multi-consumer scenarios, use the **transactional outbox pattern** (as used by Plane.so in production):

```python
# models.py
class OutboxEvent(models.Model):
    aggregate_type = models.CharField(max_length=100)  # e.g. "Order"
    aggregate_id   = models.CharField(max_length=255)
    event_type     = models.CharField(max_length=100)  # e.g. "status_changed"
    payload        = models.JSONField()
    published      = models.BooleanField(default=False)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["published", "created_at"])]

# In the same DB transaction as the Order update:
with transaction.atomic():
    order.status = "shipped"
    order.save()
    OutboxEvent.objects.create(
        aggregate_type="Order",
        aggregate_id=str(order.pk),
        event_type="status_changed",
        payload={"old": old_status, "new": "shipped"},
    )

# Separate Celery Beat task publishes to RabbitMQ:
@shared_task
def publish_outbox_events():
    events = OutboxEvent.objects.select_for_update(skip_locked=True).filter(
        published=False
    ).order_by("created_at")[:100]
    for event in events:
        channel.basic_publish(exchange="events", routing_key=event.event_type,
                              body=json.dumps(event.payload))
        event.published = True
        event.save()
```

`SELECT FOR UPDATE SKIP LOCKED` enables horizontal scaling — multiple relay workers coordinate at the DB row level, no lock contention.

**Auth triggers (Django equivalent):**

```python
# functions/triggers.py — fires on User create/delete
from django.db.models.signals import post_save, post_delete
from django.contrib.auth import get_user_model
from django.dispatch import receiver

User = get_user_model()

@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if created:
        from functions.scheduled import provision_user_profile
        provision_user_profile.delay(instance.pk)

@receiver(post_delete, sender=User)
def on_user_deleted(sender, instance, **kwargs):
    from functions.scheduled import cleanup_user_data
    cleanup_user_data.delay(instance.pk)
```

For blocking behavior (reject registration mid-flow), use Django middleware or override `perform_create` in a DRF serializer.

**Storage triggers (MinIO/S3-compatible equivalent):**

```python
# Django post-save signal on a FileField model, or
# MinIO webhook → Django endpoint → Celery task
# apphosting/views.py

@api_view(["POST"])
def minio_webhook(request):
    """MinIO calls this URL on bucket events (configured via mc event add)."""
    event = request.data
    for record in event.get("Records", []):
        key  = record["s3"]["object"]["key"]
        mime = record["s3"]["object"].get("contentType", "")
        if mime.startswith("image/"):
            generate_thumbnail.delay(bucket=record["s3"]["bucket"]["name"], key=key)
    return Response({"ok": True})
```

MinIO supports S3-compatible event notifications delivered as HTTP webhooks, which mirrors Firebase Storage trigger semantics exactly.

---

### 4. Scheduled Functions (Cloud Scheduler / Pub/Sub)

#### Firebase

```js
// 2nd gen — App Engine cron syntax or unix-cron
const { onSchedule } = require("firebase-functions/v2/scheduler");

exports.dailyCleanup = onSchedule(
  {
    schedule: "every 24 hours",    // or "0 2 * * *" (unix-cron)
    timeZone: "America/New_York",
    retryCount: 3,
  },
  async (event) => {
    await deleteExpiredSessions();
  }
);
```

**Under the hood:** `onSchedule` automatically creates a Cloud Scheduler job that publishes a message to a Pub/Sub topic at the specified interval. The Pub/Sub message triggers the Cloud Run service via Eventarc. No infrastructure to manage.

#### Django rebuild — Celery Beat

```python
# pip install celery django-celery-beat redis
# mybackend/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mybackend.settings")
app = Celery("mybackend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# functions/scheduled.py
from celery import shared_task
from django.utils import timezone

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def daily_cleanup(self):
    try:
        deleted, _ = Session.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()
        return {"deleted": deleted}
    except Exception as exc:
        raise self.retry(exc=exc)

@shared_task(bind=True)
def provision_user_profile(self, user_id: int):
    from django.contrib.auth import get_user_model
    user = get_user_model().objects.get(pk=user_id)
    Profile.objects.get_or_create(user=user)
```

Schedule in `settings.py` (database-backed via `django-celery-beat`):
```python
# settings.py
CELERY_BROKER_URL       = "redis://redis:6379/0"
CELERY_RESULT_BACKEND   = "redis://redis:6379/1"
CELERY_BEAT_SCHEDULER   = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_BEAT_SCHEDULE = {
    "daily-cleanup": {
        "task": "functions.scheduled.daily_cleanup",
        "schedule": crontab(hour=2, minute=0),  # 02:00 daily
        "options": {"timezone": "America/New_York"},
    },
}
```

`django-celery-beat` stores schedules in the database. You can add, edit, or disable schedules from the Django admin without restarting the beat process — equivalent to Cloud Scheduler's console UI.

**Key packages:**
- `celery[redis]>=5.3` — task queue and beat scheduler
- `django-celery-beat>=2.5` — database-backed periodic tasks with admin UI
- `django-celery-results` — store task results in Django DB (optional)
- `flower` — real-time monitoring UI for Celery workers (equivalent to Cloud Functions logs)

---

### 5. Pub/Sub Triggers & Eventarc (Custom Events)

#### Firebase

```js
// Subscribe to a Pub/Sub topic
const { onMessagePublished } = require("firebase-functions/v2/pubsub");

exports.processPubSub = onMessagePublished("my-topic", async (event) => {
  const message = event.data.message;
  const payload = JSON.parse(Buffer.from(message.data, "base64").toString());
  await processEvent(payload);
});

// Publish custom Eventarc event from server
const { getEventarc } = require("firebase-admin/eventarc");
await getEventarc().channel().publish({
  type: "com.myapp.order.completed",
  subject: `orders/${orderId}`,
  data: { orderId, amount },
});
```

**Under the hood:** Eventarc is Google's managed event bus implementing the CloudEvents spec. All Firebase background triggers (Firestore, Auth, Storage) funnel through Eventarc internally. Custom events are published to named Eventarc channels and delivered to Cloud Run services.

#### Django rebuild — Redis Streams or Celery + RabbitMQ

For the self-hosted equivalent, use **Redis Streams** (lightweight, built-in to the Redis you already have) or **RabbitMQ** (full fan-out exchange model):

```python
# Publish a custom event (replaces Eventarc publish)
import redis
import json

r = redis.Redis.from_url("redis://redis:6379/0")

def publish_event(event_type: str, subject: str, data: dict):
    """CloudEvents-shaped event on a Redis Stream."""
    r.xadd(
        "eventarc:custom",
        {
            "type":    event_type,
            "subject": subject,
            "source":  "myapp",
            "data":    json.dumps(data),
            "time":    datetime.utcnow().isoformat(),
        },
        maxlen=10_000,  # retain last 10k events
    )

# Consumer (long-running management command or Celery worker)
# management/commands/event_consumer.py
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        r = redis.Redis.from_url(settings.REDIS_URL)
        last_id = "0"
        while True:
            entries = r.xread({"eventarc:custom": last_id}, block=5000, count=10)
            for stream, messages in entries:
                for msg_id, fields in messages:
                    self._dispatch(fields)
                    last_id = msg_id

    def _dispatch(self, fields):
        event_type = fields[b"type"].decode()
        data       = json.loads(fields[b"data"])
        HANDLERS   = {
            "com.myapp.order.completed": handle_order_completed,
        }
        handler = HANDLERS.get(event_type)
        if handler:
            handler.delay(data)  # Celery task
```

For true fan-out (multiple consumers receiving every event), use **RabbitMQ** with fanout exchanges — the architecture Plane.so uses in production for zero-loss event streaming.

---

### 6. Firebase App Hosting (Managed SSR Hosting on Cloud Run)

#### What it does

Firebase App Hosting (GA since April 2025) is a fully managed platform for deploying full-stack web apps built with Next.js or Angular. It:
- Integrates with GitHub for CI/CD (push-to-deploy).
- Runs SSR routes on **Cloud Run** (auto-scales, min instances configurable).
- Serves static assets via Google's global CDN.
- Manages SSL, domain routing, and networking transparently.
- Supports `FirebaseServerApp` so SSR code can call Firestore/Auth with user credentials from the incoming request.

**Configuration (`apphosting.yaml`):**
```yaml
runConfig:
  minInstances: 1          # keep-warm in production, 0 in staging
  maxInstances: 100
  concurrency:  80
  cpu:          1
  memoryMiB:    512

env:
  - variable: NEXT_PUBLIC_API_URL
    value:     https://api.myapp.com
    availability: [BUILD, RUNTIME]
  - variable: DATABASE_URL
    secret:   DATABASE_SECRET      # Cloud Secret Manager reference
    availability: [RUNTIME]
```

The file is checked into source control; secrets reference Cloud Secret Manager and are never stored in the file.

#### Under the hood

1. GitHub push triggers App Hosting CI pipeline (Cloud Build under the hood).
2. Build step runs `next build` or `ng build --prerender`.
3. Static output is deployed to CDN.
4. Server bundle is wrapped in a Cloud Run container and deployed as a new revision.
5. Traffic splits can be configured for canary deployments.

#### Django rebuild — Nginx + Gunicorn/Uvicorn + Docker (App Hosting analog)

For Django (which is WSGI/ASGI, not Next.js), the analog is:

```
Nginx (static files + reverse proxy + SSL termination)
    → Gunicorn (WSGI) or Uvicorn (ASGI, for Django Channels)
        → Django application
```

**`docker-compose.yml` (production-like):**
```yaml
version: "3.9"
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB:       myapp
      POSTGRES_USER:     myapp
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

  web:
    build: .
    command: gunicorn mybackend.wsgi:application --workers 4 --bind 0.0.0.0:8000
    env_file: .env
    depends_on: [db, redis]
    volumes:
      - static:/app/static

  celery_worker:
    build: .
    command: celery -A mybackend worker --loglevel=info --queues=default,high_priority
    env_file: .env
    depends_on: [db, redis]

  celery_beat:
    build: .
    command: celery -A mybackend beat --scheduler django_celery_beat.schedulers:DatabaseScheduler --loglevel=info
    env_file: .env
    depends_on: [db, redis]

  pgpubsub_listener:
    build: .
    command: python manage.py pgpubsub_listen --channel order_status_changed --channel user_events
    env_file: .env
    depends_on: [db]

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - static:/app/static:ro
      - certs:/etc/letsencrypt:ro
    depends_on: [web]

volumes:
  pgdata:
  static:
  certs:
```

**`nginx.conf` snippet (replaces App Hosting CDN + routing):**
```nginx
server {
    listen 443 ssl http2;
    server_name myapp.com;

    ssl_certificate     /etc/letsencrypt/live/myapp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myapp.com/privkey.pem;

    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;           # match Cloud Run 300s default
    }
}
```

For **async Django** (Django Channels, long-lived connections):
```bash
uvicorn mybackend.asgi:application --workers 4 --host 0.0.0.0 --port 8000
```

**CI/CD analog (replaces App Hosting GitHub integration):**
Use GitHub Actions with Docker Build + push to your container registry, then `docker compose pull && docker compose up -d` on the host, or deploy to Fly.io / Render / Railway which provide PaaS-like push-to-deploy for containers.

---

### 7. Complete Architecture Diagram

```
CLIENT (mobile / web)
        │  HTTPS
        ▼
    [ Nginx ]
    ├── /static/*  → Static files (CDN equivalent: Nginx + long cache headers, or Cloudflare)
    ├── /api/*     → Gunicorn/Uvicorn → Django + DRF
    │                   ├── HTTP endpoints     (replaces onRequest)
    │                   ├── Callable endpoints (replaces onCall, w/ JWT auth)
    │                   └── Webhook endpoints  (MinIO events, Stripe, etc.)
    └── /ws/*      → Uvicorn → Django Channels (WebSocket, replaces Firebase Realtime push)

[ PostgreSQL ]
    ├── pgtrigger: fires pg_notify() on INSERT/UPDATE/DELETE
    └── Outbox table for reliable event fan-out

[ pgpubsub listener process ]
    └── LISTEN channels → dispatches to Celery tasks

[ Redis ]
    ├── Celery broker queue
    ├── Celery result backend
    └── Redis Streams (Eventarc custom events analog)

[ Celery Worker(s) ]
    ├── Background tasks (replaces onCall async, onDocumentWritten heavy processing)
    ├── User lifecycle (replaces Auth onCreate/onDelete)
    └── Storage processing (replaces onObjectFinalized)

[ Celery Beat ]
    └── Periodic tasks via django-celery-beat (replaces Cloud Scheduler + onSchedule)

[ MinIO ]
    └── S3-compatible storage with HTTP webhooks → Django endpoint → Celery
```

---

### 8. Key Packages Reference

| Layer | Package | PyPI / Docker | Replaces |
|---|---|---|---|
| HTTP / callable endpoints | `djangorestframework` | `pip install djangorestframework` | `onRequest` / `onCall` |
| JWT auth (callable tokens) | `djangorestframework-simplejwt` | `pip install djangorestframework-simplejwt` | Firebase ID token verification |
| Alternative API framework | `django-ninja` | `pip install django-ninja` | `onCall` with OpenAPI |
| DB-change triggers | `django-pgtrigger` | `pip install django-pgtrigger` | Firestore / RTDB triggers |
| DB event bus | `django-pgpubsub` | `pip install django-pgpubsub` | Eventarc (lightweight) |
| Async background tasks | `celery[redis]` | `pip install "celery[redis]"` | Cloud Functions background |
| Scheduled tasks | `django-celery-beat` | `pip install django-celery-beat` | Cloud Scheduler / `onSchedule` |
| Task result storage | `django-celery-results` | `pip install django-celery-results` | Cloud Functions logs/results |
| Worker monitoring | `flower` | `pip install flower` | Cloud Functions console |
| ASGI server | `uvicorn[standard]` | `pip install "uvicorn[standard]"` | Cloud Run container runtime |
| WSGI server | `gunicorn` | `pip install gunicorn` | Cloud Run container runtime |
| Storage webhooks | MinIO | `docker pull minio/minio` | Cloud Storage triggers |
| Message fan-out | RabbitMQ | `docker pull rabbitmq:3-management` | Pub/Sub / Eventarc |

---

### 9. Gotchas and Hard Parts

#### Cold starts
Firebase 2nd gen reduces cold starts via per-instance concurrency (up to 1000 req/instance). In the Django setup, **there are no cold starts** — Gunicorn workers are long-lived processes. The analog to `minInstances` is keeping at least one container/dyno running at all times, which any PaaS or Docker deployment does by default.

#### At-least-once delivery and idempotency
Both Firebase Cloud Functions and Celery use **at-least-once** delivery semantics. Functions/tasks may run more than once. Design all handlers to be idempotent:
- Use `get_or_create` instead of `create` for side-effect operations.
- Track processed event IDs in a database table and skip duplicates.
- Use Celery's `task_id` as an idempotency key.

#### Django signals miss bulk operations
`post_save` signals do not fire on `Model.objects.update()`, `bulk_create()`, or raw SQL. Use `django-pgtrigger` for triggers that fire on every write path — this is the same guarantee Firebase's Firestore triggers provide (they observe the storage layer, not the SDK).

#### Exactly-once is not achievable
Firebase explicitly states it cannot guarantee exactly-once execution; neither can Celery. Use the transactional outbox pattern for critical financial or side-effect-heavy flows to minimize duplicates.

#### App Hosting SSR vs Django SSR
Firebase App Hosting is purpose-built for Next.js/Angular. Django is inherently server-rendered (WSGI). If you need a separate Next.js frontend with a Django API backend, deploy them as separate services — Django as the API, Next.js on Vercel or self-hosted on the same Docker Compose via a separate Nginx upstream.

#### How OSS alternatives solve this
- **Supabase**: Uses PostgreSQL `pg_net` extension + `pg_cron` to deliver database webhooks as HTTP calls. No separate listener process needed — webhooks are dispatched directly from the DB.
- **Appwrite**: Uses a microservices queue (`appwrite/worker-functions` container) that consumes Appwrite internal events and executes functions in isolated runtime containers. Scale workers by duplicating the container in `docker-compose.yml`.
- **PocketBase**: Hook system runs Go functions server-side on record create/update/delete events. Simpler than Celery but single-process — suitable for lower traffic.

---

### 10. Summary Comparison Table

| Firebase Feature | How Firebase Does It | Django Equivalent | Key Libraries |
|---|---|---|---|
| HTTP functions (`onRequest`) | Cloud Run container, any HTTP method | DRF `@api_view` | `djangorestframework` |
| Callable functions (`onCall`) | HTTPS with auto auth/AppCheck, `{"data":…}` protocol | DRF POST with JWT auth, same JSON envelope | `djangorestframework-simplejwt` |
| Firestore triggers | Eventarc CloudEvents → Cloud Run | pgtrigger → pgpubsub LISTEN/NOTIFY → Celery | `django-pgtrigger`, `django-pgpubsub` |
| RTDB triggers | Firebase internal event bus → Cloud Run | Same pgtrigger stack (RTDB replaced by PostgreSQL) | `django-pgtrigger`, `django-pgpubsub` |
| Auth triggers (onCreate/onDelete) | Firebase Auth event → Eventarc → Cloud Run | Django `post_save`/`post_delete` signals → Celery | `celery` |
| Blocking auth triggers | Firebase Identity Platform blocking functions | DRF serializer `validate_*` / middleware | `djangorestframework` |
| Storage triggers (`onObjectFinalized`) | GCS PubSub notification → Cloud Run | MinIO HTTP webhook → DRF view → Celery | `celery`, MinIO |
| Scheduled functions (`onSchedule`) | Cloud Scheduler → Pub/Sub → Cloud Run | Celery Beat + `django-celery-beat` | `django-celery-beat` |
| Pub/Sub triggers | Eventarc Pub/Sub → Cloud Run | Redis Streams consumer / RabbitMQ fanout | `redis-py`, RabbitMQ |
| Eventarc custom events | CloudEvents on Eventarc channels | Redis Streams or RabbitMQ with CloudEvents envelope | `redis-py` |
| App Hosting SSR | Cloud Run + CDN + GitHub CI/CD | Gunicorn/Uvicorn + Nginx + Docker + GitHub Actions | `gunicorn`, `uvicorn` |
| Cold-start mitigation (`minInstances`) | Pre-warmed Cloud Run instances | Long-lived Gunicorn workers (no cold start by design) | `gunicorn` |
| 2nd gen concurrency (up to 1000/instance) | Cloud Run multi-concurrent container | Gunicorn workers + async Celery (multiple workers) | `gunicorn`, `celery` |
| Function isolation / sandboxing | Separate Cloud Run service per function | Docker container(s); consider separate Django app per domain | Docker |

## Firebase Hosting &amp; CDN

Firebase Hosting is one of the most developer-friendly static and dynamic hosting services available. It wraps a Google Cloud CDN-backed delivery tier, a hash-deduplicating atomic deploy system, a version/release/channel data model for rollback and preview environments, automatic SSL provisioning, and a rich `firebase.json` routing layer (rewrites, redirects, custom headers, i18n) into a single CLI command. This section covers every sub-feature and provides a concrete Django rebuild strategy.

---

### Architecture Overview: How Firebase Hosting Works

```
Developer Machine          Firebase Infra                 Users
─────────────────          ──────────────                 ─────
firebase deploy ──────▶  [Hosting API]
                            │  hash-dedup upload
                            ▼
                         [GCS Object Store]  ◀── versioned objects (SHA256 keys)
                            │
                         [Version record]
                            │
                         [Release record]  ──── points to Version
                            │
                            ▼
                         [Superstatic routing layer]  ─── rewrites/redirects/headers
                            │
                            ▼
                         [Google Cloud CDN edge nodes]  ──▶  User (HTTPS, Brotli)
```

**Key properties of the live system (verified 2025-2026):**

- Files are stored deduplicated by SHA-256 in a GCS-backed object store. On each deploy the CLI only uploads file bodies for hashes not already present — identical files across deploys are never re-uploaded.
- Every asset is cached on SSDs at CDN edge nodes (Google's own edge, not Fastly/Akamai). Auto-negotiated compression: Brotli for clients that support it, gzip otherwise.
- On every `firebase deploy`, the entire CDN cache for the site is invalidated globally, so users see new content on the very next request. Only the first request per edge node after deploy is a cache miss.
- A **Version** is an immutable snapshot of files + config. A **Release** is a pointer from a **Channel** to a Version. Rollback = create a new Release pointing to an older Version.
- The underlying routing layer is **Superstatic**, an open-source Node.js library Firebase maintains at `firebase/superstatic`. All `firebase.json` routing rules run through it.

**Pricing gotchas (as of August 2025):**
- Free tier: 10 GB storage, 360 MB/day bandwidth.
- Blaze: $0.026/GB stored, $0.15/GB cached bandwidth, $0.20/GB uncached bandwidth.
- Max file size: **2 GB** per individual file.
- Storage quota is project-level (not per-site or per-channel).

---

### Feature 1: Static File Hosting + Global CDN

**What it does.** You run `firebase deploy --only hosting` and your built SPA/static site is globally distributed. Every file gets a Content-Type, ETag, and appropriate Cache-Control header. Fingerprinted assets (`.abc123.js`) get `Cache-Control: public, max-age=31536000, immutable`. HTML files get short or no-cache headers.

**Under the hood.** The Firebase CLI computes SHA-256 for every local file, sends the hash list to the Hosting API, receives back a list of only the hashes it doesn't have yet, uploads those file bodies, finalizes the Version, creates a Release, and triggers a CDN purge. Brotli and gzip variants are stored at the edge.

**Django Rebuild.**

For development / small deployments, [WhiteNoise](https://whitenoise.readthedocs.io/) (`pip install whitenoise[brotli]`) serves static files directly from the Django process with pre-compressed variants and far-future cache headers:

```python
# settings.py
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # immediately after Security
    ...
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
# Generates content-hashed filenames + pre-compresses gzip + brotli at collectstatic time

WHITENOISE_MAX_AGE = 31536000     # 1 year for hashed assets
WHITENOISE_INDEX_FILE = True      # serve index.html at directory roots
```

For production / CDN-backed deployments, push static files to **MinIO** (self-hosted S3) or real S3 via `django-storages`:

```bash
pip install django-storages[s3] boto3 django-minio-backend
```

```python
# settings.py (production)
STORAGES = {
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
}
AWS_STORAGE_BUCKET_NAME = "my-static-assets"
AWS_S3_CUSTOM_DOMAIN = "static.cdn.example.com"   # Cloudflare proxied
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "public, max-age=31536000, immutable"
}
AWS_QUERYSTRING_AUTH = False
STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
```

Cloudflare sits in front of MinIO/S3 as the CDN. All static URLs contain content hashes (`ManifestStaticFilesStorage`) so cache TTL can safely be 1 year — the URL changes when content changes, so no purge is needed for static assets.

**Nginx fallback** for non-S3 setups: Nginx with `sendfile on; tcp_nopush on; gzip_static on; brotli_static on;` serves pre-compressed files directly from disk at `STATIC_ROOT`.

---

### Feature 2: Atomic Deploys + CDN Cache Invalidation

**What it does.** A deploy is all-or-nothing. Users never see a half-deployed state. The moment a deploy completes, the global CDN switches to serving the new content.

**Under the hood.** The Release pointer swap is a single atomic write in Firebase's metadata store. Before the pointer switches, the new Version is fully uploaded and validated. CDN cache purge is issued after the pointer switch, not before — so there is a brief window (milliseconds) where old content may still be cached at some edges.

**Django Rebuild.**

The atomic unit is a **Docker image**. Each deploy tags a new image with the git SHA:

```bash
# Build
docker build -t registry.example.com/app:$(git rev-parse --short HEAD) .
docker push registry.example.com/app:$(git rev-parse --short HEAD)

# Deploy atomically with Kamal (zero-downtime container swap)
kamal deploy
```

[Kamal](https://kamal-deploy.org/) (`gem install kamal`) boots the new container, waits for health checks, then cuts traffic from the old container to the new one — the old container keeps running until traffic is fully drained. This is the Django equivalent of Firebase's pointer swap.

Store the deploy history in Postgres:

```python
# models.py
class HostingVersion(models.Model):
    site = models.ForeignKey("HostingSite", on_delete=models.CASCADE)
    image_tag = models.CharField(max_length=128)           # git sha or semver
    file_manifest = models.JSONField(default=dict)         # {path: sha256}
    status = models.CharField(                             # PENDING / FINALIZED / DELETED
        max_length=20,
        choices=[("PENDING","Pending"),("FINALIZED","Finalized"),("DELETED","Deleted")],
        default="PENDING",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)


class HostingRelease(models.Model):
    channel = models.ForeignKey("HostingChannel", on_delete=models.CASCADE, related_name="releases")
    version = models.ForeignKey(HostingVersion, on_delete=models.PROTECT)
    deployed_at = models.DateTimeField(auto_now_add=True)
    deployed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-deployed_at"]
```

After the container swap, trigger a Cloudflare CDN cache purge via Celery:

```python
# tasks.py
import cloudflare

@shared_task
def purge_cdn_cache(zone_id: str, paths: list[str] | None = None):
    cf = cloudflare.Cloudflare(api_token=settings.CLOUDFLARE_API_TOKEN)
    if paths:
        cf.cache.purge(zone_id=zone_id, files=paths)
    else:
        cf.cache.purge(zone_id=zone_id, purge_everything=True)
```

```bash
pip install cloudflare celery redis
```

---

### Feature 3: One-Click Rollback

**What it does.** In the Firebase Console, hover over any previous release in the history table → Roll back. A new Release is created pointing to that old Version. The CDN immediately reflects the old content.

**Under the hood.** There is no "undo" — rollback is a forward operation that creates a new Release pointing to an old immutable Version. The content for that old version is still in GCS.

**Django Rebuild.**

```python
# views.py (DRF or django-ninja)
@api.post("/sites/{site_id}/channels/{channel_id}/rollback/{release_id}/")
def rollback(request, site_id: int, channel_id: int, release_id: int):
    target_release = get_object_or_404(
        HostingRelease, pk=release_id, channel_id=channel_id
    )
    new_release = HostingRelease.objects.create(
        channel_id=channel_id,
        version=target_release.version,
        deployed_by=request.user,
        message=f"Rollback to release #{release_id}",
    )
    # Trigger Kamal re-deploy of the old image tag
    deploy_image_tag.delay(target_release.version.image_tag, channel_id)
    purge_cdn_cache.delay(settings.CLOUDFLARE_ZONE_ID)
    return {"release_id": new_release.pk, "image_tag": target_release.version.image_tag}
```

The `deploy_image_tag` Celery task SSHes into the target host (or calls the Kamal API) and runs `kamal deploy --version=<image_tag>`. Because Docker images are immutable and already in the registry, this is near-instant.

---

### Feature 4: Preview Channels

**What it does.** `firebase hosting:channel:deploy my-feature` deploys to `https://my-feature--myproject-abc12.web.app` — an isolated URL with its own releases and versions. Channels expire (default 7 days, max 30 days). GitHub Actions auto-creates a per-PR channel and posts the URL as a comment.

**Under the hood.** A Channel is just a named slot that holds a Release pointer and a DNS record pointing a subdomain at Firebase's CDN with the channel's version. Channels share the same GCS object store — files already uploaded for `live` don't need re-uploading for a preview channel if the content is identical.

**Django Rebuild — Option A: Coolify (recommended for most teams)**

[Coolify](https://coolify.io/) (`github.com/coollabsio/coolify`) is a self-hosted open-source PaaS that natively implements preview environments:

- Push to a branch → Coolify detects via webhook → builds Docker image → deploys to an isolated container → provisions Let's Encrypt SSL for `pr-123.preview.example.com` → posts URL to GitHub PR.
- Preview environments are real Docker deployments, not "shared staging."
- Cleanup is automatic when the PR closes.
- Zero code required beyond a `Dockerfile` and Coolify project config.

**Django Rebuild — Option B: DIY with Caddy + GitHub Actions**

Store channels in Postgres:

```python
class HostingChannel(models.Model):
    site = models.ForeignKey("HostingSite", on_delete=models.CASCADE)
    name = models.SlugField(max_length=64)          # "pr-123", "staging", "live"
    subdomain = models.CharField(max_length=255)    # "pr-123.preview.example.com"
    channel_type = models.CharField(               # "live" | "preview"
        max_length=10,
        choices=[("live", "Live"), ("preview", "Preview")],
        default="preview",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    current_release = models.ForeignKey(
        "HostingRelease", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="active_for_channel",
    )

    class Meta:
        unique_together = [("site", "name")]
```

Caddy with on-demand TLS handles SSL issuance. The Caddy `ask` endpoint checks the channel exists:

```python
# views.py
@api.get("/internal/caddy/ask/")
def caddy_ask(request, domain: str):
    """Caddy calls this to authorize on-demand TLS certificate issuance."""
    exists = HostingChannel.objects.filter(subdomain=domain, expires_at__gt=timezone.now()).exists()
    if not exists:
        exists = HostingDomain.objects.filter(domain=domain, verified=True).exists()
    if exists:
        return HttpResponse(status=200)
    return HttpResponse(status=403)
```

```caddyfile
# Caddyfile (preview channels via wildcard + on-demand TLS)
{
    on_demand_tls {
        ask http://django:8000/internal/caddy/ask/
    }
}

*.preview.example.com {
    tls {
        on_demand
    }
    reverse_proxy django:8000
}
```

GitHub Actions workflow:

```yaml
# .github/workflows/preview.yml
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build & push image
        run: |
          docker build -t registry.example.com/app:pr-${{ github.event.number }} .
          docker push registry.example.com/app:pr-${{ github.event.number }}
      - name: Create preview channel
        run: |
          curl -X POST https://yourservice.com/api/hosting/channels/ \
            -H "Authorization: Bearer ${{ secrets.DEPLOY_TOKEN }}" \
            -d '{"site_id": 1, "name": "pr-${{ github.event.number }}",
                 "image_tag": "pr-${{ github.event.number }}",
                 "expires_in_days": 7}'
      - name: Post preview URL to PR
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '🚀 Preview: https://pr-${{ github.event.number }}.preview.example.com'
            })
```

A Celery beat task prunes expired channels daily:

```python
@shared_task
def cleanup_expired_channels():
    expired = HostingChannel.objects.filter(
        expires_at__lt=timezone.now(), channel_type="preview"
    )
    for channel in expired:
        deprovision_channel.delay(channel.pk)   # stops container, removes Caddy route
    expired.delete()
```

---

### Feature 5: Custom Domains + Auto SSL

**What it does.** Connect `www.example.com` to your Firebase site. Firebase proves domain ownership via DNS TXT challenge, then provisions a Let's Encrypt certificate automatically. SSL renews without any user action. Both apex and www are supported. Propagation can take up to 24 hours.

**Under the hood.** Firebase uses the ACME DNS-01 challenge (requires adding a TXT record). Once verified, Let's Encrypt issues a wildcard or specific cert. Firebase stores and manages the cert on the CDN layer. If a user has conflicting A/CNAME/AAAA records, cert provisioning fails.

**Django Rebuild.**

```python
class HostingDomain(models.Model):
    site = models.ForeignKey("HostingSite", on_delete=models.CASCADE)
    domain = models.CharField(max_length=253, unique=True)   # "www.example.com"
    verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=128, blank=True)
    ssl_provisioned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

Two approaches for automatic SSL:

**Approach A — Caddy on-demand TLS (recommended):**

Caddy handles cert issuance transparently on first TLS handshake. The Django `ask` endpoint (shown above) approves the domain if `HostingDomain.verified=True`. The user adds a CNAME pointing their domain at your Caddy server; Caddy obtains the cert via HTTP-01 or DNS-01.

```caddyfile
# Custom domains — on-demand TLS
:443 {
    tls {
        on_demand
    }
    reverse_proxy django:8000
}
```

**Approach B — Certbot + Cloudflare DNS-01 (for wildcard certs):**

```bash
pip install certbot certbot-dns-cloudflare
certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/cloudflare.ini \
  -d "*.preview.example.com" \
  -d "example.com"
```

For user-provided custom domains, Certbot runs via a Celery task after DNS verification:

```python
@shared_task
def provision_ssl_for_domain(domain_id: int):
    domain = HostingDomain.objects.get(pk=domain_id)
    # Run certbot; update nginx/caddy config
    result = subprocess.run(
        ["certbot", "certonly", "--webroot", "-w", "/var/www/certbot",
         "-d", domain.domain, "--non-interactive", "--agree-tos",
         "-m", settings.LETSENCRYPT_EMAIL],
        capture_output=True,
    )
    if result.returncode == 0:
        domain.ssl_provisioned = True
        domain.save(update_fields=["ssl_provisioned"])
        reload_caddy_config.delay()
```

**DNS Verification flow:**

```python
@api.post("/api/hosting/domains/{domain_id}/verify/")
def verify_domain(request, domain_id: int):
    domain = get_object_or_404(HostingDomain, pk=domain_id, site__project__owner=request.user)
    import dns.resolver
    try:
        answers = dns.resolver.resolve(f"_firebase.{domain.domain}", "TXT")
        for rdata in answers:
            if domain.verification_token in str(rdata):
                domain.verified = True
                domain.save(update_fields=["verified"])
                provision_ssl_for_domain.delay(domain.pk)
                return {"verified": True}
    except Exception:
        pass
    return {"verified": False}
```

```bash
pip install dnspython
```

---

### Feature 6: Rewrites, Redirects, and Custom Headers

**What it does.** `firebase.json` has three arrays that define the full routing behavior of the site:

```json
{
  "hosting": {
    "public": "build",
    "cleanUrls": true,
    "trailingSlash": false,
    "rewrites": [
      { "source": "/api/**", "run": { "serviceId": "api", "region": "us-central1" } },
      { "source": "**", "destination": "/index.html" }
    ],
    "redirects": [
      { "source": "/old-path", "destination": "/new-path", "type": 301 }
    ],
    "headers": [
      {
        "source": "**/*.@(js|css)",
        "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }]
      },
      {
        "source": "**",
        "headers": [
          { "key": "X-Frame-Options", "value": "DENY" },
          { "key": "X-Content-Type-Options", "value": "nosniff" }
        ]
      }
    ]
  }
}
```

Processing order (Superstatic): exact file match → custom headers → redirects → rewrites → 404.

**Django Rebuild — Redirects:**

Use `django-redirects` for DB-backed URL redirects managed via Django admin:

```bash
pip install django-redirects
```

```python
INSTALLED_APPS += ["redirects"]
MIDDLEWARE += ["redirects.middleware.RedirectMiddleware"]
```

For high-volume or edge redirects, render Nginx `map` blocks from the DB:

```nginx
# /etc/nginx/conf.d/redirects.conf (generated by Celery task)
map $uri $redirect_uri {
    /old-path  /new-path;
    /legacy    https://external.com/page;
}
server {
    if ($redirect_uri) { return 301 $redirect_uri; }
}
```

**Django Rebuild — Rewrites (SPA fallback):**

```nginx
location / {
    try_files $uri $uri.html $uri/ /index.html;
}

location /api/ {
    proxy_pass http://django:8000;
    proxy_set_header Host $host;
}
```

For dynamic Nginx config from DB rules, a Celery task renders a Jinja2 template and runs `nginx -s reload`. Caddy supports this via its JSON config API (`POST /config/`) without restarting.

**Django Rebuild — Custom Headers:**

```python
# settings.py
SECURE_CONTENT_TYPE_NOSNIFF = True       # X-Content-Type-Options: nosniff
X_FRAME_OPTIONS = "DENY"                 # X-Frame-Options
SECURE_HSTS_SECONDS = 31536000           # Strict-Transport-Security

# CORS
INSTALLED_APPS += ["corsheaders"]
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")
CORS_ALLOWED_ORIGINS = ["https://app.example.com"]

# CSP
INSTALLED_APPS += ["csp"]
MIDDLEWARE += ["csp.middleware.CSPMiddleware"]
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'nonce-{NONCE}'"],
    }
}
```

```bash
pip install django-cors-headers django-csp
```

Per-URL-glob header rules from DB rendered into Nginx `add_header` or Caddy `header` directives.

---

### Feature 7: cleanUrls and trailingSlash

**What it does.** `cleanUrls: true` makes `/about.html` accessible at `/about`. `trailingSlash: false` removes trailing slashes from all paths (redirect 301).

**Django Rebuild.**

```python
# settings.py
APPEND_SLASH = True   # Django's built-in trailing slash behavior (adds, not removes)

# For cleanUrls: WhiteNoise supports index files but not .html stripping natively.
# Use a custom middleware:

class CleanUrlsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.endswith(".html") and path != "/index.html":
            from django.http import HttpResponsePermanentRedirect
            return HttpResponsePermanentRedirect(path[:-5])
        return self.get_response(request)
```

For Nginx: `try_files $uri $uri.html $uri/index.html =404;` combined with `rewrite ^/(.*)/$ /$1 permanent;` for trailing slash removal.

---

### Feature 8: i18n Rewrites (Accept-Language / Country Routing)

**What it does.** Firebase reads `Accept-Language` and `x-country-code` request headers and serves content from matching locale sub-directories transparently, falling back to the root.

**Django Rebuild.**

```python
# settings.py
MIDDLEWARE += [
    "django.middleware.locale.LocaleMiddleware",
]
LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("fr", "French"),
    ("de", "German"),
]
USE_I18N = True
# URL-prefix routing (Django built-in):
# /en/about/, /fr/about/, /de/about/
```

For header-based routing without URL prefix changes (matching Firebase behavior more closely), use a custom middleware:

```python
class AcceptLanguageRoutingMiddleware:
    """Serve locale-specific static bundles based on Accept-Language without URL change."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = self._detect_language(request)
        request.LANGUAGE_CODE = lang
        return self.get_response(request)

    def _detect_language(self, request):
        from django.utils.translation import get_language_from_request
        return get_language_from_request(request)
```

```bash
pip install django-localflavor   # country-code data
```

---

### Feature 9: Hosting REST API (Programmatic Deploy)

**What it does.** Enables CI/CD tools to deploy to Firebase Hosting without the CLI. The API is hash-aware: it asks which file hashes it already has, so only genuinely new files need uploading.

**API flow:**
1. `POST /v1beta1/sites/{site}/versions` → returns `{name, status: "CREATED"}`
2. `POST /v1beta1/{version}:populateFiles` with `{files: {"/path": "sha256hash"}}` → returns `{uploadRequiredHashes: [...]}`
3. `POST /upload/{uploadUrl}` for each required hash
4. `PATCH /v1beta1/{version}` with `{status: "FINALIZED"}`
5. `POST /v1beta1/sites/{site}/releases` with `{versionName: "..."}` → atomically goes live

**Django Rebuild.**

```python
# api/hosting.py (django-ninja)
from ninja import Router
import hashlib

router = Router()

@router.post("/sites/{site_id}/versions/")
def create_version(request, site_id: int):
    site = get_object_or_404(HostingSite, pk=site_id)
    version = HostingVersion.objects.create(site=site, created_by=request.user)
    return {"id": version.pk, "status": version.status}


@router.post("/versions/{version_id}/populate-files/")
def populate_files(request, version_id: int, payload: FileManifestSchema):
    version = get_object_or_404(HostingVersion, pk=version_id)
    # Check which hashes MinIO already has
    existing = set(HostingFile.objects.filter(sha256__in=payload.files.values()).values_list("sha256", flat=True))
    required = [sha for sha in payload.files.values() if sha not in existing]
    version.file_manifest = payload.files
    version.save(update_fields=["file_manifest"])
    # Generate pre-signed MinIO upload URLs for required hashes
    upload_urls = {sha: minio_presign_put(sha) for sha in required}
    return {"upload_required_hashes": required, "upload_urls": upload_urls}


@router.patch("/versions/{version_id}/finalize/")
def finalize_version(request, version_id: int):
    version = get_object_or_404(HostingVersion, pk=version_id)
    version.status = "FINALIZED"
    version.save(update_fields=["status"])
    return {"status": "FINALIZED"}


@router.post("/sites/{site_id}/releases/")
def create_release(request, site_id: int, payload: CreateReleaseSchema):
    version = get_object_or_404(HostingVersion, pk=payload.version_id, status="FINALIZED")
    channel = HostingChannel.objects.get(site_id=site_id, name="live")
    release = HostingRelease.objects.create(
        channel=channel, version=version, deployed_by=request.user
    )
    channel.current_release = release
    channel.save(update_fields=["current_release"])
    # Trigger deploy + CDN purge asynchronously
    deploy_version.delay(version.pk, channel.pk)
    purge_cdn_cache.delay(settings.CLOUDFLARE_ZONE_ID)
    return {"release_id": release.pk}
```

```bash
pip install django-ninja minio cloudflare celery redis
```

---

### Feature 10: Multiple Sites per Project

**What it does.** One Firebase project can host multiple distinct sites (`app.example.com`, `docs.example.com`, `admin.example.com`), each with its own deploy history, channels, and custom domains. The `firebase use` + `.firebaserc` configuration routes CLI commands to the correct site.

**Django Rebuild.**

```python
class HostingSite(models.Model):
    project = models.ForeignKey("Project", on_delete=models.CASCADE, related_name="hosting_sites")
    name = models.SlugField(max_length=64)             # "app", "docs", "admin"
    default_subdomain = models.CharField(max_length=255)  # "app.preview.example.com"
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("project", "name")]
```

Caddy virtual hosts are generated per site. A Celery task re-renders the Caddy JSON config and calls `POST http://caddy:2019/load` (Caddy admin API) for hot reload when a site or custom domain is added/removed.

```python
def reload_caddy_config():
    import requests, json
    config = build_caddy_config_from_db()  # reads all active HostingSite + HostingDomain
    resp = requests.post("http://caddy:2019/load",
                         headers={"Content-Type": "application/json"},
                         data=json.dumps(config))
    resp.raise_for_status()
```

---

### Data Model Summary

```
Project
  └── HostingSite (name, default_subdomain)
        ├── HostingChannel (name, subdomain, expires_at, current_release_fk)
        │     └── HostingRelease (version_fk, deployed_at, deployed_by)
        ├── HostingVersion (image_tag, file_manifest JSON, status)
        ├── HostingDomain (domain, verified, ssl_provisioned)
        ├── HostingRedirect (source_pattern, destination, status_code)
        ├── HostingRewrite (source_pattern, destination_type, destination)
        └── HostingHeader (source_pattern, key, value)
```

---

### Infrastructure Stack Summary

| Layer | Firebase | Django Self-Hosted |
|---|---|---|
| Edge CDN | Google Cloud CDN (global) | Cloudflare (CDN + Cache Purge API) |
| SSL/TLS | Let's Encrypt via Firebase (auto) | Caddy on-demand TLS / Certbot |
| Static file serving | GCS + CDN edge | WhiteNoise (dev), MinIO+S3+Nginx (prod) |
| Compression | Brotli/gzip auto-negotiated | `whitenoise[brotli]`, Nginx brotli module |
| Atomic deploy | Version pointer swap + CDN purge | Kamal blue-green + Cloudflare purge |
| Rollback | New Release → old Version | Re-deploy old Docker image tag via Kamal |
| Preview channels | Firebase CDN subdomains + TTL | Caddy on-demand TLS + Docker Compose + Coolify |
| Custom domains | DNS TXT challenge + LE cert | Caddy ask-endpoint + dnspython verification |
| Routing rules | Superstatic (firebase.json) | Nginx config / Caddy JSON API |
| Redirects | firebase.json array | django-redirects + Nginx map |
| Custom headers | firebase.json array | Django SecurityMiddleware + django-cors-headers + django-csp + Nginx |
| Deploy API | Firebase Hosting REST API | django-ninja endpoints + MinIO presigned URLs |
| Expire / cleanup | Firebase TTL (built-in) | Celery beat + cleanup task |
| Config reload | Automatic (managed service) | Caddy admin API `POST /load` |

---

### Gotchas and Hard Parts

1. **Global CDN purge latency.** Firebase purges all CDN edges in seconds. Cloudflare's Cache Purge API is fast but not instantaneous. Use content-hashed filenames for all JS/CSS/images so they never need purging — only HTML files need purging on deploy.

2. **On-demand TLS rate limits.** Let's Encrypt has rate limits: 50 certs per registered domain per week. For large numbers of custom user domains, use Caddy with ZeroSSL as a fallback (Caddy does this automatically) and implement cert issuance throttling in the `ask` endpoint.

3. **Preview environment isolation.** Firebase preview channels share the same GCS object store, so they are cheap. Self-hosted Docker preview envs each need a container + cert. Use Coolify or a shared Nginx/Caddy proxy with per-channel path prefixes rather than full per-PR containers for cost control.

4. **Cache poisoning with Vary headers.** If serving i18n content from the same URL based on `Accept-Language`, ensure the CDN is configured to vary the cache key on that header. Cloudflare requires explicit Cache Rules to add `Accept-Language` to the cache key.

5. **Caddy persistence.** Caddy stores Let's Encrypt certs in `/data`. This volume must survive container restarts. Mount a named Docker volume and back it up. Using Redis or a shared filesystem for cert storage allows multi-node Caddy deployments.

6. **Superstatic processing order is strict.** In Nginx, replicate the exact order: `location =` (exact) before `location /` (prefix) before `try_files`. Failing to do this causes subtle routing bugs where rewrites shadow redirects.

7. **File upload deduplication.** The Firebase Hosting API's hash-based dedup is efficient. In the Django rebuild, MinIO object keys should be the SHA-256 hash of the file content (not the path), so `populateFiles` can check existence with a single DB or MinIO `HEAD` call.

## Realtime Sync Engine for the Django Clone

This is the hardest cluster to clone. Firebase's realtime layer is not a single service — it is a deeply integrated stack of proprietary transport, server-side query matching, change propagation, client-local caching, and offline reconciliation. This section gives you the full architecture of both Firebase's implementation and the Django equivalent, sub-feature by sub-feature.

---

### Overview: How Firebase Realtime Works

Firebase exposes two realtime databases with different internal architectures:

| | **RTDB** | **Firestore** |
|---|---|---|
| Transport | WebSocket (persistent, proprietary JSON framing) | gRPC bidirectional streaming (HTTP/2) |
| Data model | Mutable JSON tree | Document/Collection |
| Subscription model | Path-based (subtree) | Document or query listeners |
| Consistency | Eventual (single-shard per path) | Strong (Spanner-backed, TrueTime) |
| Fan-out model | Stateful node owns path shard | Reverse query matcher + changelog fan-out |
| Offline support | Disk queue, LWW on reconnect | IndexedDB cache, pending writes, LWW |
| Presence | Native (.info/connected + onDisconnect) | Not native — bridged via RTDB + Cloud Functions |
| Pricing gotcha | Simultaneous connections limit (Spark: 100, Blaze: pay-per-GB download) | Per-document read charged even for realtime snapshots |

---

### 1. Firestore Realtime Listeners (`onSnapshot`)

#### Developer-Facing API

```js
// Subscribe to a single document
import { doc, onSnapshot } from "firebase/firestore";
const unsub = onSnapshot(doc(db, "orders", "abc123"), (snapshot) => {
  console.log(snapshot.data(), snapshot.metadata.hasPendingWrites);
});

// Subscribe to a query
import { collection, query, where, onSnapshot } from "firebase/firestore";
const q = query(collection(db, "orders"), where("status", "==", "pending"));
const unsub = onSnapshot(q, { includeMetadataChanges: true }, (snapshot) => {
  snapshot.docChanges().forEach(change => {
    // change.type: "added" | "modified" | "removed"
    console.log(change.type, change.doc.id, change.doc.data());
  });
});
```

#### How Firebase Does It Under the Hood

Firestore's realtime path uses **gRPC bidirectional streaming** (`google.firestore.v1.Firestore/Listen`). The client opens a `ListenRequest` stream to a Firestore frontend server. That request registers the query with Firestore's internal **subscription service**.

The internal flow when a document is written:

```
Write commit → Spanner WAL/TrueTime log
    → Internal changelog / fan-out bus (Google Pub/Sub internal)
        → Subscription service (reverse query matcher)
            → Evaluates: which registered live queries match this document?
                → Per-matching-query: evaluate Security Rules for each subscriber
                    → Route DocumentChange delta to frontend servers
                        → Push via gRPC stream to client
```

The **reverse query matcher** is the key insight: instead of scanning documents to find which match a query, it scans registered queries to find which match an incoming document. It works like an inverted index over query predicates. This allows a single document mutation to fan out to millions of live queries efficiently.

Scaling gotcha: Firestore documentation warns that at very high subscription density, fan-out latency increases. They recommend using **Firestore aggregation queries** + batch delivery rather than millions of individual `onSnapshot` listeners on the same document.

#### Django Rebuild

The Django equivalent composes three layers:

```
[Client WebSocket] ←→ [Django Channels Consumer]
                              ↑
                     [Redis Channel Layer (channels_redis)]
                              ↑
                   [Change Bridge Worker]
                    /           \
         [Postgres pg_notify]  [Redis Streams / Debezium CDC]
```

**Step 1 — ASGI server and channel layer**

```python
# requirements: django-channels>=4.0, channels-redis>=4.2, daphne>=4.1
# settings.py
INSTALLED_APPS = ["channels", ...]
ASGI_APPLICATION = "myproject.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("redis", 6379)]},
    }
}
```

```python
# asgi.py
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import myapp.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(URLRouter(myapp.routing.websocket_urlpatterns))
    ),
})
```

**Step 2 — WebSocket consumer with per-document and per-query subscription**

```python
# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .subscriptions import SubscriptionRegistry
from .auth import authorize_subscription

class RealtimeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.subscriptions = {}  # sub_id → group_name
        await self.accept()

    async def disconnect(self, code):
        # Unsubscribe from all groups
        for sub_id, group_name in self.subscriptions.items():
            await self.channel_layer.group_discard(group_name, self.channel_name)
        await SubscriptionRegistry.remove_all(self.channel_name)

    async def receive(self, text_data):
        msg = json.loads(text_data)
        action = msg["action"]

        if action == "subscribe":
            await self._handle_subscribe(msg)
        elif action == "unsubscribe":
            await self._handle_unsubscribe(msg)
        elif action == "write":
            await self._handle_write(msg)

    async def _handle_subscribe(self, msg):
        sub_id = msg["sub_id"]
        collection = msg["collection"]
        doc_id = msg.get("doc_id")  # None means query subscription
        filters = msg.get("filters", [])

        # Authorization check
        if not await authorize_subscription(self.user, collection, doc_id, filters):
            await self.send(json.dumps({"type": "error", "sub_id": sub_id, "code": 403}))
            return

        if doc_id:
            # Document subscription: join group keyed by doc
            group_name = f"doc:{collection}:{doc_id}"
        else:
            # Query subscription: register filter spec in Redis
            group_name = f"query:{collection}:{sub_id}"
            await SubscriptionRegistry.add_query(
                collection=collection,
                filters=filters,
                group_name=group_name,
                channel_name=self.channel_name,
            )

        await self.channel_layer.group_add(group_name, self.channel_name)
        self.subscriptions[sub_id] = group_name

        # Send initial snapshot
        snapshot = await self._fetch_snapshot(collection, doc_id, filters)
        await self.send(json.dumps({
            "type": "snapshot",
            "sub_id": sub_id,
            "docs": snapshot,
            "_meta": {"from_cache": False, "pending": False},
        }))

    async def doc_change(self, event):
        """Called when channel layer delivers a document change to this consumer."""
        await self.send(json.dumps(event["payload"]))
```

**Step 3 — Change capture: PostgreSQL LISTEN/NOTIFY trigger**

```sql
-- migrations: install this trigger on every tracked table
CREATE OR REPLACE FUNCTION notify_doc_change() RETURNS TRIGGER AS $$
DECLARE
  payload JSON;
BEGIN
  payload := json_build_object(
    'collection', TG_TABLE_NAME,
    'doc_id',     COALESCE(NEW.id, OLD.id)::TEXT,
    'op',         TG_OP,                          -- INSERT / UPDATE / DELETE
    'data',       CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE row_to_json(NEW) END,
    'old',        CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE row_to_json(OLD) END
  );
  PERFORM pg_notify('doc_changes', payload::TEXT);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER orders_realtime
  AFTER INSERT OR UPDATE OR DELETE ON orders
  FOR EACH ROW EXECUTE FUNCTION notify_doc_change();
```

**Step 4 — Change bridge (async Postgres listener → Redis fan-out)**

```python
# change_bridge.py  — run as: python manage.py run_change_bridge
import asyncio, json
import psycopg  # psycopg>=3.1 (async-native)
from channels.layers import get_channel_layer
from .subscriptions import SubscriptionRegistry

async def run_bridge():
    channel_layer = get_channel_layer()
    dsn = "postgresql://user:pass@db:5432/mydb"

    async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
        await conn.execute("LISTEN doc_changes")
        async for notify in conn.notifies():
            event = json.loads(notify.payload)
            await fan_out(channel_layer, event)

async def fan_out(channel_layer, event):
    collection = event["collection"]
    doc_id = event["doc_id"]

    # 1. Fan-out to all direct document subscribers
    doc_group = f"doc:{collection}:{doc_id}"
    await channel_layer.group_send(doc_group, {
        "type": "doc.change",
        "payload": {"type": "change", "op": event["op"], "doc": event.get("data")},
    })

    # 2. Evaluate query subscriptions for this collection
    matching_groups = await SubscriptionRegistry.match_queries(collection, event)
    for group_name in matching_groups:
        await channel_layer.group_send(group_name, {
            "type": "doc.change",
            "payload": {"type": "change", "op": event["op"], "doc": event.get("data")},
        })
```

**Django management command to run the bridge:**

```python
# management/commands/run_change_bridge.py
import asyncio
from django.core.management.base import BaseCommand
from myapp.change_bridge import run_bridge

class Command(BaseCommand):
    help = "Run the Postgres LISTEN/NOTIFY → Redis fan-out bridge"

    def handle(self, *args, **options):
        asyncio.run(run_bridge())
```

**Gotchas:**
- `pg_notify` has a **8000 byte payload limit**. If document payloads exceed this, send only `(collection, doc_id)` in the notify and have the bridge re-fetch the full document from Postgres before fanning out.
- `pg_notify` is **not durable**: notifications sent while the listener is disconnected are lost. For guaranteed delivery, write to a `event_log` table and use a cursor-based polling approach as a fallback.
- At high write rates (>500 writes/s per table), `pg_notify` can flood the async listener. Use Redis Streams (via Debezium Server or a custom writer) for higher throughput.

---

### 2. Reverse Query Matching (Fan-Out)

#### How Firebase Does It

Firebase's subscription service maintains an in-memory inverted index of all active queries. When a document write arrives:
1. Extract all indexed field values from the new/old document.
2. Probe the inverted index to find all queries whose `where` clauses could potentially match.
3. Evaluate each candidate query fully against the document.
4. For each matching query, check Security Rules.
5. Deliver the document delta to the frontend server handling those subscribers.

This allows O(matching_queries) fan-out rather than O(all_queries) for each write.

#### Django Rebuild: SubscriptionRegistry

```python
# subscriptions.py
import json
import redis.asyncio as aioredis
from django.conf import settings

REDIS_URL = getattr(settings, "REDIS_URL", "redis://redis:6379/0")
redis_client = aioredis.from_url(REDIS_URL)

class SubscriptionRegistry:
    """Stores active query subscriptions in Redis and matches them on document change."""

    @staticmethod
    async def add_query(collection: str, filters: list, group_name: str, channel_name: str):
        key = f"query_subs:{collection}"
        value = json.dumps({"filters": filters, "group": group_name})
        await redis_client.hset(key, group_name, value)
        # Set TTL to auto-expire stale subscriptions (60 minutes)
        await redis_client.expire(key, 3600)

    @staticmethod
    async def remove_query(collection: str, group_name: str):
        key = f"query_subs:{collection}"
        await redis_client.hdel(key, group_name)

    @staticmethod
    async def match_queries(collection: str, event: dict) -> list[str]:
        """Return group names of all registered queries matching this event."""
        key = f"query_subs:{collection}"
        all_subs = await redis_client.hgetall(key)
        matching = []
        doc = event.get("data") or {}

        for group_name_bytes, spec_bytes in all_subs.items():
            spec = json.loads(spec_bytes)
            if _evaluate_filters(doc, spec["filters"]):
                matching.append(spec["group"])

        return matching


def _evaluate_filters(doc: dict, filters: list) -> bool:
    """
    Evaluate a list of filter specs against a document dict.
    Filter spec: {"field": "status", "op": "==", "value": "pending"}
    Supports: ==, !=, <, <=, >, >=, in, not-in, array-contains
    """
    for f in filters:
        field, op, value = f["field"], f["op"], f["value"]
        doc_val = doc.get(field)
        if op == "==" and doc_val != value: return False
        elif op == "!=" and doc_val == value: return False
        elif op == "<"  and not (doc_val is not None and doc_val < value): return False
        elif op == "<=" and not (doc_val is not None and doc_val <= value): return False
        elif op == ">"  and not (doc_val is not None and doc_val > value): return False
        elif op == ">=" and not (doc_val is not None and doc_val >= value): return False
        elif op == "in" and doc_val not in value: return False
        elif op == "not-in" and doc_val in value: return False
        elif op == "array-contains" and value not in (doc_val or []): return False
    return True
```

**Scale note:** For large deployments with tens of thousands of active query subscriptions per collection, the HSCAN + Python evaluation loop will become a bottleneck. Options:
- Move filter evaluation into a **Lua script** (executed atomically in Redis, no round-trip per filter).
- Shard `query_subs:{collection}` by a hash of the first filter predicate.
- Use a dedicated **matching worker** (separate process, not in the Channels event loop).

---

### 3. RTDB Realtime Sync (WebSocket JSON Protocol)

#### Developer-Facing API

```js
import { getDatabase, ref, onValue, push, set } from "firebase/database";
const db = getDatabase();

// Subscribe to a path
onValue(ref(db, "chats/room1/messages"), (snapshot) => {
  console.log(snapshot.val());
});

// Write
push(ref(db, "chats/room1/messages"), { text: "hello", uid: "u123" });
```

#### How Firebase Does It

RTDB is architecturally simpler than Firestore. It is a **mutable JSON tree** stored in an in-house database (not Spanner). The cluster shards the tree: each path prefix is owned by a specific server node. All reads/writes for that path route to the owning node. The owning node is responsible for:
- Maintaining WebSocket connections for all clients subscribed to that subtree.
- Fanning out writes to all connected subscribers **synchronously** (writes are not confirmed to the writer until all local subscribers have been updated).
- Persisting changes to disk.

The WebSocket wire format uses a JSON envelope: `{"t": "d", "d": {"b": {"p": "/chats/room1", "d": {...}}}}`.

#### Django Rebuild

RTDB's simpler model is actually easier to replicate than Firestore. Use a `JsonDocument` model with a `path` field:

```python
# models.py
from django.db import models

class RTNode(models.Model):
    path = models.TextField(unique=True, db_index=True)  # e.g. "chats/room1/messages"
    data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL)

    class Meta:
        indexes = [models.Index(fields=["path"])]
```

```python
# consumers.py (RTDB-style path subscription)
class RTDBConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.subscribed_paths = set()
        await self.accept()

    async def receive(self, text_data):
        msg = json.loads(text_data)
        if msg["action"] == "subscribe_path":
            path = msg["path"]
            group = f"rtdb:{path.replace('/', ':')}"
            await self.channel_layer.group_add(group, self.channel_name)
            self.subscribed_paths.add(group)
            # Send current value
            node = await RTNode.objects.filter(path=path).afirst()
            await self.send(json.dumps({
                "t": "d", "d": {"p": path, "d": node.data if node else None}
            }))
```

---

### 4. Connection Management, Reconnect & Exponential Backoff

#### How Firebase Does It

Both SDKs implement:
- **Persistent connection detection**: a periodic ping/pong or keep-alive frame.
- **Reconnect with truncated binary exponential backoff**: initial delay 1s, doubles each retry, capped at 30s, with ±25% random jitter to prevent thundering herd.
- **Subscription re-registration**: on reconnect, the SDK re-sends all active `ListenRequest`s and merges server state with local cache.
- **Resume token**: Firestore `ListenRequest` can include a `resume_token` opaque bytes field that lets the server replay changes since the last delivered snapshot, avoiding a full re-sync.

#### Django Rebuild

Server side: Django Channels handles disconnection detection automatically via the WebSocket protocol ping/pong. The consumer's `websocket_disconnect` handler fires and cleans up.

Client side (your JavaScript SDK must implement this):

```js
// client-sdk/connection.js
class RealtimeConnection {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.retries = 0;
    this.maxDelay = 30000;
    this.subscriptions = new Map();  // sub_id → {collection, doc_id, filters, callback}
    this.pendingOutbox = [];
  }

  connect() {
    this.ws = new WebSocket(this.url);
    this.ws.onopen = () => {
      this.retries = 0;
      this._resubscribeAll();
      this._flushOutbox();
    };
    this.ws.onmessage = (e) => this._dispatch(JSON.parse(e.data));
    this.ws.onclose = () => this._scheduleReconnect();
  }

  _scheduleReconnect() {
    const delay = Math.min(
      1000 * Math.pow(2, this.retries) * (0.75 + Math.random() * 0.5),
      this.maxDelay
    );
    this.retries++;
    setTimeout(() => this.connect(), delay);
  }

  _resubscribeAll() {
    for (const [sub_id, spec] of this.subscriptions) {
      this.ws.send(JSON.stringify({ action: "subscribe", sub_id, ...spec }));
    }
  }
}
```

Server-side **event log** for catch-up replay (avoids full re-sync):

```python
# models.py
class ChangeEvent(models.Model):
    collection = models.CharField(max_length=200)
    doc_id = models.CharField(max_length=200)
    op = models.CharField(max_length=10)   # INSERT / UPDATE / DELETE
    data = models.JSONField(null=True)
    seq = models.BigAutoField(primary_key=True)  # monotonically increasing
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["collection", "doc_id", "seq"]),
        ]
```

Client sends `{"action": "subscribe", ..., "since_seq": 4821}` and the server replays all `ChangeEvent` rows with `seq > 4821` for that collection/query before switching to live feed.

---

### 5. Presence System

#### How Firebase Does It

**RTDB** has native presence:
- `/.info/connected` — a synthetic boolean path that changes to `true`/`false` on WebSocket connect/disconnect, updated by the server (not the client).
- `onDisconnect()` — registers server-side hooks that execute **atomically when TCP drops**, even if the client never sends a clean close. This is the key reliability property: the server commits these operations when it detects connection loss.
- `ServerValue.TIMESTAMP` — a sentinel that the server replaces with its own clock, preventing client clock skew.

**Firestore** has NO native presence. Google's own documentation recommends bridging through RTDB for presence data.

#### Django Rebuild

Use Redis sorted sets (score = timestamp) for presence. The WebSocket consumer writes presence on connect and deletes on disconnect. A background sweeper evicts stale entries (dead connections that missed the disconnect event):

```python
# presence.py
import time
import redis.asyncio as aioredis

redis_client = aioredis.from_url("redis://redis:6379/0")

class PresenceManager:
    HEARTBEAT_INTERVAL = 20   # seconds
    PRESENCE_TTL = 60         # seconds; evict if no heartbeat

    @staticmethod
    async def join(room: str, user_id: str, metadata: dict):
        key = f"presence:{room}"
        score = time.time()
        value = json.dumps({"user_id": user_id, **metadata})
        await redis_client.zadd(key, {value: score})
        await redis_client.expire(key, 3600)

    @staticmethod
    async def leave(room: str, user_id: str):
        key = f"presence:{room}"
        # Remove all members for this user_id (iterate if multiple sessions)
        members = await redis_client.zrange(key, 0, -1)
        for m in members:
            d = json.loads(m)
            if d.get("user_id") == user_id:
                await redis_client.zrem(key, m)

    @staticmethod
    async def heartbeat(room: str, user_id: str):
        """Call every HEARTBEAT_INTERVAL seconds to keep presence alive."""
        key = f"presence:{room}"
        members = await redis_client.zrange(key, 0, -1, withscores=True)
        for m, score in members:
            d = json.loads(m)
            if d.get("user_id") == user_id:
                await redis_client.zadd(key, {m: time.time()})

    @staticmethod
    async def list_present(room: str) -> list:
        key = f"presence:{room}"
        cutoff = time.time() - PresenceManager.PRESENCE_TTL
        # Evict stale members
        await redis_client.zremrangebyscore(key, "-inf", cutoff)
        members = await redis_client.zrange(key, 0, -1)
        return [json.loads(m) for m in members]
```

Integrate into the consumer:

```python
class RealtimeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.room = self.scope["url_route"]["kwargs"]["room"]
        await PresenceManager.join(self.room, str(self.user.id), {"name": self.user.username})
        # Broadcast presence change to room
        await self.channel_layer.group_send(
            f"room:{self.room}",
            {"type": "presence.update", "event": "join", "user_id": str(self.user.id)}
        )
        await self.accept()
        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def disconnect(self, code):
        self._heartbeat_task.cancel()
        await PresenceManager.leave(self.room, str(self.user.id))
        await self.channel_layer.group_send(
            f"room:{self.room}",
            {"type": "presence.update", "event": "leave", "user_id": str(self.user.id)}
        )

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(PresenceManager.HEARTBEAT_INTERVAL)
            await PresenceManager.heartbeat(self.room, str(self.user.id))
```

---

### 6. Optimistic Local Writes + Server Reconciliation

#### How Firebase Does It

When the Firestore SDK performs a write while online or offline:
1. **Local apply**: The mutation is applied immediately to the in-memory + IndexedDB cache. All `onSnapshot` listeners fire with `metadata.hasPendingWrites = true`.
2. **Outbox queue**: The mutation is appended to a persistent local outbox (IndexedDB, one entry per mutation).
3. **Server flush**: The SDK sends the mutation to the server. On ACK, the outbox entry is removed. `hasPendingWrites` clears.
4. **Reconciliation**: If the server returns a different value (e.g., a transform or security rule–triggered rewrite), the SDK applies the canonical server state over the local cache. `fromCache` becomes `false`.
5. **Rejection**: On auth failure or validation error, the mutation is removed from the outbox and the previous server state is restored in the local cache.

For RTDB: writes to the local tree are immediately applied, queued in an in-memory array (or disk if persistence enabled), and flushed on reconnect in order.

#### Django Rebuild

**Server side:** Use DRF with optimistic concurrency versioning:

```python
# models.py
class Document(models.Model):
    collection = models.CharField(max_length=200, db_index=True)
    doc_id = models.CharField(max_length=200, db_index=True)
    data = models.JSONField(default=dict)
    version = models.PositiveBigIntegerField(default=0)  # Lamport clock
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = [("collection", "doc_id")]

# serializers.py
class DocumentWriteSerializer(serializers.Serializer):
    data = serializers.DictField()
    client_version = serializers.IntegerField(required=False, default=0)

# views.py
class DocumentWriteView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, collection, doc_id):
        ser = DocumentWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        client_version = ser.validated_data.get("client_version", 0)

        with transaction.atomic():
            doc, created = Document.objects.select_for_update().get_or_create(
                collection=collection, doc_id=doc_id,
                defaults={"data": {}, "version": 0}
            )
            if not created and client_version > 0 and doc.version > client_version:
                # Conflict: server version is ahead of client
                return Response({
                    "error": "conflict",
                    "server_version": doc.version,
                    "server_data": doc.data,
                }, status=409)

            doc.data.update(ser.validated_data["data"])
            doc.version += 1
            doc.updated_by = request.user
            doc.save()

        return Response({"version": doc.version, "data": doc.data, "pending": False})
```

**Client side:** Recommend **RxDB** (`rxdb` npm package) as the local persistence layer for web clients — it provides IndexedDB-backed collections, a replication protocol, conflict handlers, and `hasPendingWrites`-equivalent state out of the box. For React Native use WatermelonDB.

---

### 7. Offline Queue + Conflict Resolution (LWW / CRDT)

#### How Firebase Does It

Firebase's default conflict resolution is **last-write-wins (LWW)** at the field level: the last mutation that reaches the server wins, regardless of when it was generated on the client. There is no vector clock or CRDT in the default path. For RTDB transactions, Firebase uses **read-hash compare-and-swap** (if the server value hasn't changed since you read it, the transaction applies; otherwise it retries). Firestore transactions retry up to 5 times under contention using optimistic concurrency.

#### Django Rebuild

**Strategy 1 — Pure LWW (simplest, matches Firebase default):**
- Each document has `updated_at` (server timestamp) and `client_seq` (monotonic integer per client session).
- On conflict, the write with the higher `updated_at` wins.
- Client's offline queue flushes in order; each write carries the `client_seq`.

**Strategy 2 — Field-level LWW with Lamport clocks (safer for concurrent edits):**

```python
# models.py — store per-field version clocks
class DocumentField(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="fields")
    field_name = models.CharField(max_length=200)
    value = models.JSONField()
    lamport_clock = models.PositiveBigIntegerField(default=0)

    class Meta:
        unique_together = [("document", "field_name")]

def merge_fields(document, incoming_fields: dict, incoming_clock: int):
    """Apply field-level LWW merge."""
    for field_name, value in incoming_fields.items():
        field, _ = DocumentField.objects.get_or_create(
            document=document, field_name=field_name,
            defaults={"value": None, "lamport_clock": 0}
        )
        if incoming_clock >= field.lamport_clock:  # LWW: higher clock wins
            field.value = value
            field.lamport_clock = incoming_clock
            field.save()
```

**Strategy 3 — CRDT (for collaborative / truly concurrent edits):**

Use `ypy` (Python bindings for Yjs, the gold-standard CRDT library) for text/rich content, or `py-crdt` for maps/lists:

```python
# pip install ypy>=0.6.2
import y_py as Y

# On the server, store the Yjs update bytes in a BinaryField
class YDocument(models.Model):
    doc_id = models.CharField(max_length=200, unique=True)
    ydoc_state = models.BinaryField(default=bytes)  # Yjs binary state vector

def apply_yjs_update(doc_id: str, update_bytes: bytes) -> bytes:
    """Apply a Yjs update from a client and return the new state."""
    ydoc_obj, _ = YDocument.objects.get_or_create(doc_id=doc_id)
    ydoc = Y.YDoc()
    if ydoc_obj.ydoc_state:
        Y.apply_update(ydoc, ydoc_obj.ydoc_state)
    Y.apply_update(ydoc, update_bytes)
    new_state = Y.encode_state_as_update(ydoc)
    YDocument.objects.filter(doc_id=doc_id).update(ydoc_state=new_state)
    return new_state
```

---

### 8. Change Data Capture (CDC) — At Scale

#### How Firebase Does It

Firestore's internal change pipeline is proprietary. The closest public analogy is **Supabase Realtime**, which uses PostgreSQL logical replication:

1. A **replication slot** is acquired on the Postgres primary.
2. Supabase's Elixir server **polls the replication slot** (`pg_logical_slot_get_changes`) rather than using streaming replication directly.
3. Each WAL record is decoded into a JSON change event.
4. Subscription IDs (Erlang process PIDs, globally unique) are appended to matching records.
5. The Erlang VM routes messages to those PIDs, which correspond to WebSocket connections.

This design avoids the complexity of Kafka while maintaining durability (WAL is durable by definition).

#### Django Rebuild — Three CDC Options

| Option | Latency | Durability | Complexity | Best For |
|---|---|---|---|---|
| Django signals (`post_save`) | ~0ms | None (in-process) | Trivial | Dev/small scale |
| Postgres LISTEN/NOTIFY | <5ms | Not durable (events lost on disconnect) | Low | Medium scale (<500 writes/s) |
| Debezium Server (WAL) | <50ms | Durable (WAL-backed) | Medium | Production, high scale |
| Sequin (managed WAL CDC) | <50ms | Durable | Low | Managed alternative to Debezium |

**Option A — Django signals (dev only):**

```python
# signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

channel_layer = get_channel_layer()

@receiver(post_save, sender=Document)
def document_saved(sender, instance, created, **kwargs):
    group = f"doc:{instance.collection}:{instance.doc_id}"
    async_to_sync(channel_layer.group_send)(group, {
        "type": "doc.change",
        "payload": {
            "type": "change",
            "op": "INSERT" if created else "UPDATE",
            "doc": instance.data,
        }
    })
```

**Option B — Postgres LISTEN/NOTIFY (medium scale):**
See the SQL trigger and Python bridge in Section 1 above. This is the recommended approach for most self-hosted deployments.

**Option C — Debezium Server (production, high scale):**

```yaml
# docker-compose.yml
debezium-server:
  image: quay.io/debezium/server:2.7
  environment:
    DEBEZIUM_SOURCE_CONNECTOR_CLASS: io.debezium.connector.postgresql.PostgresConnector
    DEBEZIUM_SOURCE_DATABASE_HOSTNAME: db
    DEBEZIUM_SOURCE_DATABASE_PORT: 5432
    DEBEZIUM_SOURCE_DATABASE_USER: replicator
    DEBEZIUM_SOURCE_DATABASE_PASSWORD: secret
    DEBEZIUM_SOURCE_DATABASE_DBNAME: mydb
    DEBEZIUM_SOURCE_TABLE_INCLUDE_LIST: public.document,public.orders
    DEBEZIUM_SOURCE_PLUGIN_NAME: pgoutput
    DEBEZIUM_SINK_TYPE: redis
    DEBEZIUM_SINK_REDIS_ADDRESS: redis:6379
    DEBEZIUM_SINK_REDIS_TYPE: stream          # writes to Redis Streams
```

A Django Channels background worker consumes from Redis Streams:

```python
# cdc_consumer.py
import redis.asyncio as aioredis, json
from channels.layers import get_channel_layer

async def consume_cdc_stream():
    r = aioredis.from_url("redis://redis:6379/0")
    channel_layer = get_channel_layer()
    last_id = "0"

    while True:
        results = await r.xread({"debezium.mydb.public.document": last_id}, count=100, block=5000)
        for stream, messages in results:
            for msg_id, fields in messages:
                event = json.loads(fields[b"value"])
                collection = event["source"]["table"]
                doc_id = str(event["after"]["doc_id"])
                await fan_out(channel_layer, collection, doc_id, event)
                last_id = msg_id
```

---

### 9. Presence — Self-Hosting Gotchas & OSS Reference Implementations

**Supabase Realtime Presence:**
Uses Phoenix's built-in presence module (CRDT-based distributed presence tracking using Erlang's PG process groups). Each node tracks local presence; nodes gossip presence state using a distributed map. Presence diffs (`join`, `leave`) are computed and broadcast to channel members.

**Django equivalent:** The Redis sorted-set approach (Section 5) is simpler and adequate for most scale. For large multi-node deployments, use Redis Cluster with a `presence:{room}` ZSET per room on a dedicated Redis node.

**PocketBase Realtime:**
Uses Server-Sent Events (SSE, not WebSocket). On every record change, it iterates over **all connected clients** in memory and evaluates each client's subscription filter. This is `O(clients × subscriptions)` per write — fine for single-node, but does not horizontally scale. PocketBase has no Redis channel layer and no cross-node fan-out.

**Lesson for Django clone:** Django Channels + Redis channel layer gives you cross-node fan-out that PocketBase lacks, at the cost of a Redis dependency. This is the right trade-off for any multi-node deployment.

---

### 10. Metadata Flags: `hasPendingWrites`, `fromCache`, Snapshot Options

#### How Firebase Does It

Every Firestore snapshot carries `SnapshotMetadata`:
- `hasPendingWrites`: true if local mutations exist that haven't been ACKed.
- `fromCache`: true if the data came from local cache (client was offline).
- `includeMetadataChanges`: subscribe option that triggers a new snapshot delivery when only metadata changes (e.g., a pending write gets confirmed).

#### Django Rebuild

Include `_meta` in every WebSocket message envelope:

```python
# In the consumer, when sending a snapshot or change event:
await self.send(json.dumps({
    "type": "snapshot",
    "sub_id": sub_id,
    "docs": snapshot_docs,
    "_meta": {
        "from_cache": False,         # True when replaying from EventLog on reconnect
        "pending": False,            # True for optimistic local writes (client-side only)
        "server_time": datetime.utcnow().isoformat() + "Z",
        "seq": latest_event_seq,     # Client stores this as reconnect cursor
    }
}))
```

On the client SDK:
- `pending: true` is set by the client locally when a write is in the outbox.
- `from_cache: true` is set by the client when it is disconnected and returning stale IndexedDB/SQLite data.
- These flags are never set by the server — the server always sends authoritative data with `pending: false, from_cache: false`.

---

### Infrastructure Summary

| Component | Technology | Package / Image |
|---|---|---|
| ASGI server | Daphne or Uvicorn | `daphne>=4.1` / `uvicorn[standard]>=0.30` |
| WebSocket framework | Django Channels | `channels>=4.0` |
| Channel layer | Redis Pub/Sub | `channels-redis>=4.2` |
| Postgres async driver | psycopg v3 | `psycopg[async]>=3.1` |
| Change capture (simple) | pg_notify trigger | Built-in Postgres |
| Change capture (scale) | Debezium Server | `quay.io/debezium/server:2.7` |
| CDC sink (scale) | Redis Streams | `redis-py>=5.0` |
| Optimistic locking | django-concurrency | `django-concurrency>=2.5` |
| CRDT support | ypy (Yjs) | `ypy>=0.6.2` |
| Local client cache | RxDB (web) | `rxdb` (npm) |
| Offline queue (mobile) | WatermelonDB | `@nozbe/watermelondb` (npm) |
| Presence | Redis ZSET | `redis-py>=5.0` |
| Background worker | Celery or custom asyncio | `celery>=5.3` |

---

### Hard Parts When Self-Hosting

1. **Exactly-once delivery**: `pg_notify` drops events on listener disconnect. Mitigation: write to `ChangeEvent` table + cursor-based catch-up replay.
2. **Per-query fan-out at scale**: Evaluating thousands of query subscriptions per write in Python is slow. Mitigation: Lua scripts in Redis, or move matching to a dedicated Go/Rust microservice.
3. **Cross-node presence consistency**: Redis ZSET is eventually consistent under failure. Mitigation: use Redis Cluster with WAIT for stronger guarantees, or accept stale presence for up to `PRESENCE_TTL` seconds.
4. **CRDT merge on the server**: Requires storing binary CRDT state per document, increases storage significantly. Mitigation: only enable CRDT for specific collections (e.g., collaborative text editors), use LWW everywhere else.
5. **Client SDK complexity**: Firebase's SDK hides all of this (IndexedDB, backoff, re-subscription, pending writes, fromCache). You must build a client library that replicates this behavior. Use RxDB's replication plugin as a starting point and add the WebSocket transport adapter.

## Cloud Messaging (Push) & In-App Messaging

Firebase's messaging stack covers two distinct problems: getting a message to a device that is not currently connected to your server (push), and showing a rendered UI overlay to a user who is actively inside your app (in-app messaging). The push side alone spans three separate delivery pipelines — APNs for Apple devices, FCM transport for Android, and the W3C Web Push protocol for browsers — and FCM acts as a unified broker in front of all three. The Django rebuild must reimplement that broker layer directly.

---

### 1. Firebase Cloud Messaging (FCM) — Overview & Developer-Facing Shape

**What it does.** FCM is a cross-platform push notification gateway. Your app server sends a single HTTP request; FCM fans it out to one device token, a topic (pub/sub group of device tokens), or a boolean condition expression over topics. FCM then handles the last-mile delivery through the appropriate OS push channel.

**FCM HTTP v1 API (current, as of June 2024 — legacy API is fully retired)**

Endpoint: `POST https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send`

Authentication: OAuth 2.0 bearer token from a Google service account (scope `https://www.googleapis.com/auth/firebase.messaging`). The old Server Key string is no longer accepted.

```python
# Get short-lived access token (60-minute expiry)
from google.oauth2 import service_account
import google.auth.transport.requests

SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

def get_fcm_access_token(service_account_file: str) -> str:
    creds = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token
```

```json
// Minimal message — single device token
{
  "message": {
    "token": "eBx...device_registration_token",
    "notification": {
      "title": "New order shipped",
      "body": "Your order #1234 is on its way."
    },
    "data": {
      "order_id": "1234",
      "deep_link": "myapp://orders/1234"
    },
    "android": {
      "priority": "high",
      "ttl": "86400s",
      "collapse_key": "order_updates",
      "notification": {
        "channel_id": "orders",
        "click_action": "OPEN_ORDER"
      }
    },
    "apns": {
      "headers": {
        "apns-priority": "10",
        "apns-expiration": "0"
      },
      "payload": {
        "aps": {
          "alert": { "title": "New order shipped" },
          "badge": 1,
          "sound": "default",
          "mutable-content": 1
        }
      }
    },
    "webpush": {
      "headers": { "TTL": "86400" },
      "notification": {
        "title": "New order shipped",
        "icon": "/icon.png"
      }
    }
  }
}
```

```json
// Topic target
{ "message": { "topic": "weather_alerts", "notification": { "title": "Storm warning" } } }

// Condition target (boolean expression over topics)
{ "message": { "condition": "'dogs' in topics || 'cats' in topics", "notification": { "title": "Pet news" } } }
```

**Message types.**

| Type | Description |
|---|---|
| **Notification message** | Predefined keys (`title`, `body`, `icon`, `sound`, etc.) handled automatically by the OS/FCM SDK when the app is in background. |
| **Data message** | Arbitrary key-value pairs, always delivered to your app's `onMessage` handler regardless of foreground/background state. |
| **Notification + data** | Both payloads; OS renders the notification, app receives data on tap. |

---

### 2. How FCM Routes Under the Hood

```
App Server ──HTTP v1──► FCM Backend (Google infrastructure)
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    Android path         iOS path           Web path
          │                   │                   │
    Google Play          APNs gateway       Browser push
    Services (GMS)       (Apple)            endpoint
          │                   │                   │
    FCM SDK on          iOS device         Service worker
    device              (APNs delivers)    on browser
```

**Android.** Android devices maintain a single, persistent TCP/IP connection to FCM servers (shared across all apps on the device, managed by GMS). FCM delivers messages over this connection. High-priority messages wake the device even in Doze mode. Normal-priority messages are deferred until the next maintenance window.

**iOS / APNs.** FCM does NOT maintain a direct connection to iOS devices. When FCM receives a message for an iOS token, it forwards the payload to Apple's APNs HTTP/2 endpoint using token-based authentication (a `.p8` key signed as a JWT — certificate-based auth was deprecated in 2024). APNs then delivers to the device via Apple's own persistent TLS connection. FCM's iOS delivery guarantee is only as strong as APNs: once APNs accepts the message, FCM considers it delivered.

**APNs JWT flow (what FCM does internally):**
```
FCM ──JWT signed with Apple .p8 key──► APNs (api.push.apple.com:443, HTTP/2)
                                            │
                                    ──push frame──► Device persistent TLS
```

**Web Push / VAPID.** FCM supports Web Push by accepting a `webpush` config block. Internally, FCM encrypts the payload using the browser's `p256dh` public key + `auth` secret (RFC 8291 encryption), signs the request with a VAPID JWT (RFC 8292), and POSTs to the browser's push service endpoint (Chrome → FCM, Firefox → Mozilla autopush, Safari → Apple). This is the W3C standard push protocol; nothing proprietary about it.

**Topic fan-out.** Topics are stored as a mapping of `topic_name → [device_token, ...]` in FCM's backend (essentially a distributed subscription store). When you publish to a topic, FCM performs a fan-out — it reads the subscriber list and dispatches individual messages to each token. For large topics this is asynchronous and not instantaneous; FCM limits concurrent fan-outs to 1,000 per project, with a practical throughput ceiling of ~10,000 QPS per project. Limits: one app instance can subscribe to at most 2,000 topics; batch subscription requests are capped at 1,000 app instances per call; subscription management is rate-limited to 3,000 QPS per project.

**Token lifecycle.** Registration tokens are long-lived but can be refreshed by FCM or the OS at any time (app reinstall, device restore, data clear). A token inactive for >60 days is considered stale; at 270 days FCM marks it expired and returns `UNREGISTERED` errors. You must listen for these errors and delete stale tokens from your database.

**Collapse keys.** Collapsible messages share a `collapse_key`; if the device is offline, FCM keeps only the last message per collapse key per device (up to 4 distinct collapse keys simultaneously). Notification messages are always collapsible; data messages need an explicit `collapse_key` to collapse.

**Priority & TTL.** `HIGH` priority wakes the device immediately (counts against Android battery optimization budget). `NORMAL` is deferred. TTL ranges from 0 (discard if device unreachable) to 2,419,200 seconds (28 days, default). A `ttl: 0s` + `HIGH` priority message is a "transient" notification — never stored, fire-and-forget.

**Delivery receipts.** FCM does not provide real-time delivery callbacks by default. Delivery data is available only via BigQuery export (Firebase project feature, opt-in) with a reporting delay. There is no webhook when the device receives the message.

---

### 3. Device Token Management

**What Firebase does.** The client SDK calls `getToken()` → registers with FCM → gets a registration token. The SDK automatically refreshes the token when FCM rotates it and fires an `onTokenRefresh` callback. You must send the new token to your server.

```javascript
// Web SDK
import { getMessaging, getToken, onMessage } from "firebase/messaging";
const messaging = getMessaging();
const token = await getToken(messaging, { vapidKey: "YOUR_PUBLIC_VAPID_KEY" });
// Send `token` to your server via an authenticated API call
```

```kotlin
// Android
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    val token = task.result
    // POST token to your server
}
```

---

### 4. FCM Topics & Device Groups

**Topics.** Pub/sub at the device level. Subscribe a device:
```kotlin
// Android client
FirebaseMessaging.getInstance().subscribeToTopic("weather")
```
```javascript
// Web
messaging.subscribeToTopic(token, "weather")   // server-side only via Admin SDK
```

**Device Groups (legacy).** A server-maintained group of tokens identified by a `notification_key`. Messages sent to the group go to all tokens in it. This is largely superseded by topics for most use cases; device groups require explicit server-side management of the group key.

**Conditions.** Boolean expressions over topic membership: `'dogs' in topics && 'cats' in topics` — useful for cross-topic targeting without pre-building lists.

---

### 5. Notifications Composer

The Firebase console provides a visual campaign builder ("Cloud Messaging" → "Compose notification") that allows: scheduling, local timezone delivery, targeting by app, user segment (via Analytics audiences), or topic; A/B variant testing via Firebase A/B Testing integration; analytics tracking (open rate, conversion). It sends messages via the same FCM HTTP v1 API internally. This is the "no-code" layer on top of the raw API.

---

### 6. Firebase In-App Messaging (FIAM)

**What it does.** FIAM displays a rich UI overlay (card, banner, modal, or image-only) to users who are actively using the app, triggered by Analytics events. It is NOT push — it uses the Firebase Installation ID (FID), not the FCM registration token. The SDK polls Firebase servers once per day (interval = 86,400 s) to fetch active campaigns for the current installation. Triggers are matched client-side against Analytics events.

**Architecture.**
```
Firebase Console (campaign creator)
        │  Campaign stored in Firebase backend
        │
        ▼
App SDK polls once/day ──GET campaigns──► Firebase FIAM backend
        │  Returns list of active campaigns + trigger conditions
        │
On Analytics event (e.g. "click_restaurant"):
  SDK checks local campaign list → finds matching campaign → renders UI overlay
        │
User interaction → SDK reports impression/click back to Firebase
```

Key behavior:
- Campaigns are fetched eagerly and cached locally (up to once per day, configurable only via internal flags)
- Message display is suppressed while another message is showing
- Frequency cap: by default, one in-app message per 24 hours per user (global cap); per-campaign caps are also configurable
- Trigger events: any Firebase Analytics event, including auto-events (`app_open`, `screen_view`, custom events)
- A/B testing: campaigns integrate with Firebase A/B Testing for variant experiments

**Message types (SDK renders these natively):**

| Type | Description |
|---|---|
| Card | Image + title + body + primary button + optional secondary button |
| Modal | Close button (X) + optional image + title + body + button |
| Banner | Top/bottom strip, auto-dismisses, tappable |
| ImageOnly | Full-screen or partial-screen image with tap action |

---

### 7. The Django Rebuild — Concrete Architecture

#### 7.1 High-Level Component Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Django App Server (DRF)                                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  PushDevice registration API  │  Topic subscription API          │   │
│  │  Notification Dispatch API    │  Campaign CRUD API               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                │ enqueue                                                 │
└────────────────┼────────────────────────────────────────────────────────┘
                 │
        ┌────────▼────────┐
        │   Redis (broker)│  ◄── Celery task queue
        └────────┬────────┘
                 │
        ┌────────▼──────────────────────────────────────────┐
        │   Celery Workers                                   │
        │  ┌───────────────┐ ┌─────────────┐ ┌──────────┐  │
        │  │ send_fcm_task │ │ send_apns   │ │ send_web │  │
        │  │ (Android/FCM) │ │ _task (iOS) │ │ _push    │  │
        │  └───────────────┘ └─────────────┘ └──────────┘  │
        └───────────────────────────────────────────────────┘
                 │                    │              │
         FCM HTTP v1 API         APNs HTTP/2    Browser push
         (google-auth-library)   (aioapns)      endpoint (pywebpush)
```

#### 7.2 Data Models

```python
# push/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PushDevice(models.Model):
    """Stores one push token per device/browser per user."""

    PLATFORM_FCM = "fcm"       # Android
    PLATFORM_APNS = "apns"     # iOS
    PLATFORM_WEB = "web"       # Web Push (VAPID)
    PLATFORM_CHOICES = [
        (PLATFORM_FCM, "FCM (Android)"),
        (PLATFORM_APNS, "APNs (iOS)"),
        (PLATFORM_WEB, "Web Push"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="push_devices", null=True, blank=True
    )
    platform = models.CharField(max_length=8, choices=PLATFORM_CHOICES, db_index=True)
    registration_id = models.TextField(unique=True)  # FCM token / APNs token / web push endpoint
    # Web Push only — encrypted subscription keys
    p256dh = models.TextField(blank=True)
    auth = models.TextField(blank=True)
    # Metadata
    device_id = models.CharField(max_length=255, blank=True, db_index=True)
    app_version = models.CharField(max_length=50, blank=True)
    locale = models.CharField(max_length=10, blank=True)
    active = models.BooleanField(default=True, db_index=True)
    last_used_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "platform", "active"]),
            models.Index(fields=["last_used_at"]),  # for stale token cleanup
        ]


class TopicSubscription(models.Model):
    """Maps devices to topics (replicates FCM topic subscriptions locally)."""

    topic = models.CharField(max_length=255, db_index=True)
    device = models.ForeignKey(PushDevice, on_delete=models.CASCADE, related_name="subscriptions")
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("topic", "device")
        indexes = [models.Index(fields=["topic"])]


class NotificationCampaign(models.Model):
    """In-App Messaging: a campaign defining content + trigger + targeting."""

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_COMPLETED, "Completed"),
    ]

    MESSAGE_TYPE_CARD = "card"
    MESSAGE_TYPE_BANNER = "banner"
    MESSAGE_TYPE_MODAL = "modal"
    MESSAGE_TYPE_IMAGE = "image_only"
    MESSAGE_TYPE_CHOICES = [
        (MESSAGE_TYPE_CARD, "Card"),
        (MESSAGE_TYPE_BANNER, "Banner"),
        (MESSAGE_TYPE_MODAL, "Modal"),
        (MESSAGE_TYPE_IMAGE, "Image Only"),
    ]

    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default=MESSAGE_TYPE_CARD)

    # Content
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    primary_action_url = models.URLField(blank=True)
    primary_action_label = models.CharField(max_length=100, blank=True)
    secondary_action_url = models.URLField(blank=True)
    secondary_action_label = models.CharField(max_length=100, blank=True)

    # Trigger (event name from client analytics)
    trigger_event = models.CharField(max_length=255, default="app_open", db_index=True)

    # Targeting
    target_topic = models.CharField(max_length=255, blank=True)  # blank = all users
    target_user_properties = models.JSONField(default=dict)       # e.g. {"plan": "premium"}
    target_locale = models.CharField(max_length=10, blank=True)
    target_app_version = models.CharField(max_length=50, blank=True)  # semver range

    # Scheduling
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    # Frequency capping
    max_impressions_per_user = models.PositiveIntegerField(default=1)
    cooldown_seconds = models.PositiveIntegerField(default=86400)  # 24h default

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CampaignImpression(models.Model):
    """Tracks which user saw which campaign (for frequency capping)."""

    campaign = models.ForeignKey(NotificationCampaign, on_delete=models.CASCADE, related_name="impressions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="campaign_impressions")
    shown_at = models.DateTimeField(auto_now_add=True)
    clicked = models.BooleanField(default=False)
    dismissed = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["campaign", "user", "shown_at"])]


class PushNotificationLog(models.Model):
    """Delivery audit log per notification attempt."""

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_INVALID_TOKEN = "invalid_token"

    device = models.ForeignKey(PushDevice, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default=STATUS_PENDING, db_index=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### 7.3 Celery Tasks — FCM (Android), APNs (iOS), Web Push

```python
# push/tasks.py
import asyncio
import logging
from celery import shared_task, group
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── FCM (Android) via firebase-admin or raw HTTP v1 ──────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_fcm_notification(self, device_ids: list[int], title: str, body: str,
                           data: dict = None, collapse_key: str = None):
    """Send to a list of FCM (Android) devices in one multicast batch."""
    import firebase_admin
    from firebase_admin import messaging as fb_msg

    from .models import PushDevice, PushNotificationLog

    devices = PushDevice.objects.filter(id__in=device_ids, active=True, platform="fcm")
    tokens = [d.registration_id for d in devices]
    if not tokens:
        return

    message = fb_msg.MulticastMessage(
        tokens=tokens,
        notification=fb_msg.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        android=fb_msg.AndroidConfig(
            priority="high",
            collapse_key=collapse_key,
            ttl=86400,
        ),
    )
    try:
        response = fb_msg.send_each_for_multicast(message)
        # Handle per-token responses
        for device, resp in zip(devices, response.responses):
            if resp.success:
                PushNotificationLog.objects.create(
                    device=device, title=title, body=body, data=data or {},
                    status="sent", sent_at=timezone.now()
                )
            else:
                err = resp.exception.code if resp.exception else "unknown"
                if err in ("registration-token-not-registered", "invalid-registration-token"):
                    device.active = False
                    device.save(update_fields=["active"])
                    status = "invalid_token"
                else:
                    status = "failed"
                PushNotificationLog.objects.create(
                    device=device, title=title, body=body, data=data or {},
                    status=status, error_message=str(resp.exception)
                )
    except Exception as exc:
        raise self.retry(exc=exc)


# ── APNs (iOS) via aioapns ────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_apns_notification(self, device_ids: list[int], title: str, body: str,
                            data: dict = None, badge: int = None):
    """Send to a list of APNs (iOS) devices."""
    from .models import PushDevice, PushNotificationLog
    from django.conf import settings

    devices = PushDevice.objects.filter(id__in=device_ids, active=True, platform="apns")

    async def _send_all():
        from aioapns import APNs, NotificationRequest, PushType
        apns = APNs(
            key=settings.APNS_AUTH_KEY_PATH,         # path to .p8 file
            key_id=settings.APNS_AUTH_KEY_ID,
            team_id=settings.APNS_TEAM_ID,
            topic=settings.APNS_BUNDLE_ID,
            use_sandbox=settings.APNS_USE_SANDBOX,
        )
        payload = {"aps": {"alert": {"title": title, "body": body}, "sound": "default"}}
        if badge is not None:
            payload["aps"]["badge"] = badge
        if data:
            payload.update(data)

        for device in devices:
            from uuid import uuid4
            req = NotificationRequest(
                device_token=device.registration_id,
                message=payload,
                notification_id=str(uuid4()),
                push_type=PushType.ALERT,
            )
            result = await apns.send_notification(req)
            if result.is_successful:
                PushNotificationLog.objects.create(
                    device=device, title=title, body=body, data=data or {},
                    status="sent", sent_at=timezone.now()
                )
            else:
                err = result.description
                if err in ("BadDeviceToken", "Unregistered"):
                    device.active = False
                    device.save(update_fields=["active"])
                PushNotificationLog.objects.create(
                    device=device, title=title, body=body, data=data or {},
                    status="invalid_token" if err in ("BadDeviceToken", "Unregistered") else "failed",
                    error_message=err
                )

    try:
        asyncio.run(_send_all())
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Web Push (VAPID) via pywebpush ───────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_webpush_notification(self, device_ids: list[int], title: str, body: str,
                               data: dict = None, icon: str = None):
    """Send to a list of WebPush (browser) devices using VAPID."""
    import json
    from pywebpush import webpush, WebPushException
    from django.conf import settings
    from .models import PushDevice, PushNotificationLog

    devices = PushDevice.objects.filter(id__in=device_ids, active=True, platform="web")

    payload = json.dumps({"title": title, "body": body, "icon": icon, **(data or {})})

    for device in devices:
        subscription_info = {
            "endpoint": device.registration_id,
            "keys": {"p256dh": device.p256dh, "auth": device.auth},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.WEBPUSH_ADMIN_EMAIL}"},
            )
            PushNotificationLog.objects.create(
                device=device, title=title, body=body, data=data or {},
                status="sent", sent_at=timezone.now()
            )
        except WebPushException as ex:
            if ex.response and ex.response.status_code in (404, 410):
                # Subscription expired or unsubscribed
                device.active = False
                device.save(update_fields=["active"])
                status = "invalid_token"
            else:
                status = "failed"
            PushNotificationLog.objects.create(
                device=device, title=title, body=body, data=data or {},
                status=status, error_message=str(ex)
            )
        except Exception as exc:
            raise self.retry(exc=exc)
```

#### 7.4 Topic Fan-Out — Scalable Dispatch

```python
# push/dispatch.py
from celery import group as celery_group
from .tasks import send_fcm_notification, send_apns_notification, send_webpush_notification
from .models import PushDevice, TopicSubscription

CHUNK_SIZE = 500  # FCM multicast max is 500 tokens per call


def dispatch_to_topic(topic: str, title: str, body: str, data: dict = None):
    """
    Fan-out a notification to all devices subscribed to a topic.
    Splits into chunks to avoid hitting platform batch limits.
    Dispatches platform chunks in parallel via Celery group.
    """
    device_ids = list(
        TopicSubscription.objects
        .filter(topic=topic, device__active=True)
        .values_list("device_id", flat=True)
    )
    if not device_ids:
        return

    # Separate by platform
    devices_qs = PushDevice.objects.filter(id__in=device_ids, active=True)
    by_platform = {"fcm": [], "apns": [], "web": []}
    for d in devices_qs.values("id", "platform"):
        by_platform[d["platform"]].append(d["id"])

    tasks = []

    # FCM — batch up to 500 per call (send_each_for_multicast limit)
    for i in range(0, len(by_platform["fcm"]), CHUNK_SIZE):
        chunk = by_platform["fcm"][i:i + CHUNK_SIZE]
        tasks.append(send_fcm_notification.s(chunk, title, body, data))

    # APNs — individual sends via aioapns (async within task)
    for i in range(0, len(by_platform["apns"]), CHUNK_SIZE):
        chunk = by_platform["apns"][i:i + CHUNK_SIZE]
        tasks.append(send_apns_notification.s(chunk, title, body))

    # Web Push — individual sends via pywebpush
    for i in range(0, len(by_platform["web"]), CHUNK_SIZE):
        chunk = by_platform["web"][i:i + CHUNK_SIZE]
        tasks.append(send_webpush_notification.s(chunk, title, body, data))

    # Dispatch all chunks in parallel
    celery_group(tasks).apply_async()


def dispatch_to_device(device_id: int, title: str, body: str, data: dict = None):
    """Send to a single device — routes to the correct platform task."""
    device = PushDevice.objects.get(id=device_id, active=True)
    if device.platform == "fcm":
        send_fcm_notification.delay([device.id], title, body, data)
    elif device.platform == "apns":
        send_apns_notification.delay([device.id], title, body)
    elif device.platform == "web":
        send_webpush_notification.delay([device.id], title, body, data)
```

#### 7.5 DRF API Endpoints

```python
# push/serializers.py
from rest_framework import serializers
from .models import PushDevice, TopicSubscription

class DeviceRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushDevice
        fields = ["id", "platform", "registration_id", "p256dh", "auth", "device_id", "app_version", "locale"]

    def create(self, validated_data):
        user = self.context["request"].user
        obj, _ = PushDevice.objects.update_or_create(
            registration_id=validated_data["registration_id"],
            defaults={**validated_data, "user": user if user.is_authenticated else None, "active": True},
        )
        return obj


class TopicSubscriptionSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=255)
    action = serializers.ChoiceField(choices=["subscribe", "unsubscribe"])
```

```python
# push/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PushDevice, TopicSubscription
from .serializers import DeviceRegistrationSerializer, TopicSubscriptionSerializer
from .dispatch import dispatch_to_device, dispatch_to_topic


class DeviceViewSet(viewsets.ModelViewSet):
    """
    POST /api/push/devices/              → register or update a device token
    DELETE /api/push/devices/{id}/       → unregister (logout, uninstall)
    POST /api/push/devices/{id}/topics/  → subscribe/unsubscribe from a topic
    """
    serializer_class = DeviceRegistrationSerializer

    def get_queryset(self):
        return PushDevice.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def topics(self, request, pk=None):
        device = self.get_object()
        serializer = TopicSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        topic = serializer.validated_data["topic"]
        action_type = serializer.validated_data["action"]
        if action_type == "subscribe":
            TopicSubscription.objects.get_or_create(topic=topic, device=device)
        else:
            TopicSubscription.objects.filter(topic=topic, device=device).delete()
        return Response({"status": "ok"})


class NotificationDispatchView(generics.CreateAPIView):
    """
    POST /api/push/send/
    Body: { "target_type": "token|topic", "target": "...", "title": "...", "body": "...", "data": {} }
    Requires admin or service-account permission.
    """
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        target_type = request.data.get("target_type")
        target = request.data.get("target")
        title = request.data.get("title", "")
        body = request.data.get("body", "")
        data = request.data.get("data", {})

        if target_type == "topic":
            dispatch_to_topic.delay(target, title, body, data)
        elif target_type == "token":
            try:
                device = PushDevice.objects.get(registration_id=target, active=True)
                dispatch_to_device(device.id, title, body, data)
            except PushDevice.DoesNotExist:
                return Response({"error": "Token not found"}, status=404)
        return Response({"status": "queued"}, status=202)
```

#### 7.6 Web Push — Client-Side Service Worker

```javascript
// public/sw.js  (service worker)
self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {};
  event.waitUntil(
    self.registration.showNotification(data.title || "Notification", {
      body: data.body,
      icon: data.icon || "/icons/icon-192.png",
      data: data,
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/";
  event.waitUntil(clients.openWindow(url));
});
```

```javascript
// client: subscribe and register with Django
async function subscribePush() {
  const reg = await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(PUBLIC_VAPID_KEY),
  });
  // sub.toJSON() gives { endpoint, keys: { p256dh, auth } }
  await fetch("/api/push/devices/", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
    body: JSON.stringify({
      platform: "web",
      registration_id: sub.endpoint,
      p256dh: btoa(String.fromCharCode(...new Uint8Array(sub.getKey("p256dh")))),
      auth: btoa(String.fromCharCode(...new Uint8Array(sub.getKey("auth")))),
    }),
  });
}
```

#### 7.7 VAPID Key Generation (one-time setup)

```bash
pip install py-vapid
vapid --applicationServerKey
# Outputs: private_key.pem, public_key.pem, and an applicationServerKey string for the browser
```

```python
# settings.py (relevant push config)
WEBPUSH_VAPID_PRIVATE_KEY = "/path/to/private_key.pem"
WEBPUSH_ADMIN_EMAIL = "push-admin@example.com"

# APNs (iOS)
APNS_AUTH_KEY_PATH = "/path/to/AuthKey_ABCD1234.p8"
APNS_AUTH_KEY_ID = "ABCD1234"
APNS_TEAM_ID = "YOUR_TEAM_ID"
APNS_BUNDLE_ID = "com.example.yourapp"
APNS_USE_SANDBOX = False  # True for development

# FCM (Android) — via firebase-admin SDK
import firebase_admin
from firebase_admin import credentials
firebase_admin.initialize_app(credentials.Certificate("/path/to/serviceAccountKey.json"))
```

#### 7.8 In-App Messaging — Campaign Engine

The Django rebuild treats FIAM as a polling-based campaign delivery system. The mobile/web app fetches eligible campaigns on app open (or at max once per hour to balance freshness vs. load), evaluates triggers client-side, and reports impressions.

```python
# push/views.py — campaign fetch endpoint
class CampaignFetchView(generics.ListAPIView):
    """
    GET /api/inam/campaigns/?event=app_open&locale=en&app_version=2.1.0
    Returns active campaigns that the client should evaluate for this trigger event.
    The client checks frequency capping using locally stored impression timestamps.
    """
    def list(self, request, *args, **kwargs):
        from django.utils import timezone
        from .models import NotificationCampaign, CampaignImpression

        now = timezone.now()
        trigger_event = request.query_params.get("event", "app_open")

        campaigns = NotificationCampaign.objects.filter(
            status="active",
            trigger_event=trigger_event,
        ).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now)
        ).filter(
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=now)
        )

        # Server-side frequency cap check
        if request.user.is_authenticated:
            impression_counts = CampaignImpression.objects.filter(
                user=request.user,
                campaign__in=campaigns,
                shown_at__gte=now - timezone.timedelta(seconds=86400),
            ).values("campaign_id").annotate(count=models.Count("id"))
            over_cap = {
                row["campaign_id"]
                for row in impression_counts
                # fetch max_impressions from campaign (use subquery in production)
            }
            campaigns = campaigns.exclude(id__in=over_cap)

        # Serialize lightweight payload
        data = [
            {
                "id": str(c.id),
                "message_type": c.message_type,
                "trigger_event": c.trigger_event,
                "title": c.title,
                "body": c.body,
                "image_url": c.image_url,
                "primary_action_url": c.primary_action_url,
                "primary_action_label": c.primary_action_label,
                "cooldown_seconds": c.cooldown_seconds,
                "max_impressions": c.max_impressions_per_user,
            }
            for c in campaigns
        ]
        return Response(data)


class CampaignImpressionView(generics.CreateAPIView):
    """POST /api/inam/impressions/  — record that a campaign was shown or clicked."""
    def create(self, request, *args, **kwargs):
        from .models import CampaignImpression, NotificationCampaign
        campaign = NotificationCampaign.objects.get(id=request.data["campaign_id"])
        CampaignImpression.objects.create(
            campaign=campaign,
            user=request.user,
            clicked=request.data.get("clicked", False),
            dismissed=request.data.get("dismissed", False),
        )
        return Response({"status": "recorded"}, status=201)
```

#### 7.9 Stale Token Cleanup — Periodic Celery Beat Task

```python
# push/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task
def cleanup_stale_tokens():
    """
    Deactivate tokens not seen in 60 days (matches FCM's 60-day stale threshold).
    Run daily via Celery Beat.
    """
    from .models import PushDevice
    cutoff = timezone.now() - timedelta(days=60)
    updated = PushDevice.objects.filter(last_used_at__lt=cutoff, active=True).update(active=False)
    logger.info(f"Deactivated {updated} stale push tokens")
```

```python
# celery_beat settings
CELERY_BEAT_SCHEDULE = {
    "cleanup-stale-push-tokens": {
        "task": "push.tasks.cleanup_stale_tokens",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
}
```

#### 7.10 Required Packages

```
# requirements.txt
django>=4.2
djangorestframework>=3.15
celery[redis]>=5.4
redis>=5.0
firebase-admin>=6.5          # FCM multicast + admin operations
google-auth>=2.29            # OAuth2 tokens for raw FCM HTTP v1
aioapns>=3.2                 # APNs HTTP/2 async client (iOS)
pywebpush>=2.0               # Web Push / VAPID (browsers)
py-vapid>=1.9                # VAPID key generation (one-time, server setup)
django-celery-beat>=2.6      # Periodic tasks (token cleanup, campaign checks)
```

#### 7.11 Infrastructure Stack

| Component | Role | Notes |
|---|---|---|
| PostgreSQL 15+ | Device tokens, topics, campaigns, impressions, logs | Add GIN indexes on `data` JSONField if filtering |
| Redis 7+ | Celery broker + result backend | Use Redis Streams or a separate DB for result backend to avoid broker/result contention |
| Celery 5.x (workers) | Async push dispatch, fan-out chunking, stale token cleanup | Run separate worker pools for FCM/APNs/WebPush queues |
| Celery Beat | Periodic maintenance (cleanup, campaign expiry) | One beat instance only |
| Nginx | Serve SW registration endpoint with correct `Service-Worker-Allowed` header; enforce HTTPS (required for Web Push) | HTTPS is mandatory for Web Push |
| Django Admin | Campaign composer UI (FIAM), notification test sends | Customize for campaign builder UX |

---

### 8. What OSS Alternatives Do

| Project | Push approach |
|---|---|
| **Appwrite** | Microservice architecture; has a Messaging service that wraps FCM/APNs/SMTP into a unified adapter pattern. For mobile push, Appwrite still proxies through FCM/APNs (no self-contained delivery). |
| **Novu** | Open-source notification infrastructure (Node.js/TypeScript). Unified workflow engine with a topic/subscriber model. Supports push via FCM adapter. Architecture: API server + Worker (Bull queue) + WebSocket server + MongoDB/Redis. Good reference for workflow + preference modeling. |
| **PocketBase** | No built-in push notifications. |
| **Supabase** | No built-in push. Community integrations via Edge Functions calling FCM directly. |
| **Parse Platform** | Has `Parse.Push` with APNs + FCM adapters. Expiration + badge handling built into the OSS SDK. Closest to FCM feature parity but aging Node.js codebase. |

**Key insight from OSS alternatives:** None of them self-host the actual delivery channel (APNs/FCM/browser push endpoints). They all call through to the OS vendor's infrastructure. A Django rebuild is in the same position — you cannot bypass APNs for iOS or the browser vendor's push service for web. The only true "zero third-party" push path is long-polling/WebSocket (Django Channels), which only works when the app is open.

---

### 9. Gotchas & Hard Parts

| Problem | Detail | Mitigation |
|---|---|---|
| APNs requires HTTPS/2 with persistent connections | HTTP/1.1 clients will fail. `aioapns` uses asyncio + HTTP/2; do not run it inside a synchronous Django view. | Always dispatch APNs sends to Celery tasks using `asyncio.run()` inside the task. |
| iOS requires APNs; you cannot bypass it | Even with a self-hosted backend, iOS push delivery goes through Apple's servers. Apple requires a paid developer account ($99/year) and a `.p8` key tied to your Team ID. | Accept this dependency; it is a platform constraint, not a Firebase dependency. |
| Web Push requires HTTPS on both server and client origin | HTTP development servers will fail at `pushManager.subscribe()`. | Use a local HTTPS proxy (caddy, mkcert) during development. |
| VAPID keys must be stable | Rotating VAPID private keys invalidates all existing browser subscriptions. All users must re-subscribe. | Generate once, back up securely, never rotate unless you force re-subscribe in the app. |
| FCM multicast deprecated → `send_each_for_multicast` | The old `sendMulticast` was deprecated. Use `firebase_admin.messaging.send_each_for_multicast()` which sends individual requests in parallel internally. Max 500 tokens per call. | See chunk logic in `dispatch.py` above. |
| Topic fan-out latency at scale | For 100k+ subscribers, the Celery group of 200+ tasks adds queue scheduling overhead. | Pre-warm the queue; use Celery priority queues; consider Kafka for very high scale. |
| In-app message fetch timing | FIAM polls once per day; if you push an urgent campaign, users won't see it until their next poll. | Offer a manual refresh API call on `app_resume` events; combine with WebSocket push to invalidate the client cache. |
| Token deduplication | Users may have multiple active tokens per device if they reinstall. | `update_or_create` on `registration_id` prevents duplicates; the `device_id` field helps identify the physical device for deduplication. |
| APNs environment mismatch | Development `.p8` keys can only reach APNs sandbox; production keys go to production endpoint. | `APNS_USE_SANDBOX = DEBUG` is a safe default. |
| Delivery receipts are hard | Unlike email, push has no reliable bounce/delivery callback (FCM BigQuery export is batch + delayed). | Log every send attempt; treat HTTP 410/404 from APNs/WebPush as definitive "unsubscribed". For Android: FCM returns `UNREGISTERED` in the response body synchronously. |

## Analytics, Crashlytics & Performance Monitoring

This cluster maps to three distinct Firebase product surfaces: **Google Analytics for Firebase** (GA4-backed product analytics with BigQuery export), **Firebase Crashlytics** (mobile crash and ANR reporting with server-side symbolication), and **Firebase Performance Monitoring** (automatic and custom traces, network interception, screen rendering metrics). All three funnel into BigQuery for long-term analysis. The Django rebuild requires three independent sub-systems assembled from OSS components.

---

### 1. Google Analytics for Firebase

#### 1.1 What It Does (Developer View)

Firebase Analytics is an event-based product analytics SDK embedded directly in mobile/web apps. It auto-collects lifecycle events and lets developers log custom events:

```kotlin
// Android (Firebase Analytics SDK)
firebaseAnalytics.logEvent("purchase") {
    param("item_id", "sku_123")
    param("value", 29.99)
    param("currency", "USD")
}

// Set user properties (persisted across sessions)
firebaseAnalytics.setUserProperty("subscription_tier", "pro")
```

**Auto-collected events** (no code required): `app_open`, `session_start`, `first_open`, `screen_view`, `os_update`, `app_update`, `app_remove`, `in_app_purchase`, `notification_open`.

**Limits:** Up to 500 distinct event types per app, 25 parameters per event, 36 user properties, parameter values capped at 100 characters. Free tier BigQuery export capped at **1 million events/day**; GA360 removes the cap.

#### 1.2 Under the Hood — Firebase / Google Cloud Architecture

The SDK writes events to a local **SQLite database** (client-side buffer). Every ~1 hour it flushes the batch to Firebase's ingestion endpoints (distinct from the app backend). The pipeline:

```
Mobile SDK (SQLite buffer, 1-hr batch)
    → Firebase Ingestion API (proprietary HTTPS endpoint)
    → Google Cloud Pub/Sub (internal fan-out)
    → Cloud Bigtable (raw hot store for realtime audience evaluation)
    → BigQuery Streaming Inserts (intraday_YYYYMMDD tables, near-realtime)
    → BigQuery daily merge → events_YYYYMMDD (permanent sharded tables)
```

**BigQuery export schema** (GA4/Firebase event row):

| Field | Type | Notes |
|---|---|---|
| `event_date` | STRING | YYYYMMDD partition key |
| `event_timestamp` | INT64 | microseconds since epoch |
| `event_name` | STRING | e.g., `purchase` |
| `event_params` | ARRAY<RECORD> | `{key STRING, value {string_value, int_value, float_value, double_value}}` |
| `user_pseudo_id` | STRING | anonymous installation ID |
| `user_id` | STRING | developer-set authenticated ID |
| `user_properties` | ARRAY<RECORD> | same nested shape as event_params |
| `user_first_touch_timestamp` | INT64 | |
| `device` | RECORD | `{mobile_brand_name, mobile_model_name, mobile_os_hardware_model, operating_system, operating_system_version, language, time_zone_offset_seconds}` |
| `geo` | RECORD | `{continent, country, region, city}` |
| `app_info` | RECORD | `{id, version, install_source, firebase_app_id}` |
| `traffic_source` | RECORD | `{name, medium, source}` |

Intraday tables (`events_intraday_YYYYMMDD`) receive data via BigQuery streaming inserts as events arrive; they are deleted once the daily batch table is written. The nested `event_params` RECORD type exists because BigQuery requires typed columns — this is Firebase's workaround for polymorphic parameter values.

**Audiences** are server-side cohorts evaluated periodically over Bigtable event history. They gate Remote Config personalisation, FCM targeting, and Google Ads remarketing. Funnels are ad-hoc queries over BigQuery in the Analytics console.

#### 1.3 Django Rebuild — Event Ingest + Analytics

**Architecture:**

```
Mobile/Web Client SDK (thin wrapper)
    → Django DRF Ingest API (POST /api/v1/events/batch)
    → Redis Stream (or Kafka topic)
    → Celery Consumer Worker (batch flush)
    → ClickHouse (events table, columnar, compressed)
    → Grafana / Metabase dashboard
```

**Why ClickHouse over Postgres/TimescaleDB:** ClickHouse achieves 2–3 million inserts/second in multi-threaded batching, 10–30× better compression than TimescaleDB for sparse event columns, and sub-second aggregations over billions of rows. TimescaleDB is a sensible fallback if you're already on Postgres and volume is under ~500 M events total.

**pip packages:**
```
clickhouse-connect==0.8.x        # official ClickHouse Python HTTP client
django-clickhouse-backend==1.3.x # Django ORM backend for ClickHouse (DDL migrations)
djangorestframework==3.15.x
celery[redis]==5.4.x
redis==5.x
confluent-kafka==2.x             # if using Kafka instead of Redis Streams
```

**ClickHouse events table DDL:**

```sql
CREATE TABLE events
(
    event_id        UUID            DEFAULT generateUUIDv4(),
    event_date      Date            MATERIALIZED toDate(event_time),
    event_time      DateTime64(6, 'UTC'),
    event_name      LowCardinality(String),
    app_id          LowCardinality(String),
    user_pseudo_id  String,
    user_id         Nullable(String),
    session_id      String,
    -- Typed flat columns for common params (avoids nested for hot paths)
    param_value_str  Nullable(String),
    param_key       Nullable(String),
    -- Full parameter bag as JSON for arbitrary params
    properties      String,          -- JSON blob
    user_properties String,          -- JSON blob
    device_os       LowCardinality(String),
    device_model    LowCardinality(String),
    country         LowCardinality(String),
    app_version     LowCardinality(String),
    insert_time     DateTime         DEFAULT now()
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/events', '{replica}')
PARTITION BY toYYYYMM(event_date)
ORDER BY (app_id, event_name, event_date, user_pseudo_id)
TTL event_date + INTERVAL 24 MONTH;
```

> **Note:** Unlike Firebase's BigQuery nested RECORD, ClickHouse stores the parameter bag as a JSON string column for flexibility, with frequently queried params hoisted to typed columns. For high-cardinality param sets, use ClickHouse's `Map(String, String)` type (available since 22.x) instead.

**Django DRF Ingest View:**

```python
# analytics/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .tasks import ingest_events_batch
import uuid, time

class EventBatchView(APIView):
    authentication_classes = []  # SDK posts with API key header
    permission_classes = []

    def post(self, request):
        api_key = request.headers.get("X-API-Key")
        if not validate_api_key(api_key):  # check against Postgres
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        events = request.data.get("events", [])
        if not events or len(events) > 1000:
            return Response({"error": "1-1000 events per batch"}, status=400)

        debug_mode = request.headers.get("X-Debug-Mode") == "true"
        app_id = resolve_app_id(api_key)

        # Enrich with server-side fields
        enriched = []
        for ev in events:
            enriched.append({
                "event_id": str(uuid.uuid4()),
                "event_time": ev.get("timestamp", time.time_ns() // 1000),
                "event_name": ev["name"][:40],
                "app_id": app_id,
                "user_pseudo_id": ev.get("user_pseudo_id", ""),
                "user_id": ev.get("user_id"),
                "session_id": ev.get("session_id", ""),
                "properties": ev.get("params", {}),
                "user_properties": ev.get("user_properties", {}),
                "device_os": ev.get("device", {}).get("os", ""),
                "device_model": ev.get("device", {}).get("model", ""),
                "country": ev.get("geo", {}).get("country", ""),
                "app_version": ev.get("app_version", ""),
            })

        if debug_mode:
            # Synchronous write for DebugView — skip queue
            flush_to_clickhouse(enriched)
            broadcast_debug_events(enriched)  # Django Channels
        else:
            ingest_events_batch.delay(enriched)

        return Response({"received": len(enriched)}, status=202)
```

**Celery consumer task (batch write):**

```python
# analytics/tasks.py
from celery import shared_task
import clickhouse_connect

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def ingest_events_batch(self, events: list[dict]):
    client = clickhouse_connect.get_client(
        host="clickhouse", port=8123, database="analytics"
    )
    try:
        client.insert(
            "events",
            [list(ev.values()) for ev in events],
            column_names=list(events[0].keys()),
            settings={"async_insert": 1, "wait_for_async_insert": 0},
        )
    except Exception as exc:
        raise self.retry(exc=exc)
```

> **Gotcha:** ClickHouse performs best with **batch inserts of 1,000–100,000 rows**. Never insert row-by-row from Django views. Use ClickHouse's `async_insert` (server-side buffering) or accumulate in Redis and flush on a 10-second Celery beat.

**Audiences / Funnels in ClickHouse:**

```sql
-- Funnel: users who hit sign_up then purchase within 7 days
SELECT countIf(step = 2) / countIf(step >= 1) AS conversion
FROM (
    SELECT
        user_pseudo_id,
        windowFunnel(7 * 86400)(
            event_time,
            event_name = 'sign_up',
            event_name = 'purchase'
        ) AS step
    FROM events
    WHERE app_id = 'my_app' AND event_date >= today() - 30
    GROUP BY user_pseudo_id
);
```

**Best OSS alternative — PostHog (self-hosted):** PostHog runs Django + ClickHouse + Kafka + Postgres + Redis under the hood and ships funnels, retention, session recordings, feature flags, and A/B testing out of the box. Its hobby Docker Compose stack uses ~2.1 GB RAM idle. Use PostHog when you want Firebase Analytics feature parity without building the query layer yourself.

```bash
git clone https://github.com/PostHog/posthog.git
docker compose -f docker-compose.hobby.yml up -d
```

---

### 2. Firebase Crashlytics

#### 2.1 What It Does (Developer View)

Crashlytics captures unhandled exceptions, native crashes (NDK/JNI), ANRs (Application Not Responding on Android), and logged non-fatal exceptions. It groups crashes into **issues** by stack trace fingerprint and tracks crash-free user/session rates over time.

```kotlin
// Android — custom key/value context
FirebaseCrashlytics.getInstance().apply {
    setCustomKey("user_tier", "premium")
    log("User tapped checkout")
}

// Log non-fatal error (no crash — uploaded next session)
FirebaseCrashlytics.getInstance().recordException(exception)
```

```swift
// iOS
Crashlytics.crashlytics().setCustomValue("premium", forKey: "user_tier")
Crashlytics.crashlytics().log("User tapped checkout")
Crashlytics.crashlytics().record(error: error)  // non-fatal
```

#### 2.2 Under the Hood

**Collection flow:**
1. SDK registers JVM `Thread.UncaughtExceptionHandler` (Android) / `NSSetUncaughtExceptionHandler` + signal handlers (iOS/macOS).
2. On crash: captures stack frames + thread states + device metadata + custom keys/logs/breadcrumbs. Writes serialised protobuf to disk (survives process death).
3. On **next app launch**: SDK reads the crash file and POSTs to Firebase's Crashlytics ingestion endpoint over HTTPS.
4. For NDK crashes: Crashlytics uses Breakpad (Google's open-source minidump writer). It also captures Android tombstone files (as of 2025) for richer native context — both minidump and tombstone are shown side-by-side in the console.
5. **Server-side symbolication**: Firebase runs a symbolication service. Developers upload dSYM (iOS), ProGuard mapping.txt (Android), and ELF symbol files via `firebase crashlytics:symbols:upload` CLI command or the Gradle `uploadCrashlyticsSymbolFile` task. The service resolves obfuscated/offset frames back to source file + line.
6. **Issue grouping**: events are fingerprinted by normalised stack trace hash. The console shows crash count, impacted users, first/last seen, affected OS versions, and velocity alerts.
7. **ANR detection** (Android 11+): SDK hooks into the `ApplicationExitInfo` API to detect ANR exits and reports them as a separate event type.

**BigQuery export schema** (`firebase_crashlytics` dataset, table per app):

| Column | Type | Description |
|---|---|---|
| `platform` | STRING | `ANDROID` / `IOS` |
| `bundle_identifier` | STRING | package name |
| `version` | STRING | app version string |
| `error_type` | STRING | `CRASH`, `NON_FATAL`, `ANR` |
| `issue_id` | STRING | fingerprint-based issue group |
| `issue_title` | STRING | top exception class |
| `issue_subtitle` | STRING | top exception message |
| `exception.type` | STRING | exception class |
| `exception.object` | STRING | |
| `exception.frames` | ARRAY<RECORD> | `{file, line, symbol, library, blame}` |
| `breadcrumbs` | ARRAY<RECORD> | `{timestamp, name, params}` |
| `custom_keys` | ARRAY<RECORD> | developer-set key-value pairs |
| `device_model` | STRING | |
| `os_version` | STRING | |
| `sessions.session_id` | STRING | |

Realtime export available with a `_REALTIME` suffix table fed by BigQuery streaming inserts.

#### 2.3 Django Rebuild — Crash Reporting

**Recommendation: GlitchTip for simple setups, self-hosted Sentry for full fidelity.**

| | GlitchTip | Self-hosted Sentry |
|---|---|---|
| Stack | Django + Postgres + Celery + Redis (4 containers) | ~20 containers (Kafka, ClickHouse, Zookeeper, Symbolicator, Relay, Snuba…) |
| RAM (idle) | ~512 MB | ~8 GB minimum |
| Symbolication | Basic (dSYM / ProGuard via sentry-cli) | Full Symbolicator service (minidump, Apple crash reports, source maps) |
| ANR support | Via Sentry SDK ANR detection | Full (Sentry's Android SDK reports ANRs natively) |
| SDK compat | Full Sentry SDK wire protocol | Full Sentry SDK wire protocol |
| Release (2026) | GlitchTip 6 (Feb 2026): improved stacktraces | Sentry 25.x |

**GlitchTip Docker Compose (minimal):**

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: glitchtip
      POSTGRES_USER: glitchtip
      POSTGRES_PASSWORD: secret
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  web:
    image: glitchtip/glitchtip:latest
    env_file: .env
    depends_on: [postgres, redis]
    ports:
      - "8080:8080"

  worker:
    image: glitchtip/glitchtip:latest
    command: celery -A glitchtip worker -c 4
    env_file: .env
    depends_on: [postgres, redis]

  beat:
    image: glitchtip/glitchtip:latest
    command: celery -A glitchtip beat
    env_file: .env

volumes:
  pg_data:
```

`.env` keys: `SECRET_KEY`, `DATABASE_URL=postgres://glitchtip:secret@postgres/glitchtip`, `REDIS_URL=redis://redis:6379/0`, `GLITCHTIP_DOMAIN=https://errors.yourdomain.com`

**Mobile SDK integration (zero code change from Firebase):**

```kotlin
// Android — sentry-java, point at your GlitchTip or Sentry instance
Sentry.init { options ->
    options.dsn = "https://PUBLIC_KEY@errors.yourdomain.com/PROJECT_ID"
    options.tracesSampleRate = 1.0
    options.isAnrEnabled = true           // ANR detection
    options.isAttachScreenshot = true
}
```

```swift
// iOS — sentry-cocoa
SentrySDK.start { options in
    options.dsn = "https://PUBLIC_KEY@errors.yourdomain.com/PROJECT_ID"
    options.tracesSampleRate = 1.0
}
```

```dart
// Flutter — sentry-dart
await SentryFlutter.init(
  (options) { options.dsn = 'https://KEY@errors.yourdomain.com/ID'; },
  appRunner: () => runApp(MyApp()),
);
```

**Server-side symbolication pipeline:**

```bash
# Upload iOS dSYM after each release build (CI step)
sentry-cli --url https://errors.yourdomain.com upload-dif \
  --org my-org --project my-ios-app \
  path/to/dSYMs/

# Upload Android ProGuard mapping
sentry-cli --url https://errors.yourdomain.com difutil upload \
  --org my-org --project my-android-app \
  app/build/outputs/mapping/release/mapping.txt
```

Sentry's **Symbolicator** (open-source Rust service: `getsentry/symbolicator`) resolves addresses using the three-step pipeline: fetch debug info → build SymCache → symbolicate frames. It supports Breakpad minidumps, Apple crash reports, and ELF/DWARF symbols.

**Gotcha — NDK / native crashes:** GlitchTip's symbolication for NDK is limited. For apps with heavy C++ code, deploy full self-hosted Sentry which ships Symbolicator as a sidecar. Alternatively, process Breakpad minidumps offline with the Sentry CLI and re-attach symbolicated traces before ingestion.

**Django backend integration (server errors → same GlitchTip instance):**

```python
# settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn="https://KEY@errors.yourdomain.com/PROJECT_ID",
    integrations=[DjangoIntegration(), CeleryIntegration()],
    traces_sample_rate=0.2,
    send_default_pii=False,
)
```

---

### 3. Firebase Performance Monitoring

#### 3.1 What It Does (Developer View)

Performance Monitoring instruments apps to measure: app startup time, screen rendering (slow/frozen frames), HTTP/S network requests, and custom code traces with custom metrics.

```kotlin
// Android — custom trace
val trace = Firebase.performance.newTrace("image_processing")
trace.start()
trace.putAttribute("filter_type", "sepia")
// ... do work ...
trace.putMetric("images_processed", count.toLong())
trace.stop()

// Custom network trace (for non-intercepted libraries)
val metric = Firebase.performance.newHttpMetric(url, FirebasePerformance.HttpMethod.GET)
metric.start()
// ... make request ...
metric.httpResponseCode = 200
metric.requestPayloadSize = 1024
metric.stop()
```

#### 3.2 Under the Hood

**Automatic instrumentation mechanism:**
- **Android:** Gradle transform plugin (`com.google.firebase.firebase-perf` Gradle plugin) performs **bytecode weaving** at compile time. It injects hooks into `OkHttp` interceptor chains, `HttpURLConnection`, `Activity` lifecycle callbacks, and `Fragment` transactions. No app code changes needed for automatic traces.
- **iOS:** Method swizzling on `NSURLSession` and `UIViewController` lifecycle. SDK registers for `UIApplicationDidBecomeActiveNotification` to measure cold/warm start.
- **Automatic trace types:** `_app_start` (pre-main → first frame), `_app_in_foreground`, `_app_in_background`, `_screen_rendering_{ActivityName}` (tracks slow >16 ms and frozen >700 ms frames per screen).
- **Upload cadence:** Traces batched and uploaded every ~30 seconds (not the 1-hour Analytics cadence).
- **BigQuery export:** Separate dataset from Analytics. Table schema per app with fields: `trace_type` (`DURATION_TRACE`, `NETWORK_TRACE`, `SCREEN_TRACE`), `trace_name`, `start_time`, `duration_us`, `country`, `app_version`, `os_version`, `custom_attributes` (REPEATED RECORD), and for network traces: `url_pattern`, `http_method`, `http_response_code`, `request_payload_bytes`, `response_payload_bytes`.

#### 3.3 Django Rebuild — Performance Monitoring Stack

**Recommended stack: OpenTelemetry → OTLP Collector → Grafana Tempo (traces) + Prometheus (metrics) + Loki (logs) + Grafana (dashboards).**

For a unified all-in-one alternative: **SigNoz** (ClickHouse-backed, ships Tempo + Prometheus + Loki equivalents in one deployment).

**pip packages for Django backend instrumentation:**

```
opentelemetry-api==1.27.x
opentelemetry-sdk==1.27.x
opentelemetry-instrumentation-django==0.48bx
opentelemetry-instrumentation-psycopg2==0.48bx      # Postgres spans
opentelemetry-instrumentation-redis==0.48bx
opentelemetry-instrumentation-celery==0.48bx
opentelemetry-instrumentation-requests==0.48bx       # outbound HTTP
opentelemetry-exporter-otlp-proto-grpc==1.27.x       # export to Collector
prometheus-client==0.21.x                            # custom metrics
django-prometheus==2.3.x                             # /metrics endpoint
```

**Zero-code Django instrumentation setup:**

```python
# manage.py or wsgi.py — before Django loads
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317"))
)
trace.set_tracer_provider(provider)

DjangoInstrumentor().instrument()
Psycopg2Instrumentor().instrument()
CeleryInstrumentor().instrument()
RedisInstrumentor().instrument()
```

**Custom traces (Firebase Performance parity):**

```python
# mirrors Firebase's newTrace() / startTrace() / stopTrace() API
from opentelemetry import trace
import time

tracer = trace.get_tracer("my_app")

def process_image(image_id: str, filter_type: str) -> dict:
    with tracer.start_as_current_span("image_processing") as span:
        span.set_attribute("filter_type", filter_type)
        span.set_attribute("image_id", image_id)
        start = time.perf_counter()

        result = _do_processing(image_id, filter_type)

        duration_ms = (time.perf_counter() - start) * 1000
        span.set_attribute("duration_ms", duration_ms)
        span.set_attribute("images_processed", result["count"])
        return result
```

**Custom metrics (Prometheus):**

```python
from prometheus_client import Histogram, Counter

IMAGE_PROCESSING_DURATION = Histogram(
    "image_processing_duration_seconds",
    "Time spent processing images",
    ["filter_type"],
)
IMAGES_PROCESSED_TOTAL = Counter(
    "images_processed_total",
    "Total images processed",
    ["filter_type"],
)

# In your view / service:
with IMAGE_PROCESSING_DURATION.labels(filter_type="sepia").time():
    result = process_image(image_id, "sepia")
IMAGES_PROCESSED_TOTAL.labels(filter_type="sepia").inc(result["count"])
```

**Grafana OSS stack Docker Compose:**

```yaml
version: "3.8"
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.110.0
    volumes:
      - ./otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP

  tempo:
    image: grafana/tempo:2.6.0
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml
      - tempo_data:/var/tempo

  prometheus:
    image: prom/prometheus:v2.54.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  loki:
    image: grafana/loki:3.2.0

  grafana:
    image: grafana/grafana:11.2.0
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true

volumes:
  tempo_data:
```

`otel-collector-config.yaml` snippet:
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true
  prometheusremotewrite:
    endpoint: http://prometheus:9090/api/v1/write

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp]
      exporters: [prometheusremotewrite]
```

**For mobile app performance (screen rendering / app start / network traces):**

Use the **Sentry mobile SDKs** (sentry-java, sentry-cocoa, sentry-dart) pointing at your GlitchTip or self-hosted Sentry instance. Sentry's performance SDK captures:
- App start transactions (cold/warm start, equivalent to `_app_start`)
- Screen load transactions per Activity/ViewController
- OkHttp/URLSession network spans (equivalent to Firebase's auto HTTP traces)
- Custom spans within transactions

This consolidates crash reporting + performance monitoring in a single self-hosted service, matching Firebase's integration between Crashlytics and Performance Monitoring.

---

### 4. Firebase DebugView

#### 4.1 What It Does

DebugView is a real-time event stream for development devices. When enabled, the SDK bypasses the 1-hour batching and uploads events with sub-second delay. The Firebase console shows:

- **Seconds column:** events in the last 60 seconds
- **Minutes column:** events over the last 30 minutes  
- **Right panel:** top event names + current user properties for the selected device

Enable on Android:
```bash
adb shell setprop debug.firebase.analytics.app com.example.myapp
```
Disable:
```bash
adb shell setprop debug.firebase.analytics.app .none.
```
Enable on iOS: launch arg `-FIRAnalyticsDebugEnabled`

#### 4.2 Django Rebuild — DebugView Equivalent

DebugView is a **real-time WebSocket stream** of events from a specific installation. The Django equivalent uses Django Channels.

**How it works:**
1. Mobile SDK sends header `X-Debug-Mode: true` in the ingest request.
2. Django view detects debug mode → skips Kafka/Celery → writes synchronously to ClickHouse's `debug_events` table AND publishes to a Redis channel keyed by `installation_id`.
3. A Django Channels WebSocket consumer subscribes to that Redis channel and streams events to the browser dashboard.

```python
# analytics/consumers.py (Django Channels)
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json

class DebugViewConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.installation_id = self.scope["url_route"]["kwargs"]["installation_id"]
        self.group_name = f"debug_{self.installation_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def debug_event(self, event):
        await self.send(text_data=json.dumps(event["data"]))
```

```python
# In the ingest view, for debug mode events:
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_debug_events(events: list[dict]):
    channel_layer = get_channel_layer()
    for ev in events:
        async_to_sync(channel_layer.group_send)(
            f"debug_{ev['user_pseudo_id']}",
            {"type": "debug.event", "data": ev},
        )
```

**pip packages:**
```
channels==4.x
channels-redis==4.x
daphne==4.x          # ASGI server
```

---

### 5. Gotchas & Hard Parts

| Problem | Firebase's solution | Self-hosted approach |
|---|---|---|
| **Event deduplication** | Firebase deduplicates on install ID + event timestamp server-side | Use ClickHouse `ReplacingMergeTree` keyed on `(event_id)` or implement idempotent Kafka consumer with Redis dedup set |
| **ClickHouse small insert problem** | N/A (Google's pipeline handles batching) | Never insert row-by-row. Use `async_insert=1` or accumulate 1k-100k rows in Celery beat |
| **Symbol file storage** | Firebase/Google Cloud hosts symbol files indefinitely | S3/MinIO + path by `app_version + build_uuid`; reference in Symbolicator config. Sentry self-hosted uses MinIO by default |
| **NDK / native crash symbolication** | Firebase 2025: Breakpad minidump + Android tombstone, both symbolicated | GlitchTip has limited native support. Full self-hosted Sentry + Symbolicator handles Breakpad minidumps. Requires serving symbol files via HTTP to Symbolicator |
| **Audience computation at scale** | Google Bigtable + server-side scheduled jobs | Celery beat task running ClickHouse queries → audience membership stored in Postgres, cached in Redis. PostHog handles this automatically |
| **DebugView device isolation** | Firebase identifies device by `app_instance_id`; console filtered per device | Use `installation_id` as Channels group key; rotate on app reinstall |
| **Performance Monitoring on mobile** | Bytecode weaving at compile time (Gradle plugin) | Sentry mobile SDK auto-instrumentation (no bytecode weaving; uses OkHttp interceptor + Activity callbacks); slightly less transparent but ships as a standard SDK dependency |
| **BigQuery-scale export** | Managed streaming insert service | ClickHouse native replication + S3-backed MergeTree for cold storage; `clickhouse-backup` for snapshots |
| **Scaling Kafka for ingestion** | Managed Pub/Sub (Google) | WarpStream (Kafka-compatible, S3-backed, no ZooKeeper) or Redpanda as lightweight Kafka drop-in for <10M events/day |

---

### 6. Reference Implementation — Minimal Docker Compose

A production-ready self-hosted bootstrap covering all three Firebase clusters in this section:

```yaml
# docker-compose.yml (condensed — expand volumes/env for prod)
services:
  # --- Analytics ingest ---
  django:
    build: .
    command: gunicorn myapp.asgi:application -k uvicorn.workers.UvicornWorker
    env_file: .env
    depends_on: [postgres, redis, clickhouse]

  celery-worker:
    build: .
    command: celery -A myapp worker -Q analytics -c 8
    env_file: .env

  clickhouse:
    image: clickhouse/clickhouse-server:24.x
    volumes:
      - ch_data:/var/lib/clickhouse
      - ./clickhouse-config.xml:/etc/clickhouse-server/config.d/custom.xml

  # --- Crash reporting ---
  glitchtip:
    image: glitchtip/glitchtip:latest
    env_file: glitchtip.env
    depends_on: [postgres, redis]
    ports: ["8081:8080"]

  glitchtip-worker:
    image: glitchtip/glitchtip:latest
    command: celery -A glitchtip worker -c 2
    env_file: glitchtip.env

  # --- Performance monitoring ---
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.110.0
    volumes: [./otel-config.yaml:/etc/otelcol-contrib/config.yaml]

  tempo:
    image: grafana/tempo:2.6.0

  prometheus:
    image: prom/prometheus:v2.54.0

  grafana:
    image: grafana/grafana:11.2.0
    ports: ["3000:3000"]

  # --- Shared infra ---
  postgres:
    image: postgres:16
    volumes: [pg_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

volumes:
  ch_data:
  pg_data:
```

**Approximate resource footprint (single server):**

| Component | RAM idle |
|---|---|
| Django + Celery | ~400 MB |
| ClickHouse | ~1 GB (configurable) |
| GlitchTip (web + worker) | ~512 MB |
| Tempo + Prometheus + Grafana | ~600 MB |
| Postgres + Redis | ~300 MB |
| **Total** | **~2.8 GB** |

A $40/month VPS (8 GB RAM, 4 vCPU) runs the full stack comfortably for up to ~50 M events/month. Upgrade ClickHouse to a dedicated node when crossing ~500 M events/month.

## Remote Config, A/B Testing, Dynamic Links & Predictions

> **Deprecation alerts in this cluster:** Firebase Dynamic Links shut down permanently on 25 August 2025 (all links return 404). Firebase Predictions (legacy) is effectively deprecated — the capability is absorbed into GA4 Predictive Audiences. Everything else in this cluster is current as of June 2026.

---

### 4.1 Firebase Remote Config

#### What it does (developer-facing)

Remote Config is a cloud key-value store that lets you change app behavior and appearance server-side without publishing an app update. Each client fetches a fully resolved JSON template — all conditions have already been evaluated server-side — and the SDK caches it locally with a default 12-hour minimum fetch interval. A separate real-time invalidation channel (persistent WebSocket) signals clients to re-fetch as soon as a new template is published.

```swift
// iOS SDK — typical fetch-activate-get pattern
let remoteConfig = RemoteConfig.remoteConfig()
try await remoteConfig.fetchAndActivate()
let buttonColor = remoteConfig["button_color"].stringValue  // "blue"

// Real-time listener (iOS)
remoteConfig.addOnConfigUpdateListener { update, error in
    Task { try await remoteConfig.activate() }
}
```

```js
// Web SDK
import { getRemoteConfig, fetchAndActivate, getValue } from "firebase/remote-config";
const rc = getRemoteConfig(app);
rc.settings.minimumFetchIntervalMillis = 3600_000; // 1 hour
await fetchAndActivate(rc);
const showNewUI = getValue(rc, "show_new_checkout").asBoolean();
```

Server-side (Admin SDK) is different: the server downloads the **raw, unevaluated template** and calls `template.evaluate(signals)` per incoming request with sub-millisecond latency.

```js
// Node.js Admin SDK — server-side evaluation
const template = await rc.getServerTemplate();
const config = template.evaluate({ user_tier: "premium", region: "EU" });
const modelName = config.getString("llm_model");
```

#### How Firebase implements it under the hood

| Layer | Detail |
|-------|--------|
| Storage | Config templates stored in Spanner (globally replicated) as versioned JSON blobs. Up to 300 lifetime versions per project per template type (client vs. server). |
| Fetch endpoint | `https://firebaseremoteconfig.googleapis.com/v1/projects/{id}/remoteConfig` (REST) or Firebase SDK wraps it. Request carries app metadata; server evaluates all conditions and returns a resolved `{entries: {key: value}}` JSON. |
| Caching | Client caches resolved template with ETag. Subsequent fetches send `If-None-Match`; server returns 304 if unchanged. Throttle: max 5 fetches/hour per device in production; unlimited in debug mode (but emulator recommended). |
| Real-time | Server-Sent Events / WebSocket persistent connection to a separate streaming endpoint. On publish, server sends `{"latestTemplateVersionNumber": N}` invalidation; client auto-fetches bypassing the fetch cache. |
| Condition evaluation | Ordered list of conditions evaluated top-to-bottom per fetch request; first TRUE condition wins. Server has access to: install ID, app metadata, Analytics user properties (via GA4 lookaside), and client-supplied custom signals. |
| Limits | 3 000 parameters per template type, 24 running experiments + rollouts at once, 300 total experiment history. |
| Pricing | Free, unlimited daily active users. |

**Condition types (full list from `condition-reference` docs):**

| Element | Operators | Notes |
|---------|-----------|-------|
| `app.version` | `==`, `!=`, `contains`, `notContains`, `<`, `<=`, `>`, `>=`, `matches` (RE2) | Semver string comparison |
| `app.build` | same as version | iOS/Android build number |
| `app.audiences` | `inAtLeastOne`, `notInAtLeastOne`, `inAll`, `notInAll` | GA4 audience membership (24–48 h latency for new users) |
| `app.userProperty` | `==`, `!=`, `contains`, `matches` | Analytics user properties |
| `app.firstOpenTimestamp` | `<=`, `>` | Cohort targeting by first-open date |
| `app.firebaseInstallationId` | `in [...]` | Allowlist specific device installs (QA / dogfood) |
| `app.customSignal` | `<`, `<=`, `==`, `!=`, `>=`, `>`, `contains` | Client-supplied key-value, evaluated server-side |
| `app.operatingSystemAndVersion` | `inOne` | Web/server targets |
| `app.browserAndVersion` | `inOne` | Web targets |
| `device.os` | `==` | iOS vs Android |
| `device.language` | `==`, `inOne` | BCP-47 locale |
| `device.country` | `==`, `inOne` | ISO 3166 country |
| `percent` | `<=`, `>`, `between` | Random fractional percentage; supports named `seed` for independent bucketing |

The `percent` operator is the backbone of gradual rollouts. A named seed — e.g., `percent('checkout_v2') <= 15` — means "15% of users bucketed independently from all other percentage conditions that use a different seed". Bucket assignment: `HMAC-SHA256(seed_name + firebase_installation_id) % 10^7` mapped to 0–100.

---

#### Django Rebuild — Remote Config Service

**Architecture overview:**

```
┌──────────────────────────────────────────────────────────────────┐
│  Admin UI (Django Admin / custom React console)                  │
│  └─ creates Parameters, Conditions, Templates                    │
├──────────────────────────────────────────────────────────────────┤
│  Config API (DRF)                                                │
│  GET /config/fetch  ─ evaluates conditions, returns resolved JSON│
│  WebSocket /config/stream  ─ invalidation push (Channels)        │
├──────────────────────────────────────────────────────────────────┤
│  PostgreSQL   Redis (resolved template cache, pub/sub)           │
└──────────────────────────────────────────────────────────────────┘
```

**Data model:**

```python
# models.py
import hashlib, hmac
from django.db import models

class ConfigTemplate(models.Model):
    """Versioned config template — client or server type."""
    name = models.CharField(max_length=255)
    template_type = models.CharField(max_length=10, choices=[("client","client"),("server","server")])
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)

class Parameter(models.Model):
    template = models.ForeignKey(ConfigTemplate, on_delete=models.CASCADE, related_name="parameters")
    key = models.CharField(max_length=256)
    default_value = models.TextField()
    description = models.TextField(blank=True)
    value_type = models.CharField(max_length=10, default="string",
        choices=[("string","string"),("boolean","boolean"),("number","number"),("json","json")])

class Condition(models.Model):
    """Ordered condition — first TRUE wins."""
    template = models.ForeignKey(ConfigTemplate, on_delete=models.CASCADE, related_name="conditions")
    name = models.CharField(max_length=100)
    expression = models.JSONField()  # structured DSL, see below
    priority = models.PositiveIntegerField(default=0)  # lower = evaluated first
    tag_color = models.CharField(max_length=20, blank=True)

class ConditionalValue(models.Model):
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name="conditional_values")
    condition = models.ForeignKey(Condition, on_delete=models.CASCADE)
    value = models.TextField()
```

**Condition evaluator (the core logic):**

```python
# evaluator.py
import hashlib, hmac, re
from typing import Any

HMAC_SECRET = b"your-stable-secret-per-project"

def percent_bucket(seed: str, installation_id: str) -> float:
    """Return a stable 0-100 float for this (seed, installation_id) pair."""
    key = f"{seed}:{installation_id}".encode()
    digest = hmac.new(HMAC_SECRET, key, hashlib.sha256).hexdigest()
    return (int(digest[:8], 16) % 10_000_000) / 100_000.0  # 0.0 – 99.99999

def evaluate_rule(expr: dict, signals: dict) -> bool:
    """Evaluate a single atomic rule expression."""
    t = expr["type"]
    if t == "app_version":
        return _version_op(signals.get("app_version",""), expr["operator"], expr["value"])
    elif t == "language":
        return signals.get("language","") in expr["values"]
    elif t == "country":
        return signals.get("country","") in expr["values"]
    elif t == "device_os":
        return signals.get("os","") == expr["value"]
    elif t == "user_property":
        return signals.get("user_properties",{}).get(expr["key"],"") == expr["value"]
    elif t == "installation_id_allowlist":
        return signals.get("installation_id","") in expr["ids"]
    elif t == "custom_signal":
        actual = signals.get("custom_signals",{}).get(expr["key"])
        return _compare(actual, expr["operator"], expr["value"])
    elif t == "random_percent":
        seed = expr.get("seed", "__default__")
        bucket = percent_bucket(seed, signals.get("installation_id",""))
        lo, hi = expr.get("lo", 0), expr["hi"]
        return lo <= bucket < hi
    elif t == "segment":
        return expr["segment_id"] in signals.get("segment_ids", [])
    return False

def evaluate_condition(condition_expr: list, signals: dict) -> bool:
    """All rules in a condition must be TRUE (logical AND)."""
    return all(evaluate_rule(r, signals) for r in condition_expr)

def resolve_template(template, signals: dict) -> dict:
    """Resolve all parameters given client signals."""
    conditions = list(template.conditions.order_by("priority").prefetch_related())
    true_conditions = {c.id for c in conditions if evaluate_condition(c.expression, signals)}

    result = {}
    for param in template.parameters.prefetch_related("conditional_values__condition"):
        value = param.default_value
        for cv in sorted(param.conditional_values.all(), key=lambda x: x.condition.priority):
            if cv.condition_id in true_conditions:
                value = cv.value
                break
        result[param.key] = _cast(value, param.value_type)
    return result
```

**Fetch API endpoint:**

```python
# views.py
from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ConfigTemplate
from .evaluator import resolve_template
import hashlib, json

@api_view(["GET", "POST"])
def fetch_config(request):
    signals = request.data if request.method == "POST" else {}
    signals.update({
        "app_version": request.headers.get("X-App-Version", ""),
        "language": request.headers.get("Accept-Language", "en")[:5],
        "country": request.headers.get("CF-IPCountry", ""),  # Cloudflare header
        "os": request.headers.get("X-Platform", ""),
        "installation_id": request.headers.get("X-Installation-Id", ""),
    })
    template_type = request.headers.get("X-Template-Type", "client")
    template = ConfigTemplate.objects.filter(is_active=True, template_type=template_type).first()
    if not template:
        return Response({})

    # Cache resolved config per (template_version, signals_hash)
    sig_hash = hashlib.md5(json.dumps(signals, sort_keys=True).encode()).hexdigest()
    cache_key = f"config:{template.version}:{sig_hash}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached, headers={"ETag": f'"{template.version}"'})

    resolved = resolve_template(template, signals)
    cache.set(cache_key, resolved, timeout=300)  # 5-min cache for hot paths
    return Response(resolved, headers={"ETag": f'"{template.version}"'})
```

**Real-time invalidation via Django Channels:**

```python
# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ConfigConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        template_type = self.scope["url_route"]["kwargs"].get("type", "client")
        self.group_name = f"config_{template_type}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def config_updated(self, event):
        await self.send(text_data=json.dumps({
            "type": "config_updated",
            "version": event["version"]
        }))

# signals.py — fire on template save
from django.db.models.signals import post_save
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def on_template_save(sender, instance, **kwargs):
    if instance.is_active:
        layer = get_channel_layer()
        async_to_sync(layer.group_send)(
            f"config_{instance.template_type}",
            {"type": "config.updated", "version": instance.version}
        )
```

**OSS alternative: Flagsmith**

For teams that want to avoid building this from scratch, Flagsmith is the closest match — it is literally a Python/Django + PostgreSQL service:

```bash
# Self-host Flagsmith (Django-based, BSD-3 license)
git clone https://github.com/Flagsmith/flagsmith
cd flagsmith
docker-compose up -d   # flagsmith-api (Django, ~512 MB RAM) + PostgreSQL

# Python client
pip install flagsmith
from flagsmith import Flagsmith
client = Flagsmith(environment_key="your-key", api_url="https://your-host/api/v1/")
flags = client.get_environment_flags()
show_feature = flags.is_feature_enabled("new_checkout")
button_color = flags.get_feature_value("button_color")  # "blue"
```

Flagsmith supports boolean flags, remote config values, identity traits (≈ user properties), percentage rollout splits, and multi-variate flags. It ships an Edge Proxy (Go) for local flag evaluation without a round-trip to the API server.

**Gotchas when self-hosting:**

| Gotcha | Solution |
|--------|----------|
| Cache invalidation consistency across multiple Django instances | Use Redis pub/sub; broadcast invalidation to all instances via Channels layer |
| Percent-bucket drift if secret key changes | Treat `HMAC_SECRET` as an immutable project-level constant; never rotate it |
| GA4 Audience latency (24–48 h) | For time-sensitive targeting, avoid audience conditions; use user_property or custom_signal instead |
| 3 000-param limit per template | Non-issue self-hosted; partition by app/environment if needed |
| Client SDK caching means deployed config takes time to propagate | Combine real-time invalidation + client-side `fetchAndActivate()` on WebSocket nudge |

---

### 4.2 Remote Config Rollouts (Gradual Feature Release)

#### What it does

A Rollout is a named Remote Config condition with a `percent` rule that expands incrementally. Firebase creates an equal-sized **control group** (same size as the enabled group, up to max 50% enabled) so you can compare Crashlytics crash rates and GA4 conversion side-by-side. Group assignment is **sticky** — expanding from 10% to 20% keeps the original 10% in place and adds a fresh 10% to the enabled group.

#### Django Rebuild

```python
# models.py (addition)
class Rollout(models.Model):
    STATUS = [("draft","draft"),("running","running"),("paused","paused"),("complete","complete")]
    name = models.CharField(max_length=255)
    seed_key = models.CharField(max_length=100, unique=True)  # HMAC seed
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    enabled_value = models.TextField()
    control_value = models.TextField()   # usually the same as param default
    enabled_pct = models.FloatField(default=0.0)   # 0–50
    control_pct = models.FloatField(default=0.0)   # auto = same as enabled_pct
    status = models.CharField(max_length=20, choices=STATUS, default="draft")

    def evaluate(self, installation_id: str) -> str:
        """Return 'enabled' | 'control' | 'holdout'."""
        from .evaluator import percent_bucket
        bucket = percent_bucket(self.seed_key, installation_id)
        if bucket < self.enabled_pct:
            return "enabled"
        elif bucket < self.enabled_pct + self.control_pct:
            return "control"
        return "holdout"
```

Monitor rollout health via a Celery periodic task:

```python
# tasks.py
from celery import shared_task
from .models import Rollout, ExperimentEvent

@shared_task
def check_rollout_health():
    for rollout in Rollout.objects.filter(status="running"):
        enabled_crashes = ExperimentEvent.objects.filter(
            rollout=rollout, group="enabled", event_name="app_crash"
        ).count()
        control_crashes = ExperimentEvent.objects.filter(
            rollout=rollout, group="control", event_name="app_crash"
        ).count()
        if enabled_crashes > control_crashes * 1.5:
            rollout.status = "paused"
            rollout.save()
            # send alert (Slack webhook, email, etc.)
```

---

### 4.3 Firebase A/B Testing

#### What it does (developer-facing)

A/B Testing wraps Remote Config in an experiment framework. You define:
- **Targeting**: app version, country, language, GA4 audience, user property, percentage exposure (e.g., 50% of eligible users enter the experiment)
- **Variants**: control (default Remote Config values) + up to N treatment arms, each with Remote Config parameter overrides
- **Goal metric** (primary): any GA4 event, or predefined metrics (purchase revenue, crash-free users, retention 2–3d, retention 4–7d, estimated ad revenue, DAU)
- **Secondary metrics** (up to 5)

Variant assignment: `HMAC(experiment_id + firebase_installation_id) % 100` → bucket → variant by weight. Sticky for experiment lifetime even if user properties change post-enrollment. Stats refreshed once per day. Up to 300 total experiments per project (24 simultaneously running).

**Statistical model:** Firebase uses **frequentist inference** (p-value < 0.05 significance threshold) plus a **Bayesian layer** (probability-to-beat-baseline, credible intervals at 50% and 95% certainty). Both views are shown side-by-side in the console.

#### How Firebase implements it under the hood

- Experiment metadata stored in Firestore-backed Firebase infrastructure
- Variant assignment happens at the Remote Config fetch layer — if the user is in an experiment, the assigned variant's parameter overrides take effect
- Metric computation runs on BigQuery over GA4 event exports, once daily
- Bayesian model: Beta-Binomial conjugate for binary metrics, t-test / Bayesian Normal for continuous

#### Django Rebuild

**Full GrowthBook (recommended — best OSS match):**

```bash
# Self-host GrowthBook — MIT license
git clone https://github.com/growthbook/growthbook
cd growthbook
docker-compose up -d
# Services: growthbook-app (Node.js), mongodb

# Python SDK
pip install growthbook

from growthbook import GrowthBook
gb = GrowthBook(
    api_host="https://your-growthbook.internal",
    client_key="sdk-abc123",
    attributes={
        "id": str(user.id),
        "country": user.country,
        "app_version": request.headers.get("X-App-Version"),
    }
)
gb.load_features()  # fetches feature definitions (cached in Redis by SDK)
result = gb.run(Experiment(key="checkout_v2", variations=["control", "treatment"]))
if result.value == "treatment":
    show_new_checkout()
gb.destroy()
```

GrowthBook has SDKs for Python, JavaScript/React, Android (Kotlin), iOS (Swift), Flutter, PHP, Go, Ruby, and 15+ more. Its stats engine supports both Bayesian and frequentist methods, CUPED variance reduction, sequential testing with always-valid p-values, and SRM (Sample Ratio Mismatch) detection. It queries your existing PostgreSQL/BigQuery/Redshift data warehouse directly — no data duplication.

**Build-your-own (lighter weight, if GrowthBook is too heavy):**

```python
# models.py
class Experiment(models.Model):
    key = models.SlugField(unique=True)
    status = models.CharField(max_length=20, default="draft",
        choices=[("draft","draft"),("running","running"),("stopped","stopped")])
    targeting_rules = models.JSONField(default=list)  # same DSL as Condition above
    exposure_pct = models.FloatField(default=100.0)

class Variant(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="variants")
    key = models.CharField(max_length=50)   # "control", "treatment_a"
    weight = models.FloatField(default=0.5)
    config_overrides = models.JSONField(default=dict)

class Assignment(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=255)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = [("experiment", "user_id")]

class ExperimentMetricEvent(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    user_id = models.CharField(max_length=255)
    event_name = models.CharField(max_length=100)
    value = models.FloatField(default=1.0)
    ts = models.DateTimeField(auto_now_add=True)
```

```python
# assignment.py
import hashlib, hmac

def assign_variant(experiment, user_id: str) -> "Variant | None":
    """Sticky, weighted variant assignment via HMAC bucketing."""
    from .models import Assignment
    try:
        return Assignment.objects.get(experiment=experiment, user_id=user_id).variant
    except Assignment.DoesNotExist:
        pass

    # Check exposure
    bucket = _bucket(experiment.key, user_id)
    if bucket >= experiment.exposure_pct:
        return None  # user not in experiment

    # Weighted variant selection
    variants = list(experiment.variants.order_by("key"))
    cumulative = 0.0
    # Re-bucket within 0-100 for variant selection
    variant_bucket = _bucket(experiment.key + ":variant", user_id)
    for v in variants:
        cumulative += v.weight * 100
        if variant_bucket < cumulative:
            Assignment.objects.create(experiment=experiment, user_id=user_id, variant=v)
            return v
    return None

def _bucket(seed: str, user_id: str) -> float:
    key = f"{seed}:{user_id}".encode()
    digest = hmac.new(b"STABLE_SECRET", key, hashlib.sha256).hexdigest()
    return (int(digest[:8], 16) % 100_000) / 1000.0   # 0.000 – 99.999
```

```python
# stats_tasks.py — nightly Celery Beat job
from celery import shared_task
from scipy import stats
import numpy as np

@shared_task
def compute_experiment_stats(experiment_id: int):
    from .models import Experiment, ExperimentMetricEvent, Variant
    exp = Experiment.objects.get(id=experiment_id)
    control = Variant.objects.get(experiment=exp, key="control")
    treatments = Variant.objects.exclude(key="control").filter(experiment=exp)

    for treatment in treatments:
        ctrl_values = list(ExperimentMetricEvent.objects.filter(
            experiment=exp, variant=control
        ).values_list("value", flat=True))
        trt_values = list(ExperimentMetricEvent.objects.filter(
            experiment=exp, variant=treatment
        ).values_list("value", flat=True))

        if len(ctrl_values) < 30 or len(trt_values) < 30:
            continue  # not enough data

        t_stat, p_value = stats.ttest_ind(ctrl_values, trt_values)
        lift = (np.mean(trt_values) - np.mean(ctrl_values)) / (np.mean(ctrl_values) or 1)

        # Bayesian: Beta-Binomial (for binary metrics like conversion)
        # alpha_ctrl, beta_ctrl = conversions, non_conversions
        # P(treatment > control) via Monte Carlo
        alpha_t = sum(1 for v in trt_values if v > 0)
        beta_t = len(trt_values) - alpha_t
        alpha_c = sum(1 for v in ctrl_values if v > 0)
        beta_c = len(ctrl_values) - alpha_c
        samples_t = np.random.beta(alpha_t + 1, beta_t + 1, 10_000)
        samples_c = np.random.beta(alpha_c + 1, beta_c + 1, 10_000)
        prob_to_beat = (samples_t > samples_c).mean()

        ExperimentResult.objects.update_or_create(
            experiment=exp, variant=treatment,
            defaults={"p_value": p_value, "lift": lift, "prob_to_beat_baseline": float(prob_to_beat)}
        )
```

**Gotchas:**

| Gotcha | Solution |
|--------|----------|
| Novelty effect — users react differently just because something is new | Run experiments for at least 2 full weeks; don't stop at first p < 0.05 |
| Assignment pollution (same user on multiple devices) | Use a stable user_id (not session_id or device_id) as the HMAC input |
| GA4 audience latency in targeting | Use user_property or custom_signal for immediate targeting; audiences for broader campaigns |
| Multiple comparisons inflation | Apply Bonferroni correction or use GrowthBook's built-in multiple-comparison corrections |
| Experiment velocity limits | 24 running at once in Firebase; no such limit self-hosted — but running too many simultaneously degrades statistical power per experiment |

---

### 4.4 Firebase Dynamic Links (DEAD — shut down 25 Aug 2025)

#### Status

**Firebase Dynamic Links are permanently shut down as of 25 August 2025.** All links on `page.link` subdomains and all Firebase-hosted custom domain Dynamic Links return HTTP 404. No migration path was provided by Google. The correct replacement is a combination of platform-native deep linking and a custom redirect service.

#### What it did

Dynamic Links was a smart URL service: a single link redirected the user to the correct destination depending on context — to the App Store (iOS, not installed), to Google Play (Android, not installed), directly into the app via a deep link (installed), or to a web fallback URL. The "deferred" aspect stored the deep-link payload server-side and delivered it to the app after install via platform-specific matching (Play Install Referrer on Android, probabilistic fingerprinting on iOS).

#### Django Rebuild — Modern Deep Linking Stack

**Step 1: Serve the platform verification files**

```python
# urls.py
urlpatterns = [
    path(".well-known/assetlinks.json", views.asset_links),
    path(".well-known/apple-app-site-association", views.aasa),
]

# views.py
from django.http import JsonResponse
from django.views.decorators.cache import cache_control

@cache_control(max_age=86400)
def asset_links(request):
    """Android App Links verification — serves from your branded domain."""
    return JsonResponse([{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": "com.example.app",
            "sha256_cert_fingerprints": ["AA:BB:CC:..."]
        }
    }], safe=False, content_type="application/json")

@cache_control(max_age=86400)
def aasa(request):
    """iOS Universal Links verification."""
    return JsonResponse({
        "applinks": {
            "apps": [],
            "details": [{
                "appID": "TEAMID.com.example.app",
                "paths": ["/link/*", "/promo/*"]
            }]
        }
    })
```

**Step 2: Smart redirect view**

```python
# views.py
import user_agents
from django.shortcuts import redirect
from django.http import HttpResponse

def smart_redirect(request, link_id):
    """Universal smart redirect — replaces Firebase Dynamic Links routing."""
    link = get_object_or_404(DynamicLink, link_id=link_id, is_active=True)
    ua = user_agents.parse(request.headers.get("User-Agent", ""))

    # Store click for deferred deep linking
    click = Click.objects.create(
        link=link,
        ip=get_client_ip(request),
        user_agent=str(ua),
        os=("ios" if ua.is_ios else "android" if ua.is_android else "web"),
    )

    if ua.is_ios:
        # Universal Link — if app installed, iOS intercepts before hitting this view.
        # If not installed, serve a page that redirects to App Store and stores click_id.
        return render(request, "redirect_ios.html", {
            "app_store_url": link.ios_fallback_url,
            "deep_link": link.deep_link_path,
            "click_id": str(click.id),
        })
    elif ua.is_android:
        # Intent URL — if app installed, Android intercepts. Otherwise, Play Store.
        intent_url = (
            f"intent://{link.deep_link_path}#Intent;"
            f"scheme=https;"
            f"package={link.android_package};"
            f"S.click_id={click.id};"
            f"S.browser_fallback_url={link.android_fallback_url};"
            f"end"
        )
        return redirect(intent_url)
    else:
        return redirect(link.web_fallback_url)
```

**Step 3: Deferred deep link models and match endpoint**

```python
# models.py
import uuid
class DynamicLink(models.Model):
    link_id = models.UUIDField(default=uuid.uuid4, unique=True)
    deep_link_path = models.CharField(max_length=2000)
    payload = models.JSONField(default=dict)
    ios_fallback_url = models.URLField()
    android_fallback_url = models.URLField()
    web_fallback_url = models.URLField()
    android_package = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

class Click(models.Model):
    link = models.ForeignKey(DynamicLink, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField()
    user_agent = models.TextField()
    os = models.CharField(max_length=10)
    click_id = models.UUIDField(default=uuid.uuid4, unique=True)
    clicked_at = models.DateTimeField(auto_now_add=True)
    matched = models.BooleanField(default=False)
```

```python
# views.py — deferred deep link resolution endpoint (called by app on first launch)
@api_view(["POST"])
def resolve_deferred_link(request):
    method = request.data.get("method")  # "referrer" or "fingerprint"

    if method == "referrer":
        # Android Play Install Referrer — deterministic, ~98% accuracy
        click_id = request.data.get("click_id")
        click = Click.objects.filter(click_id=click_id, matched=False).first()
        if click:
            click.matched = True; click.save()
            return Response({"deep_link": click.link.deep_link_path, "payload": click.link.payload})
        return Response({}, status=404)

    elif method == "fingerprint":
        # iOS probabilistic — match on IP + UA within 15-minute window
        ip = get_client_ip(request)
        ua = request.data.get("user_agent", "")
        cutoff = now() - timedelta(minutes=15)
        candidates = Click.objects.filter(
            ip=ip, os="ios", matched=False, clicked_at__gte=cutoff
        ).order_by("-clicked_at")
        for candidate in candidates:
            if ua[:50] == candidate.user_agent[:50]:  # UA prefix match
                candidate.matched = True; candidate.save()
                return Response({"deep_link": candidate.link.deep_link_path,
                                 "payload": candidate.link.payload})
        return Response({}, status=404)

    return Response({"error": "unknown method"}, status=400)
```

**OSS hosted alternatives (since Firebase Dynamic Links is dead):**

| Tool | License | Notes |
|------|---------|-------|
| Dub | MIT (core) | Open-source link management, supports custom domains; add smart redirect logic yourself |
| 1link.io | Commercial SaaS | Drop-in FDL replacement with SDK |
| Branch | Commercial SaaS | Industry standard, most feature-complete |
| Adjust / AppsFlyer | Commercial SaaS | Attribution-first, MMP with deep linking |

**Gotchas:**

| Gotcha | Solution |
|--------|----------|
| iOS fingerprinting accuracy degrades with VPNs, IPv6 rotation, ATT restrictions | Accept 70–90% match rate on iOS; always provide a good web fallback UX |
| Android Privacy Sandbox restricting Play Install Referrer | Not yet restricted as of 2026; monitor Google's Privacy Sandbox roadmap |
| apple-app-site-association must be served without redirect, with correct Content-Type | Use `Content-Type: application/json`; serve from Nginx directly, not through a Django redirect |
| Universal Links fallback to Safari if app not installed | Include a proper `<meta name="apple-itunes-app">` tag on the fallback page for Smart App Banner UX |

---

### 4.5 Firebase Predictions (Deprecated — absorbed into GA4)

#### Status

Firebase Predictions (legacy) is effectively deprecated. The "new" Firebase Predictions product was renamed and merged into **GA4 Predictive Audiences**, which Google computes daily using AutoML on GA4 event data. Legacy Predictions can still be enabled in the Firebase console by selecting "Legacy Predictions" for projects that have it, but it should be treated as end-of-life.

#### What it did

ML-based daily-refreshed user segments fed into Remote Config conditions and FCM audiences:
- `will_churn`: active in last 7 days, predicted to stop
- `will_spend`: likely to make an in-app purchase
- `will_not_spend`
- `top_spenders`
- `predicted_ltv_*`: LTV bucket (low / mid / high)

These segments were used as Remote Config condition targets — e.g., offer a discount only to `will_churn` users.

#### Django Rebuild — ML-Based User Segments

**Architecture:**

```
Celery Beat (nightly at 2 AM)
  → query PostgreSQL analytics events (last 30 days per user)
  → feature-engineer per-user behavioral vectors
  → run scikit-learn / XGBoost model
  → write scores to UserPrediction table
  → upsert into Flagsmith identity traits OR RemoteConfig custom_signal for targeting
```

**Implementation:**

```python
# models.py
class UserPrediction(models.Model):
    user_id = models.CharField(max_length=255, db_index=True)
    churn_probability = models.FloatField(null=True)
    purchase_probability = models.FloatField(null=True)
    predicted_ltv_bucket = models.CharField(max_length=10, null=True)  # "low","mid","high"
    computed_at = models.DateTimeField(auto_now=True)
    class Meta:
        indexes = [models.Index(fields=["user_id", "computed_at"])]
```

```python
# tasks.py
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from celery import shared_task
from django.db import connection

@shared_task
def compute_predictions():
    # 1. Feature engineering from analytics events
    with connection.cursor() as c:
        c.execute("""
            SELECT
                user_id,
                COUNT(*) FILTER (WHERE event_name = 'session_start') AS session_count,
                COUNT(*) FILTER (WHERE event_name = 'purchase') AS purchase_count,
                MAX(created_at) AS last_active,
                SUM(value) FILTER (WHERE event_name = 'purchase') AS total_revenue,
                COUNT(DISTINCT DATE(created_at)) AS active_days
            FROM analytics_events
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY user_id
        """)
        rows = c.fetchall()

    df = pd.DataFrame(rows, columns=["user_id","sessions","purchases","last_active","revenue","active_days"])
    now = pd.Timestamp.now(tz="UTC")
    df["days_since_active"] = (now - pd.to_datetime(df["last_active"], utc=True)).dt.days
    df["churned_label"] = (df["days_since_active"] > 7).astype(int)

    # 2. Train churn model (in production: load pre-trained model from MLflow/S3)
    features = ["sessions", "purchases", "active_days", "days_since_active", "revenue"]
    X = df[features].fillna(0).values
    y = df["churned_label"].values
    if y.sum() < 10:
        return  # not enough data

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = LogisticRegression(max_iter=1000)
    model.fit(X_scaled, y)
    churn_probs = model.predict_proba(X_scaled)[:, 1]

    # 3. Write predictions
    predictions = [
        UserPrediction(
            user_id=row["user_id"],
            churn_probability=float(churn_probs[i]),
            purchase_probability=float(row["purchases"] / max(row["sessions"], 1)),
            predicted_ltv_bucket=(
                "high" if row["revenue"] > 100 else
                "mid" if row["revenue"] > 10 else "low"
            )
        )
        for i, (_, row) in enumerate(df.iterrows())
    ]
    UserPrediction.objects.bulk_create(
        predictions,
        update_conflicts=True,
        update_fields=["churn_probability","purchase_probability","predicted_ltv_bucket","computed_at"],
        unique_fields=["user_id"]
    )
```

**Targeting integration** — expose prediction scores as `custom_signals` in the config fetch:

```python
# In your config fetch view, enrich signals with ML predictions:
def enrich_signals_with_predictions(signals: dict, user_id: str) -> dict:
    try:
        pred = UserPrediction.objects.get(user_id=user_id)
        signals.setdefault("custom_signals", {})
        signals["custom_signals"]["churn_probability"] = pred.churn_probability
        signals["custom_signals"]["ltv_bucket"] = pred.predicted_ltv_bucket
        # Now a Condition with type=custom_signal, key=churn_probability, operator=">", value=0.7
        # will correctly target high-churn-risk users.
    except UserPrediction.DoesNotExist:
        pass
    return signals
```

**Gotchas:**

| Gotcha | Solution |
|--------|----------|
| Cold-start: no predictions for new users | Use rule-based heuristics for first 7 days (session count thresholds) |
| Model staleness if Celery Beat misses a night | Monitor task success with Celery Flower; fall back to cached predictions (use `computed_at` TTL) |
| Class imbalance in churn model (few churners) | Use `class_weight="balanced"` in LogisticRegression; threshold tune for recall |
| Privacy compliance (GDPR) | Predictions are derived data; ensure user deletion cascades to UserPrediction; document in your privacy policy |

---

### Summary Table — Full Cluster

| Firebase Feature | Django/OSS Equivalent | Key Libraries |
|-----------------|----------------------|---------------|
| Remote Config (parameters, conditions) | DRF endpoint + PostgreSQL conditions + Redis cache | `djangorestframework`, `django-redis`, `psycopg2-binary` |
| Remote Config conditions engine | Custom HMAC evaluator or Flagsmith identity traits | `flagsmith`, `hmac` (stdlib) |
| Remote Config real-time invalidation | Django Channels WebSocket group broadcast | `channels`, `channels-redis`, `daphne` |
| Remote Config percent rollout | HMAC-bucketing `Rollout` model + Celery health monitor | `celery`, `django-waffle` (simpler alternative) |
| A/B Testing | GrowthBook (self-hosted, MIT) or custom + scipy/numpy | `growthbook`, `scipy`, `numpy`, `celery` |
| Firebase Dynamic Links (DEAD) | Django smart-redirect view + .well-known static files | `django`, `user-agents`, `python-ipware` |
| Deferred deep linking | Click-store + Play Referrer match + iOS fingerprint endpoint | `djangorestframework`, `django-redis` |
| Firebase Predictions | Nightly Celery task → scikit-learn → UserPrediction → custom_signal targeting | `scikit-learn`, `pandas`, `celery`, `xgboost` |

## AI: Genkit, Vertex AI in Firebase (AI Logic) & ML Kit

Firebase's AI surface in 2025–2026 divides into three distinct layers: **Genkit** (open-source server-side agent framework), **Firebase AI Logic** (previously "Vertex AI in Firebase" — a client-to-LLM proxy gateway with App Check protection), and **ML Kit** (standalone on-device SDK, now decoupled from Firebase). The older **Firebase ML** product is deprecated and will shut down on **June 15, 2027**. This section covers all four in depth.

---

### 1. Firebase Genkit

#### 1.1 What Genkit Is

Genkit is Google's open-source framework for building production AI features in **TypeScript/JavaScript** (GA Feb 2025), **Go** (GA Sep 2025), and **Python** (alpha Apr 2025). It is hosted at `github.com/firebase/genkit` under Apache 2.0. Genkit is not a Firebase service — it runs entirely in your own infra and simply has deployment helpers for Cloud Functions/Run.

Core primitive: a **Flow** — a named, Zod-typed, streamable function that wraps LLM logic with:
- Type-safe inputs/outputs (Zod schemas, validated at runtime)
- Streaming support (`sendChunk()` callback)
- Automatic trace/span generation (OpenTelemetry-compatible)
- One-command deployment as an HTTP endpoint

#### 1.2 Flows — SDK Shape

```typescript
// genkit/src/flows/menuFlow.ts
import { genkit, z } from 'genkit';
import { googleAI } from '@genkit-ai/google-genai';

const ai = genkit({ plugins: [googleAI()], model: googleAI.model('gemini-flash-latest') });

const MenuItemSchema = z.object({
  dishname: z.string(),
  description: z.string(),
  calories: z.number(),
});

// Non-streaming flow → HTTP POST /menuSuggestionFlow
export const menuSuggestionFlow = ai.defineFlow(
  {
    name: 'menuSuggestionFlow',
    inputSchema: z.object({ theme: z.string() }),
    outputSchema: MenuItemSchema,
  },
  async ({ theme }) => {
    const { output } = await ai.generate({
      prompt: `Invent a menu item for a ${theme} themed restaurant.`,
      output: { schema: MenuItemSchema },
    });
    return output!;
  }
);

// Streaming flow → HTTP POST /menuStreamFlow with chunked SSE body
export const menuStreamFlow = ai.defineFlow(
  {
    name: 'menuStreamFlow',
    inputSchema: z.object({ theme: z.string() }),
    streamSchema: z.string(),           // type of each chunk
    outputSchema: MenuItemSchema,
  },
  async ({ theme }, { sendChunk }) => {
    const { stream, response } = ai.generateStream({
      prompt: `Invent a menu item for a ${theme} themed restaurant.`,
      output: { schema: MenuItemSchema },
    });
    for await (const chunk of stream) {
      sendChunk(chunk.text);            // push SSE chunk to client
    }
    return (await response).output!;
  }
);

// Deploy all flows as HTTP endpoints on port 3400
import { startFlowServer } from '@genkit-ai/express';
startFlowServer({ flows: [menuSuggestionFlow, menuStreamFlow] });
```

Clients call flows via simple POST:
```bash
curl -X POST http://localhost:3400/menuSuggestionFlow \
  -H 'Content-Type: application/json' \
  -d '{"data": {"theme": "Japanese"}}'
```

#### 1.3 Dotprompt — Prompts as Code

`.prompt` files store prompts alongside application code with YAML frontmatter:

```
---
# prompts/menu.prompt
model: googleai/gemini-flash-latest
config:
  temperature: 0.9
  maxOutputTokens: 300
tools: [search_restaurants]
input:
  schema:
    theme?: string
  default:
    theme: "French"
output:
  schema:
    dishname: string
    description: string
    calories: integer
    allergens(array): string
---
Invent a creative menu item for a {{theme}} themed restaurant.
```

Using it in code:
```typescript
const menuPrompt = ai.prompt('menu');
const { output } = await menuPrompt({ theme: 'medieval' });
console.log(output.dishname); // type-safe
```

Dotprompt uses **Picoschema** (compact YAML schema DSL) or standard JSON Schema. The `tools:` key references registered tool names — the model automatically calls them and the framework executes them.

#### 1.4 Tool Calling / Agents

```typescript
const getWeather = ai.defineTool(
  {
    name: 'getWeather',
    description: 'Gets the current weather in a given location',
    inputSchema: z.object({ location: z.string().describe('City name') }),
    outputSchema: z.string(),
  },
  async ({ location }) => {
    // call external API
    return `72°F and sunny in ${location}`;
  }
);

// Pass tools to generate(); Genkit handles the tool-call loop automatically
const result = await ai.generate({
  prompt: 'Should I bring an umbrella to Paris tomorrow?',
  tools: [getWeather],
});
```

**Middleware (May 2026)** adds a programmable interception layer with three hooks:
- **Model middleware** — retries, fallbacks, request/response logging
- **Tool middleware** — human-in-the-loop approvals, sandboxing, audit logs
- **Generate middleware** — inject system instructions or tools before the loop

Multi-agent systems: define one flow that calls another flow as a tool, creating a supervisor/subagent pattern.

#### 1.5 RAG

Genkit provides `defineIndexer` / `defineRetriever` / `ai.retrieve()` with plugins for:
- Cloud Firestore vector store
- Cloud SQL for PostgreSQL (pgvector)
- Pinecone, Chroma, Astra DB, LanceDB, Neo4j, Vertex AI Vector Search

Two-stage retrieval: retrieve a large candidate set, then rerank with a custom reranker or Vertex AI Rank API.

#### 1.6 Observability

Traces stored in Cloud Trace or Firestore. Local **Genkit Developer UI** (web app launched by `genkit start`) shows flow runs, model inputs/outputs, tool calls, latency. In production, the Firebase Console displays AI monitoring dashboards. Traces are OpenTelemetry spans, so they export to any OTel backend.

---

### 1.7 Genkit — Under the Hood

Genkit is a **thin coordination layer**, not a managed service:
- Each flow becomes a Node.js/Go/Python function
- Deployed to Cloud Functions for Firebase or Cloud Run, it becomes an HTTPS endpoint
- The framework sets up Express.js routes (`startFlowServer`) automatically
- Trace data is written to Cloud Firestore (via a Firestore trace plugin) or Cloud Trace
- There is no Firebase-managed inference; model calls go directly to the chosen provider (Vertex AI, Google AI, Anthropic, OpenAI, Ollama, etc. via plugins)
- Pricing: you pay Cloud Functions/Run compute + the underlying LLM provider's token cost; no extra Genkit fee

**Gotchas:**
- Long-running agentic flows can exceed Cloud Functions timeout (9 min max); Cloud Run is better for that
- "Durable streaming" (reconnect to interrupted streams) requires Firestore for flow state — adds Firestore cost
- The Python SDK is still alpha as of mid-2026; Go and Node are production-ready

---

### 2. Firebase AI Logic (formerly Vertex AI in Firebase)

#### 2.1 What It Does

Firebase AI Logic is a **server-side proxy gateway** that lets client apps call Gemini/Imagen models without embedding API keys in client code. The developer experience is: initialize a Firebase client SDK → call `generateContent()` → Firebase's proxy validates the request, holds API keys, forwards to either the Gemini Developer API or Vertex AI Gemini API.

**Product timeline:**
- Launched as "Vertex AI in Firebase" at Google I/O 2024
- Renamed to "Firebase AI Logic" in May 2025, adding Gemini Developer API support
- GA announced at Google Cloud Next 2026

**Models supported (2025–2026):**
- Gemini 2.0 Flash, Gemini 2.0 Flash Lite, Gemini 3 Flash Preview (text, multimodal, structured output, function calling, streaming)
- Imagen 3.0 (image generation + editing: inpainting, outpainting, style transfer) — Android + Flutter
- Gemini Live API (bidirectional audio/video streaming)

#### 2.2 SDK Shape (Web example)

```javascript
// Firebase JS SDK — client-side, no API key in code
import { initializeApp } from 'firebase/app';
import { getAI, getGenerativeModel, GoogleAIBackend } from 'firebase/ai';

const app = initializeApp(firebaseConfig);
const ai = getAI(app, { backend: new GoogleAIBackend() });
const model = getGenerativeModel(ai, { model: 'gemini-2.0-flash' });

// Non-streaming
const result = await model.generateContent('Explain quantum entanglement simply.');
console.log(result.response.text());

// Streaming
const stream = await model.generateContentStream('Write a poem about autumn.');
for await (const chunk of stream.stream) {
  process.stdout.write(chunk.text());
}

// Multimodal
const imageResult = await model.generateContent([
  { inlineData: { data: base64ImageData, mimeType: 'image/jpeg' } },
  'What is in this image?',
]);
```

#### 2.3 App Check Integration — Architecture

```
Mobile/Web Client
    │  (1) Obtain App Check token from Play Integrity / DeviceCheck / reCAPTCHA
    │
    ▼
Firebase AI Logic Proxy (firebasevertexai.googleapis.com)
    │  (2) Validate App Check token
    │  (3) (May 2026+) Mark token as consumed (single-use / replay-attack protection)
    │
    ▼
Gemini Developer API  OR  Vertex AI Gemini API
    (Firebase holds API key — never sent to client)
```

As of **May 2026**: App Check tokens are **strictly single-use**. Even an intercepted valid token cannot be replayed. Combined with token TTLs as short as 5 minutes (limited-use tokens), this makes the proxy highly abuse-resistant.

**April 2026 additions (Cloud Next '26):**
- **Explicit context caching**: upload large context once (policy doc, product catalog), get a `cacheId`, reference it in server prompt templates to avoid re-processing the same tokens
- **Server Prompt Templates**: store system instructions, model config, and tool schemas server-side in the Firebase Console; clients pass only `templateId + parameters`; hot-swap model/instructions without a client release
- **Chat with templates**: `{{history}}` placeholder in template powers multi-turn conversations

#### 2.4 Hybrid On-Device / Cloud Inference (Sep 2025)

Firebase JS SDK checks if Gemini Nano is available in the user's Chrome browser (via Chrome's built-in AI Prompt API), then transparently routes to on-device inference or falls back to cloud Gemini based on developer-configured preference. Zero code change needed.

---

### 3. ML Kit (Standalone On-Device SDK)

#### 3.1 Status

ML Kit is a **standalone SDK** (no Firebase project required) since June 2020. It is available on Android and iOS. All on-device APIs are free, operate offline, and keep data on-device.

**Vision APIs:**
- Text Recognition (300+ languages, including Latin, CJK, Devanagari, handwriting)
- Face Detection (landmarks, contours, classification)
- Barcode Scanning (QR, EAN, UPC, Code 128, Data Matrix, etc.)
- Image Labeling (1000+ categories)
- Object Detection & Tracking
- Pose Detection (33 body landmarks)
- Selfie Segmentation

**Language APIs:**
- On-device Translation (100 language pairs, ~30 MB per language model, lazy download)
- Language Identification (110 languages)
- Smart Reply (contextual chat suggestions)

**GenAI APIs (2025 — Gemini Nano on-device):**
- Prompt API: natural language requests to Gemini Nano on Android
- Image Description, Proofreading, Rewriting, Summarization (pre-built tasks backed by Gemini Nano)

SDK size improvement: unbundled Vision API variants reduced by ~65% (900 KB) from the previous release.

#### 3.2 The Old Firebase ML (Deprecated — shut down June 15, 2027)

Firebase ML had two pieces:
1. **Cloud-based vision APIs** (Image Labeling, Text Recognition via Cloud Vision) — migrate to Firebase AI Logic or call Cloud Vision API directly
2. **TFLite custom model hosting** — host models in Firebase, deliver OTA to devices — migrate to Cloud Storage or self-hosted S3

---

### 4. Django Rebuild

#### 4.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Django Backend                        │
│                                                         │
│  ┌───────────────┐  ┌──────────────────────────────┐   │
│  │  LLM Gateway  │  │  Agent Flow Engine           │   │
│  │  (DRF views)  │  │  (Celery tasks + chains)     │   │
│  │  + LiteLLM    │  │  + tool registry             │   │
│  └───────┬───────┘  └──────────────┬───────────────┘   │
│          │                          │                   │
│  ┌───────▼──────────────────────────▼───────────────┐   │
│  │  App Attestation Middleware                      │   │
│  │  (Play Integrity / DeviceCheck / reCAPTCHA)      │   │
│  │  → Redis nonce store (single-use tokens)         │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────┐  ┌────────────────────────────┐   │
│  │  pgvector        │  │  Prompt Templates          │   │
│  │  (RAG store)     │  │  (PromptTemplate model)    │   │
│  └──────────────────┘  └────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
        │                    │
        ▼                    ▼
  Anthropic API          Google Gemini API
  (claude-opus-4-8,      (gemini-2.0-flash, etc.)
   claude-sonnet-4-6,
   claude-haiku-4-5)
```

#### 4.2 LLM Proxy Gateway (replaces Firebase AI Logic)

**Install:**
```bash
pip install litellm anthropic google-generativeai djangorestframework django-async-sse
```

**settings.py:**
```python
LITELLM_DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"
LITELLM_API_KEYS = {
    "anthropic": os.environ["ANTHROPIC_API_KEY"],
    "gemini":    os.environ["GOOGLE_AI_API_KEY"],
}
```

**models.py:**
```python
from django.db import models

class PromptTemplate(models.Model):
    """Server-side prompt templates (replaces Firebase AI Logic Server Prompt Templates)."""
    slug          = models.SlugField(unique=True)
    version       = models.PositiveIntegerField(default=1)
    model_slug    = models.CharField(max_length=100, default="anthropic/claude-sonnet-4-6")
    system        = models.TextField(blank=True)
    body          = models.TextField(help_text="Jinja2 template string")
    config        = models.JSONField(default=dict)    # temperature, max_tokens, etc.
    tool_schemas  = models.JSONField(default=list)    # function/tool definitions
    cache_id      = models.CharField(max_length=200, blank=True)  # for context caching
    updated_at    = models.DateTimeField(auto_now=True)

    def render(self, **kwargs):
        from jinja2 import Template
        return Template(self.body).render(**kwargs)
```

**views.py — streaming proxy:**
```python
import litellm
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .attestation import require_app_attestation   # custom middleware (see §4.4)

class LLMGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    @require_app_attestation
    def post(self, request):
        template_id = request.data.get("template_id")
        params      = request.data.get("params", {})
        stream      = request.data.get("stream", False)

        template = PromptTemplate.objects.get(slug=template_id)
        rendered_body = template.render(**params)

        messages = []
        if template.system:
            messages.append({"role": "system", "content": template.system})
        # inject chat history if present
        for turn in request.data.get("history", []):
            messages.append(turn)
        messages.append({"role": "user", "content": rendered_body})

        if stream:
            def event_stream():
                response = litellm.completion(
                    model=template.model_slug,
                    messages=messages,
                    stream=True,
                    **template.config,
                )
                for chunk in response:
                    delta = chunk.choices[0].delta.content or ""
                    yield f"data: {delta}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingHttpResponse(
                event_stream(), content_type="text/event-stream"
            )
        else:
            response = litellm.completion(
                model=template.model_slug,
                messages=messages,
                **template.config,
            )
            return Response({"text": response.choices[0].message.content})
```

**urls.py:**
```python
path("ai/generate/", LLMGenerateView.as_view()),
path("ai/flows/<str:flow_name>/", FlowRunView.as_view()),
```

#### 4.3 Agent Flow Engine (replaces Genkit Flows)

```python
# flows/registry.py
from celery import shared_task
from pydantic import BaseModel
import anthropic, json

client = anthropic.Anthropic()

TOOL_REGISTRY: dict[str, callable] = {}

def register_tool(name: str, description: str, input_schema: dict):
    """Decorator to register a tool (Genkit's defineTool equivalent)."""
    def decorator(fn):
        TOOL_REGISTRY[name] = {
            "fn": fn,
            "spec": {
                "name": name,
                "description": description,
                "input_schema": input_schema,
            }
        }
        return fn
    return decorator


@register_tool(
    name="get_weather",
    description="Gets current weather for a city",
    input_schema={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
)
def get_weather(city: str) -> str:
    # call real weather API here
    return f"72°F and sunny in {city}"


@shared_task(bind=True, max_retries=3)
def run_agent_flow(self, flow_name: str, input_data: dict) -> dict:
    """
    Celery task that runs a multi-step agentic loop with tool calling.
    Equivalent to Genkit's defineFlow + tool-call loop.
    """
    tools = [spec["spec"] for spec in TOOL_REGISTRY.values()]
    messages = [{"role": "user", "content": json.dumps(input_data)}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            # Extract final text
            for block in response.content:
                if block.type == "text":
                    return {"result": block.text}
            return {"result": ""}

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_fn = TOOL_REGISTRY[block.name]["fn"]
                    result = tool_fn(**block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
            messages.append({"role": "user", "content": tool_results})


class FlowRunView(APIView):
    """Kick off a Celery flow task and return a job ID."""
    def post(self, request, flow_name):
        task = run_agent_flow.delay(flow_name, request.data)
        return Response({"job_id": task.id, "status": "queued"})

class FlowStatusView(APIView):
    """Poll for flow result."""
    def get(self, request, job_id):
        from celery.result import AsyncResult
        result = AsyncResult(job_id)
        return Response({"status": result.status, "result": result.result})
```

#### 4.4 App Attestation Middleware (replaces Firebase App Check)

Firebase App Check's key capability is **device attestation** (proving the request comes from an unmodified, genuine app) combined with **single-use token enforcement** (May 2026). Replicating this:

```python
# attestation/middleware.py
import hashlib, hmac, time, uuid
from functools import wraps
from django.core.cache import cache  # backed by Redis
from rest_framework.exceptions import PermissionDenied

# Phase 1: Mobile client calls Google Play Integrity API (Android) or
# Apple App Attest (iOS) and gets a signed attestation receipt.
# Client sends: X-Attestation-Token: <receipt>, X-Attestation-Platform: android|ios|web

# Phase 2: Django validates the receipt server-side.
def validate_play_integrity(token: str, package_name: str) -> bool:
    """Verify Google Play Integrity token via Google API."""
    from google.oauth2 import service_account
    import google.auth.transport.requests, requests as req, base64, json
    # Decode and verify the integrity verdict
    # See: https://developer.android.com/google/play/integrity/verdict
    # Returns True if MEETS_DEVICE_INTEGRITY and package matches
    ...  # implementation calls Play Integrity API

def validate_apple_attest(token: str, bundle_id: str) -> bool:
    """Verify Apple App Attest receipt."""
    import pyattest  # pip install pyattest
    # pyattest.verify(...) returns True on valid receipt
    ...

# Phase 3: Issue a short-lived, single-use HMAC token (like Firebase's limited-use tokens)
APP_CHECK_SECRET = os.environ["APP_CHECK_HMAC_SECRET"]
TOKEN_TTL = 300  # 5 minutes, matching Firebase's minimum

def issue_app_token(device_id: str) -> str:
    nonce = str(uuid.uuid4())
    payload = f"{device_id}:{nonce}:{int(time.time())}"
    sig = hmac.new(APP_CHECK_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = f"{payload}:{sig}"
    # Store nonce in Redis for single-use enforcement (TTL = TOKEN_TTL)
    cache.set(f"app_token:{nonce}", "valid", timeout=TOKEN_TTL)
    return token

def verify_app_token(token: str) -> bool:
    """Verify and consume a single-use app token."""
    try:
        device_id, nonce, ts, sig = token.rsplit(":", 3)
    except ValueError:
        return False
    # Check expiry
    if time.time() - int(ts) > TOKEN_TTL:
        return False
    # Check signature
    payload = f"{device_id}:{nonce}:{ts}"
    expected = hmac.new(APP_CHECK_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False
    # Single-use: consume the nonce (replay-attack protection)
    redis_key = f"app_token:{nonce}"
    if not cache.get(redis_key):
        return False  # already used or expired
    cache.delete(redis_key)  # consume
    return True


def require_app_attestation(view_func):
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        token = request.headers.get("X-App-Token")
        if not token or not verify_app_token(token):
            raise PermissionDenied("Invalid or expired app attestation token")
        return view_func(self, request, *args, **kwargs)
    return wrapper
```

**Token issuance endpoint** (called once on app startup after device attestation):
```python
class AttestationExchangeView(APIView):
    """Exchange a Play Integrity / App Attest receipt for a short-lived app token."""
    def post(self, request):
        receipt   = request.data["receipt"]
        platform  = request.data["platform"]  # android | ios | web
        device_id = request.data["device_id"]

        if platform == "android":
            valid = validate_play_integrity(receipt, settings.ANDROID_PACKAGE_NAME)
        elif platform == "ios":
            valid = validate_apple_attest(receipt, settings.IOS_BUNDLE_ID)
        elif platform == "web":
            valid = validate_recaptcha_enterprise(receipt)  # google-cloud-recaptcha-enterprise
        else:
            valid = False

        if not valid:
            raise PermissionDenied("Attestation failed")

        return Response({"app_token": issue_app_token(device_id), "ttl": TOKEN_TTL})
```

#### 4.5 RAG with pgvector (replaces Genkit RAG)

```bash
pip install pgvector pgvector-python anthropic
# PostgreSQL must have pgvector extension: CREATE EXTENSION vector;
```

```python
# models.py
from django.db import models
from pgvector.django import VectorField, HnswIndex

class Document(models.Model):
    content     = models.TextField()
    source      = models.CharField(max_length=500)
    embedding   = VectorField(dimensions=1536, null=True)  # voyage-3 dim
    metadata    = models.JSONField(default=dict)
    indexed_at  = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            HnswIndex(
                name="doc_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]

# tasks.py — indexing pipeline (run as Celery task)
import anthropic
from pgvector.django import CosineDistance

client = anthropic.Anthropic()

@shared_task
def index_documents(doc_ids: list[int]):
    """Embed and index documents — equivalent to Genkit's ai.index()."""
    docs = Document.objects.filter(id__in=doc_ids)
    texts = [d.content for d in docs]

    # Use Anthropic's voyage-3 embedding model via the API
    response = client.beta.messages.create(
        model="voyage-3",  # or use google-generativeai for text-embedding-004
        messages=[{"role": "user", "content": t} for t in texts],
    )
    # Alternatively with the voyageai package:
    # import voyageai; vo = voyageai.Client(); result = vo.embed(texts, model="voyage-3")

    for doc, embedding in zip(docs, embeddings):
        doc.embedding = embedding
    Document.objects.bulk_update(docs, ["embedding"])


def retrieve(query: str, k: int = 5) -> list[Document]:
    """Retrieve top-k documents — equivalent to Genkit's ai.retrieve()."""
    # Embed the query
    query_embedding = embed_text(query)  # same embedding fn as above
    return list(
        Document.objects
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .order_by("distance")[:k]
    )


def rag_flow(query: str) -> str:
    """Full RAG pipeline — index + retrieve + generate."""
    docs = retrieve(query)
    context = "\n\n".join(d.content for d in docs)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="Answer the question using only the provided context.",
        messages=[{
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}"
        }],
    )
    return response.content[0].text
```

#### 4.6 ML Kit Replacement Strategy

ML Kit is a **mobile-client SDK** — there is no server-side equivalent needed for the on-device APIs. However, if you need server-side inference for the same tasks:

| ML Kit API | Server-Side Django Equivalent | Package |
|---|---|---|
| Text Recognition (OCR) | `pytesseract` + Tesseract 5, or Google Cloud Vision | `pytesseract`, `Pillow`, `google-cloud-vision` |
| Face Detection | `face_recognition` (dlib) or `deepface` | `face-recognition`, `deepface` |
| Barcode Scanning | `pyzbar` or `zxing-cpp` | `pyzbar`, `Pillow` |
| Image Labeling | ONNX Runtime + MobileNetV3 or EfficientNet | `onnxruntime`, `Pillow` |
| Object Detection | ONNX Runtime + YOLOv8 or Torchvision | `onnxruntime` or `torchvision` |
| Translation | ArgosTranslate (offline) or LibreTranslate | `argostranslate`, `libretranslatepy` |
| Language ID | `lingua-py` or `langdetect` | `lingua-py`, `langdetect` |
| Gemini Nano (on-device GenAI) | Client-only; server fallback via Anthropic/Gemini proxy | (see §4.2) |

For **custom TFLite model hosting** (replacing deprecated Firebase ML):
```python
# Serve model files from MinIO/S3 with versioning
class MLModel(models.Model):
    name       = models.CharField(max_length=100)
    version    = models.CharField(max_length=20)
    file       = models.FileField(upload_to="ml_models/")  # MinIO backend
    platform   = models.CharField(max_length=20)  # tflite, onnx, coreml
    checksum   = models.CharField(max_length=64)   # SHA-256 for integrity
    is_active  = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

# Client fetches: GET /api/ml/models/?name=classifier&platform=tflite
# Returns presigned URL + version + checksum for OTA download
```

---

### 5. Gotchas & Hard Parts

| Problem | Firebase's Solution | Self-Hosted Approach |
|---|---|---|
| **Device attestation** is hardware-rooted and Google/Apple-enforced | Play Integrity + DeviceCheck + reCAPTCHA Enterprise, all verified by Firebase's proxy | `pyattest` for Apple, Google Play Integrity API for Android; harder to harden — a jailbroken device can fake attestation with more effort |
| **Single-use token replay protection** | Firebase's proxy marks tokens consumed atomically across all instances | Redis `SETNX` (set if not exists) for atomic nonce consumption; works well but requires Redis high availability |
| **Durable streaming** (reconnect to interrupted flows) | Genkit stores flow state in Firestore, client reconnects and replays | Celery task ID + Redis for partial result caching; full replay requires storing chunks, more complex |
| **Prompt template hot-swap** without client release | Firebase Console UI, server-side templates | `PromptTemplate` Django model editable via Django admin or a custom UI |
| **Context caching** (send large context once, reuse) | Firebase AI Logic / Gemini context caching with `cacheId` | Anthropic supports prompt caching natively (`"cache_control": {"type": "ephemeral"}`); pass `cache_control` on system prompt blocks |
| **On-device inference** (Gemini Nano, ML Kit) | First-class SDK feature | Pure client-side concern; ship WebLLM (web) or ML Kit (mobile) unchanged; Django is the fallback |
| **LLM vendor lock-in** | Firebase supports only Gemini / Imagen | LiteLLM abstracts 100+ providers; swap `model_slug` in `PromptTemplate` with zero code change |
| **Observability & spend tracking** | Firebase Console AI dashboard | LiteLLM's built-in `/ui` admin + Langfuse + OpenTelemetry traces to Jaeger/Grafana Tempo |

### 6. OSS Alternatives Doing Parts of This

| Alternative | Relevant Feature |
|---|---|
| **LiteLLM** (`litellm`) | Multi-provider LLM proxy, virtual keys, spend limits, 100+ models including Claude and Gemini — the closest to Firebase AI Logic's proxy layer |
| **LangChain** / **LangGraph** | Agent/flow orchestration, RAG chains, tool calling — more batteries-included than Genkit but heavier |
| **Haystack** (`haystack-ai`) | Production-grade RAG pipelines with Django integration |
| **Supabase** | pgvector-native, has its own Edge Functions that can proxy LLM calls |
| **Appwrite** | Has "Appwrite Functions" with OpenAI integration helpers |

**Recommended stack:**
```
LiteLLM (proxy + multi-model) + Django REST Framework (API) +
PostgreSQL + pgvector (RAG) + Redis (nonce store + Celery broker) +
Celery (async flows) + OpenTelemetry → Jaeger (observability) +
pyattest + Play Integrity API (attestation)
```

## Tooling: CLI, Admin SDK, Emulator Suite, Security Rules, Test Lab, App Distribution &amp; Firebase Studio

This cluster covers the **developer experience layer** — the tooling that makes Firebase feel like a cohesive platform rather than a collection of independent services. Every sub-system here must be replicated in the Django rebuild to achieve parity in developer productivity.

---

### 1. Firebase CLI (`firebase init` / `deploy` / `emulators:start`)

#### What it does

The Firebase CLI (`firebase-tools`, installed via `npm install -g firebase-tools`) is the single entry point for all local development and production deployment operations:

```bash
firebase login                        # OAuth2 browser flow, stores token in ~/.config/configstore/firebase-tools.json
firebase init                         # interactive wizard: scaffolds firebase.json, .firebaserc, .rules files
firebase deploy                       # multi-service deploy: Hosting → GCS CDN, Functions → Cloud Build, Rules → Rules API, Indexes
firebase deploy --only firestore:rules # targeted deploy
firebase emulators:start              # spawn all local emulators
firebase emulators:export ./seed      # snapshot emulator state to disk
firebase emulators:start --import ./seed  # restore snapshot
```

`firebase.json` is the single source of truth:

```json
{
  "hosting": { "public": "dist", "ignore": ["firebase.json"] },
  "firestore": { "rules": "firestore.rules", "indexes": "firestore.indexes.json" },
  "functions": { "source": "functions" },
  "storage": { "rules": "storage.rules" },
  "emulators": {
    "auth": { "port": 9099 },
    "firestore": { "port": 8080 },
    "functions": { "port": 5001 },
    "hosting": { "port": 5000 },
    "ui": { "enabled": true, "port": 4000 }
  }
}
```

#### How Firebase implements it under the hood

`firebase-tools` is a Node.js monorepo (GitHub: `firebase/firebase-tools`). `firebase deploy` is a multi-phase pipeline:

1. **Pre-flight**: reads `firebase.json`, resolves `.firebaserc` project alias → project ID.
2. **Hosting**: hashes local files, diffs against last release hash manifest, uploads only changed files to GCS, atomically promotes a new release version.
3. **Functions**: zips source, calls Cloud Build API to build, then Cloud Functions Admin API to update function configs. Handles deploy ordering for function dependencies.
4. **Rules**: reads `.rules` files, calls `firebaserules.googleapis.com/v1/projects/{id}/rulesets` (Rules Management API) to create an immutable ruleset, then creates/updates a `Release` pointing to it.
5. **Indexes**: calls Firestore Admin API to update composite index definitions.

Authentication uses OAuth2 device/browser flow; tokens stored in `configstore`. Service-account auth (`GOOGLE_APPLICATION_CREDENTIALS`) is the CI pattern.

#### Django Rebuild: `ownfb` CLI

Build with **Typer** — the modern Python CLI framework using type hints, built on Click.

```bash
pip install typer rich python-dotenv boto3 requests pyyaml
```

Structure:

```
ownfb_cli/
├── __init__.py
├── main.py          # typer app
├── commands/
│   ├── init.py      # scaffold ownfirebase.json + project structure
│   ├── deploy.py    # multi-service deploy
│   ├── emulators.py # docker-compose lifecycle
│   ├── rules.py     # push permission policies
│   └── distribution.py
```

```python
# ownfb_cli/main.py
import typer
from .commands import init, deploy, emulators, rules, distribution

app = typer.Typer(name="ownfb", help="OwnFirebase CLI - self-hosted Firebase on Django")
app.add_typer(init.app, name="init")
app.add_typer(deploy.app, name="deploy")
app.add_typer(emulators.app, name="emulators")
app.add_typer(rules.app, name="rules")
app.add_typer(distribution.app, name="appdistribution")

if __name__ == "__main__":
    app()
```

```python
# ownfb_cli/commands/deploy.py
import typer, yaml, boto3, requests
from pathlib import Path
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def all(
    only: str = typer.Option("", help="Comma-separated targets: hosting,rules,functions"),
    config: Path = typer.Option("ownfirebase.json"),
):
    cfg = yaml.safe_load(config.read_text())
    targets = only.split(",") if only else ["hosting", "rules", "functions", "indexes"]
    
    if "hosting" in targets:
        _deploy_hosting(cfg)
    if "rules" in targets:
        _deploy_rules(cfg)
    if "functions" in targets:
        _deploy_functions(cfg)

def _deploy_rules(cfg):
    console.print("[bold blue]Deploying permission policies...[/]")
    api_url = cfg["api"]["url"]
    token = _get_token()
    rules_path = Path(cfg.get("rules", {}).get("source", "rules/"))
    for rules_file in rules_path.glob("*.rego"):
        resp = requests.post(
            f"{api_url}/api/v1/management/rules/deploy/",
            json={"name": rules_file.stem, "content": rules_file.read_text()},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
    console.print("[green]Rules deployed.[/]")
```

`ownfirebase.json` mirrors `firebase.json`:

```json
{
  "api": { "url": "https://api.yourproject.com" },
  "hosting": { "public": "dist", "bucket": "your-s3-bucket" },
  "rules": { "source": "rules/" },
  "emulators": {
    "compose_file": "docker-compose.local.yml",
    "ui_port": 4000
  }
}
```

**Django management command integration** via `django-typer`:

```bash
pip install django-typer
# Then: python manage.py ownfb deploy --only rules
```

---

### 2. Firebase Admin SDK

#### What it does

Server-side SDK available in Node.js, Python, Java, Go, C#, and PHP. Initialized once with a service account; thereafter all calls bypass Security Rules and use elevated privileges.

```python
# Python Admin SDK
import firebase_admin
from firebase_admin import credentials, auth, firestore

cred = credentials.Certificate("service-account.json")
firebase_admin.initialize_app(cred)

# Verify a client-supplied ID token
decoded = auth.verify_id_token(id_token)  # raises on invalid/expired
uid = decoded["uid"]

# Create a custom token for a user (signed RS256 JWT)
custom_token = auth.create_custom_token(uid, {"admin": True, "role": "editor"})

# Set custom claims (persisted in user record, appear in next token refresh)
auth.set_custom_user_claims(uid, {"premium": True, "tier": "gold"})

# Firestore admin write — bypasses all Security Rules
db = firestore.client()
db.collection("orders").document(order_id).set({"status": "approved"})
```

Key properties:
- Custom tokens are signed JWTs (RS256) where the private key belongs to the service account. The Firebase Auth backend verifies them and issues standard Firebase ID tokens.
- Claims payload must be ≤ 1000 bytes.
- `verify_id_token()` validates signature, expiry, and issuer against Firebase's public key endpoint (`https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com`).
- Admin SDK calls go to REST APIs directly; Firestore Admin uses the Cloud Firestore gRPC API.

#### How Firebase implements it under the hood

The Admin SDK is a thin REST/gRPC client that authenticates via OAuth2 using the service account. It calls `iamcredentials.googleapis.com` to sign JWTs remotely when no private key is available (e.g., on Cloud Run with ADC). All Admin SDK operations go through the same production APIs as client SDKs but with an OAuth2 access token that grants full project-level access — Security Rules are enforced only for client SDK calls that carry user ID tokens, not admin OAuth2 tokens.

#### Django Rebuild: Admin SDK Layer

```python
# pip install djangorestframework-simplejwt PyJWT cryptography djangorestframework-api-key
```

```python
# ownfb_admin/sdk.py
import jwt, time
from cryptography.hazmat.primitives import serialization
from rest_framework_simplejwt.tokens import UntypedToken
from django.contrib.auth import get_user_model
from .models import AdminApiKey

User = get_user_model()

class AdminSDK:
    """Server-side privileged access — equivalent to Firebase Admin SDK."""
    
    def __init__(self, api_key: str):
        self._key = AdminApiKey.objects.get_from_key(api_key)  # raises if invalid
    
    def verify_id_token(self, token: str) -> dict:
        """Validate client-issued JWT. Returns decoded payload."""
        try:
            payload = UntypedToken(token)
            return dict(payload.payload)
        except Exception as exc:
            raise ValueError(f"Invalid token: {exc}") from exc
    
    def create_custom_token(self, uid: str, claims: dict = None) -> str:
        """Issue a short-lived signed JWT for a given UID."""
        private_key = self._load_private_key()
        payload = {
            "uid": uid,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "custom_claims": claims or {},
        }
        return jwt.encode(payload, private_key, algorithm="RS256")
    
    def set_custom_user_claims(self, uid: str, claims: dict):
        """Persist claims on user record; included in next issued JWT."""
        user = User.objects.get(pk=uid)
        user.custom_claims = claims  # JSONField on User model
        user.save(update_fields=["custom_claims"])
    
    def get_firestore_client(self):
        """Returns ORM queryset bypassing all permission checks."""
        from ownfb_firestore.models import FirestoreDocument
        return AdminQuerySet(FirestoreDocument, admin=True)
    
    @staticmethod
    def _load_private_key():
        from django.conf import settings
        return serialization.load_pem_private_key(
            settings.OWNFB_PRIVATE_KEY.encode(), password=None
        )
```

DRF middleware that checks the admin bypass:

```python
# ownfb_admin/permissions.py
from rest_framework.permissions import BasePermission

class IsAdminSDKClient(BasePermission):
    """Grants full access when request carries a valid Admin API key."""
    def has_permission(self, request, view):
        key = request.headers.get("X-Admin-Key")
        if not key:
            return False
        from .models import AdminApiKey
        return AdminApiKey.objects.filter(key_hash=hash_key(key), revoked=False).exists()
    
    def has_object_permission(self, request, view, obj):
        return True  # Admin bypasses all object-level checks
```

---

### 3. Local Emulator Suite

#### What it does

Runs complete Firebase service replicas locally so development never touches production:

```bash
firebase emulators:start --only auth,firestore,functions,storage
# Auth:      http://localhost:9099
# Firestore: http://localhost:8080
# Functions: http://localhost:5001
# Storage:   http://localhost:9199
# Hub:       http://localhost:4400
# UI:        http://localhost:4000
```

Client SDKs detect emulators:

```typescript
import { connectFirestoreEmulator, getFirestore } from "firebase/firestore";
import { connectAuthEmulator, getAuth } from "firebase/auth";

const db = getFirestore();
const auth = getAuth();

if (process.env.NODE_ENV === "development") {
  connectFirestoreEmulator(db, "localhost", 8080);
  connectAuthEmulator(auth, "http://localhost:9099");
}
```

#### How Firebase implements it under the hood

- **Emulator Hub** (Node.js, port 4400): service registry. Each emulator registers itself; the hub exposes `/emulators` endpoint listing running services with their ports. The UI polls this.
- **Firestore emulator**: Java JAR (~85MB, `cloud-firestore-emulator-*.jar`). Implements the full Firestore gRPC API plus REST, including Security Rules evaluation. Data stored in-memory (export/import serializes to JSON).
- **RTDB emulator**: Java JAR. WebSocket server implementing RTDB's Firebase protocol.
- **Auth emulator**: Node.js. Implements Identity Toolkit REST API. Does not send real emails — intercepts and logs them.
- **Functions emulator**: Node.js. Spawns user code in child processes, registers trigger listeners on Firestore/Auth/Pub/Sub emulators. Watches for file changes with `chokidar`.
- **Storage emulator**: Node.js. GCS JSON API compatible. Stores files on local disk.
- **Pub/Sub emulator**: Java JAR. Google Pub/Sub gRPC emulator.
- **UI**: React SPA served by the Hub, connects to each emulator's HTTP API.
- Cross-emulator triggers work via event bus in the Hub: Firestore emulator notifies Hub of document writes; Hub dispatches to Functions emulator.

#### Django Rebuild: docker-compose Local Stack

Replace the entire Emulator Suite with a single `docker-compose.local.yml`:

```yaml
# docker-compose.local.yml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ownfb_dev
      POSTGRES_USER: ownfb
      POSTGRES_PASSWORD: devpassword
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports: ["9000:9000", "9001:9001"]
    volumes: ["miniodata:/data"]

  mailhog:
    image: mailhog/mailhog:latest
    ports: ["1025:1025", "8025:8025"]  # SMTP + Web UI

  django:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes: [".:/app"]
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgres://ownfb:devpassword@postgres:5432/ownfb_dev
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      EMAIL_HOST: mailhog
      EMAIL_PORT: 1025
      OWNFB_EMULATOR_MODE: "true"
    depends_on: [postgres, redis, minio, mailhog]

  celery:
    build: .
    command: celery -A ownfb worker --loglevel=info
    volumes: [".:/app"]
    environment:
      DATABASE_URL: postgres://ownfb:devpassword@postgres:5432/ownfb_dev
      REDIS_URL: redis://redis:6379/0
    depends_on: [postgres, redis]

  celery_beat:
    build: .
    command: celery -A ownfb beat --loglevel=info
    volumes: [".:/app"]
    depends_on: [redis]

  channels:
    build: .
    command: daphne -b 0.0.0.0 -p 8001 ownfb.asgi:application
    volumes: [".:/app"]
    ports: ["8001:8001"]
    depends_on: [redis, django]

  emulator_ui:
    build: ./emulator-ui  # React SPA
    ports: ["4000:80"]

volumes:
  pgdata:
  miniodata:
```

Start everything with:

```bash
ownfb emulators:start    # wraps: docker-compose -f docker-compose.local.yml up -d
ownfb emulators:stop     # wraps: docker-compose -f docker-compose.local.yml down
ownfb emulators:export ./seed  # pg_dump + minio sync + redis-cli BGSAVE
ownfb emulators:import ./seed  # pg_restore + minio sync + redis restore
```

Client SDK detection:

```typescript
// ownfb-client-js/src/config.ts
const EMULATOR_HOST = process.env.OWNFB_EMULATOR_HOST || null;
export const API_URL = EMULATOR_HOST ? `http://${EMULATOR_HOST}:8000` : "https://api.yourproject.com";
export const WS_URL  = EMULATOR_HOST ? `ws://${EMULATOR_HOST}:8001`  : "wss://ws.yourproject.com";
```

---

### 4. Security Rules Language & Engine

#### What it does

Firebase Security Rules are a declarative, server-side access control language evaluated before every read/write. Rules are colocated with the database and enforced without any backend server code:

```javascript
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Public read, owner write
    match /posts/{postId} {
      allow read: if true;
      allow write: if request.auth != null 
                   && request.auth.uid == resource.data.authorUid;
    }
    
    // Role-based: only admins can write; check a separate /roles collection
    match /products/{productId} {
      allow read: if true;
      allow write: if request.auth != null
                   && get(/databases/$(database)/documents/roles/$(request.auth.uid)).data.role == 'admin';
    }
    
    // Validate incoming data shape
    match /orders/{orderId} {
      allow create: if request.auth != null
                    && request.resource.data.keys().hasAll(['userId', 'items', 'total'])
                    && request.resource.data.total is number
                    && request.resource.data.total > 0;
    }
    
    // Wildcard: lock down everything else
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

Key variables:
| Variable | Description |
|---|---|
| `request.auth` | Verified JWT payload (`uid`, `token.email`, `token.email_verified`, custom claims) |
| `request.auth.token` | Full decoded token including custom claims |
| `resource.data` | Existing document fields (on read/update/delete) |
| `request.resource.data` | Incoming document fields (on write) |
| `get(path)` | Cross-document lookup (counts as a read, billed) |
| `exists(path)` | Check if a document exists |
| `request.time` | Server timestamp of the request |

#### How Firebase implements it under the hood

The rules engine is a **CEL (Common Expression Language)** superset interpreter embedded in the Firestore/Storage/RTDB server processes. Key architectural properties:

- **Stateless evaluation**: rules are compiled to an AST at deploy time; each request evaluation is a pure function of `(rules_AST, request_context, resource_snapshot)`.
- **`get()`/`exists()` calls**: trigger synchronous Firestore reads inside the rule evaluation — these are billed separately and can add latency. Max 10 `get()`/`exists()` calls per rule evaluation chain.
- **Security Rules do not filter queries**: a query is only allowed if the rules would allow reading every document the query might return. Use `request.auth.uid == resource.data.uid` guards to ensure queries include the same filter.
- **Rules are immutable rulesets**: deployed via the Firebase Rules Management API as versioned, content-addressed snapshots. Rollback = point the `Release` at a previous `Ruleset`.
- **Emulator replication**: the Firestore emulator Java JAR includes a full CEL interpreter that evaluates the same rules locally, enabling accurate local testing.

#### Django Rebuild: Three-Layer Permission Architecture

Firebase Security Rules map to three complementary Django layers:

**Layer 1: DRF Object-Level Permissions with `django-rules`**

```bash
pip install rules drf-rules
```

```python
# rules_engine/predicates.py
import rules
from django.contrib.auth import get_user_model

@rules.predicate
def is_document_owner(user, document):
    return document.author_id == user.pk

@rules.predicate  
def is_admin_user(user, obj=None):
    return getattr(user, "custom_claims", {}).get("role") == "admin"

@rules.predicate
def is_premium_user(user, obj=None):
    return getattr(user, "custom_claims", {}).get("premium", False)

# Compose predicates (equivalent to Security Rules boolean operators)
can_write_post = is_document_owner | is_admin_user
can_read_premium = is_premium_user | is_admin_user

rules.add_perm("posts.change_post", can_write_post)
rules.add_perm("posts.delete_post", can_write_post)
rules.add_perm("posts.view_premium_post", can_read_premium)
```

```python
# views.py
from rest_framework.viewsets import ModelViewSet
from drf_rules.permissions import OperandHolder
import rules

class PostViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, rules.contrib.rest_framework.AutoPermission]
    
    def get_queryset(self):
        # Security Rules CANNOT filter queries — we must replicate this:
        # only return documents the user is allowed to read
        if self.request.user.custom_claims.get("role") == "admin":
            return Post.objects.all()
        return Post.objects.filter(author=self.request.user)
```

**Layer 2: PostgreSQL Row-Level Security (database-enforced)**

```sql
-- Applied via Django migration using django-pgtrigger or raw SQL
ALTER TABLE ownfb_firestore_document ENABLE ROW LEVEL SECURITY;

CREATE POLICY document_owner_policy ON ownfb_firestore_document
  FOR ALL
  USING (author_id = current_setting('app.current_user_id')::uuid);

-- Set in Django middleware:
-- connection.cursor().execute("SET LOCAL app.current_user_id = %s", [str(user.pk)])
```

**Layer 3: OPA (Open Policy Agent) for complex cross-document rules**

Equivalent to `get()`/`exists()` cross-document lookups:

```python
# pip install requests  (OPA runs as a sidecar)
# docker run -p 8181:8181 openpolicyagent/opa:latest run --server
```

```rego
# policies/firestore.rego
package ownfb.firestore

import future.keywords.if

default allow = false

# Owner can write their own documents
allow if {
    input.request.method in ["PUT", "PATCH", "DELETE"]
    input.request.auth.uid == input.resource.author_id
}

# Admin role check (cross-document lookup via OPA data)
allow if {
    input.request.method in ["PUT", "PATCH"]
    data.roles[input.request.auth.uid].role == "admin"
}

# Validate incoming data shape (equivalent to request.resource.data validation)
allow if {
    input.request.method == "POST"
    input.resource_data.total > 0
    input.resource_data.user_id != ""
}
```

```python
# ownfb_rules/middleware.py
import requests
from django.http import JsonResponse

class OPARulesMiddleware:
    OPA_URL = "http://localhost:8181/v1/data/ownfb/firestore/allow"
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if self._should_enforce(request):
            decision = self._query_opa(request)
            if not decision:
                return JsonResponse({"error": "Permission denied"}, status=403)
        return self.get_response(request)
    
    def _query_opa(self, request) -> bool:
        payload = {
            "input": {
                "request": {
                    "method": request.method,
                    "path": request.path,
                    "auth": getattr(request, "opa_auth_context", {}),
                },
                "resource": getattr(request, "opa_resource_context", {}),
            }
        }
        resp = requests.post(self.OPA_URL, json=payload, timeout=0.05)
        return resp.json().get("result", False)
```

**Rules deployment** (equivalent to `firebase deploy --only firestore:rules`):

```bash
ownfb rules:deploy --source rules/
# Uploads .rego files to OPA bundle endpoint; OPA hot-reloads policies.
```

**Gotcha**: Firebase Security Rules block queries where the rules could theoretically return documents the user cannot read. Django/DRF does NOT do this automatically — your `get_queryset()` must manually apply the same filters as your permission predicates. This is a discipline requirement, not a technical limitation.

---

### 5. Firebase Test Lab

#### What it does

Cloud device farm for automated mobile testing. Runs APK/IPA binaries against real hardware in Google data centers:

```bash
gcloud firebase test android run \
  --type instrumentation \
  --app app-debug.apk \
  --test app-debug-androidTest.apk \
  --device model=Pixel6,version=33,locale=en,orientation=portrait \
  --device model=GalaxyS21,version=31 \
  --results-bucket gs://my-project-test-results

# Also supports:
# --type robo         (ML UI crawler, no test APK needed)
# --type game-loop    (for games using Game Loop API)
```

Test results (video recordings, logcat, screenshots, coverage XML) are stored in GCS and viewable in the Firebase console.

**Pricing**: Free tier = 10 virtual device hours/day on Spark plan; Blaze = ~$1–5 per physical device hour depending on device class. Quotas are per-project, not per-user.

#### How Firebase implements it under the hood

- Backed by the **Cloud Testing API** (`testing.googleapis.com`) and **Tool Results API** (`toolresults.googleapis.com`).
- Real Android/iOS devices run in Google data centers with remote ADB connections.
- Robo test uses Google's proprietary UI traversal ML model to autonomously exercise the app.
- Test matrix: parallelizes across device × OS × locale combinations as independent test executions.
- Results streamed to GCS; Tool Results API provides structured pass/fail/step data.

#### Django Rebuild: Self-Hosted Test Infrastructure

Firebase Test Lab is mobile CI infrastructure, not a Django backend concern. The appropriate self-hosted equivalent:

| Firebase Test Lab Feature | Self-Hosted Replacement |
|---|---|
| Real device farm | AWS Device Farm / BrowserStack / Sauce Labs (all paid) |
| Android virtual device testing | Android emulator in Docker (`budtmo/docker-android`) + Appium |
| Robo test (UI crawler) | Appium with `io.appium:appium-android-driver` UIAutomator2 |
| iOS device testing | macOS GitHub Actions runners + XCTest / Fastlane |
| Test results storage | PostgreSQL (test runs) + S3/MinIO (artifacts) |
| Results dashboard | Custom React dashboard or Allure Report (`allure-pytest`) |
| CI integration | GitHub Actions / GitLab CI |

Self-hosted Android test grid with Docker:

```yaml
# docker-compose.testlab.yml
services:
  appium-server:
    image: appium/appium:latest
    ports: ["4723:4723"]
    
  android-emulator:
    image: budtmo/docker-android:emulator_11.0
    privileged: true
    environment:
      EMULATOR_DEVICE: "Samsung Galaxy S10"
      WEB_VNC: true
    ports: ["6080:6080"]  # VNC web UI
```

```python
# ownfb_testlab/runner.py
# pip install Appium-Python-Client pytest-appium allure-pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options

def run_android_test(apk_path: str, test_apk_path: str, device_config: dict):
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.app = apk_path
    options.device_name = device_config["model"]
    options.platform_version = device_config["version"]
    
    driver = webdriver.Remote("http://localhost:4723", options=options)
    # ... run tests, collect results
    driver.quit()
```

A Django management command `ownfb test:run --apk build.apk` submits jobs to a Celery queue, polling Appium for results and storing them in PostgreSQL with S3 artifact links.

---

### 6. Firebase App Distribution

#### What it does

Pre-release build distribution to testers — the replacement for the now-defunct Visual Studio App Center (retired March 2025):

```bash
# Via CLI
firebase appdistribution:distribute app-debug.apk \
  --app 1:123456789:android:abcdef \
  --groups "beta-testers,internal-qa" \
  --release-notes "Fixed login bug, new onboarding flow"

# Via Fastlane
lane :distribute do
  firebase_app_distribution(
    app: "1:123456789:android:abcdef",
    groups: "beta-testers",
    release_notes: "Nightly build",
    service_credentials_file: "service-account.json"
  )
end

# Via Gradle plugin
firebaseAppDistribution {
  artifactType = "APK"
  groups = "beta-testers"
  releaseNotes = "New release"
  serviceCredentialsFile = "service-account.json"
}
```

Testers receive an email with a one-tap install link. An in-app SDK (`FirebaseAppDistribution.checkForUpdate()`) shows an in-app update prompt when a new build is available.

**Pricing**: completely free, no limits on apps, testers, or builds.

#### How Firebase implements it under the hood

- REST API: `firebaseappdistribution.googleapis.com/v1/projects/{project}/apps/{app}/releases`
- APK/IPA stored in GCS; signed download URLs with time-limited tokens for tester access.
- Android OTA install: custom install page that triggers `ACTION_INSTALL_PACKAGE` via a companion "Firebase App Tester" app (required for Android 8+ due to package installer restrictions).
- iOS OTA install: HTTPS-served `.plist` manifest + signed IPA; triggered via `itms-services://` deep link.
- Email delivery via Google Workspace / SendGrid infrastructure.
- GitHub Actions integration via `wzieba/Firebase-Distribution-Github-Action`.

#### Django Rebuild: Self-Hosted App Distribution

```bash
pip install django django-storages boto3 django-anymail Pillow
```

**Models:**

```python
# ownfb_distribution/models.py
from django.db import models

class App(models.Model):
    name = models.CharField(max_length=255)
    platform = models.CharField(choices=[("android", "Android"), ("ios", "iOS")])
    bundle_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

class TesterGroup(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # e.g. "beta-testers"
    testers = models.ManyToManyField("auth.User", related_name="tester_groups")

class Release(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE)
    version_name = models.CharField(max_length=50)
    version_code = models.IntegerField()
    binary = models.FileField(upload_to="releases/", storage=S3BotoStorage())
    release_notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    tester_groups = models.ManyToManyField(TesterGroup)
    
    def get_install_url(self):
        """Returns time-limited signed S3 URL."""
        return self.binary.storage.url(self.binary.name, expire=3600)
```

**OTA install page (Android):**

```python
# ownfb_distribution/views.py
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

def android_install(request, release_id, token):
    release = get_object_or_404(Release, pk=release_id)
    _verify_tester_token(token, release)  # raises 403 if invalid
    # Serve APK directly; Android's browser will trigger install prompt
    return HttpResponse(
        release.binary.read(),
        content_type="application/vnd.android.package-archive",
        headers={"Content-Disposition": f'attachment; filename="{release.app.name}-{release.version_name}.apk"'},
    )

def ios_install(request, release_id, token):
    release = get_object_or_404(Release, pk=release_id)
    _verify_tester_token(token, release)
    # iOS OTA: serve .plist manifest
    ipa_url = release.get_install_url()
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>items</key><array><dict>
    <key>assets</key><array><dict>
      <key>kind</key><string>software-package</string>
      <key>url</key><string>{ipa_url}</string>
    </dict></array>
    <key>metadata</key><dict>
      <key>bundle-identifier</key><string>{release.app.bundle_id}</string>
      <key>bundle-version</key><string>{release.version_name}</string>
      <key>kind</key><string>software</string>
      <key>title</key><string>{release.app.name}</string>
    </dict>
  </dict></array>
</dict></plist>"""
    return HttpResponse(plist, content_type="application/x-apple-aspen-config")
```

**CLI distribution command:**

```bash
ownfb appdistribution:distribute \
  --app myapp \
  --apk build/outputs/apk/debug/app-debug.apk \
  --groups beta-testers,internal-qa \
  --release-notes "Fixed login bug"
```

```python
# ownfb_cli/commands/distribution.py
@app.command()
def distribute(
    app: str, apk: Path, groups: str, release_notes: str = ""
):
    api_url = _load_config()["api"]["url"]
    with open(apk, "rb") as f:
        resp = requests.post(
            f"{api_url}/api/v1/distribution/releases/",
            files={"binary": f},
            data={"app_name": app, "groups": groups, "release_notes": release_notes},
            headers={"Authorization": f"Bearer {_get_token()}"},
        )
    resp.raise_for_status()
    console.print(f"[green]Release uploaded. Tester emails dispatched.[/]")
```

---

### 7. Firebase Studio (formerly Project IDX) — SUNSET March 2027

#### What it was

VS Code running on dedicated Google Cloud VMs (one VM per developer workspace). Launched as Project IDX in 2023, renamed Firebase Studio in April 2025. Shutdown announced March 19, 2026; final shutdown March 22, 2027. Migrate to **Google Antigravity** (agent-first platform) or **Google AI Studio**.

Architecture: VS Code Server (open-source fork) + Nix (`nix-shell`) for reproducible dev environments + QEMU Android emulator + macOS worker pool for iOS simulator + Gemini AI code assistant.

```nix
# idx/dev.nix
{ pkgs, ... }: {
  channel = "stable-23.11";
  packages = [ pkgs.nodejs_20 pkgs.python311 pkgs.google-cloud-sdk ];
  services.firebase.enable = true;
  idx.previews = {
    enable = true;
    previews = {
      web = { command = ["npm" "run" "dev"]; manager = "web"; };
    };
  };
}
```

#### Django Rebuild: Self-Hosted Cloud IDE

Firebase Studio is now defunct; the Django BaaS rebuild should offer a `devcontainer.json` + `docker-compose.yml` that works with any cloud IDE:

**Option 1: Coder (recommended for enterprise/self-hosted)**

```bash
# Install Coder server
curl -fsSL https://coder.com/install.sh | sh
coder server --postgres-url "postgres://..."

# Create workspace template (Terraform)
# workspace spins up Django dev container with full OwnFirebase stack
```

**Option 2: Gitpod (open-source CE, self-hostable)**

```yaml
# .gitpod.yml
image:
  file: .gitpod.Dockerfile

tasks:
  - init: |
      pip install -r requirements.txt
      python manage.py migrate
    command: ownfb emulators:start

ports:
  - port: 8000   # Django API
  - port: 8001   # Django Channels (WebSocket)
  - port: 4000   # Emulator UI
  - port: 9000   # MinIO
```

**Option 3: devcontainer (GitHub Codespaces / VS Code Dev Containers)**

```json
// .devcontainer/devcontainer.json
{
  "name": "OwnFirebase Dev",
  "dockerComposeFile": "../docker-compose.local.yml",
  "service": "django",
  "workspaceFolder": "/app",
  "postStartCommand": "python manage.py migrate && python manage.py createsuperuser --noinput",
  "forwardPorts": [8000, 8001, 4000, 9000, 9001],
  "extensions": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "streetsidesoftware.code-spell-checker"
  ]
}
```

```bash
# CLI command to open IDE
ownfb studio:open --provider codespaces
# Generates a GitHub Codespaces launch URL for the current project
```

---

### 8. Firebase Management API

#### What it does

REST API for programmatic project and app management — used by `firebase init` under the hood and by CI/CD pipelines:

```bash
# List projects
GET https://firebase.googleapis.com/v1beta1/projects

# Register a new web app in a project
POST https://firebase.googleapis.com/v1beta1/projects/{projectId}/webApps
Body: { "displayName": "My Web App" }
# Returns an Operation; poll until done=true

# Get SDK config (the firebaseConfig object)
GET https://firebase.googleapis.com/v1beta1/projects/{projectId}/webApps/{appId}/config
# Returns: { apiKey, authDomain, projectId, storageBucket, messagingSenderId, appId }
```

#### Django Rebuild: Management API + Multi-Tenancy

```bash
pip install django-tenants drf-spectacular
```

```python
# ownfb_management/views.py
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

class ProjectViewSet(ModelViewSet):
    """Equivalent to Firebase Management API /projects endpoints."""
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsAdminSDKClient]
    
    @extend_schema(responses=SdkConfigSerializer)
    @action(detail=True, methods=["get"], url_path="config")
    def sdk_config(self, request, pk=None):
        """Return equivalent of Firebase's firebaseConfig JSON."""
        project = self.get_object()
        return Response({
            "apiUrl": f"https://api.{project.domain}",
            "projectId": str(project.pk),
            "authDomain": project.domain,
            "storageBucket": project.s3_bucket,
            "realtimeUrl": f"wss://ws.{project.domain}",
        })
    
    @action(detail=True, methods=["post"], url_path="apps/web")
    def create_web_app(self, request, pk=None):
        project = self.get_object()
        app = WebApp.objects.create(project=project, **request.data)
        return Response(WebAppSerializer(app).data, status=201)
```

Multi-tenancy strategy:
- **Schema-per-tenant** (`django-tenants`): strongest isolation, each project gets its own PostgreSQL schema.
- **Row-level tenant isolation** (simpler, shared schema): add `project_id` FK to all models, enforce via `get_queryset()` filtering + PostgreSQL RLS.

---

### 9. Client SDKs (Web / iOS / Android / Flutter)

#### What they do

Firebase provides platform-native SDKs that handle: authentication state management, realtime listeners, offline persistence, and typed data access. The Web SDK (v9+) is modular/tree-shakeable:

```typescript
// Firebase Web SDK v9
import { initializeApp } from "firebase/app";
import { getFirestore, collection, onSnapshot, query, where } from "firebase/firestore";
import { getAuth, onAuthStateChanged } from "firebase/auth";

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);

// Realtime listener with offline support
const q = query(collection(db, "posts"), where("authorUid", "==", auth.currentUser.uid));
const unsubscribe = onSnapshot(q, (snapshot) => {
  snapshot.docs.forEach(doc => console.log(doc.id, doc.data()));
});
```

Firebase SDKs provide:
- **Offline persistence**: IndexedDB (web) / SQLite (mobile) local cache; writes queued offline and synced on reconnect.
- **Realtime listeners**: persistent gRPC stream (Firestore) or WebSocket (RTDB) multiplexed over a single connection.
- **Type safety**: Firebase Data Connect (2025) generates typed client SDKs from GraphQL schema.

#### Django Rebuild: Auto-Generated Client SDKs

**Step 1: Generate OpenAPI schema with `drf-spectacular`**

```python
# settings.py
INSTALLED_APPS += ["drf_spectacular"]
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "OwnFirebase API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema")),
]
```

```bash
python manage.py spectacular --color --file openapi.json
```

**Step 2: Generate typed client SDKs**

```bash
# Install openapi-generator-cli
npm install -g @openapitools/openapi-generator-cli

# Generate TypeScript SDK (web)
openapi-generator-cli generate \
  -i openapi.json \
  -g typescript-fetch \
  -o sdk/typescript \
  --additional-properties=npmName=@ownfb/client-js,supportsES6=true

# Generate Dart SDK (Flutter)
openapi-generator-cli generate \
  -i openapi.json \
  -g dart-dio \
  -o sdk/dart \
  --additional-properties=pubName=ownfb_flutter

# Generate Swift SDK (iOS)
openapi-generator-cli generate -i openapi.json -g swift5 -o sdk/swift

# Generate Kotlin SDK (Android)
openapi-generator-cli generate -i openapi.json -g kotlin -o sdk/android
```

**Step 3: Add realtime and offline capabilities**

```typescript
// @ownfb/client-js — generated base + hand-written realtime layer
import { OwnFbClient } from "./generated";
import { RealtimeClient } from "./realtime";

export class OwnFirebase {
  private api: OwnFbClient;
  private ws: RealtimeClient;
  
  constructor(config: OwnFbConfig) {
    this.api = new OwnFbClient({ basePath: config.apiUrl });
    this.ws = new RealtimeClient(config.realtimeUrl);  // Django Channels WS
  }
  
  // Equivalent to onSnapshot() — realtime listener with offline fallback
  onSnapshot(collection: string, query: Query, callback: (docs: Doc[]) => void): () => void {
    // Subscribe via WebSocket
    const sub = this.ws.subscribe(`collection/${collection}`, query, callback);
    
    // Offline: serve from IndexedDB cache if WS unavailable
    this.ws.onDisconnect(() => {
      idb.get(`cache/${collection}`).then(cached => cached && callback(cached));
    });
    
    return () => sub.unsubscribe();
  }
}
```

For **Flutter** offline sync, use `drift` (SQLite ORM):

```dart
// pubspec.yaml: drift: ^2.14.0, drift_flutter: ^0.1.0
// Local SQLite cache with delta sync from OwnFirebase API
class OwnFbRepository {
  final OwnFbApi _api;
  final DriftDatabase _db;
  
  Stream<List<Post>> watchPosts() {
    // Subscribe to local DB changes (instant)
    return _db.watchPosts().asyncMap((cached) {
      // Background sync from API
      _api.getPosts().then((remote) => _db.upsertPosts(remote));
      return cached;
    });
  }
}
```

**CLI command to regenerate SDKs after API changes:**

```bash
ownfb sdk:generate --all          # regenerates all platform SDKs
ownfb sdk:generate --platform ts  # TypeScript only
ownfb sdk:publish --platform ts   # publishes to npm
```

---

### Architecture Summary Table

| Firebase Feature | GCP Backing | Django Equivalent | Key Libraries |
|---|---|---|---|
| Firebase CLI | firebase-tools (Node.js) | `ownfb` CLI (Typer) | typer, django-typer, rich |
| Admin SDK | Service account + IAM + REST APIs | `AdminSDK` class + `X-Admin-Key` | djangorestframework-api-key, PyJWT |
| Emulator Suite | Java JARs + Node.js + Hub | `docker-compose.local.yml` | postgres, redis, minio, mailhog, channels |
| Security Rules | CEL interpreter in Firestore/Storage | django-rules + OPA sidecar + PostgreSQL RLS | rules, drf-rules, opa, django-pgtrigger |
| Test Lab | Cloud Testing API + real devices | Appium Grid + Android Emulator Docker | Appium-Python-Client, pytest-appium |
| App Distribution | GCS + custom install pages | S3/MinIO + Django OTA views | django-storages, django-anymail |
| Firebase Studio | VS Code Server on GCP VMs | Coder / Gitpod / devcontainer | coder, .devcontainer/devcontainer.json |
| Management API | firebase.googleapis.com/v1beta1 | DRF Management API + django-tenants | django-tenants, drf-spectacular |
| Client SDKs | Hand-crafted per-platform | Auto-generated from OpenAPI | drf-spectacular, openapi-generator-cli |

---

### Key Gotchas &amp; Hard Parts

1. **Security Rules query semantics**: Firebase rejects queries unless the rules allow reading every potentially-returned document. Django DRF does NOT enforce this — you must manually mirror permission predicates in `get_queryset()`. Failure to do so creates security holes where a user gets 403 on object access but 200 on list access.

2. **`get()`/`exists()` cross-document lookups**: These synchronous database reads inside rule evaluation are expensive (billed separately in Firebase). In the OPA sidecar approach, equivalent cross-entity lookups require either denormalizing data into OPA's `data` bundle or making synchronous DB queries during policy evaluation — both add latency. Target <50ms OPA decision time.

3. **Emulator state export/import**: Firebase's emulator export captures all service state in a single atomic operation. With docker-compose, you need coordinated `pg_dump` + `redis-cli BGSAVE` + `mc mirror` (MinIO) — these are not atomic and can produce inconsistent snapshots under write load. Use `docker-compose pause` before export.

4. **Admin SDK custom token flow**: Firebase custom tokens are short-lived (1 hour) and must be exchanged for Firebase ID tokens by the client SDK — clients cannot use custom tokens directly for API calls. The Django rebuild must implement the same two-step flow: `create_custom_token()` → client exchanges at `/api/v1/auth/exchange-custom-token/` → server issues standard JWT.

5. **OTA iOS distribution**: HTTPS is mandatory for `itms-services://` install links. Self-hosted distribution requires a valid TLS certificate on the domain serving the `.plist` manifest and IPA. Let's Encrypt works but must be renewed before expiry to avoid breaking existing install links.

6. **Client SDK offline conflicts**: Firebase uses a last-write-wins conflict resolution strategy for Firestore. When implementing offline sync in the auto-generated SDK, you must decide on a conflict resolution strategy (LWW, CRDT, or manual merge) — Firebase hides this complexity. Supabase handles this by relying on PostgreSQL's transactional guarantees; Nhost uses Hasura's event system.

7. **Firebase Studio sunset (March 2027)**: If you were using Firebase Studio as your cloud dev environment, migrate workspaces to Google Antigravity or use the `devcontainer.json` approach for portability across Codespaces, Gitpod, and Coder.

## Community Wisdom & Open-Source Firebase Alternatives

This section aggregates real-world lessons from developer communities (Hacker News, Reddit r/Firebase, r/selfhosted, dev.to, production post-mortems) and performs a deep architectural comparison of every major open-source Firebase clone — Supabase, Appwrite, PocketBase, Parse Platform, Nhost, Convex, and Hasura — extracting concrete patterns to borrow for a self-hosted Django BaaS.

---

### 1. The Firebase Billing Trap: Read Amplification & Cost Horror Stories

**What it is (developer-facing)**

Firebase's Blaze plan charges per Firestore operation — every document read, write, and delete is metered. This sounds reasonable at small scale; it becomes catastrophic at production scale.

**Free-tier limits (Spark plan)**

| Resource | Daily Free Quota |
|---|---|
| Firestore reads | 50,000 |
| Firestore writes | 20,000 |
| Firestore deletes | 20,000 |
| Firestore storage | 1 GB total |
| Firebase Auth MAU | 50,000 (then $0.0055/MAU) |
| Phone SMS auth | 10,000/month (then $0.06/SMS) |

**The read-amplification trap — documented by the community**

The most common trigger for a billing shock is attaching `onSnapshot()` (real-time) listeners to large collections. Every document in the result set is charged on every refresh triggered by any change anywhere in the collection.

The compound pattern that burns teams:

1. Ship a "live feed" screen → attach collection-level listener.
2. Add an AI feature that re-reads the same documents (summarise, classify, extract) — each pipeline pass is a separate read.
3. Multiply by: retries on network flap + reconnects + cold starts.
4. A single user action → dozens of reads. A DoS crawl → unbounded cost.

Real incidents reported on Hacker News (Jan 2025, item #42732714): a developer's Firebase bill, normally $50/month, hit **$70,000 in a single day**. A WebGL games site hit **$100,000 in one day** from a DoS. Firebase has no hard spending cap by default.

**Other documented billing traps**

```
# TRAP 1: Query offsets — skipped docs are still charged
db.collection('logs').offset(1000).limit(10).get()
# → 1,010 document reads billed. Use cursors instead:
db.collection('logs').startAfter(lastDoc).limit(10).get()

# TRAP 2: Composite query without index = full collection scan
db.collection('users').where('country', '==', 'US').where('age', '>', 25).get()
# If the composite index does not exist, Firestore reads ALL users

# TRAP 3: Re-opening listeners on hidden screens
# Screens that are not visible still hold active listeners — every change = billing
```

**Django rebuild — solving the billing trap at the architecture level**

A self-hosted Django BaaS eliminates per-operation billing entirely. You pay for infrastructure (VMs, disk, bandwidth), not per query. Concrete protections:

```python
# settings.py — DRF throttling to prevent DoS-driven cost spikes
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '10000/day',
    }
}

# Use cursor pagination instead of offset pagination (matches Firebase cursor pattern)
from rest_framework.pagination import CursorPagination

class StandardCursorPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'  # Must be a unique, stable field
```

```python
# Install: pip install django-ratelimit djangorestframework
# Nginx upstream rate limiting (infra layer, prevents unbounded traffic)
# limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;
```

**Key lesson for Django BaaS design**: expose flat-rate pricing tiers (e.g., $29/month for X projects, unlimited reads). Never expose per-operation pricing to tenants.

---

### 2. Firebase Vendor Lock-In: The Structural vs. Recoverable Distinction

**What lock-in means in practice**

Firebase's lock-in is *structural*, not incidental:

- **Firestore data format**: proprietary. Export via `gcloud firestore export` produces Avro/LevelDB snapshots. Not standard SQL. Importing into Postgres requires custom transformation.
- **Firebase Auth JWTs**: issued by `securetoken.google.com`, validated against Google's JWKS endpoint. Every client SDK and backend middleware is hardcoded to Google's issuer.
- **Firebase SDKs**: deeply integrated into mobile apps. Migrating off Firebase Auth from a live app requires shipping a new binary, maintaining a **dual-issuer window for 60–90 days** (old binary uses Firebase tokens; new binary uses replacement tokens), and waiting for user adoption to drop below 5% on the old binary before cutting the Firebase validation path.
- **No self-hosting**: Firebase cannot run on your own infrastructure. Data residency is Google Cloud only — a dealbreaker for GDPR, healthcare (HIPAA), finance, and public sector workloads.

**Migration cost from the community**

Teams migrating off Firebase have documented:
- Firestore → PostgreSQL: 2–4 weeks for data migration scripts + schema redesign.
- Firebase Auth → alternative: 60–90 day dual-issuer window + mobile binary rollout.
- Firebase Storage → S3/MinIO: straightforward but requires URL migration in all stored records.
- Firebase Functions → alternative compute: rewrite required (Firestore triggers use Firebase-specific event types).

From r/Firebase and Hacker News: *"The Supabase migration isn't about Firebase breaking. It's about developers wanting SQL, open source, and predictable pricing. Firebase's NoSQL lock-in was acceptable when there was no credible alternative; now there is."*

**Django rebuild — zero structural lock-in**

```python
# Data is in standard Postgres. Export anytime:
# pg_dump -h localhost -U myuser mydb > backup.sql

# JWT tokens are RFC 7519 standard — portable across any issuer
# djangorestframework-simplejwt issues standard HS256/RS256 tokens

# Dual-issuer middleware for migrations FROM Firebase:
import jwt
import requests
from django.conf import settings

class DualIssuerAuthBackend:
    """Accept both Firebase-issued AND local-issued JWTs during migration window."""

    def _validate_firebase_token(self, token):
        FIREBASE_JWKS_URL = 'https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com'
        keys = requests.get(FIREBASE_JWKS_URL).json()
        # validate RS256 token against Google public keys
        return jwt.decode(token, keys, algorithms=['RS256'],
                          audience=settings.FIREBASE_PROJECT_ID)

    def _validate_local_token(self, token):
        from rest_framework_simplejwt.tokens import AccessToken
        return AccessToken(token)
```

```
# pip install djangorestframework-simplejwt python-jose cryptography
```

---

### 3. Supabase Architectural Blueprint — The Primary Reference

Supabase is the most studied Firebase alternative and the clearest blueprint for a Django BaaS. Its architecture is a composition of proven OSS tools behind a Kong API gateway.

**Supabase component map**

```
┌──────────────────────────────────────────────────────┐
│                  Kong (API Gateway)                  │
│         (NGINX-based, Lua, Apache 2.0)               │
└────┬──────┬──────┬──────┬──────┬──────┬─────────────┘
     │      │      │      │      │      │
  GoTrue PostgREST Realtime Storage pg_meta pg_graphql
  (Go)   (Go)    (Elixir) (Go)   (Go)   (pg extension)
     │      │      │       │      │      │
     └──────┴──────┴───────┴──────┴──────┘
                          │
                    PostgreSQL 15+
```

Each component maps directly to a Django BaaS layer:

| Supabase Component | Technology | Django Equivalent |
|---|---|---|
| Kong API Gateway | Lua/NGINX | nginx + gunicorn/uvicorn |
| PostgREST (auto REST) | Go, reads Postgres schema | DRF ModelViewSet + DefaultRouter |
| GoTrue (Auth) | Go, JWTs, stores in Postgres | django-allauth + simplejwt |
| Realtime | Elixir/Phoenix, WAL CDC | Django Channels + Redis + pgoutput |
| Storage | Go, S3-compatible | django-storages + MinIO |
| pg_graphql | Postgres extension | strawberry-graphql-django |
| pg_meta | Go, schema introspection | Django migrations + inspectdb |
| Edge Functions | Deno 2.1 | Celery workers or ASGI views |

**Supabase's PostgREST pattern → DRF auto-router**

PostgREST introspects Postgres schema and serves:
- `GET /tablename` → list with filter params
- `GET /tablename?id=eq.5` → single record
- `POST /tablename` → insert
- `PATCH /tablename?id=eq.5` → update
- `DELETE /tablename?id=eq.5` → delete

Replicate in Django DRF:

```python
# models.py
from django.db import models

class Post(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['-created_at'])]

# serializers.py
from rest_framework import serializers

class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = '__all__'

# views.py
from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.select_related('user').all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'created_at']
    pagination_class = StandardCursorPagination

# urls.py
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'posts', PostViewSet)
urlpatterns = router.urls
```

```
# pip install djangorestframework django-filter drf-spectacular
```

**Supabase's GoTrue pattern → django-allauth + SimpleJWT**

GoTrue stores user identities in a dedicated `auth.users` Postgres table. JWTs contain `sub` (user UUID), `role`, and custom claims. The JWT is passed to every service; Postgres RLS reads it via `current_setting('request.jwt.claims')`.

```python
# settings.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ALGORITHM': 'RS256',          # use RS256 for multi-service environments
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'sub',        # matches Supabase/GoTrue convention
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
```

```
# pip install django-allauth djangorestframework-simplejwt social-auth-app-django
```

**Supabase's Postgres RLS pattern → Django migrations + RLS SQL**

GoTrue + PostgREST + RLS means: the JWT user ID is injected into the Postgres session, and RLS policies enforce that users can only read/write their own rows — enforced at the DB engine, not the application layer.

```python
# Django migration: enable RLS on a table
from django.db import migrations

class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE api_post ENABLE ROW LEVEL SECURITY;

                -- Users can read all posts (public feed)
                CREATE POLICY post_select_policy ON api_post
                    FOR SELECT USING (true);

                -- Users can only INSERT their own posts
                CREATE POLICY post_insert_policy ON api_post
                    FOR INSERT WITH CHECK (
                        user_id = current_setting('app.current_user_id', true)::integer
                    );

                -- Users can only UPDATE/DELETE their own posts
                CREATE POLICY post_modify_policy ON api_post
                    FOR UPDATE USING (
                        user_id = current_setting('app.current_user_id', true)::integer
                    );
            """,
            reverse_sql="ALTER TABLE api_post DISABLE ROW LEVEL SECURITY;"
        )
    ]
```

```python
# middleware.py — inject user_id into Postgres session variable
from django.db import connection

class PostgresRLSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.current_user_id = %s",
                    [request.user.id]
                )
        return self.get_response(request)
```

---

### 4. Supabase Realtime → Django Channels + PostgreSQL WAL

**How Supabase Realtime works under the hood**

Supabase Realtime is a globally distributed Elixir/Phoenix cluster. Three capabilities:

1. **Broadcast** — ephemeral pub/sub messages between clients (low latency, not persisted)
2. **Presence** — CRDT-based online user tracking (who is in this channel right now)
3. **Postgres Changes** — WAL logical decoding: Postgres writes to the WAL, Realtime's replication slot consumes `pgoutput` messages, checks RLS per subscriber, and forwards matching events over WebSocket

```
Postgres WAL (pgoutput) → Elixir GenServer → RLS check → Phoenix Channel → Client WebSocket
```

The RLS check is critical: before forwarding a row change to a subscriber, Realtime runs a Postgres query as that subscriber's role to verify they have SELECT permission. Single-threaded to preserve change ordering.

**Django Channels equivalent**

```python
# pip install channels channels-redis daphne

# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import myapp.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(myapp.routing.websocket_urlpatterns)
    ),
})

# consumers.py — table-change consumer (Postgres Changes equivalent)
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class TableSubscriptionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.table = self.scope['url_route']['kwargs']['table']
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Group name: changes to a specific table for this user
        # Scope tightly — never subscribe to all-table groups for all users
        self.group_name = f"table_{self.table}_user_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def table_change(self, event):
        """Called when a DB change is pushed to this group."""
        await self.send(text_data=json.dumps({
            'type': event['change_type'],  # INSERT / UPDATE / DELETE
            'table': event['table'],
            'record': event['record'],
        }))

    async def receive(self, text_data):
        pass  # Client-to-server messages handled elsewhere
```

**Postgres WAL consumer (the Realtime equivalent process)**

```python
# management/commands/wal_consumer.py
# pip install psycopg2-binary

import asyncio
import json
from django.core.management.base import BaseCommand
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import psycopg2
import psycopg2.extras
import select

class Command(BaseCommand):
    help = "Listen to Postgres NOTIFY events and broadcast to Channels"

    def handle(self, *args, **kwargs):
        """
        Strategy: use pg_notify from triggers (simpler than full WAL decoding).
        For production WAL decoding, use python-pglast or logical replication.
        """
        conn = psycopg2.connect(dsn="postgresql://user:pass@localhost/dbname")
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        curs = conn.cursor()
        curs.execute("LISTEN table_changes;")

        channel_layer = get_channel_layer()
        self.stdout.write("WAL consumer started, listening for changes...")

        while True:
            if select.select([conn], [], [], 5) == ([], [], []):
                continue
            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop(0)
                payload = json.loads(notify.payload)
                table = payload['table']
                user_id = payload.get('user_id')
                group_name = f"table_{table}_user_{user_id}"

                # Push to Channels group
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'table_change',
                        'change_type': payload['action'],
                        'table': table,
                        'record': payload['record'],
                    }
                )
```

```sql
-- Postgres trigger that calls pg_notify (replaces WAL decoding for most use cases)
CREATE OR REPLACE FUNCTION notify_table_change()
RETURNS TRIGGER AS $$
DECLARE
  payload JSON;
BEGIN
  payload = json_build_object(
    'table', TG_TABLE_NAME,
    'action', TG_OP,
    'user_id', NEW.user_id,
    'record', row_to_json(NEW)
  );
  PERFORM pg_notify('table_changes', payload::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER post_change_trigger
  AFTER INSERT OR UPDATE OR DELETE ON api_post
  FOR EACH ROW EXECUTE FUNCTION notify_table_change();
```

```
# pip install channels channels-redis django-pgpubsub
# django-pgpubsub: pip install django-pgpubsub
# (wraps pg_notify/LISTEN in a Django-idiomatic interface)
```

**Presence (online user tracking)**

```python
# consumers.py — Presence consumer
class PresenceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room = self.scope['url_route']['kwargs']['room']
        self.group_name = f"presence_{self.room}"
        self.user = self.scope['user']

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Announce join
        await self.channel_layer.group_send(self.group_name, {
            'type': 'presence_join',
            'user_id': str(self.user.id),
            'username': self.user.username,
        })

    async def disconnect(self, code):
        await self.channel_layer.group_send(self.group_name, {
            'type': 'presence_leave',
            'user_id': str(self.user.id),
        })
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def presence_join(self, event):
        await self.send(text_data=json.dumps({'event': 'join', **event}))

    async def presence_leave(self, event):
        await self.send(text_data=json.dumps({'event': 'leave', **event}))
```

**Settings (channel layer)**

```python
# settings.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("redis", 6379)]},
    }
}
```

---

### 5. Appwrite Microservices Architecture — Self-Hosting Pattern

**What Appwrite does**

Appwrite (PHP/Go, BSD-3, github.com/appwrite/appwrite) is the most production-complete self-hosted Firebase clone. It ships as a Docker Compose stack covering: auth (30+ OAuth2 providers), document databases (MariaDB backend), storage (encryption + image transforms), serverless functions (30+ runtimes), WebSocket realtime, and push/email/SMS messaging.

**Container topology (from Docker Compose)**

```
┌────────────────────────────────────────────────────────────────┐
│  Traefik (reverse proxy / TLS)                                 │
└──────────────────────┬─────────────────────────────────────────┘
                       │
    ┌──────────────────┼──────────────────────┐
    │                  │                      │
appwrite (PHP API)  appwrite-realtime    appwrite-console
    │                  │                      │
    ├── MariaDB (documents / collections)      │
    ├── Redis (task queues + cache)            │
    ├── InfluxDB (metrics / usage stats)       │
    └── Telegraf (metrics collector)           │
                                               │
appwrite-worker-audits  appwrite-worker-functions
appwrite-worker-builds  appwrite-worker-mails
appwrite-worker-databases appwrite-worker-messaging
```

Each worker is a separate container processing a specific Celery-equivalent queue. This enables **independent scaling** — scale the functions worker without touching the database worker.

**Django equivalent Docker Compose pattern**

```yaml
# docker-compose.yml
version: "3.9"
services:
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    depends_on: [web]

  web:
    build: .
    command: gunicorn myproject.asgi:application -k uvicorn.workers.UvicornWorker -w 4
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/mydb
      - REDIS_URL=redis://redis:6379/0
    depends_on: [postgres, redis]

  asgi:
    build: .
    command: daphne -b 0.0.0.0 -p 8001 myproject.asgi:application
    depends_on: [redis]

  worker-default:
    build: .
    command: celery -A myproject worker -Q default -c 4

  worker-email:
    build: .
    command: celery -A myproject worker -Q emails -c 2

  worker-storage:
    build: .
    command: celery -A myproject worker -Q storage -c 2

  wal-consumer:
    build: .
    command: python manage.py wal_consumer

  beat:
    build: .
    command: celery -A myproject beat -l info

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes: [minio_data:/data]

volumes:
  pgdata:
  minio_data:
```

**Appwrite's permission system → Django guardian + DRF**

Appwrite uses per-collection permissions (role → create/read/update/delete), configurable without code via its admin console. In Django:

```python
# pip install django-guardian

# Object-level permissions
from guardian.shortcuts import assign_perm

def create_document(user, collection, data):
    doc = Document.objects.create(collection=collection, data=data, owner=user)
    assign_perm('view_document', user, doc)
    assign_perm('change_document', user, doc)
    assign_perm('delete_document', user, doc)
    return doc

# DRF view with object-level permission
from guardian.rest_framework import ObjectPermissionMixin

class DocumentViewSet(ObjectPermissionMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, DjangoObjectPermissions]
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
```

---

### 6. PocketBase — Single-Binary Pattern

**What PocketBase does and why it matters**

PocketBase (Go, MIT) ships as a ~15 MB executable: embedded SQLite, auto-generated REST + WebSocket API, auth, file storage, and an admin dashboard — zero dependencies, deployable on a $5 VPS. Its API Rules system (per-collection filter expressions) is the simplest approximation of Firebase Security Rules.

```
# PocketBase API rule example
listRule: "@request.auth.id != ''"      # must be authenticated
viewRule: "@request.auth.id != ''"
createRule: "@request.auth.id != ''"
updateRule: "user.id = @request.auth.id" # own records only
deleteRule: "user.id = @request.auth.id"
```

**Django BaaS equivalent (minimal single-server)**

For small/internal deployments, Django with SQLite closely mirrors PocketBase:

```python
# settings.py — SQLite single-file for small deploys
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# dj-database-url for easy DATABASE_URL switching
# pip install dj-database-url
import dj_database_url
DATABASES['default'] = dj_database_url.config(
    default='sqlite:///db.sqlite3',
    conn_max_age=600
)
```

PocketBase's admin UI = Django admin. PocketBase's auto-REST = DRF router. PocketBase's API Rules = DRF `get_queryset()` filtering + `permission_classes`.

**Critical caveat**: PocketBase uses SQLite which cannot horizontally scale. Django's Postgres backend does — switch `DATABASE_URL` and nothing else changes. **Do not use SQLite in production for a multi-tenant BaaS**.

---

### 7. Parse Platform — The Mature OSS Pattern

**What Parse does**

Parse Server (Node.js/Express, MIT, github.com/parse-community/parse-server) is the most battle-tested self-hosted BaaS, originally open-sourced by Facebook in 2016. Backed by MongoDB or PostgreSQL. Provides:

- REST + GraphQL APIs (auto-generated from schema)
- Cloud Code (server-side JS hooks on beforeSave/afterSave)
- Live Queries (WebSocket subscriptions to any query)
- Push notifications (APNs/FCM)
- Parse Dashboard (admin UI)
- Cross-platform SDKs (JS, iOS, Android, .NET)

**Django feature parity map**

| Parse Feature | Django Equivalent |
|---|---|
| Cloud Code `beforeSave` | `pre_save` signal or model `save()` override |
| Cloud Code `afterSave` | `post_save` signal → Celery task |
| Live Queries | Django Channels + pg_notify |
| Parse Schema (dynamic) | Django migrations (explicit) |
| Parse Dashboard | Django Admin |
| REST API | DRF ModelViewSet |
| GraphQL | strawberry-graphql-django |
| Push | django-push-notifications (pip) |

```python
# Parse beforeSave equivalent in Django
from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=Post)
def before_post_save(sender, instance, **kwargs):
    """Equivalent to Parse Cloud Code beforeSave hook."""
    if not instance.slug:
        instance.slug = slugify(instance.title)
    # Run validation, sanitisation, business logic
```

```python
# Parse Live Query equivalent
# pip install channels django-pgpubsub

# Client subscribes to a query:
# ws://mybaas.com/ws/query/posts/?user_id=42
# Server streams INSERT/UPDATE/DELETE events matching that filter

# routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/query/(?P<table>\w+)/$', consumers.QuerySubscriptionConsumer.as_asgi()),
]
```

**Parse's key lesson**: Cloud Code (server-side hooks on every DB event) is one of Parse's most loved features. Django signals + Celery reproduce this exactly. The architectural lesson: **treat every model save as an event bus entry point**.

---

### 8. Nhost — GraphQL-First Postgres BaaS (Hasura Stack)

**What Nhost does**

Nhost = Hasura (GraphQL engine) + GoTrue (auth) + nhost-storage (S3) + nhost-functions (Node.js) all pre-wired over PostgreSQL. It is Supabase's main competitor for teams that prefer GraphQL over REST. Self-hostable via Docker. Real-time via Hasura GraphQL subscriptions (long-poll or WebSocket).

**Django BaaS with GraphQL via Strawberry**

```python
# pip install strawberry-graphql-django channels

# schema.py
import strawberry
import strawberry_django
from strawberry_django import auto

@strawberry_django.type(Post)
class PostType:
    id: auto
    title: auto
    body: auto
    created_at: auto

@strawberry.type
class Query:
    posts: list[PostType] = strawberry_django.field()

    @strawberry_django.field
    def post(self, id: int) -> PostType:
        return Post.objects.get(id=id)

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def post_created(self) -> PostType:
        # Subscribe via Channels / Redis pub-sub
        async with channel_layer.subscribe("post_created") as messages:
            async for message in messages:
                yield Post(**message['data'])

schema = strawberry.Schema(query=Query, subscription=Subscription)

# urls.py
from strawberry.django.views import AsyncGraphQLView
urlpatterns += [path("graphql/", AsyncGraphQLView.as_view(schema=schema))]
```

**Nhost/Hasura lesson for Django BaaS**: GraphQL subscriptions over WebSocket are the cleanest API for real-time data. Consider offering both REST (DRF) and GraphQL (Strawberry) from the same Django app — they can share the same Postgres queries.

---

### 9. Hasura — Permissions Model & Event Triggers

**Hasura's key architectural innovations**

1. **Schema-introspected GraphQL** — same idea as PostgREST but for GraphQL: auto-generate queries, mutations, subscriptions from Postgres schema.
2. **Role-based permissions translated to SQL WHERE clauses** — permission rules are JSON that Hasura compiles into SQL predicates before executing. Never returns rows the user cannot see, even in batch mutations.
3. **Event Triggers** — Postgres triggers capture DML events → Hasura queues them → HTTP POST to any webhook, with at-least-once delivery and horizontal scalability.

**Replicating Hasura Event Triggers in Django**

```python
# models.py — event trigger equivalent
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
import httpx

class WebhookEndpoint(models.Model):
    """Let tenants register webhooks — just like Hasura Event Triggers."""
    table = models.CharField(max_length=100)
    events = models.JSONField(default=list)  # ['INSERT', 'UPDATE', 'DELETE']
    url = models.URLField()
    headers = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

@receiver(post_save)
def dispatch_webhook(sender, instance, created, **kwargs):
    """Generic post_save dispatcher — replicates Hasura Event Triggers."""
    table_name = sender._meta.db_table
    event = 'INSERT' if created else 'UPDATE'

    endpoints = WebhookEndpoint.objects.filter(
        table=table_name, is_active=True
    ).filter(events__contains=[event])

    for endpoint in endpoints:
        # Dispatch async via Celery for at-least-once delivery
        deliver_webhook.apply_async(
            args=[endpoint.id, {
                'table': table_name,
                'event': event,
                'record': {'id': instance.pk},
                'timestamp': instance.updated_at.isoformat() if hasattr(instance, 'updated_at') else None,
            }],
            retry=True,
            retry_policy={'max_retries': 5, 'interval_start': 1, 'interval_step': 2}
        )

# tasks.py
from celery import shared_task

@shared_task(bind=True, max_retries=5)
def deliver_webhook(self, endpoint_id, payload):
    endpoint = WebhookEndpoint.objects.get(id=endpoint_id)
    try:
        resp = httpx.post(endpoint.url, json=payload,
                          headers=endpoint.headers, timeout=10.0)
        resp.raise_for_status()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

```
# pip install celery httpx
```

**Hasura RLS lesson**: Hasura translates permission rules to SQL predicates that run inside Postgres — not in application code. This is the most secure pattern. Django's equivalent is Postgres RLS (Section 3 above). **Application-layer filtering is not sufficient for a multi-tenant BaaS** — rows can leak through joins, aggregates, and raw SQL if RLS is not enforced at the DB layer.

---

### 10. Convex — Reactive Query Invalidation Model

**What Convex does architecturally**

Convex (open-sourced 2024, github.com/get-convex/convex-backend) collapses database + API server + cache into a single reactive runtime. Backend logic is TypeScript queries/mutations executed inside the Convex database engine. The engine tracks which documents each query function reads. Any mutation that touches those documents marks the query dirty and pushes a diff (not the full result set) to all subscribed clients. No manual cache invalidation. ACID transactions.

| Layer | Traditional | Convex |
|---|---|---|
| Data | Separate DB | Integrated document store |
| API | Separate server | TypeScript queries/mutations in DB |
| Cache | Redis/Memcached | Built-in reactive cache |
| Real-time | Manual WebSocket logic | Auto-invalidation by dependency tracking |

**Django BaaS equivalent: WAL-driven reactive cache**

```python
# The core insight from Convex: track what each "query" (view/endpoint) reads,
# and invalidate its cached result when any of those rows change.

# Step 1: cache DRF viewset responses with cache key = query fingerprint
from django.core.cache import cache
from rest_framework.response import Response

class ReactiveCachedViewSet(viewsets.ReadOnlyModelViewSet):
    def list(self, request, *args, **kwargs):
        # Cache key includes filters + user identity
        cache_key = f"posts:list:{request.user.id}:{request.query_params.urlencode()}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        cache.set(cache_key, serializer.data, timeout=60)

        # Register this cache key as dependent on 'api_post' table
        cache.sadd(f"table_deps:api_post", cache_key)  # Redis SADD
        return Response(serializer.data)

# Step 2: On pg_notify (post_save), invalidate all registered cache keys
# In wal_consumer.py:
def invalidate_reactive_cache(table):
    keys = cache.smembers(f"table_deps:{table}")
    for key in keys:
        cache.delete(key)
    # Push WebSocket notification to subscribed clients
    channel_layer.group_send(f"table_{table}", {'type': 'cache_invalidated'})
```

```
# pip install django-redis channels
```

This is a pragmatic approximation of Convex's reactive model using standard Django primitives.

---

### 11. Firebase Security Rules → Postgres RLS

**Firebase Security Rules (what they do)**

Firebase Security Rules are a custom DSL that runs server-side on every Firestore read/write:

```javascript
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /posts/{postId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null
                   && request.auth.uid == resource.data.userId;
      allow create: if request.auth != null
                    && request.resource.data.userId == request.auth.uid;
    }
  }
}
```

**Postgres RLS equivalent (enforced at the DB engine — same security guarantee)**

```sql
-- Migration SQL (put in Django RunSQL migration)
ALTER TABLE api_post ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_post FORCE ROW LEVEL SECURITY;  -- applies to table owner too

-- Anyone authenticated can read posts
CREATE POLICY post_read ON api_post
    FOR SELECT
    USING (current_setting('app.current_user_id', true) IS NOT NULL);

-- Users can only write their own posts
CREATE POLICY post_write ON api_post
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true)::integer)
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);

-- Grant the Django DB user restricted access (no SUPERUSER bypass of RLS)
GRANT SELECT, INSERT, UPDATE, DELETE ON api_post TO django_app_user;
```

**firebase-admin SDK equivalent (bypass security rules for admin operations)**

```python
# In Django: use a separate database connection role that bypasses RLS
# (equivalent to Firebase Admin SDK which bypasses Security Rules)

from django.db import connections

def admin_operation(user_id, data):
    """Bypass RLS for admin operations — use sparingly."""
    with connections['admin'].cursor() as cursor:  # 'admin' role = BYPASSRLS in Postgres
        cursor.execute("INSERT INTO api_post (user_id, data) VALUES (%s, %s)",
                       [user_id, data])
```

---

### 12. Firebase Auth Migration Path → Django

**The 11 critical checks (from production migrations 2025–2026)**

Documented by teams migrating off Firebase Auth at scale:

| Check | Firebase Behaviour | Django Action |
|---|---|---|
| JWT issuer | `securetoken.google.com` | simplejwt — configure your own issuer |
| JWKS endpoint | Google-hosted public keys | Serve `/well-known/jwks.json` from Django |
| Phone SMS billing | $0.06/SMS after 10K/month | Twilio/Vonage direct — cheaper at volume |
| Passkey (WebAuthn) | Not natively supported | `django-passkeys` (pip) or `py_webauthn` |
| SAML / enterprise SSO | Not available in Firebase Auth | `django-saml2-auth` (pip) |
| Dual-issuer window | Must maintain for 60–90 days | Middleware that validates both token types |
| Mobile SDK swap | Requires app store review + rollout | Plan 90-day window; monitor old binary MAU |
| Custom claims | Supported via Admin SDK | `SIMPLE_JWT['AUTH_TOKEN_CLASSES']` custom payload |
| Anonymous auth | Supported | `django-guest-user` (pip) |
| Email enumeration protection | Built-in | Configure `django-allauth` `PREVENT_ENUMERATION=True` |
| App Check (abuse prevention) | Firebase-specific | `django-ratelimit` + `django-captcha` |

```python
# Dual-issuer middleware (critical for Firebase → Django migration)
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import httpx
import jwt as pyjwt

class DualIssuerAuthentication(BaseAuthentication):
    """Accepts Firebase JWTs (old mobile binary) OR local simplejwt tokens."""

    FIREBASE_CERTS_URL = (
        "https://www.googleapis.com/robot/v1/metadata/x509/"
        "securetoken@system.gserviceaccount.com"
    )

    def authenticate(self, request):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return None
        token = header[7:]

        # Try local JWT first (fast path)
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication
            return JWTAuthentication().authenticate(request)
        except Exception:
            pass

        # Fall back to Firebase JWT validation (migration period only)
        if getattr(settings, 'ACCEPT_FIREBASE_JWT', False):
            try:
                certs = httpx.get(self.FIREBASE_CERTS_URL).json()
                payload = pyjwt.decode(
                    token, certs,
                    algorithms=['RS256'],
                    audience=settings.FIREBASE_PROJECT_ID
                )
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user, _ = User.objects.get_or_create(
                    firebase_uid=payload['sub'],
                    defaults={'email': payload.get('email', '')}
                )
                return (user, token)
            except Exception:
                raise AuthenticationFailed('Invalid token')
        return None
```

```
# pip install djangorestframework-simplejwt pyjwt httpx cryptography
# pip install django-passkeys  # for WebAuthn/passkey support
# pip install django-saml2-auth  # for SAML enterprise SSO
```

---

### 13. Firebase Offline Persistence → Client-Side SDK Strategy

**What Firebase does**

Firestore SDK caches all read documents in IndexedDB (web) or LevelDB (mobile). Queries are served from cache when offline. Pending writes are queued and synced on reconnect. Enabled with one call:

```javascript
// Firebase offline persistence (web)
import { enableIndexedDbPersistence } from 'firebase/firestore';
await enableIndexedDbPersistence(db);
```

**This is a client SDK concern — not a server concern.** The Django BaaS server cannot provide this; the client library must. Strategy:

```typescript
// client/baas-sdk.ts — Django BaaS client with offline support
import Dexie, { Table } from 'dexie';  // npm install dexie

class BaaSDatabase extends Dexie {
    posts!: Table<Post>;
    pendingWrites!: Table<PendingWrite>;

    constructor() {
        super('BaaSOfflineCache');
        this.version(1).stores({
            posts: '++id, user_id, created_at',
            pendingWrites: '++id, table, action, payload, timestamp',
        });
    }
}

const db = new BaaSDatabase();

// Read-through cache: IndexedDB → Django API
async function getPosts(userId: string): Promise<Post[]> {
    try {
        const resp = await fetch(`/api/posts/?user_id=${userId}`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        const posts = await resp.json();
        await db.posts.bulkPut(posts.results);  // update IndexedDB cache
        return posts.results;
    } catch (e) {
        // Offline: serve from IndexedDB
        return db.posts.where('user_id').equals(userId).toArray();
    }
}

// Write-through with offline queue
async function createPost(payload: Partial<Post>): Promise<void> {
    try {
        await fetch('/api/posts/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
            body: JSON.stringify(payload),
        });
    } catch (e) {
        // Queue for later sync
        await db.pendingWrites.add({
            table: 'posts', action: 'CREATE',
            payload, timestamp: new Date().toISOString()
        });
    }
}

// Sync pending writes on reconnect
window.addEventListener('online', async () => {
    const pending = await db.pendingWrites.toArray();
    for (const write of pending) {
        await fetch(`/api/${write.table}/`, {
            method: write.action === 'CREATE' ? 'POST' : 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(write.payload),
        });
        await db.pendingWrites.delete(write.id!);
    }
});
```

**Gotcha**: Firebase's offline sync handles conflict resolution automatically (last-write-wins). A Django BaaS needs an explicit conflict resolution strategy. Recommended: include a `version` or `updated_at` field in all models and use optimistic locking:

```python
# Optimistic locking on update
class PostViewSet(viewsets.ModelViewSet):
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        client_version = request.data.get('version')
        if client_version and instance.version != client_version:
            return Response(
                {'error': 'Conflict', 'server_version': instance.version},
                status=409
            )
        return super().update(request, *args, **kwargs)
```

---

### 14. OSS Alternatives Feature Matrix

Summary comparison for Django BaaS architectural decisions:

| Platform | DB | API | Real-time | Auth | Storage | Self-host | License | Lesson to borrow |
|---|---|---|---|---|---|---|---|---|
| **Supabase** | PostgreSQL | PostgREST (auto REST) | Elixir WAL CDC | GoTrue (Go) | S3-compat (Go) | Docker/K8s | Apache 2.0 | RLS + PostgREST DX |
| **Appwrite** | MariaDB | PHP REST | WebSocket (Go) | Built-in PHP | PHP + transforms | Docker Compose | BSD-3 | Worker queue separation |
| **PocketBase** | SQLite | Go REST | Go WebSocket | Embedded | Embedded | Single binary | MIT | API Rules DSL |
| **Parse Server** | MongoDB/PG | Node.js REST+GQL | Node.js LiveQuery | Parse Auth | Parse Storage | Node.js + Docker | MIT | Cloud Code hooks |
| **Nhost** | PostgreSQL | Hasura GraphQL | GraphQL subscriptions | GoTrue | nhost-storage | Docker | MIT | GraphQL-first pattern |
| **Hasura** | PostgreSQL | GraphQL engine | GraphQL subscriptions | External | External | Docker | Apache 2.0 | Event Triggers + RLS |
| **Convex** | Document | TypeScript fns | Reactive push | External | External | Yes (2024) | Apache 2.0 | Reactive invalidation |
| **Django BaaS** | **PostgreSQL** | **DRF ViewSets** | **Channels+Redis** | **allauth+simplejwt** | **django-storages+MinIO** | **Docker Compose** | **Your license** | All of the above |

---

### 15. Community-Documented Pitfalls: What NOT to Do

Aggregated from r/Firebase, r/selfhosted, Hacker News, and dev.to (2024–2026):

**Firebase pitfalls to explicitly avoid in the Django BaaS design**

```
❌ Per-operation billing           → ✅ Flat-rate infra pricing
❌ No spending cap by default      → ✅ Rate limiting at nginx + DRF throttle
❌ Collection-wide listeners       → ✅ Row-scoped WebSocket groups
❌ Query offsets = charged scans   → ✅ Cursor pagination (CursorPagination)
❌ Missing index = full scan       → ✅ Mandatory index in Meta + django-silk alerts
❌ Client SDK reads same doc 3x    → ✅ select_related / prefetch_related
❌ NoSQL → denormalised hell       → ✅ PostgreSQL with proper relations
❌ No self-hosting                 → ✅ Docker Compose single-command deploy
❌ No data export                  → ✅ pg_dump always available
❌ Auth lock-in to Google issuer   → ✅ Standard RFC 7519 JWT from simplejwt
❌ No SAML / passkeys / WebAuthn   → ✅ django-saml2-auth + django-passkeys
❌ Firebase rules DSL (new syntax) → ✅ Standard SQL RLS (every DBA knows it)
❌ Cold starts 500ms–2s            → ✅ Persistent gunicorn workers, ~0ms cold start
```

**Appwrite pitfall**: MariaDB as the document store creates impedance mismatch for relational queries. Django's ORM on Postgres has no such problem.

**PocketBase pitfall**: SQLite cannot horizontally scale. Django on Postgres can add read replicas (`DATABASE_ROUTERS`), connection pooling (PgBouncer), and partitioning without changing application code.

**Supabase pitfall**: PostgREST's RLS check happens in the database but Supabase's Realtime WAL consumer must also perform RLS checks before forwarding events — a single-threaded bottleneck. Django Channels avoids this by putting users into per-object groups at subscribe time — no per-event RLS check needed.

**Convex pitfall**: Reactive query tracking creates overhead proportional to the number of unique queries. Django's approach (pg_notify + group-scoped Channels) is simpler and scales better because the server does not need to track per-client query dependencies.

---

### Key Packages Summary

```
# Core BaaS stack
django>=5.1
djangorestframework>=3.16
django-filter
drf-spectacular         # OpenAPI schema auto-generation (PostgREST DX)
django-cors-headers

# Auth
django-allauth
djangorestframework-simplejwt
social-auth-app-django
django-passkeys         # WebAuthn/passkey support
django-saml2-auth       # Enterprise SAML SSO
python-jose             # JWKS / Firebase JWT validation during migration
cryptography

# Real-time (Supabase Realtime equivalent)
channels
channels-redis
daphne
django-pgpubsub         # pg_notify/LISTEN wrapper

# Storage (Supabase Storage equivalent)
django-storages
boto3                   # S3/MinIO backend

# Task queues (Appwrite worker pattern)
celery
django-celery-beat
redis

# Database & performance
psycopg2-binary
django-redis            # Redis cache backend
django-silk             # Query profiling (prevent N+1 / missing indexes)
django-debug-toolbar

# Security
django-ratelimit        # DDoS/billing-spike protection
django-guardian         # Object-level permissions (Appwrite permissions model)
django-rules            # Predicate-based permissions

# Offline-first (client SDK, not server)
# npm: dexie, idb, workbox

# Observability
django-prometheus
sentry-sdk
```

## Build Roadmap

A pragmatic, dependency-ordered plan. Each phase is shippable on its own.

### Phase 0 — Foundation (1–2 weeks)
- `docker-compose` with Postgres + Redis + Django + MinIO.
- Multi-tenant **project** model, project API keys, base settings, CI.
- Typer **CLI** skeleton (`own init`, `own up`, `own deploy`).

### Phase 1 — MVP: Auth + Data + Auto-API (3–5 weeks)  ← *the core "Firebase"*
- **Auth service**: email/password, JWT (simplejwt), refresh tokens, custom claims, social login (allauth), MFA.
- **Data API**: Firestore-style collections as JSONB tables, DRF auto-CRUD, query params (`where/orderBy/limit`), transactions, server timestamps.
- **Security Rules**: Postgres RLS + a declarative policy layer (`request.auth` analog).
- **Auto-generated JS client SDK** from OpenAPI.

### Phase 2 — Realtime + Storage (3–4 weeks)
- **Realtime service**: Channels + Redis, per-query/document WebSocket subscriptions, Postgres `LISTEN/NOTIFY` change capture, presence + `onDisconnect`.
- Offline queue + last-write-wins conflict handling in the SDK.
- **Storage service**: MinIO + presigned/resumable uploads, rules-gated access, image-resize worker.

### Phase 3 — Compute + Messaging (3–4 weeks)
- **Functions/Tasks**: Celery + Beat, HTTP/callable endpoints, DB-trigger event bus (signals → Redis stream), schedules.
- **Push**: FCM v1 + APNs + web push, topics, notification composer; in-app messaging campaigns.

### Phase 4 — Observability + Engagement (2–4 weeks)
- **Analytics** ingest → ClickHouse + dashboards; **Crashlytics** via Sentry; **Performance** via OpenTelemetry/Prometheus.
- **Remote Config + A/B testing** via Flagsmith; deep links (App/Universal Links — Dynamic Links is dead).

### Phase 5 — AI + Polish (ongoing)
- **AI proxy**: server-protected Claude/Gemini access, App-Check-style attestation, `pgvector` RAG, a Genkit-like flow runner.
- **Admin Console** (React), generated SDKs for Dart/Swift/Kotlin, full **local emulator** parity, hosted dev environment, beta-distribution CI.

### Effort & sequencing notes
- **Build Phase 1 first and ship it** — auth + data + rules is 80% of Firebase's value and unblocks every client.
- Realtime (Phase 2) is the hardest engineering; study **Supabase Realtime** and **PocketBase** before building.
- Borrow architecture liberally: **Supabase** = Postgres + PostgREST + GoTrue + Realtime + Storage (closest blueprint); **Appwrite** = containerised services; **PocketBase** = single-binary simplicity.


---

_Generated by a 14-agent parallel research workflow (13 Firebase-service researchers + 1 community/OSS-alternatives deep dive) plus an authored architecture synthesis. Sections recovered from the workflow journal; master mapping table auto-built from 190 mapped features across 14 clusters._