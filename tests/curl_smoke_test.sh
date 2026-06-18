#!/bin/bash
#
# Smoke Test Script for OwnFirebase Phase 1 MVP
# Manual testing with curl to verify core functionality:
# - User registration and authentication
# - JWT token generation
# - Project and collection management
# - Document CRUD operations
# - Query functionality
# - Security rules enforcement
#
# Usage: ./curl_smoke_test.sh [BASE_URL]
# Default BASE_URL: http://localhost:8000
#

set -e

BASE_URL="${1:-http://localhost:8000}"
API_PREFIX="$BASE_URL/api"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Global variables to store tokens and IDs
ACCESS_TOKEN=""
REFRESH_TOKEN=""
USER_ID=""
PROJECT_ID=""
PROJECT_ID_2=""

# Helper functions
log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_info() {
    echo -e "[INFO] $1"
}

check_status() {
    local expected=$1
    local actual=$2
    local message=$3

    if [ "$actual" -eq "$expected" ]; then
        log_success "$message (HTTP $actual)"
        return 0
    else
        log_error "$message (expected $expected, got $actual)"
        return 1
    fi
}

# ============================================================================
# AUTH TESTS
# ============================================================================

test_register_user() {
    log_test "Register new user"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_PREFIX/auth/register/" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "testuser@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "first_name": "Test",
            "last_name": "User"
        }')

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 201 "$http_code" "User registration" || return 1

    # Extract tokens
    ACCESS_TOKEN=$(echo "$body" | jq -r '.access // empty')
    REFRESH_TOKEN=$(echo "$body" | jq -r '.refresh // empty')
    USER_ID=$(echo "$body" | jq -r '.user.id // empty')

    if [ -z "$ACCESS_TOKEN" ] || [ -z "$REFRESH_TOKEN" ]; then
        log_error "Failed to extract tokens from response"
        echo "$body" | jq .
        return 1
    fi

    log_info "Access Token: ${ACCESS_TOKEN:0:20}..."
    log_info "User ID: $USER_ID"
}

test_login_user() {
    log_test "Login with registered user"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_PREFIX/auth/login/" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "testuser@example.com",
            "password": "SecurePass123!"
        }')

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 200 "$http_code" "User login" || return 1

    # Extract tokens
    ACCESS_TOKEN=$(echo "$body" | jq -r '.access // empty')
    REFRESH_TOKEN=$(echo "$body" | jq -r '.refresh // empty')

    if [ -z "$ACCESS_TOKEN" ]; then
        log_error "Failed to extract access token from login response"
        echo "$body" | jq .
        return 1
    fi

    log_info "Successfully logged in, access token: ${ACCESS_TOKEN:0:20}..."
}

test_get_current_user() {
    log_test "Get current user profile (/api/auth/me/)"

    response=$(curl -s -w "\n%{http_code}" -X GET "$API_PREFIX/auth/me/" \
        -H "Authorization: Bearer $ACCESS_TOKEN")

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 200 "$http_code" "Get current user" || return 1

    email=$(echo "$body" | jq -r '.user.email // empty')
    log_info "Current user email: $email"
}

test_refresh_token() {
    log_test "Refresh access token"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_PREFIX/auth/refresh/" \
        -H "Content-Type: application/json" \
        -d "{\"refresh\": \"$REFRESH_TOKEN\"}")

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 200 "$http_code" "Refresh token" || return 1

    new_access=$(echo "$body" | jq -r '.access // empty')
    if [ -z "$new_access" ]; then
        log_error "Failed to extract new access token"
        return 1
    fi

    ACCESS_TOKEN="$new_access"
    log_info "Token refreshed: ${ACCESS_TOKEN:0:20}..."
}

test_login_invalid_password() {
    log_test "Login fails with wrong password"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_PREFIX/auth/login/" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "testuser@example.com",
            "password": "WrongPassword123!"
        }')

    http_code=$(echo "$response" | tail -n 1)

    check_status 401 "$http_code" "Login with wrong password rejected" || return 1
}

test_logout_user() {
    log_test "Logout user (blacklist token)"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_PREFIX/auth/logout/" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"refresh\": \"$REFRESH_TOKEN\"}")

    http_code=$(echo "$response" | tail -n 1)

    check_status 204 "$http_code" "User logout" || return 1
}

