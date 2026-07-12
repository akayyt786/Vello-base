# Migrating from Google Firebase to OwnFirebase

This guide is for a developer who currently uses real Google Firebase (Firestore, Firebase Auth,
Cloud Storage, Cloud Functions, Realtime listeners, FCM, Remote Config, Crashlytics, A/B Testing,
App Check) and wants to move to a self-hosted **OwnFirebase** instance.

Every claim below was checked against the actual Django source in this repository (models, views,
serializers, urls) and the actual SDK source in `sdk/src` (TypeScript — used as the primary worked
example) as of this snapshot. Where OwnFirebase's behavior genuinely differs from Firebase's, that
is called out explicitly rather than glossed over. Where something could not be fully verified,
that is stated too — **verify against your own running instance before shipping**.

> **Primary SDK used in examples:** `sdk/src` (TypeScript/JavaScript), imported as
> `OwnFirebaseClient` subclasses (`AuthSDK`, `DataSDK`, `StorageSDK`, `FunctionsSDK`,
> `RealtimeSDK`, `RemoteConfigSDK`, `ABTestingSDK`, `PushSDK`, `CrashlyticsSDK`, `AppCheckSDK`).
> The Kotlin (`sdk/kotlin-sdk`), Swift (`sdk/swift-sdk`), and Dart (`sdk/dart-sdk`) SDKs mirror the
> same class names and method signatures method-for-method — the patterns below translate directly.
> **The Python SDK (`sdk/python-sdk`) does not currently follow this pattern** — see the callout
> near the end of this doc before relying on it.

---

## 0. Known SDK/backend contract mismatches found during this audit

Before the worked examples: several convenience methods in the client SDKs send a different field
name, HTTP method, or URL than what the real Django endpoint expects, so calling them as documented
in the SDK's own doc-comments will currently fail (400/404/405) against this backend. These were
found by reading the SDK source side-by-side with the real DRF serializers/views. Where this
applies, the section below shows the **verified raw REST contract** instead of the broken
convenience wrapper, and flags the mismatch so you can decide whether to patch the SDK or call
`fetch`/`request()` directly in the meantime.

| Area | SDK method | What SDK sends | What the backend actually expects |
|---|---|---|---|
| Realtime | `RealtimeSDK.connect()` | `ws(s)://…/ws/realtime/{projectId}/` | `realtime/routing.py` mounts the consumer at `/ws/v1/projects/{project_id}/listen/` — different path entirely |
| Storage | `StorageSDK.upload()` / `confirmUpload()` | `{ filename, content_type, path }` then `{ object_key }` | `UploadRequestSerializer` requires `path` + `content_type` (no `filename` field) and returns `file_id`; `ConfirmUploadSerializer` requires `{ file_id }`, not `object_key` |
| Functions | `FunctionsSDK.updateFunction()` | `PATCH` | `FunctionDetailView` only implements `get`/`put`/`delete` — no `patch` handler, so this 405s |
| Functions | `FunctionsSDK.invoke()` | `{ payload: {...} }` | `InvokeSerializer` reads `data`, not `payload` — the real payload is silently dropped |
| Push | `PushSDK` platform type | `'ios' \| 'android' \| 'web'` | `DeviceToken.PLATFORM_CHOICES` is `'fcm' \| 'apns' \| 'web'` |
| Push | `PushSDK.subscribeTopic()` | `POST push/topics/{id}/` with `{ action: 'subscribe' }` | Real action endpoint is `POST push/topics/{id}/subscribe/` with `{ device_token_id }` |
| Push | `PushSDK.sendToDevice/sendToTopic()` | `{ target_type, target_id, ... }` | `PushNotificationSerializer` expects `{ device_token: <uuid> }` or `{ topic: <uuid> }` |
| App Check | `AppCheckSDK.exchangeToken()` | `POST app-check/` with `{ provider, attestation }` | Real endpoint is `POST app-check/exchange/` with `{ provider, platform, raw_token }` |
| Auth | `AuthSDK.verifyPhoneOTP()` | `{ phone_number, code }` | `VerifyOTPSerializer` requires `otp_code`, not `code` |
| Auth | `AuthSDK.confirmTOTP()` / `verifyTOTP()` | `{ code }` (no device id in the method signature) | `ConfirmTOTPSerializer` / `VerifyTOTPSerializer` both require `device_id` **and** `totp_code` |

