//! Apple Push Notification service (APNs) delivery via HTTP/2.
//!
//! Uses token-based authentication (JWT ES256) with:
//!   - `APNS_AUTH_KEY`   — PEM/DER content of the .p8 private key
//!   - `APNS_KEY_ID`     — 10-character key identifier
//!   - `APNS_TEAM_ID`    — 10-character Apple Developer team ID
//!   - `APNS_BUNDLE_ID`  — Bundle identifier (apns-topic header)
//!
//! Provider tokens are cached in memory for up to 55 minutes (Apple allows
//! at most one token per key per hour).

use std::sync::Arc;
use std::time::Instant;

use jwt_simple::algorithms::ES256KeyPair;
// `jwt_simple::prelude::*` exports coarsetime::Duration as `Duration`.
// We deliberately avoid importing std::time::Duration by name to prevent
// ambiguity; use std::time::Duration with its full path where needed.
use jwt_simple::prelude::*;
use reqwest::Client;
use serde_json::{json, Value};
use tokio::sync::Mutex;
use tracing::{debug, instrument, warn};

use crate::types::{DeliveryResult, PushError, PushJob};

const APNS_PROD_HOST: &str = "https://api.push.apple.com";
/// Re-issue the provider token 5 min before the 1-hour Apple limit.
const TOKEN_TTL_SECS: u64 = 55 * 60;

/// In-memory cached provider JWT.
#[derive(Debug)]
struct CachedToken {
    token: String,
    issued_at: Instant,
}

/// Thread-safe APNs JWT cache.  Wrap in `Arc<Mutex<…>>` and clone cheaply.
pub type TokenCache = Arc<Mutex<Option<CachedToken>>>;

pub fn new_token_cache() -> TokenCache {
    Arc::new(Mutex::new(None))
}

/// Mint a new APNs provider JWT (ES256, signed with the .p8 private key).
fn build_provider_token(key_id: &str, team_id: &str, auth_key_pem: &str) -> Result<String, PushError> {
    let key_pair = ES256KeyPair::from_pem(auth_key_pem)
        .map_err(|e| PushError::Config(format!("Invalid APNS_AUTH_KEY PEM: {e}")))?
        .with_key_id(key_id);

    // Duration here is coarsetime::Duration from jwt_simple::prelude::*.
    let claims = Claims::create(Duration::from_hours(1))
        .with_issuer(team_id);

    key_pair
        .sign(claims)
        .map_err(|e| PushError::Config(format!("APNs JWT signing failed: {e}")))
}

/// Return a valid cached JWT or mint a new one.
async fn get_token(cache: &TokenCache) -> Result<String, PushError> {
    let key_id = std::env::var("APNS_KEY_ID")
        .map_err(|_| PushError::Config("APNS_KEY_ID not set".into()))?;
    let team_id = std::env::var("APNS_TEAM_ID")
        .map_err(|_| PushError::Config("APNS_TEAM_ID not set".into()))?;
    let auth_key = std::env::var("APNS_AUTH_KEY")
        .map_err(|_| PushError::Config("APNS_AUTH_KEY not set".into()))?;

    let mut guard = cache.lock().await;

    let needs_refresh = guard.as_ref().map_or(true, |c| {
        c.issued_at.elapsed().as_secs() >= TOKEN_TTL_SECS
    });

    if needs_refresh {
        let token = build_provider_token(&key_id, &team_id, &auth_key)?;
        *guard = Some(CachedToken {
            token: token.clone(),
            issued_at: Instant::now(),
        });
        return Ok(token);
    }

    Ok(guard.as_ref().unwrap().token.clone())
}

/// Send a push notification to an APNs device token.
///
/// # Errors
/// Returns [`PushError::Config`] for missing/invalid env vars.
/// Returns [`PushError::Http`] on network / TLS failures.
#[instrument(skip(client, cache, job), fields(notification_id = job.notification_id))]
pub async fn send(
    client: &Client,
    cache: &TokenCache,
    job: &PushJob,
) -> Result<DeliveryResult, PushError> {
    let bundle_id = std::env::var("APNS_BUNDLE_ID")
        .map_err(|_| PushError::Config("APNS_BUNDLE_ID not set".into()))?;

    let jwt = get_token(cache).await?;

    // Build the APS payload.
    let mut aps = json!({
        "alert": {
            "title": job.title,
            "body":  job.body,
        },
        "sound": "default",
    });

    if job.image_url.is_some() {
        // Rich media requires a Notification Service Extension on device;
        // signal it with mutable-content=1 and pass the URL in the data payload.
        aps["mutable-content"] = Value::from(1u8);
    }

    let mut payload = json!({ "aps": aps });

    // Merge caller-supplied data at the top level.
    if let Value::Object(ref map) = job.data {
        if let Value::Object(ref mut obj) = payload {
            for (k, v) in map {
                obj.insert(k.clone(), v.clone());
            }
        }
    }

    // Provide image_url at the top level for the extension to fetch.
    if let Some(ref img) = job.image_url {
        if let Value::Object(ref mut obj) = payload {
            obj.insert("image_url".to_string(), Value::String(img.clone()));
        }
    }

    let url = format!("{APNS_PROD_HOST}/3/device/{}", job.token);

    debug!(url = %url, "Sending APNs request");

    let response = client
        .post(&url)
        .header("authorization", format!("bearer {jwt}"))
        .header("apns-topic", &bundle_id)
        .header("apns-push-type", "alert")
        .header("apns-priority", "10")
        .json(&payload)
        .send()
        .await
        .map_err(PushError::Http)?;

    let status_code = response.status().as_u16();

    if response.status().is_success() {
        Ok(DeliveryResult::ok(status_code))
    } else {
        let resp_body: Value = response.json().await.unwrap_or_default();
        let reason = resp_body
            .get("reason")
            .and_then(|r| r.as_str())
            .unwrap_or("unknown")
            .to_string();

        warn!(
            notification_id = job.notification_id,
            http_status = status_code,
            reason = %reason,
            "APNs delivery failed"
        );
        Ok(DeliveryResult::fail(
            Some(status_code),
            format!("APNs {status_code}: {reason}"),
        ))
    }
}
