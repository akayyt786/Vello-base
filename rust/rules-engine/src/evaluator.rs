/// Security Rules DSL evaluator — Rust port of rules/dsl.py RuleEngine.
///
/// Condition JSON schema (mirrors Python):
///   { "operator": "and"|"or",
///     "conditions": [
///       { "type": "auth_check"|"field_check"|"owner_check"|"role_check",
///         "value": { … } }
///     ] }
use regex::Regex;
use serde_json::Value;

// ─── Context types ────────────────────────────────────────────────────────────

/// Mirrors Python RequestContext fields accessible from Rust.
/// `is_admin` is included to support role_check parity with the Python impl;
/// it defaults to `false` when called through the PyO3 binding (matching the
/// Python default of `is_admin = False`).
pub struct RequestCtx {
    pub auth_uid: String,
    pub is_authenticated: bool,
    pub is_admin: bool,
    /// Kept for API parity with Python RequestContext; not yet used inside
    /// atomic evaluators (operation-level allow/deny is handled upstream).
    #[allow(dead_code)]
    pub operation: String,
}

/// Mirrors Python Document fields.
/// `owner_id` is the direct attribute; `data` is the document's JSON payload.
pub struct DocCtx {
    pub data: Value,
    pub owner_id: String,
}

// ─── Public entry point ───────────────────────────────────────────────────────

/// Evaluate a condition tree against the given request + optional document.
///
/// Returns `false` for an empty/null condition (fail-safe deny), mirroring:
///   if not condition_json: return False
pub fn evaluate(condition: &Value, req: &RequestCtx, doc: Option<&DocCtx>) -> bool {
    match condition {
        // Null top-level → deny
        Value::Null => false,
        // Empty object {} → deny (Python `if not condition_json`)
        Value::Object(m) if m.is_empty() => false,
        _ => evaluate_condition(condition, req, doc),
    }
}

// ─── Condition tree ───────────────────────────────────────────────────────────

/// Recursively evaluate an `operator`/`conditions` node.
///
/// Mirrors Python `_evaluate_condition`.
fn evaluate_condition(condition: &Value, req: &RequestCtx, doc: Option<&DocCtx>) -> bool {
    let obj = match condition.as_object() {
        Some(o) => o,
        None => return false,
    };

    let operator = obj
        .get("operator")
        .and_then(Value::as_str)
        .unwrap_or("and");

    let conditions = match obj.get("conditions").and_then(Value::as_array) {
        Some(c) => c,
        None => {
            // No `conditions` key — treat like empty list:
            // `all([])` → true for "and", `any([])` → false for "or"
            return operator == "and";
        }
    };

    match operator {
        // all(…) — empty → true
        "and" => conditions
            .iter()
            .all(|cond| evaluate_atomic(cond, req, doc)),
        // any(…) — empty → false
        "or" => conditions
            .iter()
            .any(|cond| evaluate_atomic(cond, req, doc)),
        _ => false,
    }
}

/// Dispatch a single atomic condition by `type`.
///
/// Mirrors Python `_evaluate_atomic`.
fn evaluate_atomic(condition: &Value, req: &RequestCtx, doc: Option<&DocCtx>) -> bool {
    let obj = match condition.as_object() {
        Some(o) => o,
        None => return false,
    };

    let cond_type = match obj.get("type").and_then(Value::as_str) {
        Some(t) => t,
        None => return false,
    };

    let value = obj.get("value").unwrap_or(&Value::Null);

    match cond_type {
        "auth_check" => eval_auth_check(value, req),
        "field_check" => eval_field_check(value, req, doc),
        "owner_check" => eval_owner_check(value, req, doc),
        "role_check" => eval_role_check(value, req),
        _ => false,
    }
}

// ─── Atomic evaluators ────────────────────────────────────────────────────────

/// Check `request.auth` conditions.
///
/// Example value: `{"field": "request.auth", "op": "!=", "rhs": "null"}`
///
/// Mirrors Python `_eval_auth_check`.
fn eval_auth_check(value: &Value, req: &RequestCtx) -> bool {
    let obj = match value.as_object() {
        Some(o) => o,
        None => return false,
    };

    let field = obj
        .get("field")
        .and_then(Value::as_str)
        .unwrap_or("request.auth");
    let op = obj.get("op").and_then(Value::as_str).unwrap_or("!=");
    let rhs = obj.get("rhs").and_then(Value::as_str).unwrap_or("null");

    // In Python: lhs = request.auth_user if is_authenticated else None
    // We model lhs presence as is_authenticated.
    let lhs_present = field == "request.auth" && req.is_authenticated;

    match op {
        // (lhs is None) != (rhs == 'null')
        "!=" => (!lhs_present) != (rhs == "null"),
        // (lhs is None) == (rhs == 'null')
        "==" => (!lhs_present) == (rhs == "null"),
        "exists" => lhs_present,
        _ => false,
    }
}

