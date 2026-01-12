#!/bin/bash
# ERIOP API Test Script
# Usage: ./api_test.sh [base_url]

BASE_URL="${1:-http://localhost:8000}"
API_URL="$BASE_URL/api/v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test credentials
EMAIL="admin@vigilia.com"
PASSWORD="admin123"

echo "========================================"
echo "ERIOP API Test Suite"
echo "Base URL: $BASE_URL"
echo "========================================"
echo ""

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=$4
    local description=$5

    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            "$API_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$endpoint")
    fi

    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$status_code" == "$expected_status" ]; then
        echo -e "${GREEN}[PASS]${NC} $method $endpoint - $description (HTTP $status_code)"
        echo "$body" | jq -r '.id // .items[0].id // empty' 2>/dev/null
        return 0
    else
        echo -e "${RED}[FAIL]${NC} $method $endpoint - $description"
        echo -e "       Expected: $expected_status, Got: $status_code"
        echo -e "       Response: $body"
        return 1
    fi
}

# ======================================
# 1. Health Check (no auth required)
# ======================================
echo "--- Health Check ---"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/health")
status_code=$(echo "$response" | tail -n1)
if [ "$status_code" == "200" ]; then
    echo -e "${GREEN}[PASS]${NC} GET /health (HTTP $status_code)"
else
    echo -e "${RED}[FAIL]${NC} GET /health (HTTP $status_code)"
    exit 1
fi
echo ""

# ======================================
# 2. Authentication
# ======================================
echo "--- Authentication ---"
response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}" \
    "$API_URL/auth/login")

status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$status_code" == "200" ]; then
    TOKEN=$(echo "$body" | jq -r '.access_token')
    if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
        echo -e "${GREEN}[PASS]${NC} POST /auth/login - Got access token"
        # Decode and show agency_id from token
        payload=$(echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null)
        agency_id=$(echo "$payload" | jq -r '.agency_id // "null"' 2>/dev/null)
        echo -e "       Agency ID: $agency_id"
    else
        echo -e "${RED}[FAIL]${NC} POST /auth/login - No access token in response"
        exit 1
    fi
else
    echo -e "${RED}[FAIL]${NC} POST /auth/login (HTTP $status_code)"
    echo -e "       Response: $body"
    exit 1
fi
echo ""

# ======================================
# 3. User Profile
# ======================================
echo "--- User Profile ---"
test_endpoint "GET" "/auth/me" "" "200" "Get current user"
echo ""

# ======================================
# 4. Incidents API
# ======================================
echo "--- Incidents API ---"

# List incidents
test_endpoint "GET" "/incidents" "" "200" "List incidents"

# Create incident
INCIDENT_DATA='{
    "category": "fire",
    "priority": 2,
    "title": "Test Fire Incident",
    "description": "This is a test incident created by API test script",
    "location": {
        "latitude": 45.5017,
        "longitude": -73.5673,
        "address": "123 Test Street, Montreal"
    }
}'
echo ""
echo "Creating test incident..."
response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$INCIDENT_DATA" \
    "$API_URL/incidents")

status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$status_code" == "201" ]; then
    INCIDENT_ID=$(echo "$body" | jq -r '.id')
    echo -e "${GREEN}[PASS]${NC} POST /incidents - Created incident $INCIDENT_ID"
else
    echo -e "${RED}[FAIL]${NC} POST /incidents (HTTP $status_code)"
    echo -e "       Response: $body"
fi

# Get incident by ID (if created)
if [ -n "$INCIDENT_ID" ] && [ "$INCIDENT_ID" != "null" ]; then
    test_endpoint "GET" "/incidents/$INCIDENT_ID" "" "200" "Get incident by ID"

    # Update incident
    UPDATE_DATA='{"status": "assigned", "priority": 1}'
    test_endpoint "PATCH" "/incidents/$INCIDENT_ID" "$UPDATE_DATA" "200" "Update incident status"
fi

# Get active incidents
test_endpoint "GET" "/incidents/active" "" "200" "List active incidents"
echo ""

# ======================================
# 5. Resources API
# ======================================
echo "--- Resources API ---"
test_endpoint "GET" "/resources" "" "200" "List resources"
test_endpoint "GET" "/resources/available" "" "200" "List available resources"
echo ""

# ======================================
# 6. Alerts API
# ======================================
echo "--- Alerts API ---"
test_endpoint "GET" "/alerts" "" "200" "List alerts"
test_endpoint "GET" "/alerts/unacknowledged" "" "200" "List unacknowledged alerts"
echo ""

# ======================================
# 7. Dashboard API
# ======================================
echo "--- Dashboard API ---"
test_endpoint "GET" "/dashboard/stats" "" "200" "Get dashboard stats"
echo ""

# ======================================
# Summary
# ======================================
echo "========================================"
echo "API Test Complete"
echo "========================================"