The Kotlin/Swift/Dart SDKs were spot-checked and reproduce the same `confirmTOTP(code)` /
`verifyTOTP(code)` signature (missing `device_id`), so this isn't TypeScript-specific. Treat the
tables in this doc — which describe the actual Django contract — as the source of truth, and
double-check the SDK version you're on before assuming its convenience methods work as written.

---

## 1. Authentication

### 1.1 What's different from Firebase Auth up front

- OwnFirebase issues its **own JWTs** (via `djangorestframework-simplejwt`), not Firebase ID
  tokens/`google.firebase.auth` tokens. There is no Google-managed identity token, no
  `getIdToken()`/`getIdTokenResult()` Firebase-specific format, and no built-in Firebase Admin SDK
  verification — you verify tokens against **your own** OwnFirebase deployment.
- Token lifetimes are configured in `ownfirebase/settings.py` (`SIMPLE_JWT`) and are shorter than
  Firebase's defaults: **access token = 15 minutes**, **refresh token = 7 days**, with
  `ROTATE_REFRESH_TOKENS=True` and `BLACKLIST_AFTER_ROTATION=True` (each refresh issues a new
  refresh token and the old one is blacklisted). Firebase's ID tokens last 1 hour and refresh
  tokens are effectively long-lived/non-expiring until revoked. Both lifetimes are server config
  you can change, but as shipped they are meaningfully shorter — plan your refresh cadence
  accordingly.
- Logout is explicit and stateful: `POST /api/v1/auth/logout/` writes the refresh token's `jti` to
  a `RefreshTokenBlacklist` row (`core/models.py`). Firebase has no server-side sign-out call for
  ID tokens (it's client-side token disposal only); OwnFirebase actually revokes the refresh token
  on the server.
- Custom claims exist and are embedded in the JWT (`profile.custom_claims`, merged in on
  `/refresh/`), but they are set via `POST /api/auth/set-custom-claims/` and are gated on
  `request.user.is_staff` (Django admin flag), not Firebase's `admin.auth().setCustomUserClaims()`
  service-account flow.

### 1.2 Email/password

**Firebase (before):**
```ts
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword } from 'firebase/auth';

const auth = getAuth();
await createUserWithEmailAndPassword(auth, email, password);
const cred = await signInWithEmailAndPassword(auth, email, password);
const idToken = await cred.user.getIdToken();
```

**OwnFirebase (after)** — using `AuthSDK` (`sdk/src/auth.ts`), which posts to
`api/urls.py`'s `AuthViewSet` (`/api/v1/auth/register/`, `/api/v1/auth/login/`):
```ts
import { AuthSDK } from '@ownfirebase/sdk';

const auth = new AuthSDK({ baseUrl: 'https://your-ownfirebase-host' });

const { access, refresh, user } = await auth.register(email, password);
// or:
const { access, refresh, user } = await auth.login(email, password);

auth.setAccessToken(access); // subsequent calls send `Authorization: Bearer <access>`
```
Refreshing and reading the current user:
```ts
const { access: newAccess } = await auth.refreshToken(refresh);
const me = await auth.getMe(); // GET /api/v1/auth/me/ — includes custom_claims, sign_in_provider
```

### 1.3 Google / GitHub sign-in

Firebase's `signInWithPopup(auth, new GoogleAuthProvider())` performs the whole OAuth dance
client-side and mints a Firebase ID token. OwnFirebase does **not** run its own OAuth redirect
flow — you still get a Google ID token or GitHub access token from Google's/GitHub's own client
SDK, and OwnFirebase's backend **verifies that token server-side** (`social_auth/services.py` calls
Google's `tokeninfo` endpoint and GitHub's `/user` API respectively) and exchanges it for an
OwnFirebase JWT:

```ts
// You still obtain idToken from Google's own sign-in library (e.g. Google Identity Services),
// or accessToken from GitHub's OAuth flow — OwnFirebase does not host that redirect flow itself.
const { access, refresh } = await auth.googleSignIn(googleIdToken);
const { access, refresh } = await auth.githubSignIn(githubAccessToken);
```
Real endpoints: `POST /api/v1/auth/social/google/` `{ id_token }`, `POST /api/v1/auth/social/github/`
`{ access_token }` (`social_auth/urls.py`, `social_auth/views.py`). A third provider,
`AppleSignInSerializer`, exists in `social_auth/serializers.py` but **has no wired-up view or URL**
— Apple Sign-In is not actually reachable in this codebase despite the serializer existing; verify
against your instance before assuming it works.