/// Check a document field condition.
///
/// Example value (rhs_field): `{"path": "data.owner", "op": "==", "rhs_field": "request.auth.uid"}`
/// Example value (literal rhs): `{"path": "data.role",  "op": "==", "rhs": "admin"}`
///
/// Mirrors Python `_eval_field_check`.
fn eval_field_check(value: &Value, req: &RequestCtx, doc: Option<&DocCtx>) -> bool {
    let doc = match doc {
        Some(d) => d,
        None => return false,
    };

    let obj = match value.as_object() {
        Some(o) => o,
        None => return false,
    };

    let path = obj.get("path").and_then(Value::as_str).unwrap_or("");
    let op = obj.get("op").and_then(Value::as_str).unwrap_or("==");

    // Strip "resource.data." or "data." prefix — get_field traverses doc.data directly.
    let field_path = strip_data_prefix(path);

    // Left-hand side: document field value (Value::Null if missing).
    let lhs = get_field(&doc.data, field_path);

    // Right-hand side: resolved field expression or literal value.
    let rhs = if let Some(rhs_field) = obj.get("rhs_field").and_then(Value::as_str) {
        resolve_field(rhs_field, req, Some(doc))
    } else {
        obj.get("rhs").cloned().unwrap_or(Value::Null)
    };

    compare(&lhs, op, &rhs)
}

/// Check if the authenticated user is the document owner.
///
/// Example value: `{"field": "owner_id"}`
///
/// Strategy (mirrors Python `_eval_owner_check`):
///   1. Try `doc.owner_id` (the direct attribute on DocCtx).
///   2. Fall back to `doc.data[field]` (nested field traversal).
///
/// Mirrors Python `_eval_owner_check`.
fn eval_owner_check(value: &Value, req: &RequestCtx, doc: Option<&DocCtx>) -> bool {
    if !req.is_authenticated {
        return false;
    }
    let doc = match doc {
        Some(d) => d,
        None => return false,
    };

    let obj = match value.as_object() {
        Some(o) => o,
        None => return false,
    };

    let field = obj.get("field").and_then(Value::as_str).unwrap_or("owner_id");

    // Step 1: check direct owner_id attribute (getattr equivalent).
    if field == "owner_id" && !doc.owner_id.is_empty() {
        return req.auth_uid == doc.owner_id;
    }

    // Step 2: traverse doc.data for the field.
    let owner_val = get_field(&doc.data, field);
    match &owner_val {
        Value::Null => false,
        Value::String(s) => !s.is_empty() && req.auth_uid == s.as_str(),
        // Handle numeric owner IDs stored as JSON numbers (str(owner_id) in Python).
        Value::Number(n) => req.auth_uid == n.to_string(),
        _ => false,
    }
}

/// Check user's project role.
///
/// For Phase 1: only honours `is_admin`; complex role lookups are not
/// implemented (matching Python behaviour where anything beyond is_admin
/// returns False).
///
/// Mirrors Python `_eval_role_check`.
fn eval_role_check(_value: &Value, req: &RequestCtx) -> bool {
    if !req.is_authenticated {
        return false;
    }
    // Phase 1: admin bypass only.
    req.is_admin
}

// ─── Field resolution ─────────────────────────────────────────────────────────

/// Resolve a field expression to a JSON value.
///
/// Supported expressions:
///   "request.auth.uid"       → req.auth_uid
///   "request.auth.<other>"   → Value::Null (custom claims not available here)
///   "resource.data.<path>"   → doc.data nested traversal
///   "data.<path>"            → doc.data nested traversal
///
/// Mirrors Python `_resolve_field`.
fn resolve_field(field_expr: &str, req: &RequestCtx, doc: Option<&DocCtx>) -> Value {
    if let Some(attr) = field_expr.strip_prefix("request.auth.") {
        if attr == "uid" {
            if req.auth_uid.is_empty() {
                Value::Null
            } else {
                Value::String(req.auth_uid.clone())
            }
        } else {
            // Custom claim path — not available in this context.
            Value::Null
        }
    } else if let Some(rest) = field_expr.strip_prefix("resource.data.") {
        doc.map(|d| get_field(&d.data, rest))
            .unwrap_or(Value::Null)
    } else if let Some(rest) = field_expr.strip_prefix("data.") {
        doc.map(|d| get_field(&d.data, rest))
            .unwrap_or(Value::Null)
    } else {
        Value::Null
    }
}

