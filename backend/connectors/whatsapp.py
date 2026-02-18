"""
WhatsApp Connector
Uses wacli for real WhatsApp integration (no stub data).
"""
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..core.schemas import ConnectorStatus


class WhatsAppConnector:
    """WhatsApp connector using wacli"""
    
    def __init__(self):
        self._status = ConnectorStatus.DISCONNECTED
        self._check_availability()

    def _get_allowlist(self) -> set:
        try:
            from core.settings_typed import get_settings_store
            settings = get_settings_store().get()
            allowlist = set()
            for number in getattr(settings.agents.mail, "whatsapp_allowlist", []) or []:
                digits = "".join(c for c in str(number) if c.isdigit())
                if digits:
                    allowlist.add(digits)
            for contact in getattr(settings.agents.mail, "whatsapp_contacts", []) or []:
                try:
                    phone = getattr(contact, "phone", "") or ""
                except Exception:
                    phone = (contact or {}).get("phone") or ""
                digits = "".join(c for c in str(phone) if c.isdigit())
                if digits:
                    allowlist.add(digits)
            return allowlist
        except Exception:
            return set()
    
    def is_whitelisted(self, jid: str) -> bool:
        """Check if a JID is from a whitelisted contact"""
        allowlist = self._get_allowlist()
        if not allowlist:
            return False
        phone = jid.split("@")[0]
        digits = "".join(c for c in phone if c.isdigit())
        if not digits:
            return False
        return digits in allowlist or any(digits.endswith(wl) for wl in allowlist)
    
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
            self._status = ConnectorStatus.DISCONNECTED
        except subprocess.TimeoutExpired:
            self._status = ConnectorStatus.ERROR
    
    def get_status(self) -> ConnectorStatus:
        return self._status
    
    def fetch_messages(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recent WhatsApp chats from whitelisted contacts only"""
        if self._status != ConnectorStatus.CONNECTED:
            return []
        allowlist = self._get_allowlist()
        if not allowlist:
            return []
        
        try:
            result = subprocess.run(
                ["wacli", "chats", "list", "--limit", str(limit * 3), "--json"],  # Fetch more to filter
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return []
            
            data = json.loads(result.stdout)
            if not data.get("success"):
                return []
            
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
            return []
    
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
    
    def send_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send WhatsApp message via wacli"""
        if self._status != ConnectorStatus.CONNECTED:
            return {"success": False, "error": "whatsapp_not_connected"}
        if not to or not message:
            return {"success": False, "error": "missing_to_or_message"}
        try:
            digits = "".join(c for c in str(to) if c.isdigit())
            recipient = digits or to
            result = subprocess.run(
                ["wacli", "send", "text", "--to", recipient, "--message", message],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return {"success": True, "to": recipient}
            return {"success": False, "error": (result.stderr or "").strip() or "send_failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
