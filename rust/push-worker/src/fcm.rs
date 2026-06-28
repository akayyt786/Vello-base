//! Firebase Cloud Messaging delivery (legacy HTTP API).
//!
//! Uses the FCM legacy endpoint `https://fcm.googleapis.com/fcm/send` with
//! `Authorization: key=<FCM_SERVER_KEY>`.  This is the simplest integration
//! path for Phase 3 and works for both Android and cross-platform FCM topics.

use reqwest::Client;
use serde_json::{json, Value};
use tracing::{debug, instrument, warn};

use crate::types::{DeliveryResult, PushError, PushJob};

const FCM_SEND_URL: &str = "https://fcm.googleapis.com/fcm/send";

/// Send a push notification to a single FCM registration token.
///
/// # Errors
/// Returns [`PushError::Config`] if `FCM_SERVER_KEY` is not set.
/// Returns [`PushError::Http`] on network / TLS failures.
#[instrument(skip(client, job), fields(notification_id = job.notification_id))]
pub async fn send(client: &Client, job: &PushJob) -> Result<DeliveryResult, PushError> {
    let server_key = std::env::var("FCM_SERVER_KEY")
        .map_err(|_| PushError::Config("FCM_SERVER_KEY not set".into()))?;

    // Build the notification object.
    let mut notification = json!({
        "title": job.title,
        "body": job.body,
    });

    if let Some(ref img) = job.image_url {
        notification["image"] = Value::String(img.clone());
    }

    // Merge caller-supplied data payload; ensure it is an object.
    let data_payload: Value = if job.data.is_object() {
        job.data.clone()
    } else {
        json!({})
    };

    let body = json!({
        "to": job.token,
        "priority": "high",
        "notification": notification,
        "data": data_payload,
    });

    debug!(url = FCM_SEND_URL, "Sending FCM request");

    let response = client
        .post(FCM_SEND_URL)
        .header("Authorization", format!("key={server_key}"))
        .header("Content-Type", "application/json")
        .json(&body)
        .send()
        .await
        .map_err(PushError::Http)?;

    let status = response.status();
    let status_code = status.as_u16();

    if status.is_success() {
        let resp_body: Value = response.json().await.unwrap_or_default();
        // FCM returns success=1 in the body even on 200 when token is invalid.
        let fcm_success = resp_body
            .get("success")
            .and_then(|v| v.as_u64())
            .unwrap_or(0);

        if fcm_success == 0 {
            let fcm_error = resp_body
                .get("results")
                .and_then(|r| r.get(0))
                .and_then(|r| r.get("error"))
                .and_then(|e| e.as_str())
                .unwrap_or("unknown FCM error")
                .to_string();

            warn!(
                notification_id = job.notification_id,
                error = %fcm_error,
                "FCM reported delivery failure in body (HTTP 200)"
            );
            return Ok(DeliveryResult::fail(Some(status_code), fcm_error));
        }

        Ok(DeliveryResult::ok(status_code))
    } else {
        let text = response.text().await.unwrap_or_default();
        warn!(
            notification_id = job.notification_id,
            http_status = status_code,
            body = %text,
            "FCM HTTP error"
        );
        Ok(DeliveryResult::fail(
            Some(status_code),
            format!("FCM HTTP {status_code}: {text}"),
        ))
    }
}