// ─── Field traversal ──────────────────────────────────────────────────────────

/// Traverse a JSON object using dot-notation path.
///
/// Returns `Value::Null` for any missing key or non-object intermediate value,
/// mirroring Python `Document.get_field` which returns `None` in those cases.
pub fn get_field(data: &Value, path: &str) -> Value {
    let mut current = data;
    // Avoid allocation for single-segment paths (the common case).
    for part in path.split('.') {
        match current {
            Value::Object(map) => match map.get(part) {
                Some(v) => current = v,
                None => return Value::Null,
            },
            _ => return Value::Null,
        }
    }
    current.clone()
}

/// Strip "resource.data." or leading "data." from a field path.
///
/// Mirrors the Python one-liner in `_eval_field_check`:
///   `path.replace('resource.data.', '').replace('data.', '', 1)`
fn strip_data_prefix(path: &str) -> &str {
    if let Some(rest) = path.strip_prefix("resource.data.") {
        rest
    } else if let Some(rest) = path.strip_prefix("data.") {
        rest
    } else {
        path
    }
}

// ─── Value coercion & comparison ─────────────────────────────────────────────

/// Normalize boolean strings to JSON booleans.
///
/// Mirrors Python `_coerce`:
///   "true"  (any case) → true
///   "false" (any case) → false
///   everything else    → unchanged
fn coerce(v: Value) -> Value {
    match &v {
        Value::String(s) => {
            let lower = s.to_lowercase();
            match lower.as_str() {
                "true" => Value::Bool(true),
                "false" => Value::Bool(false),
                _ => v,
            }
        }
        _ => v,
    }
}

/// Compare two JSON values using the given operator.
///
/// Operators: `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `contains`, `matches`
///
/// Mirrors Python `_compare`:
///   • `==` / `!=` coerce both sides first (bool-string normalization).
///   • `<` / `<=` / `>` / `>=` require both values non-null and same kind.
///   • `in`:       lhs ∈ rhs (rhs must be a JSON array).
///   • `contains`: rhs ∈ lhs (lhs must be a JSON array or string).
///   • `matches`:  regex match of lhs (string) against rhs (pattern string).
pub fn compare(lhs: &Value, op: &str, rhs: &Value) -> bool {
    match op {
        "==" | "!=" => {
            let lhs_c = coerce(lhs.clone());
            let rhs_c = coerce(rhs.clone());
            if op == "==" {
                lhs_c == rhs_c
            } else {
                lhs_c != rhs_c
            }
        }

        "<" | "<=" | ">" | ">=" => {
            // Mirrors: `(lhs is not None and rhs is not None) and lhs <op> rhs`
            if lhs.is_null() || rhs.is_null() {
                return false;
            }
            compare_ordered(lhs, rhs, op)
        }

        "in" => {
            // `lhs in rhs` — rhs must be a JSON array.
            match rhs {
                Value::Array(arr) => arr.contains(lhs),
                _ => false,
            }
        }

        "contains" => {
            // `rhs in lhs` — lhs is array or string.
            match lhs {
                Value::Array(arr) => arr.contains(rhs),
                Value::String(s) => match rhs {
                    Value::String(r) => s.contains(r.as_str()),
                    _ => false,
                },
                _ => false,
            }
        }

        "matches" => {
            // Regex match: re.match(rhs_pattern, lhs_string)
            match (lhs, rhs) {
                (Value::String(s), Value::String(pattern)) => {
                    Regex::new(pattern)
                        .map(|re| re.is_match(s))
                        .unwrap_or(false)
                }
                _ => false,
            }
        }

        _ => false,
    }
}

/// Order-based comparison for `<`, `<=`, `>`, `>=`.
///
/// Both `Value::Number` (cast to f64) and `Value::String` comparisons are
/// supported, mirroring Python's dynamic operators.
fn compare_ordered(lhs: &Value, rhs: &Value, op: &str) -> bool {
    use std::cmp::Ordering;

    // Numbers: cast both to f64.
    if let (Some(a), Some(b)) = (lhs.as_f64(), rhs.as_f64()) {
        let ord = a.partial_cmp(&b).unwrap_or(Ordering::Equal);
        return match op {
            "<" => ord == Ordering::Less,
            "<=" => ord != Ordering::Greater,
            ">" => ord == Ordering::Greater,
            ">=" => ord != Ordering::Less,
            _ => false,
        };
    }

    // Strings: lexicographic.
    if let (Value::String(a), Value::String(b)) = (lhs, rhs) {
        let ord = a.cmp(b);
        return match op {
            "<" => ord == Ordering::Less,
            "<=" => ord != Ordering::Greater,
            ">" => ord == Ordering::Greater,
            ">=" => ord != Ordering::Less,
            _ => false,
        };
    }

    // Mismatched types or unsupported → false (mirrors Python TypeError → False).
    false
}

