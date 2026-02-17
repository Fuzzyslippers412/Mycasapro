"""
Gmail Connector for MyCasa Pro
OAuth2-based Gmail integration for inbox management.

This connector enables:
- Fetching emails from Gmail
- Sending emails
- Managing labels
- Syncing to unified inbox
"""
import subprocess
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from connectors.base import (
    BaseConnector,
    ConnectorStatus,
    ConnectorCredentials,
    ConnectorEvent,
    SendError,
)


logger = logging.getLogger("mycasa.connectors.gmail")


class GmailConnector(BaseConnector):
    """
    Gmail connector using the `gog` CLI tool.
    
    Leverages the gog CLI for Gmail operations, which handles OAuth
    and provides a clean interface to Gmail API.
    """
    
    connector_id = "gmail"
    display_name = "Gmail"
    description = "Connect to Gmail for email management and inbox sync"
    version = "1.0.0"
    icon = "📧"
    
    can_receive = True
    can_send = True
    requires_auth = True
    
    def __init__(self):
        super().__init__()
        self._gog_available = self._check_gog()
    
    def _check_gog(self) -> bool:
        """Check if gog CLI is available"""
        try:
            result = subprocess.run(
                ["gog", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    async def authenticate(self, tenant_id: str, credentials: Dict[str, Any]) -> ConnectorCredentials:
        """
        Authenticate with Gmail via gog CLI.
        
        The gog CLI handles OAuth flow. This method verifies the connection.
        """
        if not self._gog_available:
            raise Exception("gog CLI not installed. Install from: https://github.com/doitintl/gog")
        
        # Check if already authenticated
        try:
            result = subprocess.run(
                ["gog", "gmail", "profile"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                profile = json.loads(result.stdout) if result.stdout.startswith("{") else {}
                email = profile.get("emailAddress", "unknown")
                
                return ConnectorCredentials(
                    connector_id=self.connector_id,
                    tenant_id=tenant_id,
                    credentials={"email": email, "via": "gog_cli"}
                )
        except Exception as e:
            logger.error(f"Gmail auth check failed: {e}")
        
        raise Exception("Gmail not authenticated. Run: gog auth login")
    
    async def refresh_auth(self, tenant_id: str, credentials: ConnectorCredentials) -> ConnectorCredentials:
        """gog handles token refresh automatically"""
        return credentials
    
    async def health_check(self, tenant_id: str) -> ConnectorStatus:
        """Check Gmail connection health"""
        if not self._gog_available:
            self.set_status(tenant_id, ConnectorStatus.FAILED)
            return ConnectorStatus.FAILED
        
        try:
            result = subprocess.run(
                ["gog", "gmail", "profile"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.set_status(tenant_id, ConnectorStatus.HEALTHY)
                return ConnectorStatus.HEALTHY
        except Exception as e:
            logger.warning(f"Gmail health check failed: {e}")
        
        self.set_status(tenant_id, ConnectorStatus.FAILED)
        return ConnectorStatus.FAILED
    
    async def sync(
        self,
        tenant_id: str,
        since: datetime = None,
        limit: int = 50
    ) -> List[ConnectorEvent]:
        """
        Sync recent emails from Gmail.
        
        Returns ConnectorEvents for the unified inbox.
        """
        if not self._gog_available:
            return []
        
        events = []
        
        try:
            # Build search query
            query = "newer_than:7d"
            if since:
                # Format: YYYY/MM/DD
                query = f"after:{since.strftime('%Y/%m/%d')}"
            
            # Fetch emails via gog
            result = subprocess.run(
                ["gog", "gmail", "search", query, "--max", str(limit), "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Gmail sync failed: {result.stderr}")
                return []
            
            messages = json.loads(result.stdout) if result.stdout else []
            
            for msg in messages:
                # Convert to ConnectorEvent
                event = ConnectorEvent(
                    event_id=f"gmail_{msg.get('id', '')}",
                    connector_id=self.connector_id,
                    tenant_id=tenant_id,
                    event_type="message",
                    source_id=msg.get("id", ""),
                    source_thread_id=msg.get("threadId"),
                    sender_name=msg.get("from", {}).get("name", ""),
                    sender_id=msg.get("from", {}).get("email", ""),
                    subject=msg.get("subject", ""),
                    body=msg.get("snippet", ""),
                    preview=msg.get("snippet", "")[:100],
                    timestamp=datetime.fromisoformat(msg.get("date", datetime.utcnow().isoformat())),
                    is_read="UNREAD" not in msg.get("labelIds", []),
                )
                
                # Classify domain based on content/sender
                event.domain = self._classify_email(msg)
                events.append(event)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gmail response: {e}")
        except Exception as e:
            logger.error(f"Gmail sync error: {e}")
        
        return events
    
    def _classify_email(self, msg: Dict[str, Any]) -> str:
        """Classify email into domain based on content"""
        subject = (msg.get("subject", "") or "").lower()
        sender = (msg.get("from", {}).get("email", "") or "").lower()
        snippet = (msg.get("snippet", "") or "").lower()
        
        # Finance indicators
        finance_keywords = ["invoice", "payment", "bill", "receipt", "statement", "bank", "transaction"]
        if any(kw in subject or kw in snippet for kw in finance_keywords):
            return "finance"
        
        # Maintenance indicators
        maint_keywords = ["repair", "maintenance", "service", "appointment", "scheduled", "hvac", "plumb"]
        if any(kw in subject or kw in snippet for kw in maint_keywords):
            return "maintenance"
        
        # Security indicators
        security_keywords = ["security", "alert", "login", "password", "2fa", "verification"]
        if any(kw in subject or kw in snippet for kw in security_keywords):
            return "security"
        
        return "general"
    
    async def send(
        self,
        tenant_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send an email via Gmail.
        
        Payload format:
        {
            "to": "recipient@example.com",
            "subject": "Email subject",
            "body": "Email body text",
            "cc": "cc@example.com" (optional),
            "bcc": "bcc@example.com" (optional),
        }
        """
        if not self._gog_available:
            raise SendError("gog CLI not available")
        
        to = payload.get("to")
        subject = payload.get("subject")
        body = payload.get("body")
        
        if not to or not subject or not body:
            raise SendError("Missing required fields: to, subject, body")
        
        try:
            # Build gog send command
            cmd = [
                "gog", "gmail", "send",
                "--to", to,
                "--subject", subject,
                "--body", body
            ]
            
            if payload.get("cc"):
                cmd.extend(["--cc", payload["cc"]])
            if payload.get("bcc"):
                cmd.extend(["--bcc", payload["bcc"]])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "to": to,
                    "subject": subject,
                }
            else:
                raise SendError(f"Failed to send: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise SendError("Email send timed out")
        except Exception as e:
            raise SendError(f"Send failed: {e}")
    
    def get_auth_schema(self) -> Dict[str, Any]:
        """Gmail OAuth schema"""
        return {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "Gmail uses OAuth via gog CLI. Run 'gog auth login' to authenticate.",
                    "readOnly": True
                }
            },
            "description": "Gmail authentication is handled by the gog CLI. Run 'gog auth login' to start OAuth flow."
        }
    
    def get_settings_schema(self) -> Dict[str, Any]:
        """Gmail connector settings"""
        return {
            "type": "object",
            "properties": {
                "sync_labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Gmail labels to sync (default: INBOX)",
                    "default": ["INBOX"]
                },
                "auto_classify": {
                    "type": "boolean",
                    "description": "Automatically classify emails by domain",
                    "default": True
                },
                "sync_frequency_minutes": {
                    "type": "integer",
                    "description": "How often to sync emails (minutes)",
                    "default": 15,
                    "minimum": 5
                }
            }
        }


# Singleton instance
_gmail_connector: Optional[GmailConnector] = None


def get_gmail_connector() -> GmailConnector:
    """Get singleton Gmail connector instance"""
    global _gmail_connector
    if _gmail_connector is None:
        _gmail_connector = GmailConnector()
    return _gmail_connector
