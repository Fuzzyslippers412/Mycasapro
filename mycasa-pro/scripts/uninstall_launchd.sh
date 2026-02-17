#!/bin/bash
set -e

LAUNCH_DIR="$HOME/Library/LaunchAgents"
BACKEND_PLIST="$LAUNCH_DIR/com.mycasa.backend.plist"
FRONTEND_PLIST="$LAUNCH_DIR/com.mycasa.frontend.plist"

launchctl unload -w "$BACKEND_PLIST" 2>/dev/null || true
launchctl unload -w "$FRONTEND_PLIST" 2>/dev/null || true

rm -f "$BACKEND_PLIST" "$FRONTEND_PLIST"

echo "LaunchAgents removed."
