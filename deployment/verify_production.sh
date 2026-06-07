#!/bin/bash
# Production verification script for deployed app

set -e

DOMAIN="${1:-https://your-app.ondigitalocean.app}"
echo "🔍 Verifying production deployment at: $DOMAIN"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local endpoint=$1
    local expected_status=$2
    local description=$3
    
    echo -n "Testing $description... "
    status=$(curl -s -o /dev/null -w "%{http_code}" "$DOMAIN$endpoint")
    
    if [ "$status" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} ($status)"
        return 0
    else
        echo -e "${RED}✗${NC} (got $status, expected $expected_status)"
        return 1
    fi
}

echo ""
echo "=== Core Endpoints ==="
test_endpoint "/health" 200 "Health check"
test_endpoint "/" 200 "Landing page"
test_endpoint "/dashboard" 200 "Dashboard HTML"

echo ""
echo "=== Static Assets ==="
test_endpoint "/static/css/dashboard.css" 200 "Dashboard CSS"
test_endpoint "/static/js/dashboard.js" 200 "Dashboard JS"
test_endpoint "/static/admin_favicon.ico" 200 "Favicon"

echo ""
echo "=== API Routes (expect 401/403 without auth) ==="
test_endpoint "/admin/students" 401 "Admin students API"
test_endpoint "/v1/students" 401 "V1 students API"

echo ""
echo "=== Auth Pages ==="
test_endpoint "/login" 200 "Login page"
test_endpoint "/forgot-password" 200 "Password reset page"

echo ""
echo "=== Security Headers ==="
headers=$(curl -s -I "$DOMAIN/health")
echo "$headers" | grep -q "x-content-type-options" && echo -e "${GREEN}✓${NC} X-Content-Type-Options" || echo -e "${RED}✗${NC} X-Content-Type-Options"
echo "$headers" | grep -q "x-frame-options" && echo -e "${GREEN}✓${NC} X-Frame-Options" || echo -e "${RED}✗${NC} X-Frame-Options"
echo "$headers" | grep -q "strict-transport-security" && echo -e "${GREEN}✓${NC} Strict-Transport-Security" || echo -e "${RED}✗${NC} Strict-Transport-Security"

echo ""
echo "=== OpenAPI Docs ==="
test_endpoint "/docs" 200 "Swagger UI"
test_endpoint "/redoc" 200 "ReDoc"

echo ""
echo -e "${GREEN}Production verification complete!${NC}"