Linking/unlinking:
```ts
const linked = await auth.listLinkedAccounts();       // GET /api/v1/auth/social/linked/
await auth.unlinkSocialAccount(accountId);              // DELETE /api/v1/auth/social/linked/{id}/
```

### 1.4 Anonymous auth + upgrade

```ts
// Firebase: signInAnonymously(auth)
const { access, refresh, user } = await auth.anonymousSignIn(); // POST /api/v1/auth/anonymous-signin/
```
OwnFirebase marks anonymous users by username prefix (`anon_<hex>`) and
`UserProfile.sign_in_provider == 'anonymous'` (`enhanced_auth/views.py::_is_anonymous_user`).
Upgrading to a real account (Firebase's `linkWithCredential`) is a dedicated endpoint, not a
generic "link any credential" call:
```ts
const { access, refresh } = await auth.upgradeAnonymous(email, password, password2);
// POST /api/v1/auth/upgrade/ — requires password + password2 (confirmation) and validates
// Django's password strength rules server-side.
```

### 1.5 Custom tokens

Firebase's `admin.auth().createCustomToken(uid, claims)` (server-side, verified client-side via
`signInWithCustomToken`) maps to a project-scoped endpoint here:
```ts
const { token, expires_at } = await auth.issueCustomToken(uid, claims);
// POST /api/projects/{project_id}/auth/custom-token/  (enhanced_auth/views.py: IssueCustomTokenView)
// Caller must be an 'owner' or 'editor' member of the project (403 otherwise).
```
The token is a standalone HS256 JWT (`{jti, project_id, uid, claims, exp}`) signed with
`JWT_SIGNING_KEY` (falls back to Django's `SECRET_KEY`) — it is **not** interchangeable with the
`SIMPLE_JWT` access/refresh tokens issued by `/login/`; your client-side "verify custom token" logic
must be written against this shape, not against Firebase's custom-token format.

### 1.6 MFA / Phone OTP / Magic Links (no direct Firebase equivalent to copy 1:1)

These exist here as first-class endpoints (`enhanced_auth/`) but are **not** wire-compatible with
Firebase's multi-factor APIs (`multiFactor(user).enroll(...)`) — the request/response shapes are
OwnFirebase-specific:
```ts
// TOTP (authenticator app) MFA
const { device_id, secret, provisioning_uri } = await someRawCall('POST', '/api/v1/auth/mfa/enroll/totp/', { name: 'My Authenticator' });
await someRawCall('POST', '/api/v1/auth/mfa/confirm/totp/', { device_id, totp_code });
const tokens = await someRawCall('POST', '/api/v1/auth/mfa/verify/totp/', { device_id, totp_code });
```
(Note the `device_id` + `totp_code` field names — see the mismatch table in section 0 for why the
SDK's `confirmTOTP()`/`verifyTOTP()` convenience methods currently omit `device_id`.)

Phone OTP (`/api/v1/auth/phone/send-otp/`, `/api/v1/auth/phone/verify-otp/`) and Magic Links
(`/api/v1/auth/magic-link/send/`, `/api/v1/auth/magic-link/verify/`) work similarly — see
`enhanced_auth/views.py` for exact request/response bodies. All are rate-limited server-side
(e.g. 3 OTP SMS per phone per hour) — Firebase's phone auth rate limiting is opaque/Google-managed;
here it's an explicit `django.core.cache` counter you can see and tune.

---

## 2. Data: Firestore → OwnFirebase Data API

### 2.1 The biggest structural difference: no `where()`/`orderBy()` fluent query builder

Firestore's client SDK gives you a fluent, typed query builder:
```ts
import { getFirestore, collection, query, where, orderBy, limit, getDocs } from 'firebase/firestore';

const q = query(
  collection(db, 'users'),
  where('status', '==', 'active'),
  orderBy('age', 'desc'),
  limit(10)
);
const snap = await getDocs(q);
```
**OwnFirebase's `DataSDK` (`sdk/src/data.ts`) has no equivalent fluent builder.** Filtering is done
via REST query parameters against `data/query_parser.py`'s `where`/`orderBy` JSON shape:
```ts
import { DataSDK } from '@ownfirebase/sdk';

const data = new DataSDK({ baseUrl, projectId, accessToken });

const { documents, count, next_cursor } = await data.listDocuments('users', {
  query: JSON.stringify({
    where: [{ field: 'status', op: '==', value: 'active' }],
    order_by: [{ field: 'age', direction: 'desc' }],
    limit: 10,
  }),
});
```
This maps to `GET /api/projects/{id}/collections/users/docs/?query=<json>`
(`data/views.py::DocumentViewSet.list`). Supported operators (`data/query_parser.py`):
`==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `not-in`, `array-contains`, `array-contains-any` — this list
is a close functional match to Firestore's operator set, but the **calling convention is a raw JSON
query string over REST**, not a chained builder. If you want Firestore-style ergonomics client-side,
you will need to write your own thin wrapper around `listDocuments()`.

Also note: `array-contains` / `array-contains-any` are filtered **in Python after fetching from the
DB** (`data/query_parser.py::apply_filters_to_queryset` — "Slow path: materialize and filter in
Python", explicitly because of "SQLite incompatibility"), not pushed down to PostgreSQL, so they
don't benefit from an index and won't scale the way Firestore's array-contains does at large
collection sizes.

### 2.2 Documents

**Firestore:**
```ts
import { doc, setDoc, getDoc, updateDoc, deleteDoc } from 'firebase/firestore';

await setDoc(doc(db, 'users', 'alice'), { name: 'Alice', age: 30 });
const snap = await getDoc(doc(db, 'users', 'alice'));
await updateDoc(doc(db, 'users', 'alice'), { age: 31 });
await deleteDoc(doc(db, 'users', 'alice'));
```

**OwnFirebase:**
```ts
await data.createDocument('users', { name: 'Alice', age: 30 }); // POST …/collections/users/docs/
const doc = await data.getDocument('users', 'alice');             // GET …/docs/alice/
await data.updateDocument('users', 'alice', { age: 31 });          // PATCH …/docs/alice/ (merge)
await data.replaceDocument('users', 'alice', { age: 31 });          // PUT …/docs/alice/ (replace)
await data.deleteDocument('users', 'alice');                        // DELETE …/docs/alice/
```
`doc_id` is optional on create — omit it and the server generates a UUID (`data/views.py::create`),
same convenience as Firestore's auto-ID `addDoc()`.

Every document response includes `__v` (an integer version counter, `data/models.py::Document.v`,
DB column `version`) for **optimistic locking** — pass it back on `PATCH` to get a `409 Conflict` if
someone else wrote first:
```ts
// raw REST, since DataSDK.updateDocument() doesn't currently expose __v:
await fetch(`.../docs/alice/`, { method: 'PATCH', body: JSON.stringify({ data: { age: 31 }, __v: 2 }) });
```
Firestore's closest analog is transactions (`runTransaction`) rather than an explicit version field
on every document — the mental model is similar (detect concurrent writes) but the mechanism is
different and manual here.

### 2.3 Batch writes / transactions

**Firestore:**
```ts
import { writeBatch, doc } from 'firebase/firestore';
const batch = writeBatch(db);
batch.set(doc(db, 'users/alice'), { name: 'Alice' });
batch.update(doc(db, 'users/bob'), { age: 31 });
batch.delete(doc(db, 'users/charlie'));
await batch.commit();
```

**OwnFirebase:**
```ts
await data.writeBatch([
  { op: 'set',    path: 'users/alice', data: { name: 'Alice' } },
  { op: 'update', path: 'users/bob',   data: { age: 31 } },
  { op: 'delete', path: 'users/charlie' },
]);
```
This hits `POST /api/projects/{id}/transaction/` (`data/views.py::TransactionViewSet.write_batch`),
wrapped in a single `django.db.transaction.atomic()` block — genuinely atomic across the batch, like
Firestore's batch commit. There is no equivalent of Firestore's **read-then-write transaction**
(`runTransaction(db, updateFn)` with automatic optimistic retry across reads+writes) — only blind
batch writes; if you need read-your-writes transactional logic you must build it yourself using the
`__v` field from §2.2.

### 2.4 Security Rules

`data.getRules()` / `data.updateRules()` / `data.testRules()` exist (`sdk/src/data.ts`, hitting
`/api/v1/rules/`), backed by `rules/` app. This is a genuinely different rules engine than
Firestore's `.rules` DSL and Firebase's Rules Playground — check `rules/permissions.py` and the
`rules/` app directly before assuming 1:1 syntax compatibility; this guide does not assert parity
on rule syntax.

---

## 3. Cloud Storage → OwnFirebase Storage API

**This is the flow already verified in this codebase, and it is structurally different from how the
Firebase Storage client SDK works.** Firebase's client SDK manages the entire upload for you:
```ts
import { getStorage, ref, uploadBytes, getDownloadURL } from 'firebase/storage';

const storageRef = ref(getStorage(), `avatars/${uid}.jpg`);
await uploadBytes(storageRef, file);
const url = await getDownloadURL(storageRef);
```
OwnFirebase has **no SDK-managed direct upload** — object storage is MinIO/S3 behind presigned
URLs, and the client must do a three-step dance (`storage/views.py`):

```
1. POST /api/projects/{id}/storage/upload-url/   -> { file_id, upload_url, method, expires_in, path, bucket }
2. PUT  <upload_url>                              -> raw file bytes, Content-Type header must match
3. POST /api/projects/{id}/storage/confirm/       -> { file_id }  (marks the file "confirmed", fetches size from MinIO)
```

Verified request/response contract (`storage/serializers.py`):
```ts
// Step 1 — request a presigned PUT URL. Real body fields: path, content_type, size?, metadata?
const { file_id, upload_url } = await fetch(`${base}/api/projects/${projectId}/storage/upload-url/`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ path: `avatars/${uid}.jpg`, content_type: file.type, size: file.size }),
}).then(r => r.json());

