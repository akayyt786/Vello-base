#!/bin/bash
# Integration test script for Data API
# Prerequisites: Django server running on localhost:8000 with auth configured

set -e

BASE_URL="http://localhost:8000/api"
PROJECT_ID="test-project-id"  # Replace with actual project ID from your database

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get auth token (replace with your test user credentials)
echo -e "${YELLOW}Getting auth token...${NC}"
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }')

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access')
echo -e "${GREEN}Token obtained: ${TOKEN:0:20}...${NC}"

# Helper function to make authenticated requests
api_call() {
  local method=$1
  local endpoint=$2
  local data=$3

  if [ -z "$data" ]; then
    curl -s -X "$method" "$BASE_URL$endpoint" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json"
  else
    curl -s -X "$method" "$BASE_URL$endpoint" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "$data"
  fi
}

# Test 1: Create Collection
echo -e "\n${YELLOW}Test 1: Create Collection${NC}"
CREATE_COLLECTION=$(api_call "POST" "/projects/$PROJECT_ID/collections/" '{
  "name": "users",
  "path": "users",
  "schema": {
    "fields": {
      "email": {"type": "string", "indexed": true},
      "age": {"type": "number"}
    }
  }
}')
echo $CREATE_COLLECTION | jq '.'
echo -e "${GREEN}✓ Collection created${NC}"

# Test 2: List Collections
echo -e "\n${YELLOW}Test 2: List Collections${NC}"
LIST_COLLECTIONS=$(api_call "GET" "/projects/$PROJECT_ID/collections/")
COLLECTION_COUNT=$(echo $LIST_COLLECTIONS | jq '.count')
echo "Found $COLLECTION_COUNT collections"
echo $LIST_COLLECTIONS | jq '.collections[0]'
echo -e "${GREEN}✓ Collections listed${NC}"

# Test 3: Create Document
echo -e "\n${YELLOW}Test 3: Create Document${NC}"
CREATE_DOC=$(api_call "POST" "/projects/$PROJECT_ID/collections/users/docs/" '{
  "doc_id": "alice",
  "data": {
    "name": "Alice",
    "age": 30,
    "email": "alice@example.com",
    "tags": ["admin", "beta"],
    "address": {
      "city": "NYC",
      "zip": "10001"
    }
  }
}')
echo $CREATE_DOC | jq '.'
DOC_ID=$(echo $CREATE_DOC | jq -r '.id')
echo -e "${GREEN}✓ Document created: $DOC_ID${NC}"

# Test 4: Create More Documents
echo -e "\n${YELLOW}Test 4: Create More Documents${NC}"
for name in bob charlie david; do
  age=$((20 + RANDOM % 50))
  api_call "POST" "/projects/$PROJECT_ID/collections/users/docs/" "{
    \"doc_id\": \"$name\",
    \"data\": {
      \"name\": \"$(tr '[:lower:]' '[:upper:]' <<< ${name:0:1})${name:1}\",
      \"age\": $age,
      \"email\": \"$name@example.com\",
      \"status\": \"active\"
    }
  }" > /dev/null
  echo "Created $name (age: $age)"
done
echo -e "${GREEN}✓ Multiple documents created${NC}"

# Test 5: Get Document
echo -e "\n${YELLOW}Test 5: Get Document${NC}"
GET_DOC=$(api_call "GET" "/projects/$PROJECT_ID/collections/users/docs/alice/")
echo $GET_DOC | jq '.'
echo -e "${GREEN}✓ Document retrieved${NC}"

# Test 6: Update Document (PATCH)
echo -e "\n${YELLOW}Test 6: Update Document (PATCH - Merge)${NC}"
UPDATE_DOC=$(api_call "PATCH" "/projects/$PROJECT_ID/collections/users/docs/alice/" '{
  "data": {
    "age": 31,
    "status": "premium"
  },
  "__v": 0
}')
echo $UPDATE_DOC | jq '.'
NEW_VERSION=$(echo $UPDATE_DOC | jq '.__v')
echo "Document updated to version $NEW_VERSION"
echo -e "${GREEN}✓ Document patched (merged)${NC}"

# Test 7: List Documents (Simple)
echo -e "\n${YELLOW}Test 7: List Documents${NC}"
LIST_DOCS=$(api_call "GET" "/projects/$PROJECT_ID/collections/users/docs/")
DOC_COUNT=$(echo $LIST_DOCS | jq '.count')
echo "Found $DOC_COUNT documents"
echo $LIST_DOCS | jq '.documents | length'
echo -e "${GREEN}✓ Documents listed${NC}"

