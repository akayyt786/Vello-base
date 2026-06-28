# @ownfirebase/js-sdk

TypeScript SDK for OwnFirebase — a self-hosted Firebase alternative built on Django + PostgreSQL.

## Installation

```bash
npm install @ownfirebase/js-sdk
```

## Quick Start

```typescript
import { initOwnFirebase } from '@ownfirebase/js-sdk';

const app = initOwnFirebase({
  baseUrl: 'http://localhost:8000',
  projectId: 'my-project-id',
});

// Authenticate
const tokens = await app.auth.login('user@example.com', 'password');
app.setAccessToken(tokens.access);  // propagates to all services

// Firestore-like data
const docs = await app.data.listDocuments('users');
const doc  = await app.data.createDocument('users', { name: 'Alice', age: 30 });
await app.data.updateDocument('users', doc.id, { age: 31 });

// Cloud Functions
const result = await app.functions.invoke('send-welcome-email', { userId: doc.id });

// Storage (presigned upload)
const file = new Blob(['hello'], { type: 'text/plain' });
const obj  = await app.storage.upload(file, { filename: 'hello.txt', contentType: 'text/plain' });

// Push Notifications
await app.push.registerToken('<device-token>', 'web');
await app.push.sendToDevice('<token-id>', { title: 'Hello', body: 'World' });

// Analytics
await app.analytics.logEvent('page_view', { page: '/home' });

// A/B Testing
const assignment = await app.ab.getAssignment('<experiment-id>', tokens.user_id);
console.log(assignment.variant_name);  // e.g. "variant_b"

// RAG / AI
const answer = await app.ai.ragQuery('<collection-id>', 'What is OwnFirebase?');
console.log(answer.answer);

// Remote Config
const params = await app.remoteConfig.listParameters();

// Crashlytics / Performance
await app.crashlytics.reportCrash({
  exception_type: 'TypeError',
  message: 'Cannot read property of undefined',
  stack_trace: '...',
  app_version: '1.0.0',
  platform: 'web',
});
```

## Services

| Property | Description |
|---|---|
| `app.auth` | Registration, login, MFA, magic links, social auth, phone OTP |
| `app.data` | Firestore-like collections and documents with subcollection support |
| `app.functions` | Deploy and invoke Cloud Functions |
| `app.storage` | Presigned uploads to MinIO/S3, file listing |
| `app.push` | Device token registration, topic fan-out, campaigns |
| `app.analytics` | Event logging, user properties, conversion tracking |
| `app.crashlytics` | Crash reporting, performance traces, network monitoring |
| `app.remoteConfig` | Remote config parameters with conditional overrides |
| `app.ab` | A/B experiment assignment and conversion recording |
| `app.ai` | LLM chat (Claude/Gemini) and retrieval-augmented generation |
| `app.projects` | Project CRUD and membership management |
| `app.appCheck` | App Check token exchange for attestation-gated APIs |

## Configuration

```typescript
interface OwnFirebaseConfig {
  baseUrl: string;      // e.g. 'https://api.yourdomain.com'
  projectId?: string;   // UUID of the target project (set after login if not known upfront)
  accessToken?: string; // JWT — set via setAccessToken() rather than here
}
```

## Error Handling

All methods throw an `APIError` object on non-2xx responses:

```typescript
import type { APIError } from '@ownfirebase/js-sdk';

try {
  await app.data.getDocument('users', 'non-existent-id');
} catch (err) {
  const e = err as APIError;
  console.error(e.status, e.message, e.detail);
}
```

## Build

```bash
npm install
npm run build   # outputs to dist/
```