// Step 2 — PUT directly to MinIO/S3, not through the Django app.
await fetch(upload_url, { method: 'PUT', headers: { 'Content-Type': file.type }, body: file });

// Step 3 — confirm. Real body field is file_id, not object_key (see §0 mismatch table).
const fileRecord = await fetch(`${base}/api/projects/${projectId}/storage/confirm/`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ file_id }),
}).then(r => r.json());
```
`StorageSDK.getUploadUrl()`/`StorageSDK.confirmUpload()` (`sdk/src/storage.ts`) wrap steps 1 and 3,
but as noted in §0 the field names in its `upload()` convenience helper (`filename`, `object_key`)
don't match this contract — call `getUploadUrl({ path, contentType, ... })` and `confirmUpload()`
carefully, or use the raw calls above until that's fixed.

Downloads are also presigned: `StorageFileSerializer.get_download_url()` returns a presigned GET
URL only once `status` is `confirmed`/`ready` — there is no long-lived public "download URL" the
way `getDownloadURL()` implies for Firebase Storage with permissive rules; every read goes through
a freshly generated, time-limited presigned URL from `storage/s3.py::presigned_download_url`.

There is a hard **100 MB per-file limit** enforced server-side (`storage/views.py::MAX_FILE_SIZE`)
that Firebase Storage does not impose by default.

---

## 4. Cloud Functions — read this before assuming parity

**This is the single biggest divergence from Firebase in this repo, and it must not be glossed
over: OwnFirebase does not host or execute your function code at all.**

Real Firebase Cloud Functions: you write a function, `firebase deploy`, and Google's infrastructure
runs your code (Node.js/Python/etc. runtime) in response to triggers.

OwnFirebase's `CloudFunction` model (`functions/models.py`) is a **row that points at an external
HTTP endpoint you already run somewhere else**:
```python
# functions/models.py — the fields that matter
trigger_type   # 'http' | 'on_create' | 'on_update' | 'on_delete' | 'scheduled' | 'on_storage' | 'on_auth'
endpoint_url    # "Webhook URL to POST trigger payload to" — YOUR server, not code hosted here
secret_header   # value sent as X-OwnFirebase-Secret so your endpoint can authenticate the caller
timeout_seconds # request timeout for the outbound webhook POST
retry_count     # retries on error/timeout (functions/tasks.py, exponential-ish backoff via Celery)
```
When a trigger fires (an HTTP invoke call, a document create/update/delete, a cron schedule),
`functions/tasks.py::invoke_function_for_event` does an **outbound `POST` to `endpoint_url`** with
the trigger payload as the JSON body, `X-OwnFirebase-Secret: <secret_header>` for you to verify, and
records the response in `FunctionLog`. There is no code upload, no build step, no runtime
selection, and no execution sandboxing on OwnFirebase's side — you are responsible for hosting and
running the actual function logic yourself (e.g. as a small Express/FastAPI/Cloud Run/Lambda
endpoint), and OwnFirebase is only the **trigger router and webhook caller**. If your Firebase
Functions currently run arbitrary server-side logic with no separate hosting story, migrating means
standing up that hosting yourself first.

Also note as an SSRF hardening measure: `functions/serializers.py::validate_endpoint_url` rejects
any `endpoint_url` that resolves to a loopback/private/link-local/multicast address — you cannot
point a function at `localhost` or an internal-only service; it must be a publicly resolvable host.

**Registering + invoking (`sdk/src/functions.ts`, `functions/views.py`):**
```ts
import { FunctionsSDK } from '@ownfirebase/sdk';
const fns = new FunctionsSDK({ baseUrl, projectId, accessToken });