# ============================================================================
# PROJECT & COLLECTION TESTS
# ============================================================================

test_create_project() {
    log_test "Create a new project"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_PREFIX/projects/" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "Test Project",
            "slug": "test-project-'"$(date +%s)"'",
            "description": "Test project for smoke testing",
            "is_active": true
        }')

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 201 "$http_code" "Create project" || return 1

    PROJECT_ID=$(echo "$body" | jq -r '.id // empty')
    if [ -z "$PROJECT_ID" ]; then
        log_error "Failed to extract project ID"
        echo "$body" | jq .
        return 1
    fi

    log_info "Project created: $PROJECT_ID"
}

test_create_collection() {
    log_test "Create a collection"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_PREFIX/projects/$PROJECT_ID/collections/" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "users",
            "path": "users",
            "schema": {
                "fields": {
                    "email": {"type": "string", "indexed": true},
                    "name": {"type": "string"},
                    "age": {"type": "number"}
                }
            }
        }')

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 201 "$http_code" "Create collection" || return 1

    collection_name=$(echo "$body" | jq -r '.name // empty')
    log_info "Collection created: $collection_name"
}

# ============================================================================
# DOCUMENT TESTS
# ============================================================================

test_create_document() {
    log_test "Create a document"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_PREFIX/projects/$PROJECT_ID/collections/users/docs/" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "doc_id": "alice",
            "data": {
                "name": "Alice",
                "email": "alice@example.com",
                "age": 30,
                "status": "active"
            }
        }')

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 201 "$http_code" "Create document" || return 1

    doc_id=$(echo "$body" | jq -r '.doc_id // empty')
    log_info "Document created: $doc_id"
}

test_get_document() {
    log_test "Retrieve a document by ID"

    response=$(curl -s -w "\n%{http_code}" -X GET "$API_PREFIX/projects/$PROJECT_ID/collections/users/docs/alice/" \
        -H "Authorization: Bearer $ACCESS_TOKEN")

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 200 "$http_code" "Get document" || return 1

    name=$(echo "$body" | jq -r '.data.name // empty')
    email=$(echo "$body" | jq -r '.data.email // empty')
    log_info "Retrieved document: $name ($email)"
}

test_update_document() {
    log_test "Update a document (PATCH)"

    response=$(curl -s -w "\n%{http_code}" -X PATCH "$API_PREFIX/projects/$PROJECT_ID/collections/users/docs/alice/" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "data": {"age": 31},
            "__v": 0
        }')

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 200 "$http_code" "Update document" || return 1

    new_age=$(echo "$body" | jq -r '.data.age // empty')
    log_info "Document updated, new age: $new_age"
}

test_list_documents() {
    log_test "List documents in collection"

    # Create a few more documents first
    for i in {1..3}; do
        curl -s -X POST "$API_PREFIX/projects/$PROJECT_ID/collections/users/docs/" \
            -H "Authorization: Bearer $ACCESS_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{
                \"doc_id\": \"user$i\",
                \"data\": {
                    \"name\": \"User $i\",
                    \"email\": \"user$i@example.com\",
                    \"status\": \"active\"
                }
            }" > /dev/null
    done

    response=$(curl -s -w "\n%{http_code}" -X GET "$API_PREFIX/projects/$PROJECT_ID/collections/users/docs/" \
        -H "Authorization: Bearer $ACCESS_TOKEN")

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 200 "$http_code" "List documents" || return 1

    count=$(echo "$body" | jq -r '.count // empty')
    log_info "Total documents in collection: $count"
}

test_query_documents() {
    log_test "Query documents with WHERE filter"

    # Query for active users
    query='{"collection_path": "users", "where": [{"field": "status", "op": "==", "value": "active"}]}'
    query_encoded=$(echo -n "$query" | jq -sRr @uri)

    response=$(curl -s -w "\n%{http_code}" -X GET "$API_PREFIX/projects/$PROJECT_ID/collections/users/docs/?query=$(echo -n "$query" | jq -sRr @uri)" \
        -H "Authorization: Bearer $ACCESS_TOKEN")

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 200 "$http_code" "Query documents" || return 1

    count=$(echo "$body" | jq -r '.count // empty')
    log_info "Found $count documents matching query"
}

