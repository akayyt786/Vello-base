use chrono::{DateTime, Utc};
use sqlx::PgPool;
use tracing::{error, instrument};

use crate::types::DeliveryResult;

/// Updates `push_pushnotification` after a delivery attempt.
///
/// `status` is set to `"delivered"` on success or `"failed"` on failure.
/// `delivered_at` is only populated on success.
///
/// Uses runtime-checked SQL (`sqlx::query`) rather than compile-time checked
/// (`sqlx::query!`) so that the service can be compiled without a live
/// database connection (e.g. in a Docker builder layer or CI cache step).
#[instrument(skip(pool, result), fields(notification_id = id))]
pub async fn update_notification_status(
    pool: &PgPool,
    id: i64,
    result: &DeliveryResult,
) -> Result<(), sqlx::Error> {
    let status = if result.success { "delivered" } else { "failed" };
    let delivered_at: Option<DateTime<Utc>> = if result.success {
        Some(Utc::now())
    } else {
        None
    };
    let error_msg = result.error.as_deref();

    let rows_affected = sqlx::query(
        r#"
        UPDATE push_pushnotification
           SET status       = $1,
               error        = $2,
               delivered_at = $3,
               updated_at   = NOW()
         WHERE id = $4
        "#,
    )
    .bind(status)
    .bind(error_msg)
    .bind(delivered_at)
    .bind(id)
    .execute(pool)
    .await?
    .rows_affected();

    if rows_affected == 0 {
        error!(
            notification_id = id,
            "No row updated — notification_id not found in push_pushnotification"
        );
    }

    Ok(())
}