await fns.createFunction({
  name: 'sendWelcomeEmail',
  trigger_type: 'on_create',
  collection_path: 'users',       // required for on_create/on_update/on_delete triggers
  endpoint_url: 'https://your-server.example.com/functions/send-welcome-email',
  timeout_seconds: 30,
  retry_count: 2,
  is_enabled: true,
});

// HTTP-triggered invoke — real body field is `data`, not `payload` (see §0):
await fetch(`${base}/api/projects/${projectId}/functions/sendWelcomeEmail/invoke/`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ data: { to: 'alice@example.com' } }),
});
```
Invocation is asynchronous — the invoke call returns `202 Accepted` with a Celery `task_id`
immediately; the actual webhook call happens in the background (`functions/tasks.py`). This mirrors
Firebase's callable functions being async under the hood, but here the "handler" is entirely
off-box.

---

## 5. Realtime updates: Firestore listeners / RTDB → WebSocket protocol

**Firebase (before):**
```ts
import { onSnapshot, collection, query, where } from 'firebase/firestore';

const unsub = onSnapshot(
  query(collection(db, 'users'), where('status', '==', 'active')),
  (snap) => snap.docChanges().forEach(change => console.log(change.type, change.doc.data()))
);
```

**OwnFirebase** uses a single project-scoped WebSocket (`realtime/consumers.py::RealtimeConsumer`,
mounted per `realtime/routing.py` at `ws://<host>/ws/v1/projects/{project_id}/listen/` —
**note this differs from what `RealtimeSDK.connect()` currently dials**, see §0) with a small
JSON message protocol:
```
Client → Server: {"type":"subscribe","requestId":"r1","path":"users","query":{"where":[["status","==","active"]]}}
Server → Client: {"type":"subscribed","requestId":"r1","subscriptionId":"sub_xxx","snapshot":[...]}
Server → Client: {"type":"change","subscriptionId":"sub_xxx","event":"added|modified|removed","data":{...},"docId":"..."}
```
Using `RealtimeSDK` (`sdk/src/realtime.ts`):
```ts
import { RealtimeSDK } from '@ownfirebase/sdk';
const realtime = new RealtimeSDK({ baseUrl, projectId, accessToken });

const unsubscribe = realtime.onSnapshot(
  { path: 'users', query: { where: [['status', '==', 'active']] } },
  (snapshot) => console.log('initial:', snapshot.data),
);
const unlisten = realtime.onChange(subscriptionId, (change) => {
  console.log(change.event, change.data); // 'added' | 'modified' | 'removed'
});
```
Differences worth knowing:
- The `query.where` shape for realtime subscriptions is a flat 3-tuple array
  (`["field", "op", "value"]`, checked in `_matches_query`), which is **not the same shape** as the
  Data API's REST query object from §2.1 (`{field, op, value}` dicts) — don't reuse one query
  object for both.
