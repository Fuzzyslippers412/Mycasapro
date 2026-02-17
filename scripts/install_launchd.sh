#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/mycasa-pro"

mkdir -p "$LAUNCH_DIR" "$LOG_DIR"

BACKEND_PLIST="$LAUNCH_DIR/com.mycasa.backend.plist"
FRONTEND_PLIST="$LAUNCH_DIR/com.mycasa.frontend.plist"

cat > "$BACKEND_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.mycasa.backend</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>${REPO_DIR}/scripts/launchd_backend.sh</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>WorkingDirectory</key>
  <string>${REPO_DIR}</string>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/backend.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/backend.err</string>
</dict>
</plist>
PLIST

cat > "$FRONTEND_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.mycasa.frontend</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>${REPO_DIR}/scripts/launchd_frontend.sh</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>WorkingDirectory</key>
  <string>${REPO_DIR}/frontend</string>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/frontend.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/frontend.err</string>
</dict>
</plist>
PLIST

chmod 644 "$BACKEND_PLIST" "$FRONTEND_PLIST"
chmod +x "${REPO_DIR}/scripts/launchd_backend.sh" "${REPO_DIR}/scripts/launchd_frontend.sh"

launchctl unload -w "$BACKEND_PLIST" 2>/dev/null || true
launchctl unload -w "$FRONTEND_PLIST" 2>/dev/null || true
launchctl load -w "$BACKEND_PLIST"
launchctl load -w "$FRONTEND_PLIST"

launchctl kickstart -k "gui/$(id -u)/com.mycasa.backend" 2>/dev/null || true
launchctl kickstart -k "gui/$(id -u)/com.mycasa.frontend" 2>/dev/null || true

echo "LaunchAgents installed and started."
