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

# Dependencies
require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "❌ Missing dependency: $cmd"
        exit 1
    fi
}

require_cmd curl
require_cmd jq

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

# 12. Register + login
RAND_ID="$(date +%s)"
USERNAME="smoke${RAND_ID}"
EMAIL="smoke${RAND_ID}@example.com"
PASSWORD="Test${RAND_ID}!"

REGISTER_RESP="$(curl -sf -X POST $API_URL/api/auth/register \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"${USERNAME}\",\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" || true)"

ACCESS_TOKEN="$(echo "$REGISTER_RESP" | jq -r '.access_token // .token // empty')"

if [ -n "$ACCESS_TOKEN" ]; then
  echo "✅ Register returns access token"
  ((PASS++))
else
  echo "❌ Register returns access token"
  echo "   Response: $REGISTER_RESP"
  ((FAIL++))
fi

# 13. /auth/me works
check "Auth me works" \
  "curl -sf $API_URL/api/auth/me -H 'Authorization: Bearer ${ACCESS_TOKEN}' | jq -r '.username'" \
  "$USERNAME"

# 14. Create a task
TASK_RESP="$(curl -sf -X POST $API_URL/api/tasks \
  -H 'Authorization: Bearer ${ACCESS_TOKEN}' \
  -H 'Content-Type: application/json' \
  -d '{\"title\":\"Smoke Test Task\",\"category\":\"maintenance\",\"priority\":\"low\"}' || true)"

TASK_ID="$(echo "$TASK_RESP" | jq -r '.id // empty')"
if [ -n "$TASK_ID" ]; then
  echo "✅ Create task"
  ((PASS++))
else
  echo "❌ Create task"
  echo "   Response: $TASK_RESP"
  ((FAIL++))
fi

# 15. List tasks includes created task (best effort)
check "List tasks returns tasks" \
  "curl -sf $API_URL/api/tasks -H 'Authorization: Bearer ${ACCESS_TOKEN}' | jq -r '.tasks | type'" \
  "array"

# 16. Create task via Manager chat (should persist)
CHAT_RESP="$(curl -sf -X POST $API_URL/manager/chat \
  -H 'Authorization: Bearer ${ACCESS_TOKEN}' \
  -H 'Content-Type: application/json' \
  -d '{\"message\":\"Add a task to clean the office by Friday\"}' || true)"

CHAT_TASK_ID="$(echo "$CHAT_RESP" | jq -r '.task_created.task_id // empty')"
if [ -n "$CHAT_TASK_ID" ]; then
  echo "✅ Manager chat created task"
  ((PASS++))
else
  echo "❌ Manager chat created task"
  echo "   Response: $CHAT_RESP"
  ((FAIL++))
fi

TASKS_COUNT="$(curl -sf $API_URL/api/tasks -H 'Authorization: Bearer ${ACCESS_TOKEN}' | jq -r '.tasks | length')"
if [ -n "$TASKS_COUNT" ] && [ "$TASKS_COUNT" -gt 0 ]; then
  echo "✅ Chat-created task appears in tasks list"
  ((PASS++))
else
  echo "❌ Chat-created task appears in tasks list"
  echo "   Task count: $TASKS_COUNT"
  ((FAIL++))
fi

# 17. Contractors create/list
CONTRACTOR_RESP="$(curl -sf -X POST $API_URL/api/contractors \
  -H 'Authorization: Bearer ${ACCESS_TOKEN}' \
  -H 'Content-Type: application/json' \
  -d '{\"name\":\"Test Contractor\",\"service_type\":\"general\"}' || true)"
CONTRACTOR_ID="$(echo "$CONTRACTOR_RESP" | jq -r '.id // empty')"
if [ -n "$CONTRACTOR_ID" ]; then
  echo "✅ Create contractor"
  ((PASS++))
else
  echo "❌ Create contractor"
  echo "   Response: $CONTRACTOR_RESP"
  ((FAIL++))
fi

check "List contractors returns array" \
  "curl -sf $API_URL/api/contractors -H 'Authorization: Bearer ${ACCESS_TOKEN}' | jq -r '.contractors | type'" \
  "array"

# 18. Projects create/list
PROJECT_RESP="$(curl -sf -X POST $API_URL/api/projects \
  -H 'Authorization: Bearer ${ACCESS_TOKEN}' \
  -H 'Content-Type: application/json' \
  -d '{\"name\":\"Test Project\",\"status\":\"planning\"}' || true)"
PROJECT_ID="$(echo "$PROJECT_RESP" | jq -r '.id // empty')"
if [ -n "$PROJECT_ID" ]; then
  echo "✅ Create project"
  ((PASS++))
else
  echo "❌ Create project"
  echo "   Response: $PROJECT_RESP"
  ((FAIL++))
fi

check "List projects returns array" \
  "curl -sf $API_URL/api/projects -H 'Authorization: Bearer ${ACCESS_TOKEN}' | jq -r '.projects | type'" \
  "array"

# 19. Inbox unread count
check "Unread count returns total" \
  "curl -sf $API_URL/api/inbox/unread-count -H 'Authorization: Bearer ${ACCESS_TOKEN}' | jq -r 'has(\"total\")'" \
  "true"

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