- Realtime filtering (`_matches_query`) only supports `==`, `!=`, `>`, `>=`, `<`, `<=` — no
  `array-contains`/`in` support over the WebSocket, unlike the REST Data API.
- `presence.set` / `ondisconnect.set` message types exist (`realtime/presence.py`) and are
  conceptually close to Firebase Realtime Database's `.info/connected` + `onDisconnect()` API, but
  they are OwnFirebase-specific JSON messages, not RTDB's actual API surface — do not assume
  `onDisconnect()` semantics carry over exactly; read `realtime/presence.py` if you depend on this.
- There is no Firestore-equivalent local offline cache/local persistence layer here — this is a
  live WebSocket only; if the socket drops, `RealtimeSDK` reconnects (exponential backoff, up to 10
  attempts) but there's no offline queue of pending writes the way the Firestore SDK provides.

---

## 6. Other services — brief mappings

**Push Notifications** (`push/`, `sdk/src/push.ts`) — device tokens (`fcm`/`apns`/`web` platforms,
not Firebase's `messaging().getToken()` flow — you still get the actual FCM/APNs/WebPush token from
the platform SDK yourself, then `POST /api/projects/{id}/push/tokens/` to register it here), topics
with explicit `subscribe`/`unsubscribe` actions, one-off notifications, and scheduled "campaigns"
(`NotificationCampaign` — a broader concept than plain FCM topic messaging). Delivery to FCM/APNs/
Web Push is handled by a separate Rust worker (`rust/push-worker`, wired into `docker-compose.yml`
as the `push-worker` service) rather than inline in the Django request — check platform enum values
and payload field names in §0 before wiring this up.

