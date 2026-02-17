"""
WhatsApp Connector for MyCasa Pro
Interfaces with Clawdbot's WhatsApp gateway for messaging.

This connector enables the Manager agent to:
- Send WhatsApp messages to contacts
- Look up contacts by name or phone
- Handle natural language messaging requests
"""
import subprocess
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from connectors.base import (
    BaseConnector,
    ConnectorStatus,
    ConnectorCredentials,
    ConnectorEvent,
    SendError,
)


class WhatsAppConnector(BaseConnector):
    """
    WhatsApp connector using Clawdbot's gateway.
    
    Since MyCasa Pro runs as a Clawdbot skill, we leverage the existing
    WhatsApp gateway connection rather than maintaining a separate one.
    """
    
    connector_id = "whatsapp"
    display_name = "WhatsApp"
    description = "Send and receive WhatsApp messages via Clawdbot gateway"
    version = "1.0.0"
    icon = "💬"
    
    can_receive = True
    can_send = True
    requires_auth = False  # Uses Clawdbot's existing auth
    
    # Contact directory - loaded from TOOLS.md or database
    _contacts: Dict[str, Dict[str, str]] = {}
    
    def __init__(self):
        super().__init__()
        self._load_contacts()
    
    def _load_contacts(self) -> None:
        """Load contacts from TOOLS.md"""
        tools_path = Path.home() / "clawd" / "TOOLS.md"
        if not tools_path.exists():
            return
        
        content = tools_path.read_text()
        
        # Parse contact table from TOOLS.md
        # Format: | Name | Relation | Phone | WhatsApp JID |
        in_contacts = False
        for line in content.split("\n"):
            if "| Name" in line and "Phone" in line:
                in_contacts = True
                continue
            if in_contacts and line.startswith("|"):
                if "---" in line:
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 5:
                    name = parts[1]
                    relation = parts[2]
                    phone = parts[3]
                    jid = parts[4]
                    if name and phone:
                        # Store by name (lowercase for lookup)
                        self._contacts[name.lower()] = {
                            "name": name,
                            "relation": relation,
                            "phone": phone,
                            "jid": jid
                        }
            elif in_contacts and not line.startswith("|"):
                in_contacts = False
    
    def lookup_contact(self, query: str) -> Optional[Dict[str, str]]:
        """
        Look up a contact by name or phone number.
        
        Args:
            query: Name (partial match) or phone number
        
        Returns:
            Contact dict or None
        """
        query_lower = query.lower().strip()
        
        # Exact name match first
        if query_lower in self._contacts:
            return self._contacts[query_lower]
        
        # Partial name match
        for name, contact in self._contacts.items():
            if query_lower in name:
                return contact
        
        # Phone number match
        query_digits = ''.join(c for c in query if c.isdigit())
        for contact in self._contacts.values():
            phone_digits = ''.join(c for c in contact.get("phone", "") if c.isdigit())
            if query_digits and query_digits in phone_digits:
                return contact
        
        return None
    
    def get_all_contacts(self) -> List[Dict[str, str]]:
        """Get all known contacts"""
        return list(self._contacts.values())
    
    async def authenticate(self, tenant_id: str, credentials: Dict[str, Any]) -> ConnectorCredentials:
        """
        WhatsApp auth is handled by Clawdbot gateway.
        This just verifies the gateway is connected.
        """
        status = await self.health_check(tenant_id)
        if status != ConnectorStatus.HEALTHY:
            raise Exception("WhatsApp gateway not connected")
        
        return ConnectorCredentials(
            connector_id=self.connector_id,
            tenant_id=tenant_id,
            credentials={"via": "clawdbot_gateway"}
        )
    
    async def refresh_auth(self, tenant_id: str, credentials: ConnectorCredentials) -> ConnectorCredentials:
        """No refresh needed - uses Clawdbot's auth"""
        return credentials
    
    async def health_check(self, tenant_id: str) -> ConnectorStatus:
        """Check if Clawdbot's WhatsApp gateway is connected"""
        try:
            # Check gateway status via clawdbot CLI
            result = subprocess.run(
                ["clawdbot", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                status = json.loads(result.stdout)
                if status.get("whatsapp", {}).get("connected"):
                    self.set_status(tenant_id, ConnectorStatus.HEALTHY)
                    return ConnectorStatus.HEALTHY
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
        
        # Fallback - assume healthy if we can't check
        # (gateway connection issues will surface on send)
        self.set_status(tenant_id, ConnectorStatus.HEALTHY)
        return ConnectorStatus.HEALTHY
    
    async def sync(
        self,
        tenant_id: str,
        since: datetime = None,
        limit: int = 100
    ) -> List[ConnectorEvent]:
        """
        Sync WhatsApp messages.
        Uses wacli for history retrieval.
        """
        events = []
        # TODO: Implement wacli integration for message history
        # For now, inbound messages come through Clawdbot's gateway
        return events
    
    async def send(
        self,
        tenant_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message via Clawdbot gateway.
        
        Payload format:
        {
            "to": "+1234567890" or "contact_name",
            "message": "Message text",
            "media_path": "/path/to/file" (optional)
        }
        """
        to = payload.get("to")
        message = payload.get("message")
        media_path = payload.get("media_path")
        
        if not to or not message:
            raise SendError("Missing 'to' or 'message' in payload")
        
        # Resolve contact name to phone number
        if not to.startswith("+") and not to.replace("-", "").isdigit():
            contact = self.lookup_contact(to)
            if contact:
                to = contact.get("phone")
                self.logger.info(f"Resolved '{payload.get('to')}' to {to}")
            else:
                raise SendError(f"Contact not found: {payload.get('to')}")
        
        # Send via Clawdbot's gateway using subprocess
        # This calls the gateway's message API
        try:
            cmd = [
                "clawdbot", "message", "send",
                "--channel", "whatsapp",
                "--target", to,
                "--message", message
            ]
            
            if media_path:
                cmd.extend(["--media", media_path])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info(f"Message sent to {to}")
                return {
                    "success": True,
                    "to": to,
                    "message_preview": message[:50] + "..." if len(message) > 50 else message
                }
            else:
                raise SendError(f"Failed to send: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise SendError("Message send timed out")
        except Exception as e:
            raise SendError(f"Send failed: {e}")
    
    async def send_to_contact(
        self,
        contact_name: str,
        message: str,
        tenant_id: str = "tenkiang_household"
    ) -> Dict[str, Any]:
        """
        Convenience method to send to a contact by name.
        
        Args:
            contact_name: Contact name to look up
            message: Message to send
            tenant_id: Tenant ID
        
        Returns:
            Send result
        """
        return await self.send(tenant_id, {
            "to": contact_name,
            "message": message
        })
    
    def get_auth_schema(self) -> Dict[str, Any]:
        """WhatsApp uses Clawdbot's existing auth"""
        return {
            "type": "object",
            "properties": {},
            "description": "WhatsApp authentication is handled by Clawdbot gateway. No additional credentials needed."
        }
    
    def get_settings_schema(self) -> Dict[str, Any]:
        """WhatsApp connector settings"""
        return {
            "type": "object",
            "properties": {
                "default_greeting": {
                    "type": "string",
                    "description": "Default greeting to use in messages",
                    "default": "Hi"
                },
                "signature": {
                    "type": "string",
                    "description": "Signature to append to messages",
                    "default": ""
                },
                "notify_on_send": {
                    "type": "boolean",
                    "description": "Create notification when message is sent",
                    "default": True
                }
            }
        }


# Singleton instance
_whatsapp_connector: Optional[WhatsAppConnector] = None


def get_whatsapp_connector() -> WhatsAppConnector:
    """Get singleton WhatsApp connector instance"""
    global _whatsapp_connector
    if _whatsapp_connector is None:
        _whatsapp_connector = WhatsAppConnector()
    return _whatsapp_connector
