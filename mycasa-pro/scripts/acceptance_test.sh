#!/bin/bash
# MyCasa Pro Acceptance Tests
# Run with: bash scripts/acceptance_test.sh

set -e

API_URL="${API_URL:-http://localhost:6709}"
PASS=0
FAIL=0

echo "=== MyCasa Pro Acceptance Tests ==="
echo "API: $API_URL"
echo ""

# Helper function
check() {
    local name="$1"
    local cmd="$2"
    local expected="$3"
    
    result=$(eval "$cmd" 2>/dev/null || echo "ERROR")
    
    if [[ "$result" == *"$expected"* ]]; then
        echo "✅ $name"
        ((PASS++))
    else
        echo "❌ $name"
        echo "   Expected: $expected"
        echo "   Got: $result"
        ((FAIL++))
    fi
}

# 1. Health check
check "Health check returns ok" \
    "curl -sf $API_URL/health | jq -r '.status'" \
    "ok"

# 2. Idempotent startup (first call)
check "Startup succeeds" \
    "curl -sf -X POST $API_URL/api/system/startup | jq -r '.success'" \
    "true"

# 3. Idempotent startup (second call - should return already_running)
check "Startup is idempotent" \
    "curl -sf -X POST $API_URL/api/system/startup | jq -r '.already_running'" \
    "true"

# 4. System status shows running
check "System shows running" \
    "curl -sf $API_URL/api/system/status | jq -r '.running'" \
    "true"

# 5. Idempotent shutdown (first call)
check "Shutdown succeeds" \
    "curl -sf -X POST $API_URL/api/system/shutdown | jq -r '.success'" \
    "true"

# 6. Idempotent shutdown (second call - should return already_stopped)
check "Shutdown is idempotent" \
    "curl -sf -X POST $API_URL/api/system/shutdown | jq -r '.already_stopped'" \
    "true"

# 7. System status shows stopped
check "System shows stopped" \
    "curl -sf $API_URL/api/system/status | jq -r '.running'" \
    "false"

# 8. Backup list returns array
check "Backup list returns backups" \
    "curl -sf $API_URL/backup/list | jq -r '.backups | type'" \
    "array"

# 9. Telemetry cost endpoint works
check "Telemetry cost/today returns cost" \
    "curl -sf $API_URL/api/telemetry/cost/today | jq 'has(\"cost\")'" \
    "true"

# 10. Settings validation (invalid value should fail)
check "Settings rejects invalid recommendation_style" \
    "curl -sf -X PUT $API_URL/api/settings/agent/finance \
        -H 'Content-Type: application/json' \
        -d '{\"recommendation_style\": \"INVALID\"}' | jq -r '.error.code // .success'" \
    "VALIDATION"

# 11. Turn system back on for further use
curl -sf -X POST $API_URL/api/system/startup > /dev/null 2>&1 || true

echo ""
echo "=== Results ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -gt 0 ]; then
    echo "❌ Some tests failed"
    exit 1
else
    echo "✅ All tests passed"
    exit 0
fi