// ─── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn req(uid: &str, authenticated: bool) -> RequestCtx {
        RequestCtx {
            auth_uid: uid.to_string(),
            is_authenticated: authenticated,
            is_admin: false,
            operation: "read".to_string(),
        }
    }

    fn doc(data: Value, owner_id: &str) -> DocCtx {
        DocCtx {
            data,
            owner_id: owner_id.to_string(),
        }
    }

    // ── evaluate (top-level) ──────────────────────────────────────────────────

    #[test]
    fn empty_condition_denies() {
        let r = req("u1", true);
        assert!(!evaluate(&Value::Null, &r, None));
        assert!(!evaluate(&json!({}), &r, None));
    }

    // ── auth_check ────────────────────────────────────────────────────────────

    #[test]
    fn auth_check_not_null_authenticated() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "auth_check",
                "value": {"field": "request.auth", "op": "!=", "rhs": "null"}
            }]
        });
        let r = req("u1", true);
        assert!(evaluate(&cond, &r, None));
    }

    #[test]
    fn auth_check_not_null_unauthenticated() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "auth_check",
                "value": {"field": "request.auth", "op": "!=", "rhs": "null"}
            }]
        });
        let r = req("", false);
        assert!(!evaluate(&cond, &r, None));
    }

    #[test]
    fn auth_check_eq_null_unauthenticated() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "auth_check",
                "value": {"field": "request.auth", "op": "==", "rhs": "null"}
            }]
        });
        let r = req("", false);
        assert!(evaluate(&cond, &r, None));
    }

    #[test]
    fn auth_check_exists_authenticated() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "auth_check",
                "value": {"field": "request.auth", "op": "exists", "rhs": "null"}
            }]
        });
        assert!(evaluate(&cond, &req("u1", true), None));
        assert!(!evaluate(&cond, &req("", false), None));
    }

    // ── field_check ───────────────────────────────────────────────────────────

    #[test]
    fn field_check_literal_eq() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "field_check",
                "value": {"path": "data.role", "op": "==", "rhs": "admin"}
            }]
        });
        let d = doc(json!({"role": "admin"}), "");
        assert!(evaluate(&cond, &req("u1", true), Some(&d)));
    }

    #[test]
    fn field_check_resource_data_prefix() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "field_check",
                "value": {"path": "resource.data.active", "op": "==", "rhs": "true"}
            }]
        });
        // lhs = true (bool), rhs = "true" (string) → coerce → true == true
        let d = doc(json!({"active": true}), "");
        assert!(evaluate(&cond, &req("u1", true), Some(&d)));
    }

    #[test]
    fn field_check_rhs_field_uid() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "field_check",
                "value": {"path": "data.owner", "op": "==", "rhs_field": "request.auth.uid"}
            }]
        });
        let d = doc(json!({"owner": "u42"}), "");
        assert!(evaluate(&cond, &req("u42", true), Some(&d)));
        assert!(!evaluate(&cond, &req("u99", true), Some(&d)));
    }

    #[test]
    fn field_check_nested_path() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "field_check",
                "value": {"path": "data.meta.status", "op": "==", "rhs": "active"}
            }]
        });
        let d = doc(json!({"meta": {"status": "active"}}), "");
        assert!(evaluate(&cond, &req("u1", true), Some(&d)));
    }

    #[test]
    fn field_check_missing_field_is_null() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "field_check",
                "value": {"path": "data.missing", "op": "==", "rhs": "x"}
            }]
        });
        let d = doc(json!({}), "");
        assert!(!evaluate(&cond, &req("u1", true), Some(&d)));
    }

    #[test]
    fn field_check_no_doc_denies() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "field_check",
                "value": {"path": "data.x", "op": "==", "rhs": "y"}
            }]
        });
        assert!(!evaluate(&cond, &req("u1", true), None));
    }

    // ── owner_check ───────────────────────────────────────────────────────────

    #[test]
    fn owner_check_direct_owner_id() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "owner_check",
                "value": {"field": "owner_id"}
            }]
        });
        let d = doc(json!({}), "u42");
        assert!(evaluate(&cond, &req("u42", true), Some(&d)));
        assert!(!evaluate(&cond, &req("u99", true), Some(&d)));
    }

    #[test]
    fn owner_check_from_data() {
        let cond = json!({
            "operator": "and",
            "conditions": [{
                "type": "owner_check",
                "value": {"field": "created_by"}
            }]
        });
        let d = doc(json!({"created_by": "u55"}), "");
        assert!(evaluate(&cond, &req("u55", true), Some(&d)));
        assert!(!evaluate(&cond, &req("u00", true), Some(&d)));
    }

    #[test]
    fn owner_check_unauthenticated_denies() {
        let cond = json!({
            "operator": "and",
            "conditions": [{"type": "owner_check", "value": {"field": "owner_id"}}]
        });
        let d = doc(json!({}), "u1");
        assert!(!evaluate(&cond, &req("", false), Some(&d)));
    }

    // ── role_check ────────────────────────────────────────────────────────────

    #[test]
    fn role_check_admin_flag() {
        let cond = json!({
            "operator": "and",
            "conditions": [{"type": "role_check", "value": {"role": "admin"}}]
        });
        let admin_req = RequestCtx {
            auth_uid: "a1".to_string(),
            is_authenticated: true,
            is_admin: true,
            operation: "read".to_string(),
        };
        assert!(evaluate(&cond, &admin_req, None));
        assert!(!evaluate(&cond, &req("a1", true), None));
    }

    // ── operator: or ─────────────────────────────────────────────────────────

    #[test]
    fn or_operator_any_true() {
        let cond = json!({
            "operator": "or",
            "conditions": [
                {"type": "field_check", "value": {"path": "data.a", "op": "==", "rhs": "x"}},
                {"type": "field_check", "value": {"path": "data.b", "op": "==", "rhs": "y"}}
            ]
        });
        let d = doc(json!({"a": "nope", "b": "y"}), "");
        assert!(evaluate(&cond, &req("u1", true), Some(&d)));
    }

    #[test]
    fn and_operator_all_must_pass() {
        let cond = json!({
            "operator": "and",
            "conditions": [
                {"type": "auth_check", "value": {"field": "request.auth", "op": "!=", "rhs": "null"}},
                {"type": "field_check", "value": {"path": "data.owner", "op": "==", "rhs_field": "request.auth.uid"}}
            ]
        });
        let d = doc(json!({"owner": "u7"}), "");
        assert!(evaluate(&cond, &req("u7", true), Some(&d)));
        assert!(!evaluate(&cond, &req("u8", true), Some(&d)));
        assert!(!evaluate(&cond, &req("", false), Some(&d)));
    }

    // ── compare helpers ───────────────────────────────────────────────────────

    #[test]
    fn compare_bool_string_coerce() {
        assert!(compare(&Value::Bool(true), "==", &Value::String("true".into())));
        assert!(compare(&Value::Bool(false), "==", &Value::String("false".into())));
        assert!(compare(&Value::String("True".into()), "==", &Value::Bool(true)));
        assert!(!compare(&Value::Bool(true), "==", &Value::String("false".into())));
    }

    #[test]
    fn compare_numeric_ordering() {
        assert!(compare(&json!(5), "<", &json!(10)));
        assert!(!compare(&json!(10), "<", &json!(5)));
        assert!(compare(&json!(5.0), ">=", &json!(5)));
        assert!(compare(&json!(3), "<=", &json!(3)));
    }

    #[test]
    fn compare_in_operator() {
        assert!(compare(&json!("admin"), "in", &json!(["admin", "editor"])));
        assert!(!compare(&json!("viewer"), "in", &json!(["admin", "editor"])));
    }

    #[test]
    fn compare_contains_array() {
        assert!(compare(&json!(["a", "b"]), "contains", &json!("a")));
        assert!(!compare(&json!(["a", "b"]), "contains", &json!("c")));
    }

    #[test]
    fn compare_contains_string() {
        assert!(compare(&json!("hello world"), "contains", &json!("world")));
        assert!(!compare(&json!("hello"), "contains", &json!("xyz")));
    }

    #[test]
    fn compare_matches_regex() {
        assert!(compare(&json!("test@example.com"), "matches", &json!(r"^\S+@\S+\.\S+$")));
        assert!(!compare(&json!("not-an-email"), "matches", &json!(r"^\S+@\S+\.\S+$")));
    }

    #[test]
    fn compare_null_ordering_is_false() {
        assert!(!compare(&Value::Null, "<", &json!(5)));
        assert!(!compare(&json!(5), ">", &Value::Null));
    }

    #[test]
    fn get_field_nested() {
        let data = json!({"a": {"b": {"c": 42}}});
        assert_eq!(get_field(&data, "a.b.c"), json!(42));
        assert_eq!(get_field(&data, "a.b.missing"), Value::Null);
        assert_eq!(get_field(&data, "x"), Value::Null);
    }
}