test_delete_document() {
    log_test "Delete a document"

    response=$(curl -s -w "\n%{http_code}" -X DELETE "$API_PREFIX/projects/$PROJECT_ID/collections/users/docs/user1/" \
        -H "Authorization: Bearer $ACCESS_TOKEN")

    http_code=$(echo "$response" | tail -n 1)

    check_status 204 "$http_code" "Delete document" || return 1
}

# ============================================================================
# SECURITY & PERMISSION TESTS
# ============================================================================

test_unauthorized_access() {
    log_test "Unauthorized user cannot access project"

    # Register a second user
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_PREFIX/auth/register/" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "otheruser@example.com",
            "password": "OtherPass123!",
            "password_confirm": "OtherPass123!"
        }')

    body=$(echo "$response" | head -n -1)
    other_access=$(echo "$body" | jq -r '.access // empty')

    # Try to access original user's project
    response=$(curl -s -w "\n%{http_code}" -X GET "$API_PREFIX/projects/$PROJECT_ID/collections/" \
        -H "Authorization: Bearer $other_access")

    http_code=$(echo "$response" | tail -n 1)

    # Should be 403 Forbidden
    if [ "$http_code" -eq 403 ]; then
        log_success "Unauthorized access properly rejected (HTTP 403)"
        return 0
    else
        log_error "Expected 403, got $http_code"
        return 1
    fi
}

test_document_version_conflict() {
    log_test "Version conflict prevents concurrent updates"

    # Try to update with wrong version
    response=$(curl -s -w "\n%{http_code}" -X PATCH "$API_PREFIX/projects/$PROJECT_ID/collections/users/docs/alice/" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "data": {"age": 99},
            "__v": 999
        }')

    http_code=$(echo "$response" | tail -n 1)

    check_status 409 "$http_code" "Version conflict detected" || return 1
}

# ============================================================================
# TRANSACTION TESTS
# ============================================================================

test_transaction_batch_write() {
    log_test "Transaction: batch write multiple documents"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_PREFIX/projects/$PROJECT_ID/transaction/" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "writes": [
                {
                    "op": "set",
                    "path": "users/bob",
                    "data": {"name": "Bob", "email": "bob@example.com", "status": "active"}
                },
                {
                    "op": "set",
                    "path": "users/charlie",
                    "data": {"name": "Charlie", "email": "charlie@example.com", "status": "inactive"}
                }
            ]
        }')

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)

    check_status 200 "$http_code" "Batch transaction" || return 1

    success_count=$(echo "$body" | jq '[.results[] | select(.success == true)] | length' 2>/dev/null || echo "0")
    log_info "Transaction results: $success_count operations succeeded"
}

# ============================================================================
# MAIN TEST SUITE EXECUTION
# ============================================================================

main() {
    echo ""
    echo "=========================================="
    echo "OwnFirebase Phase 1 MVP - Smoke Tests"
    echo "=========================================="
    echo "Base URL: $BASE_URL"
    echo ""

    # Check if server is reachable
    if ! curl -s "$BASE_URL/health/" > /dev/null 2>&1; then
        log_error "Server not reachable at $BASE_URL"
        log_info "Make sure the Django server is running: python manage.py runserver"
        exit 1
    fi

    echo ""
    echo "--- Authentication Tests ---"
    test_register_user || exit 1
    test_login_user || exit 1
    test_get_current_user || exit 1
    test_refresh_token || exit 1
    test_login_invalid_password || exit 1

    echo ""
    echo "--- Project & Collection Tests ---"
    test_create_project || exit 1
    test_create_collection || exit 1

    echo ""
    echo "--- Document CRUD Tests ---"
    test_create_document || exit 1
    test_get_document || exit 1
    test_update_document || exit 1
    test_list_documents || exit 1
    test_query_documents || exit 1
    test_delete_document || exit 1

    echo ""
    echo "--- Security & Permission Tests ---"
    test_unauthorized_access || exit 1
    test_document_version_conflict || exit 1

    echo ""
    echo "--- Transaction Tests ---"
    test_transaction_batch_write || exit 1

    # Logout at the end
    test_logout_user || exit 1

    echo ""
    echo "=========================================="
    echo -e "${GREEN}All smoke tests passed!${NC}"
    echo "=========================================="
}

# Run main if script is executed directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