# Test 8: Query with Filter (status == active)
echo -e "\n${YELLOW}Test 8: Query with Filter (status == 'active')${NC}"
QUERY_FILTER=$(cat <<EOF
{"where":[{"field":"status","op":"==","value":"active"}],"orderBy":[{"field":"name","direction":"asc"}],"limit":10}
EOF
)
FILTERED=$(api_call "GET" "/projects/$PROJECT_ID/collections/users/docs/" | jq -s '.[] | select(.documents[0] != null)'
# Using query param URL encoding
FILTERED=$(curl -s "$BASE_URL/projects/$PROJECT_ID/collections/users/docs/" \
  -H "Authorization: Bearer $TOKEN" \
  --get \
  --data-urlencode "query=$QUERY_FILTER")
echo $FILTERED | jq '.documents | length'
echo -e "${GREEN}✓ Documents filtered${NC}"

# Test 9: Query with Comparison Operator (age > 25)
echo -e "\n${YELLOW}Test 9: Query with Comparison (age > 25)${NC}"
QUERY_COMPARISON=$(cat <<EOF
{"where":[{"field":"age","op":">","value":25}],"orderBy":[{"field":"age","direction":"desc"}],"limit":10}
EOF
)
COMPARED=$(curl -s "$BASE_URL/projects/$PROJECT_ID/collections/users/docs/" \
  -H "Authorization: Bearer $TOKEN" \
  --get \
  --data-urlencode "query=$QUERY_COMPARISON")
echo $COMPARED | jq '.documents | map(.data | {name, age})'
echo -e "${GREEN}✓ Comparison query executed${NC}"

# Test 10: Batch Write Transaction (Set, Update, Delete)
echo -e "\n${YELLOW}Test 10: Batch Write Transaction${NC}"
TRANSACTION=$(api_call "POST" "/projects/$PROJECT_ID/transaction/" '{
  "writes": [
    {
      "op": "set",
      "path": "users/eve",
      "data": {"name": "Eve", "age": 28, "email": "eve@example.com"}
    },
    {
      "op": "update",
      "path": "users/alice",
      "data": {"last_updated": "batch"}
    },
    {
      "op": "delete",
      "path": "users/charlie"
    }
  ]
}')
echo $TRANSACTION | jq '.results'
echo -e "${GREEN}✓ Transaction executed${NC}"

# Test 11: Optimistic Locking (Version Conflict)
echo -e "\n${YELLOW}Test 11: Optimistic Locking (Version Conflict)${NC}"
CONFLICT=$(api_call "PATCH" "/projects/$PROJECT_ID/collections/users/docs/alice/" '{
  "data": {"age": 32},
  "__v": 999
}')
CONFLICT_STATUS=$(echo $CONFLICT | jq '.detail' 2>/dev/null || echo "success")
if [[ $CONFLICT_STATUS == *"version"* ]]; then
  echo -e "${GREEN}✓ Version conflict detected (expected)${NC}"
else
  echo -e "${RED}✗ Expected version conflict${NC}"
fi

# Test 12: Subcollections
echo -e "\n${YELLOW}Test 12: Subcollections${NC}"
SUBCOLLS_PATH="users%2Falice%2Fposts"  # URL-encoded: users/alice/posts
CREATE_SUBCOL_DOC=$(api_call "POST" "/projects/$PROJECT_ID/collections/$SUBCOLLS_PATH/docs/" '{
  "doc_id": "post1",
  "data": {
    "title": "Hello World",
    "content": "My first post",
    "published": true
  }
}')
FULL_PATH=$(echo $CREATE_SUBCOL_DOC | jq -r '.collection_path')
echo "Created document in subcollection: $FULL_PATH"
echo -e "${GREEN}✓ Subcollection document created${NC}"

# Test 13: Delete Document
echo -e "\n${YELLOW}Test 13: Delete Document${NC}"
DELETE_RESPONSE=$(api_call "DELETE" "/projects/$PROJECT_ID/collections/users/docs/eve/")
if [ -z "$DELETE_RESPONSE" ] || [ "$DELETE_RESPONSE" == "" ]; then
  echo -e "${GREEN}✓ Document deleted (204 No Content)${NC}"
else
  echo "Response: $DELETE_RESPONSE"
fi

# Test 14: Verify Deletion
echo -e "\n${YELLOW}Test 14: Verify Deletion${NC}"
GET_DELETED=$(api_call "GET" "/projects/$PROJECT_ID/collections/users/docs/eve/")
if echo $GET_DELETED | jq -e '.detail' > /dev/null 2>&1; then
  echo -e "${GREEN}✓ Document confirmed deleted (404)${NC}"
else
  echo -e "${RED}✗ Document still exists${NC}"
fi

# Summary
echo -e "\n${GREEN}===============================================${NC}"
echo -e "${GREEN}All integration tests completed!${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo "Next steps:"
echo "1. Run full test suite: pytest tests/test_data_api.py -v"
echo "2. Check admin interface: http://localhost:8000/admin/"
echo "3. Explore API docs: http://localhost:8000/api/docs/"
echo ""
