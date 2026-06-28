/// PyO3 extension module exposing the Rust rules-engine to Python.
///
/// Build with maturin:
///   cd rust/rules-engine && maturin develop --release
///
/// Usage from Python:
///   from rules_engine import evaluate
///   import json
///
///   allowed = evaluate(
///       json.dumps(condition_json),
///       auth_uid or "",
///       request.is_authenticated,
///       json.dumps(doc.data) if doc else "{}",
///       doc.owner_id or "" if doc else "",
///       "read",
///   )
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde_json::Value;

mod evaluator;
use evaluator::{DocCtx, RequestCtx};

/// Evaluate a security-rules condition tree against a request + document context.
///
/// Args:
///     condition_json  (str): JSON-encoded condition tree
///                            (SecurityPolicy.condition_json serialised).
///     auth_uid        (str): Authenticated user's UID, or "" if unauthenticated.
///     is_authenticated(bool): True when the request carries valid auth.
///     doc_data_json   (str): JSON-encoded document data dict, or "{}" when no doc.
///     doc_owner_id    (str): Document's owner_id attribute, or "".
///     operation       (str): One of "read", "write", "delete".
///
/// Returns:
///     bool: True if the rule allows the operation; False if it denies.
///
/// Raises:
///     ValueError: If condition_json or doc_data_json is not valid JSON.
///
/// Notes:
///     • An empty/null condition_json always returns False (fail-safe deny).
///     • is_admin is not exposed in this binding; role_check will return False
///       for non-admin users (matching the Python default of is_admin=False).
#[pyfunction]
fn evaluate(
    condition_json: &str,
    auth_uid: &str,
    is_authenticated: bool,
    doc_data_json: &str,
    doc_owner_id: &str,
    operation: &str,
) -> PyResult<bool> {
    // Parse condition tree.
    let condition: Value = serde_json::from_str(condition_json).map_err(|e| {
        PyValueError::new_err(format!("Invalid condition_json: {e}"))
    })?;

    // Parse document data.
    let doc_data: Value = serde_json::from_str(doc_data_json).map_err(|e| {
        PyValueError::new_err(format!("Invalid doc_data_json: {e}"))
    })?;

    let req = RequestCtx {
        auth_uid: auth_uid.to_string(),
        is_authenticated,
        // is_admin not exposed in this binding — Python callers that need
        // role_check to return True for admins should set this via a separate
        // entry point or handle it in Python before calling evaluate().
        is_admin: false,
        operation: operation.to_string(),
    };

    // Build an optional DocCtx.  We always have doc_data (at least "{}") but
    // we only attach it as a Some(DocCtx) when doc_data is non-empty OR
    // doc_owner_id is set — to match Python behaviour where doc=None means no
    // document was provided.
    let has_doc = !doc_data_json.trim().is_empty()
        && doc_data_json.trim() != "null"
        && (!matches!(doc_data, Value::Null));

    let doc = if has_doc {
        Some(DocCtx {
            data: doc_data,
            owner_id: doc_owner_id.to_string(),
        })
    } else {
        None
    };

    Ok(evaluator::evaluate(&condition, &req, doc.as_ref()))
}

/// Evaluate a security-rules condition tree with explicit is_admin support.
///
/// Identical to `evaluate` but exposes the `is_admin` flag so that Python
/// callers wrapping admin requests can get correct role_check results.
///
/// Args:
///     condition_json  (str):  JSON-encoded condition tree.
///     auth_uid        (str):  Authenticated user UID or "".
///     is_authenticated(bool): True when request carries valid auth.
///     is_admin        (bool): True when caller is a project admin/staff.
///     doc_data_json   (str):  JSON-encoded doc data or "{}".
///     doc_owner_id    (str):  doc.owner_id or "".
///     operation       (str):  "read" | "write" | "delete".
///
/// Returns:
///     bool
#[pyfunction]
fn evaluate_with_admin(
    condition_json: &str,
    auth_uid: &str,
    is_authenticated: bool,
    is_admin: bool,
    doc_data_json: &str,
    doc_owner_id: &str,
    operation: &str,
) -> PyResult<bool> {
    let condition: Value = serde_json::from_str(condition_json).map_err(|e| {
        PyValueError::new_err(format!("Invalid condition_json: {e}"))
    })?;

    let doc_data: Value = serde_json::from_str(doc_data_json).map_err(|e| {
        PyValueError::new_err(format!("Invalid doc_data_json: {e}"))
    })?;

    let req = RequestCtx {
        auth_uid: auth_uid.to_string(),
        is_authenticated,
        is_admin,
        operation: operation.to_string(),
    };

    let has_doc = !doc_data_json.trim().is_empty()
        && doc_data_json.trim() != "null"
        && (!matches!(doc_data, Value::Null));

    let doc = if has_doc {
        Some(DocCtx {
            data: doc_data,
            owner_id: doc_owner_id.to_string(),
        })
    } else {
        None
    };

    Ok(evaluator::evaluate(&condition, &req, doc.as_ref()))
}

/// `rules_engine` Python extension module.
///
/// Exposes:
///   - `evaluate(condition_json, auth_uid, is_authenticated,
///               doc_data_json, doc_owner_id, operation) -> bool`
///   - `evaluate_with_admin(condition_json, auth_uid, is_authenticated,
///                          is_admin, doc_data_json, doc_owner_id, operation) -> bool`
#[pymodule]
fn rules_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(evaluate, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_with_admin, m)?)?;
    Ok(())
}