**Remote Config** (`remoteconfig/` **and** `config/` — two overlapping backend apps; see the note
below) vs. Firebase Remote Config's `fetchAndActivate()`/`getValue()`. The TypeScript SDK's
`RemoteConfigSDK` (`sdk/src/remoteconfig.ts`) talks to the `config` app's parameter CRUD endpoints
(`/api/projects/{id}/config/parameters/`) and does client-side "fetch all, find by key" with its own
TTL cache (`fetchAllParameters()`, `getConfigValue<T>()`) — reasonably close in spirit to
`fetchAndActivate()` + `getValue()`. There is **also** a separate, simpler `remoteconfig` app
mounted at `/api/projects/{id}/remoteconfig/fetch/` (`remoteconfig/views.py::RemoteConfigFetchView`)
that returns a flat `{key: typed_value}` map in one call — arguably closer to Firebase's mental
model — but it is **not currently wired into the TypeScript SDK at all**. Verify which of the two
your version of the SDK actually uses before building on it.

**A/B Testing** (`abtesting/`, `sdk/src/abtesting.ts`) vs. Firebase's Remote Config–integrated A/B
Testing — this is a standalone experiment engine (experiments → variants with percentage
allocations → deterministic assignment by a `targeting_key` like `user_id` → conversion event
recording → aggregated results). `ABTestingSDK.getAssignment()`/`recordConversion()` map cleanly
to `POST .../experiments/{id}/assign/` and `.../convert/` (`abtesting/views.py`). Note `config/`
also registers its own, separate `experiments` router (`config/urls.py`) — that one is unused by
the current SDK; the SDK talks only to the `abtesting` app.

**Crashlytics + Performance Monitoring** (`crashlytics/`, `sdk/src/crashlytics.ts`) — crash reports
are deduplicated server-side into `CrashGroup` "issues" by a signature fingerprint (mirrors
Firebase's crash grouping), plus `PerformanceTrace` (custom traces) and `NetworkRequest` monitoring,
combining what Firebase splits into two separate products (Crashlytics + Performance Monitoring)
into one app here.

**App Check** (`app_check/`, `sdk/src/appcheck.ts`) — supports `recaptcha_v3` /
`recaptcha_enterprise` / `device_check` / `safety_net` / `debug` providers in the data model
(`AppCheckConfig`), but as of this snapshot **only the `debug` provider path is actually implemented**
in `ExchangeTokenView` (`app_check/views.py`) — real reCAPTCHA/Play Integrity/DeviceCheck provider
validation returns `501 Not Implemented` with a message saying so explicitly. Don't assume
production App Check attestation providers work end-to-end without checking `app_check/services.py`
and testing against your instance first.

---

## 7. What does NOT have a direct equivalent in OwnFirebase

Confirmed absent from this codebase (searched app-by-app; no matches for these concepts anywhere in
the Python source):

- **Firebase Hosting** — there is no static-site/CDN hosting product here at all.
- **Dynamic Links** — no deferred-deep-linking service.
- **Firebase ML / ML Kit** — no on-device or cloud ML inference service.
- **Test Lab** — no device-farm testing product.
- **In-App Messaging** — no separate in-app messaging campaign product (push "campaigns" in
  `push/` are the closest thing, but they are push notifications, not in-app overlays).
- **Firebase Extensions** — no extension marketplace/installer.
- **Genkit / Firebase AI Logic** managed integration — this repo does ship its own `ai/` (AI Proxy)
  and `rag/` (pgvector-backed RAG) apps, which is *more* than stock Firebase offers in this area,
  but it is a bespoke OwnFirebase feature, not a Firebase-compatible surface — don't expect
  Firebase's Genkit APIs to apply.

## 8. The Python SDK is not yet functional — verify before use

Separately from the mismatch table in §0: as of this snapshot, `sdk/python-sdk/ownfirebase/`'s
per-service modules (`auth.py`, `data.py`, `storage.py`, `functions.py`, `push.py`, `realtime.py`,
`crashlytics.py`, `abtesting.py`, `appcheck.py`, `remote_config.py`) are each a **five-line stub**:
```python
"""OwnFirebase Auth SDK."""
from .client import OwnFirebaseClient
class AuthSDK(OwnFirebaseClient):
    """Authentication service."""
    pass
```
Only the shared HTTP plumbing (`client.py`, `config.py`, `errors.py`) is implemented — none of the
actual methods the package's own `README.md` demonstrates (`app.auth.register(...)`,
`app.data.create_document(...)`, `app.analytics.log_event(...)`) exist on these classes; calling
them raises `AttributeError`. If you need Python, either implement these methods yourself against
the REST contracts documented above, or use `requests`/`httpx` directly against the same endpoints.
The Kotlin, Swift, and Dart SDKs were spot-checked and **are** fully implemented with method bodies
matching the TypeScript SDK.

