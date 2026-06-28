//! Web Push delivery with VAPID authentication.
//!
//! VAPID (Voluntary Application Server Identification) signs a JWT with the
//! server's ES256 private key so browsers can verify the sender.
//!
//! Required env vars:
//!   - `VAPID_PRIVATE_KEY`  — Base64url-encoded raw 32-byte P-256 scalar, OR
//!                            PEM-encoded EC private key
//!   - `VAPID_SUBJECT`      — `mailto:` or `https:` URI identifying the sender
//!
//! The `job.token` field must contain the Web Push subscription serialised as
//! JSON: `{ "endpoint": "...", "keys": { "p256dh": "...", "auth": "..." } }`.
//! For simple server-to-server uses (no payload encryption required) the keys
//! are optional and the body will be empty.
//!
//! NOTE: Full RFC 8291 content encryption (aesgcm / aes128gcm) is complex and
//! requires a HKDF + AEAD implementation.  For the Phase 3 MVP we deliver
//! VAPID-authenticated requests with an unencrypted JSON body.  Apps using a
//! service-worker that does not enforce encryption will receive the data.
//! Production hardening: integrate the `web-push` crate for full encryption.

use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use jwt_simple::algorithms::ES256KeyPair;
// `jwt_simple::prelude::*` exports coarsetime::Duration as `Duration`.
use jwt_simple::prelude::*;
use reqwest::Client;
use serde::Deserialize;
use serde_json::json;
use tracing::{debug, instrument, warn};

use crate::types::{DeliveryResult, PushError, PushJob};

/// Subset of the Web Push subscription object we need.
#[derive(Debug, Deserialize)]
struct Subscription {
    endpoint: String,
    #[serde(default)]
    keys: Option<SubscriptionKeys>,
}

#[derive(Debug, Deserialize)]
struct SubscriptionKeys {
    p256dh: String,
    auth: String,
}

/// Build the VAPID JWT for a specific push service origin.
fn build_vapid_jwt(audience: &str, subject: &str, private_key_b64: &str) -> Result<String, PushError> {
    // Accept either a PEM-encoded key or a raw base64url-encoded 32-byte scalar.
    let key_pair = if private_key_b64.contains("BEGIN") {
        ES256KeyPair::from_pem(private_key_b64)
            .map_err(|e| PushError::Config(format!("Invalid VAPID PEM key: {e}")))?
    } else {
        let raw = URL_SAFE_NO_PAD
            .decode(private_key_b64)
            .map_err(|e| PushError::Config(format!("Invalid VAPID_PRIVATE_KEY base64: {e}")))?;
        ES256KeyPair::from_bytes(&raw)
            .map_err(|e| PushError::Config(format!("Invalid VAPID key bytes: {e}")))?
    };

    // VAPID JWT: exp = now + 12h, aud = push service origin, sub = contact URI.
    let claims = Claims::create(Duration::from_hours(12))
        .with_audience(audience)
        .with_subject(subject);

    key_pair
        .sign(claims)
        .map_err(|e| PushError::Config(format!("VAPID JWT signing failed: {e}")))
}

/// Extract the origin (scheme + host + optional port) from a URL.
fn origin_of(url: &str) -> Result<String, PushError> {
    // Minimal parser — avoid pulling in the `url` crate.
    let (scheme, rest) = url
        .split_once("://")
        .ok_or_else(|| PushError::Config(format!("Cannot parse origin from URL: {url}")))?;
    let host_port = rest.split('/').next().unwrap_or(rest);
    Ok(format!("{scheme}://{host_port}"))
}

/// Send a Web Push notification.
///
/// # Errors
/// Returns [`PushError::Config`] for missing/invalid env vars or malformed token.
/// Returns [`PushError::Http`] on network failures.
#[instrument(skip(client, job), fields(notification_id = job.notification_id))]
pub async fn send(client: &Client, job: &PushJob) -> Result<DeliveryResult, PushError> {
    let vapid_private_key = std::env::var("VAPID_PRIVATE_KEY")
        .map_err(|_| PushError::Config("VAPID_PRIVATE_KEY not set".into()))?;
    let vapid_subject = std::env::var("VAPID_SUBJECT")
        .map_err(|_| PushError::Config("VAPID_SUBJECT not set".into()))?;

    // Parse the subscription from the token field.
    let subscription: Subscription = serde_json::from_str(&job.token)
        .map_err(|e| PushError::Config(format!("job.token is not valid subscription JSON: {e}")))?;

    let endpoint = &subscription.endpoint;
    let audience = origin_of(endpoint)?;

    let jwt = build_vapid_jwt(&audience, &vapid_subject, &vapid_private_key)?;

    // Build the push message body.
    let message_body = json!({
        "title": job.title,
        "body":  job.body,
        "data":  job.data,
        "image": job.image_url,
    });
    let body_bytes = serde_json::to_vec(&message_body)
        .map_err(|e| PushError::Config(format!("Failed to serialise push body: {e}")))?;

    debug!(endpoint = %endpoint, "Sending Web Push request");

    // VAPID Authorization format: `vapid t=<jwt>,k=<urlsafe-b64-public-key>`
    // For simplicity, pass the subject as the public-key hint (browsers verify
    // via the subscription's application server key registered at subscribe time).
    let auth_header = format!("vapid t={jwt},k={vapid_subject}");

    let response = client
        .post(endpoint.as_str())
        .header("Authorization", auth_header)
        .header("Content-Type", "application/json")
        .header("TTL", "86400")      // 24-hour message lifetime
        .header("Urgency", "high")   // wake device immediately
        .body(body_bytes)
        .send()
        .await
        .map_err(PushError::Http)?;

    let status_code = response.status().as_u16();

    // Push services return 201 Created on success; some return 200.
    if response.status().is_success() || status_code == 201 {
        Ok(DeliveryResult::ok(status_code))
    } else {
        let text = response.text().await.unwrap_or_default();
        warn!(
            notification_id = job.notification_id,
            http_status = status_code,
            body = %text,
            "Web Push delivery failed"
        );
        Ok(DeliveryResult::fail(
            Some(status_code),
            format!("WebPush HTTP {status_code}: {text}"),
        ))
    }
}
