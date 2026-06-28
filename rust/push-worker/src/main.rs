//! OwnFirebase push-worker — async Redis-backed notification delivery service.
//!
//! Architecture:
//!   - Connects to Redis and PostgreSQL on startup.
//!   - Spawns N concurrent Tokio tasks (PUSH_WORKER_CONCURRENCY or num_cpus*2).
//!   - Each task loops: BLPOP "ownfb:push:queue" → dispatch → update DB.
//!   - Graceful shutdown on SIGTERM / Ctrl-C via a shared cancellation flag.

mod apns;
mod db;
mod fcm;
mod types;
mod webpush;

use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use std::time::Duration;

use redis::aio::ConnectionManager;
use redis::AsyncCommands;
use reqwest::Client;
use sqlx::postgres::PgPoolOptions;
use sqlx::PgPool;
use tracing::{error, info, warn};
use tracing_subscriber::{fmt, layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

use crate::apns::TokenCache;
use crate::types::{DeliveryResult, PushJob};

const QUEUE_KEY: &str = "ownfb:push:queue";
const BLPOP_TIMEOUT_SECS: f64 = 5.0;

// ── entry point ──────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() {
    // Load .env if present (ignored in containers that inject env directly).
    let _ = dotenvy::dotenv();

    // Structured JSON logging controlled by RUST_LOG env var.
    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .with(fmt::layer().json())
        .init();

    info!("push-worker starting");

    // ── config ───────────────────────────────────────────────────────────────
    let redis_url = required_env("REDIS_URL");
    let database_url = required_env("DATABASE_URL");

    let concurrency: usize = std::env::var("PUSH_WORKER_CONCURRENCY")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or_else(|| num_cpus() * 2)
        .max(1);

    info!(concurrency, "worker pool size");

    // ── connections ──────────────────────────────────────────────────────────
    let redis_client =
        redis::Client::open(redis_url.as_str()).expect("Invalid REDIS_URL");
    let redis_mgr = ConnectionManager::new(redis_client)
        .await
        .expect("Failed to connect to Redis");

    let pg_pool = PgPoolOptions::new()
        .max_connections((concurrency as u32) + 2)
        .acquire_timeout(Duration::from_secs(10))
        .connect(&database_url)
        .await
        .expect("Failed to connect to PostgreSQL");

    info!("Redis and PostgreSQL connections established");

    // ── shared state ─────────────────────────────────────────────────────────
    let shutdown = Arc::new(AtomicBool::new(false));
    let http_client = Client::builder()
        .timeout(Duration::from_secs(30))
        .tcp_keepalive(Duration::from_secs(60))
        .build()
        .expect("Failed to build HTTP client");
    let apns_token_cache: TokenCache = apns::new_token_cache();

    // ── graceful-shutdown signal ──────────────────────────────────────────────
    {
        let shutdown_flag = shutdown.clone();
        tokio::spawn(async move {
            tokio::signal::ctrl_c()
                .await
                .expect("Failed to install Ctrl-C handler");
            info!("Shutdown signal received; draining workers…");
            shutdown_flag.store(true, Ordering::SeqCst);
        });
    }

    // ── worker tasks ─────────────────────────────────────────────────────────
    let mut handles = Vec::with_capacity(concurrency);

    for worker_id in 0..concurrency {
        let redis = redis_mgr.clone();
        let pool = pg_pool.clone();
        let http = http_client.clone();
        let cache = apns_token_cache.clone();
        let stop = shutdown.clone();

        let handle = tokio::spawn(async move {
            worker_loop(worker_id, redis, pool, http, cache, stop).await;
        });
        handles.push(handle);
    }

    for handle in handles {
        let _ = handle.await;
    }

    info!("push-worker stopped");
}

// ── worker loop ──────────────────────────────────────────────────────────────

async fn worker_loop(
    id: usize,
    mut redis: ConnectionManager,
    pool: PgPool,
    http: Client,
    apns_cache: TokenCache,
    shutdown: Arc<AtomicBool>,
) {
    info!(worker_id = id, "worker started");

    loop {
        if shutdown.load(Ordering::Relaxed) {
            info!(worker_id = id, "worker shutting down");
            break;
        }

        // BLPOP blocks until an item arrives or the timeout expires.
        let raw: Option<(String, String)> = match redis
            .blpop(QUEUE_KEY, BLPOP_TIMEOUT_SECS)
            .await
        {
            Ok(v) => v,
            Err(e) => {
                error!(worker_id = id, error = %e, "BLPOP error; retrying in 1s");
                tokio::time::sleep(Duration::from_secs(1)).await;
                continue;
            }
        };

        let (_key, payload) = match raw {
            Some(pair) => pair,
            None => {
                // Timeout — loop back and check the shutdown flag.
                continue;
            }
        };

        let job: PushJob = match serde_json::from_str(&payload) {
            Ok(j) => j,
            Err(e) => {
                error!(
                    worker_id = id,
                    payload = %payload,
                    error = %e,
                    "Failed to deserialise PushJob; skipping"
                );
                continue;
            }
        };

        info!(
            worker_id = id,
            notification_id = job.notification_id,
            platform = %job.platform,
            "Processing notification"
        );

        let result = dispatch(&http, &apns_cache, &job).await;

        // Persist outcome to Postgres.
        if let Err(e) = db::update_notification_status(&pool, job.notification_id, &result).await {
            error!(
                worker_id = id,
                notification_id = job.notification_id,
                error = %e,
                "Failed to update notification status in DB"
            );
        }

        if result.success {
            info!(
                worker_id = id,
                notification_id = job.notification_id,
                platform = %job.platform,
                "Delivered"
            );
        } else {
            warn!(
                worker_id = id,
                notification_id = job.notification_id,
                platform = %job.platform,
                error = ?result.error,
                "Delivery failed"
            );
        }
    }

    info!(worker_id = id, "worker stopped");
}

// ── platform dispatcher ───────────────────────────────────────────────────────

async fn dispatch(
    http: &Client,
    apns_cache: &TokenCache,
    job: &PushJob,
) -> DeliveryResult {
    match job.platform.to_lowercase().as_str() {
        "fcm" | "android" => {
            fcm::send(http, job).await.unwrap_or_else(|e| {
                DeliveryResult::fail(None, format!("FCM error: {e}"))
            })
        }
        "apns" | "ios" => {
            apns::send(http, apns_cache, job).await.unwrap_or_else(|e| {
                DeliveryResult::fail(None, format!("APNs error: {e}"))
            })
        }
        "webpush" | "web" => {
            webpush::send(http, job).await.unwrap_or_else(|e| {
                DeliveryResult::fail(None, format!("WebPush error: {e}"))
            })
        }
        other => DeliveryResult::fail(
            None,
            format!("Unknown platform '{other}'; expected fcm | apns | webpush"),
        ),
    }
}

// ── helpers ───────────────────────────────────────────────────────────────────

fn required_env(key: &str) -> String {
    std::env::var(key).unwrap_or_else(|_| panic!("Required env var '{key}' is not set"))
}

/// Best-effort logical CPU count; falls back to 4.
fn num_cpus() -> usize {
    std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4)
}