---

## 9. Migration strategy: moving existing Firestore data

1. **Export from Firebase.** Use Firebase's own export tooling —
   `gcloud firestore export gs://<bucket>/<path>` (Firestore managed export) or the
   `firebase-tools` / Admin SDK to walk collections and dump documents to NDJSON. This guide does
   not fabricate a bespoke exporter; use Google's documented export path for your Firestore data.
2. **Transform to OwnFirebase's Document schema.** Each Firestore document becomes one row in
   `data/models.py::Document`:
   ```json
   {
     "collection_path": "users",          // Firestore collection (or "users/alice/posts" for subcollections)
     "doc_id": "alice",                    // Firestore document ID
     "data": { "name": "Alice", "age": 30 }, // the document's fields, as JSON — nested maps/arrays carry over as-is
     "v": 0                                // starts at 0; OwnFirebase's optimistic-locking version counter (see §2.2), has no Firestore source
   }
   ```
   Firestore-specific types need translation: Firestore `Timestamp` → ISO 8601 string or epoch
   number (OwnFirebase's `data` column is plain JSONB — there's no native timestamp type inside it,
   only the row-level `created_at`/`updated_at` columns are real `DateTimeField`s);
   Firestore `DocumentReference` fields → plain string paths (no native reference type here);
   Firestore `GeoPoint` → a plain `{lat, lng}` object (no native geo type in the JSONB schema you
   examined in `data/models.py`).
3. **Bulk-import via the Data API.** Use `TransactionViewSet.write_batch`
   (`POST /api/projects/{id}/transaction/`) with `op: "set"` for each document, batched to a
   reasonable size per request (this executes inside one `transaction.atomic()` per call — very
   large single batches hold one DB transaction open for the whole batch, so chunk large imports
   rather than sending everything in one request). A minimal importer:
   ```ts
   for (const chunk of chunkArray(exportedDocs, 500)) {
     await data.writeBatch(chunk.map(d => ({
       op: 'set',
       path: `${d.collection_path}/${d.doc_id}`,
       data: d.data,
     })));
   }
   ```
4. **Re-create collection metadata (optional).** `Collection` rows (`data/models.py::Collection`)
   are metadata-only (name/path/schema hints for the admin console) — Firestore has no equivalent
   concept to migrate from; you can create these after the fact or skip them, since documents don't
   require a pre-existing `Collection` row to be written (`DocumentViewSet.create` only checks for
   duplicate `doc_id`, not for a parent `Collection`).
5. **Re-implement security rules and re-point clients.** Port your Firestore `.rules` logic to
   whatever `rules/` actually supports (read `rules/permissions.py` — do not assume 1:1 rules-DSL
   syntax compatibility, this was not verified as part of this audit), then switch your app's SDK
   initialization from Firebase's `initializeApp(firebaseConfig)` to OwnFirebase's
   `new OwnFirebaseClient({ baseUrl, projectId, accessToken })`-style config across the modules
   above.
