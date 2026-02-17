"""
WhatsApp Connector
Uses wacli for real WhatsApp integration, falls back to stub
"""
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..core.schemas import ConnectorStatus


class WhatsAppConnector:
    """WhatsApp connector using wacli"""
    
    # Whitelisted contacts (JID or phone number)
    WHITELISTED_CONTACTS = {
        "12675474854": "Erika Tenkiang",      # Wife
        "13027501982": "Jessie Tenkiang",     # Mother
        "33782826145": "Rakia Baldé",         # House Assistant
        "12534312046": "Juan",                # Contractor
        "12676431585": "Dr Njoni",            # Contact
    }
    
    def __init__(self):
        self._status = ConnectorStatus.STUB
        self._check_availability()
    
    def is_whitelisted(self, jid: str) -> bool:
        """Check if a JID is from a whitelisted contact"""
        # Extract phone number from JID (format: 12675474854@s.whatsapp.net or lid format)
        phone = jid.split("@")[0]
        # Check if phone is in whitelist
        return phone in self.WHITELISTED_CONTACTS or any(
            phone.endswith(wl) for wl in self.WHITELISTED_CONTACTS.keys()
        )
    
    def add_to_whitelist(self, phone: str, name: str):
        """Add a contact to the whitelist"""
        # Remove any non-numeric characters
        phone_clean = ''.join(c for c in phone if c.isdigit())
        self.WHITELISTED_CONTACTS[phone_clean] = name
    
    def _check_availability(self):
        """Check if wacli is available and authenticated"""
        try:
            result = subprocess.run(
                ["wacli", "doctor"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and "AUTHENTICATED  true" in result.stdout:
                self._status = ConnectorStatus.CONNECTED
            else:
                self._status = ConnectorStatus.DISCONNECTED
        except FileNotFoundError:
            self._status = ConnectorStatus.STUB
        except subprocess.TimeoutExpired:
            self._status = ConnectorStatus.ERROR
    
    def get_status(self) -> ConnectorStatus:
        return self._status
    
    def fetch_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recent WhatsApp chats from whitelisted contacts only"""
        if self._status == ConnectorStatus.STUB:
            return self._get_stub_messages()
        
        try:
            result = subprocess.run(
                ["wacli", "chats", "list", "--limit", str(limit * 3), "--json"],  # Fetch more to filter
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return self._get_stub_messages()
            
            data = json.loads(result.stdout)
            if not data.get("success"):
                return self._get_stub_messages()
            
            chats = data.get("data", [])
            messages = []
            
            for chat in chats:
                jid = chat.get("JID", "")
                
                # Skip status broadcasts and non-whitelisted contacts
                if jid.startswith("status@"):
                    continue
                if not self.is_whitelisted(jid):
                    continue
                
                # Fetch actual last messages (up to 3) for content
                preview, recent_msgs = self._fetch_recent_messages(jid, limit=3)
                
                msg = self._normalize_chat(chat, preview)
                if msg:
                    messages.append(msg)
                
                if len(messages) >= limit:
                    break
            
            return messages
            
        except Exception as e:
            print(f"[WhatsApp] Fetch error: {e}")
            return self._get_stub_messages()
    
    def _fetch_last_message(self, jid: str) -> str:
        """Fetch last message from a chat"""
        preview, _ = self._fetch_recent_messages(jid, limit=1)
        return preview
    
    def _fetch_recent_messages(self, jid: str, limit: int = 3) -> tuple:
        """Fetch recent messages from a chat, returns (preview, messages_list)"""
        try:
            # Try JSON format first - use --chat flag for JID
            result = subprocess.run(
                ["wacli", "messages", "list", "--chat", jid, "--limit", str(limit), "--json"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    if data.get("success"):
                        # Messages are nested in data.messages
                        messages_data = data.get("data", {})
                        if isinstance(messages_data, dict):
                            messages = messages_data.get("messages", [])
                        else:
                            messages = messages_data if isinstance(messages_data, list) else []
                        
                        if messages:
                            for msg in messages:
                                # Get text - prefer Text, fallback to DisplayText
                                text = (msg.get("Text") or msg.get("DisplayText") or "").strip()
                                if text:
                                    return text[:300], messages
                            # Check for media
                            media_type = messages[0].get("MediaType", "")
                            if media_type:
                                return f"[{media_type}]", messages
                except json.JSONDecodeError:
                    pass
            
            # Fallback: try plain text format and parse it
            result = subprocess.run(
                ["wacli", "messages", "list", "--chat", jid, "--limit", str(limit)],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                # Skip header line, parse message lines
                for line in lines[1:]:  # Skip "TIME CHAT FROM ID TEXT" header
                    parts = line.split(None, 4)  # Split into max 5 parts
                    if len(parts) >= 5:
                        text = parts[4].strip()
                        if text and not text.startswith("---"):
                            return text[:300], []
            
            return "", []
        except Exception as e:
            print(f"[WhatsApp] Error fetching messages for {jid}: {e}")
            return "", []
    
    def _normalize_chat(self, chat: Dict[str, Any], preview: str = "") -> Optional[Dict[str, Any]]:
        """Normalize WhatsApp chat to common format"""
        try:
            jid = chat.get("JID", "")
            sender_name = chat.get("Name", jid.split("@")[0])
            
            last_msg_ts = chat.get("LastMessageTS", "")
            try:
                timestamp = datetime.fromisoformat(last_msg_ts.replace("Z", "+00:00"))
                # Strip timezone for SQLite
                timestamp = timestamp.replace(tzinfo=None)
            except Exception:
                timestamp = datetime.utcnow()
            
            domain = self._infer_domain(sender_name, jid)
            
            return {
                "external_id": f"whatsapp:{jid}",
                "source": "whatsapp",
                "thread_id": jid,
                "sender_name": sender_name,
                "sender_id": jid,
                "subject": f"WhatsApp from {sender_name}",
                "body": preview,
                "timestamp": timestamp,
                "domain": domain,
                "urgency": "medium",
                "is_read": False
            }
        except Exception:
            return None
    
    def _infer_domain(self, name: str, jid: str) -> str:
        """Infer domain from contact"""
        name_lower = name.lower()
        
        # Known contractors
        if any(kw in name_lower for kw in ["juan", "contractor", "plumber", "electrician"]):
            return "contractors"
        
        # House assistant
        if "rakia" in name_lower:
            return "maintenance"
        
        # Business contacts
        if "llc" in name_lower or "inc" in name_lower:
            return "contractors"
        
        return "unknown"
    
    def _get_stub_messages(self) -> List[Dict[str, Any]]:
        """Return demo messages when wacli is not configured"""
        return [
            {
                "external_id": "whatsapp:stub1",
                "source": "whatsapp",
                "thread_id": "stub_rakia",
                "sender_name": "Rakia Baldé",
                "sender_id": "33782826145@s.whatsapp.net",
                "subject": "WhatsApp from Rakia Baldé",
                "body": "The cleaning supplies have arrived. Should I start the deep cleaning today?",
                "timestamp": datetime.utcnow(),
                "domain": "maintenance",
                "urgency": "medium",
                "is_read": False
            },
            {
                "external_id": "whatsapp:stub2",
                "source": "whatsapp",
                "thread_id": "stub_juan",
                "sender_name": "Juan (Contractor)",
                "sender_id": "12534312046@s.whatsapp.net",
                "subject": "WhatsApp from Juan",
                "body": "I can come by Thursday to look at the deck repair. Will that work?",
                "timestamp": datetime.utcnow(),
                "domain": "contractors",
                "urgency": "medium",
                "is_read": False
            }
        ]
    
    def send_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send WhatsApp message (stub - use gateway for real sends)"""
        return {
            "success": False,
            "error": "WhatsApp sending should use Clawdbot gateway",
            "stub": True
        }
