"""
Mail Skill Agent for MyCasa Pro

ROLE: Ingestion + Normalization ONLY
- Fetches Gmail + WhatsApp messages
- Normalizes to common schema
- Deduplicates threads
- Extracts metadata (sender, topic, urgency)
- Hands off to Manager (Galidima)

DOES NOT:
- Decide actions
- Send replies
- Interpret intent beyond tagging
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import subprocess
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import BaseAgent
from database import get_db
from database.models import InboxMessage


class MailSkillAgent(BaseAgent):
    """
    Ingestion + normalization agent for Gmail and WhatsApp.
    Routes everything through Manager - no autonomous decisions.
    """
    
    def __init__(self):
        super().__init__("mail-skill")
        self.gmail_account = "tfamsec@gmail.com"
        self._last_gmail_fetch = None
        self._last_whatsapp_fetch = None
    
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task - Mail Skill only ingests, doesn't execute"""
        return {"error": "Mail Skill Agent does not execute tasks - ingestion only"}
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get pending tasks - Mail Skill has no tasks"""
        return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get mail skill agent status"""
        with get_db() as db:
            unread_count = db.query(InboxMessage).filter(
                InboxMessage.is_read == False
            ).count()
            
            gmail_count = db.query(InboxMessage).filter(
                InboxMessage.source == "gmail",
                InboxMessage.is_read == False
            ).count()
            
            whatsapp_count = db.query(InboxMessage).filter(
                InboxMessage.source == "whatsapp",
                InboxMessage.is_read == False
            ).count()
        
        return {
            "agent": "mail-skill",
            "status": "active",
            "metrics": {
                "unread_total": unread_count,
                "unread_gmail": gmail_count,
                "unread_whatsapp": whatsapp_count,
                "last_gmail_fetch": self._last_gmail_fetch,
                "last_whatsapp_fetch": self._last_whatsapp_fetch
            }
        }
    
    # ============ GMAIL INGESTION ============
    
    def fetch_gmail(self, max_results: int = 20, days_back: int = 3) -> List[Dict[str, Any]]:
        """
        Fetch recent Gmail messages and normalize them.
        Returns list of normalized messages.
        """
        try:
            # Use gog to fetch emails
            result = subprocess.run(
                ["gog", "gmail", "search", f"newer_than:{days_back}d", "--max", str(max_results), "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.error(f"gog gmail search failed: {result.stderr}")
                return []
            
            data = json.loads(result.stdout)
            threads = data.get("threads", [])
            
            messages = []
            for thread in threads:
                normalized = self._normalize_gmail(thread)
                if normalized:
                    messages.append(normalized)
            
            self._last_gmail_fetch = datetime.now().isoformat()
            self.log_action("gmail_fetched", json.dumps({"count": len(messages)}))
            
            return messages
            
        except subprocess.TimeoutExpired:
            self.logger.error("gog gmail search timed out")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse gog output: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Gmail fetch error: {e}")
            return []
    
    def _normalize_gmail(self, thread: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize Gmail thread to common message schema"""
        try:
            # Generate stable ID
            thread_id = thread.get("id", "")
            message_id = f"gmail:{thread_id}"
            
            # Parse sender
            from_field = thread.get("from", "")
            sender_name = from_field.split("<")[0].strip().strip('"')
            sender_email = from_field.split("<")[-1].rstrip(">") if "<" in from_field else from_field
            
            # Parse date
            date_str = thread.get("date", "")
            try:
                # Format: "2026-01-28 13:35"
                timestamp = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            except Exception:
                timestamp = datetime.now()
            
            # Infer domain from content/sender
            subject = thread.get("subject", "")
            domain = self._infer_domain_gmail(sender_email, subject)
            
            # Infer urgency
            labels = thread.get("labels", [])
            urgency = self._infer_urgency_gmail(labels, subject)
            
            return {
                "id": message_id,
                "source": "gmail",
                "thread_id": thread_id,
                "sender_name": sender_name,
                "sender_id": sender_email,
                "subject": subject,
                "preview": subject[:100],  # Gmail search doesn't return body
                "timestamp": timestamp,
                "domain": domain,
                "urgency": urgency,
                "is_unread": "UNREAD" in labels,
                "labels": labels,
                "raw_data": thread
            }
        except Exception as e:
            self.logger.error(f"Failed to normalize Gmail message: {e}")
            return None
    
    def _infer_domain_gmail(self, sender: str, subject: str) -> str:
        """Infer domain (Maintenance/Finance/etc.) from Gmail message"""
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        combined = f"{sender_lower} {subject_lower}"
        
        # Finance signals
        if any(kw in combined for kw in ["chase", "schwab", "bank", "payment", "invoice", "receipt", "bill", "statement"]):
            return "finance"
        
        # Maintenance/Contractors signals
        if any(kw in combined for kw in ["repair", "service", "contractor", "maintenance", "hvac", "plumb", "electric"]):
            return "maintenance"
        
        # Security signals
        if any(kw in combined for kw in ["security", "alert", "suspicious", "password", "verify"]):
            return "security"
        
        return "unknown"
    
    def _infer_urgency_gmail(self, labels: List[str], subject: str) -> str:
        """Infer urgency from Gmail labels and subject"""
        subject_lower = subject.lower()
        
        # High urgency signals
        if "IMPORTANT" in labels or any(kw in subject_lower for kw in ["urgent", "action required", "immediate"]):
            return "high"
        
        # Updates are usually medium
        if "CATEGORY_UPDATES" in labels:
            return "medium"
        
        # Promotions are low
        if "CATEGORY_PROMOTIONS" in labels:
            return "low"
        
        return "medium"
    
    # ============ WHATSAPP INGESTION ============
    
    def fetch_whatsapp(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch recent WhatsApp messages and normalize them.
        Returns list of normalized messages.
        """
        try:
            # Get recent chats with messages
            result = subprocess.run(
                ["wacli", "chats", "list", "--limit", str(limit), "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.logger.error(f"wacli chats list failed: {result.stderr}")
                return []
            
            data = json.loads(result.stdout)
            if not data.get("success"):
                return []
            
            chats = data.get("data", [])
            messages = []
            
            for chat in chats:
                # Skip status broadcasts
                jid = chat.get("JID", "")
                if jid.startswith("status@"):
                    continue
                
                # Try to fetch last message for preview
                preview = self._fetch_whatsapp_last_message(jid)
                
                normalized = self._normalize_whatsapp_chat(chat, preview)
                if normalized:
                    messages.append(normalized)
            
            self._last_whatsapp_fetch = datetime.now().isoformat()
            self.log_action("whatsapp_fetched", json.dumps({"count": len(messages)}))
            
            return messages
            
        except subprocess.TimeoutExpired:
            self.logger.error("wacli chats list timed out")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse wacli output: {e}")
            return []
        except Exception as e:
            self.logger.error(f"WhatsApp fetch error: {e}")
            return []
    
    def _fetch_whatsapp_last_message(self, jid: str) -> str:
        """Fetch the last message from a WhatsApp chat"""
        try:
            result = subprocess.run(
                ["wacli", "messages", "list", jid, "--limit", "1", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return ""
            
            data = json.loads(result.stdout)
            if not data.get("success"):
                return ""
            
            messages = data.get("data", [])
            if messages and len(messages) > 0:
                return messages[0].get("Text", "")[:200]  # First 200 chars
            
            return ""
        except Exception:
            return ""
    
    def _normalize_whatsapp_chat(self, chat: Dict[str, Any], preview: str = "") -> Optional[Dict[str, Any]]:
        """Normalize WhatsApp chat to common message schema"""
        try:
            jid = chat.get("JID", "")
            message_id = f"whatsapp:{jid}"
            
            # Parse timestamp
            last_msg_ts = chat.get("LastMessageTS", "")
            try:
                timestamp = datetime.fromisoformat(last_msg_ts.replace("Z", "+00:00"))
            except Exception:
                timestamp = datetime.now()
            
            # Get sender name
            sender_name = chat.get("Name", jid.split("@")[0])
            
            # Infer domain from contact
            domain = self._infer_domain_whatsapp(sender_name, jid)
            
            return {
                "id": message_id,
                "source": "whatsapp",
                "thread_id": jid,
                "sender_name": sender_name,
                "sender_id": jid,
                "subject": f"WhatsApp from {sender_name}",
                "preview": preview,
                "timestamp": timestamp,
                "domain": domain,
                "urgency": "medium",  # Default for WhatsApp
                "is_unread": True,  # Assume new chats are unread
                "labels": [],
                "raw_data": chat
            }
        except Exception as e:
            self.logger.error(f"Failed to normalize WhatsApp chat: {e}")
            return None
    
    def _infer_domain_whatsapp(self, name: str, jid: str) -> str:
        """Infer domain from WhatsApp contact"""
        name_lower = name.lower()
        
        # Known contractors
        if any(kw in name_lower for kw in ["juan", "contractor", "plumber", "electrician"]):
            return "contractors"
        
        # Known house assistant
        if "rakia" in name_lower:
            return "maintenance"
        
        # Business contacts
        if "llc" in name_lower or "inc" in name_lower:
            return "contractors"
        
        return "unknown"
    
    # ============ UNIFIED INGESTION ============
    
    def ingest_all(self) -> Dict[str, Any]:
        """
        Fetch and ingest messages from all sources.
        Stores in database and returns summary.
        """
        gmail_messages = self.fetch_gmail()
        whatsapp_messages = self.fetch_whatsapp()
        
        all_messages = gmail_messages + whatsapp_messages
        
        # Store in database
        new_count = 0
        updated_count = 0
        
        with get_db() as db:
            for msg in all_messages:
                # Check if exists
                existing = db.query(InboxMessage).filter(
                    InboxMessage.external_id == msg["id"]
                ).first()
                
                if existing:
                    # Update timestamp if newer (make both naive for comparison)
                    msg_ts = msg["timestamp"]
                    existing_ts = existing.timestamp
                    # Strip timezone info for comparison
                    if hasattr(msg_ts, 'tzinfo') and msg_ts.tzinfo is not None:
                        msg_ts = msg_ts.replace(tzinfo=None)
                    if hasattr(existing_ts, 'tzinfo') and existing_ts.tzinfo is not None:
                        existing_ts = existing_ts.replace(tzinfo=None)
                    
                    if msg_ts > existing_ts:
                        existing.timestamp = msg["timestamp"].replace(tzinfo=None) if hasattr(msg["timestamp"], 'tzinfo') else msg["timestamp"]
                        existing.preview = msg.get("preview", existing.preview)
                        updated_count += 1
                else:
                    # Create new - strip timezone for SQLite compatibility
                    ts = msg["timestamp"]
                    if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                        ts = ts.replace(tzinfo=None)
                    
                    inbox_msg = InboxMessage(
                        external_id=msg["id"],
                        source=msg["source"],
                        thread_id=msg["thread_id"],
                        sender_name=msg["sender_name"],
                        sender_id=msg["sender_id"],
                        subject=msg["subject"],
                        preview=msg.get("preview", ""),
                        timestamp=ts,
                        domain=msg["domain"],
                        urgency=msg["urgency"],
                        is_read=not msg.get("is_unread", True),
                        confidence="inferred",
                        raw_data=json.dumps(msg.get("raw_data", {}))
                    )
                    db.add(inbox_msg)
                    new_count += 1
            
            db.commit()
        
        self.log_action("ingest_complete", json.dumps({
            "gmail": len(gmail_messages),
            "whatsapp": len(whatsapp_messages),
            "new": new_count,
            "updated": updated_count
        }))
        
        return {
            "success": True,
            "gmail_count": len(gmail_messages),
            "whatsapp_count": len(whatsapp_messages),
            "new_messages": new_count,
            "updated_messages": updated_count
        }
    
    def get_inbox_messages(
        self, 
        source: str = None, 
        domain: str = None,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get inbox messages with optional filters"""
        with get_db() as db:
            query = db.query(InboxMessage)
            
            if source:
                query = query.filter(InboxMessage.source == source)
            if domain:
                query = query.filter(InboxMessage.domain == domain)
            if unread_only:
                query = query.filter(InboxMessage.is_read == False)
            
            # Order by timestamp descending (newest first)
            query = query.order_by(InboxMessage.timestamp.desc())
            
            messages = query.limit(limit).all()
            
            return [self._message_to_dict(m) for m in messages]
    
    def _message_to_dict(self, msg: InboxMessage) -> Dict[str, Any]:
        """Convert InboxMessage to dictionary (frontend-compatible format)"""
        return {
            "id": msg.id,
            "external_id": msg.external_id,
            "source": msg.source,
            "thread_id": msg.thread_id,
            # Frontend expects 'sender' not 'sender_name'
            "sender": msg.sender_name,
            "sender_name": msg.sender_name,
            "sender_id": msg.sender_id,
            "subject": msg.subject,
            # Frontend expects 'body' not 'preview'
            "body": msg.preview or "",
            "preview": msg.preview,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
            "domain": msg.domain,
            "linked_domain": msg.domain,
            "urgency": msg.urgency,
            "is_read": msg.is_read,
            "confidence": msg.confidence,
            "linked_task_id": msg.linked_task_id,
            "assigned_agent": msg.assigned_agent,
            "required_action": msg.required_action
        }
    
    def mark_read(self, message_id: int) -> Dict[str, Any]:
        """Mark a message as read"""
        with get_db() as db:
            msg = db.query(InboxMessage).filter(InboxMessage.id == message_id).first()
            if not msg:
                return {"error": "Message not found"}
            
            msg.is_read = True
            db.commit()
            
            return {"success": True, "message_id": message_id}
    
    def link_to_task(self, message_id: int, task_id: int) -> Dict[str, Any]:
        """Link a message to a task"""
        with get_db() as db:
            msg = db.query(InboxMessage).filter(InboxMessage.id == message_id).first()
            if not msg:
                return {"error": "Message not found"}
            
            msg.linked_task_id = task_id
            db.commit()
            
            self.log_action("message_linked", json.dumps({
                "message_id": message_id,
                "task_id": task_id
            }))
            
            return {"success": True, "message_id": message_id, "task_id": task_id}
    
    def assign_to_agent(self, message_id: int, agent: str) -> Dict[str, Any]:
        """Assign a message to an agent"""
        with get_db() as db:
            msg = db.query(InboxMessage).filter(InboxMessage.id == message_id).first()
            if not msg:
                return {"error": "Message not found"}
            
            msg.assigned_agent = agent
            db.commit()
            
            self.log_action("message_assigned", json.dumps({
                "message_id": message_id,
                "agent": agent
            }))
            
            return {"success": True, "message_id": message_id, "agent": agent}
