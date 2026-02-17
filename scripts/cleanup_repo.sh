#!/bin/bash
# Cleanup tracked non-product artifacts for a lean GitHub repo.
# Usage:
#   bash scripts/cleanup_repo.sh        # dry-run
#   bash scripts/cleanup_repo.sh --apply

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

TARGETS=(
  ".claude"
  ".claude-flow"
  ".clawdbot"
  ".learnings"
  ".streamlit"
  ".swarm"
  ".coverage"
  "coverage.xml"
  "htmlcov"
  "api.log"
  "backend.log"
  "frontend.log"
  "backend_start.log"
  "frontend_start.log"
  "debug_report.html"
  "mycasa-pro"
)

tracked_targets=()
for t in "${TARGETS[@]}"; do
  if git ls-files --error-unmatch "$t" >/dev/null 2>&1; then
    tracked_targets+=("$t")
    continue
  fi
  # Check for tracked children of directories
  if git ls-files | grep -q "^${t}/"; then
    tracked_targets+=("$t")
  fi
done

if [[ "${1:-}" != "--apply" ]]; then
  echo "Dry run. The following tracked paths would be removed:"
  if [ ${#tracked_targets[@]} -eq 0 ]; then
    echo "  (none)"
  else
    for t in "${tracked_targets[@]}"; do
      echo "  - $t"
    done
  fi
  echo ""
  echo "To apply cleanup:"
  echo "  bash scripts/cleanup_repo.sh --apply"
  exit 0
fi

if [ ${#tracked_targets[@]} -eq 0 ]; then
  echo "No tracked cleanup targets found."
  exit 0
fi

echo "Removing tracked artifacts..."
git rm -r --cached "${tracked_targets[@]}"
rm -rf "${tracked_targets[@]}"
echo "Cleanup complete."
