"""
WhatsApp Connector for MyCasa Pro
Uses wacli for local WhatsApp authentication and messaging.

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
    WhatsApp connector using wacli.
    Each MyCasa install owns its own WhatsApp session (no shared credentials).
    """
    
    connector_id = "whatsapp"
    display_name = "WhatsApp"
    description = "Send and receive WhatsApp messages via wacli"
    version = "1.0.0"
    icon = "💬"
    
    can_receive = True
    can_send = True
    requires_auth = True
    
    # Contact directory - loaded from TOOLS.md or database
    _contacts: Dict[str, Dict[str, str]] = {}
    
    def __init__(self):
        super().__init__()
        self._load_contacts()
    
    def _load_contacts(self) -> None:
        """Load contacts from settings or tenant TOOLS.md."""
        tools_paths = []
        try:
            from config.settings import DATA_DIR, DEFAULT_TENANT_ID
            tools_paths.append(DATA_DIR / "tenants" / DEFAULT_TENANT_ID / "TOOLS.md")
        except Exception:
            pass

        try:
            from core.settings_typed import get_settings_store
            settings = get_settings_store().get()
            contacts = getattr(settings.agents.mail, "whatsapp_contacts", []) or []
            for contact in contacts:
                try:
                    name = (getattr(contact, "name", "") or "").strip()
                    phone = (getattr(contact, "phone", "") or "").strip()
                except Exception:
                    name = (contact or {}).get("name") or ""
                    phone = (contact or {}).get("phone") or ""
                if name and phone:
                    self._contacts[name.lower()] = {
                        "name": name,
                        "relation": "",
                        "phone": phone,
                        "jid": ""
                    }
            if self._contacts:
                return
        except Exception:
            pass

        tools_path = next((p for p in tools_paths if p.exists()), None)
        if not tools_path:
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
        WhatsApp auth is handled by wacli.
        This verifies the local wacli session is authenticated.
        """
        status = await self.health_check(tenant_id)
        if status != ConnectorStatus.HEALTHY:
            raise Exception("WhatsApp not authenticated. Run: wacli auth")
        
        return ConnectorCredentials(
            connector_id=self.connector_id,
            tenant_id=tenant_id,
            credentials={"via": "wacli"}
        )
    
    async def refresh_auth(self, tenant_id: str, credentials: ConnectorCredentials) -> ConnectorCredentials:
        """No refresh needed - uses wacli local auth"""
        return credentials
    
    async def health_check(self, tenant_id: str) -> ConnectorStatus:
        """Check if wacli is authenticated"""
        try:
            result = subprocess.run(
                ["wacli", "auth", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                status = json.loads(result.stdout)
                data = status.get("data", status)
                if data.get("authenticated"):
                    self.set_status(tenant_id, ConnectorStatus.HEALTHY)
                    return ConnectorStatus.HEALTHY
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
        self.set_status(tenant_id, ConnectorStatus.FAILED)
        return ConnectorStatus.FAILED
    
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
        return events
    
    async def send(
        self,
        tenant_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message via wacli.
        
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
        
        # Send via wacli
        try:
            cmd = ["wacli", "send", "text", "--to", to, "--message", message]
            if media_path:
                cmd = ["wacli", "send", "media", "--to", to, "--file", media_path, "--caption", message]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info(f"Message sent to {to}")
                return {
                    "success": True,
                    "to": to,
                    "message_preview": message[:50] + "..." if len(message) > 50 else message
                }
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
        """WhatsApp uses local wacli auth"""
        return {
            "type": "object",
            "properties": {},
            "description": "WhatsApp authentication is handled by wacli. Run 'wacli auth' in terminal."
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
