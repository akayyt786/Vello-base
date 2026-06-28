use serde::{Deserialize, Serialize};
use thiserror::Error;

/// A push notification job deserialized from the Redis queue.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PushJob {
    /// Primary key of the `push_pushnotification` row.
    pub notification_id: i64,
    /// Delivery platform: "fcm" | "apns" | "webpush"
    pub platform: String,
    /// Device token (FCM registration token, APNs device token, or
    /// serialised Web Push subscription JSON endpoint URL).
    pub token: String,
    pub title: String,
    pub body: String,
    /// Arbitrary key-value pairs forwarded to the device as a data payload.
    #[serde(default)]
    pub data: serde_json::Value,
    /// Optional rich-media image URL (supported by FCM and APNs).
    #[serde(default)]
    pub image_url: Option<String>,
}

/// Outcome returned by every platform sender.
#[derive(Debug, Clone)]
pub struct DeliveryResult {
    pub success: bool,
    pub error: Option<String>,
    /// HTTP status code returned by the upstream push gateway.
    pub response_code: Option<u16>,
}

impl DeliveryResult {
    pub fn ok(code: u16) -> Self {
        Self {
            success: true,
            error: None,
            response_code: Some(code),
        }
    }

    pub fn fail(code: Option<u16>, msg: impl Into<String>) -> Self {
        Self {
            success: false,
            error: Some(msg.into()),
            response_code: code,
        }
    }
}

/// Unified error type for the worker.
#[derive(Debug, Error)]
pub enum PushError {
    #[error("Redis error: {0}")]
    Redis(#[from] redis::RedisError),

    #[error("Postgres error: {0}")]
    Postgres(#[from] sqlx::Error),

    #[error("HTTP client error: {0}")]
    Http(#[from] reqwest::Error),

    #[error("Unknown platform '{0}'; expected fcm | apns | webpush")]
    InvalidPlatform(String),

    #[error("Configuration error: {0}")]
    Config(String),
}
