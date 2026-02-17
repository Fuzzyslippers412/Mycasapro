"""
Gmail Connector
Uses gog CLI for real Gmail integration, falls back to stub
"""
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..core.schemas import ConnectorStatus


class GmailConnector:
    """Gmail connector using gog CLI"""
    
    def __init__(self):
        import os
        self.account = os.getenv("MYCASA_GMAIL_ACCOUNT", "")
        self._status = ConnectorStatus.STUB
        self._check_availability()
    
    def _check_availability(self):
        """Check if gog CLI is available"""
        try:
            result = subprocess.run(
                ["gog", "gmail", "search", "newer_than:1d", "--max", "1", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self._status = ConnectorStatus.CONNECTED
            else:
                self._status = ConnectorStatus.ERROR
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._status = ConnectorStatus.STUB
    
    def get_status(self) -> ConnectorStatus:
        return self._status
    
    def fetch_messages(self, days_back: int = 3, max_results: int = 20, unread_only: bool = True) -> List[Dict[str, Any]]:
        """Fetch recent Gmail messages (unread by default)"""
        if self._status == ConnectorStatus.STUB:
            return self._get_stub_messages()
        
        try:
            # Build search query - only unread if specified
            search_query = f"newer_than:{days_back}d"
            if unread_only:
                search_query = f"is:unread {search_query}"
            
            result = subprocess.run(
                ["gog", "gmail", "search", search_query, "--max", str(max_results), "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return self._get_stub_messages()
            
            data = json.loads(result.stdout)
            threads = data.get("threads", [])
            
            messages = []
            for thread in threads:
                msg = self._normalize_message(thread)
                if msg:
                    messages.append(msg)
            
            return messages
            
        except Exception as e:
            print(f"[Gmail] Fetch error: {e}")
            return self._get_stub_messages()
    
    def _normalize_message(self, thread: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize Gmail thread to common format"""
        try:
            thread_id = thread.get("id", "")
            from_field = thread.get("from", "")
            sender_name = from_field.split("<")[0].strip().strip('"')
            sender_email = from_field.split("<")[-1].rstrip(">") if "<" in from_field else from_field
            
            date_str = thread.get("date", "")
            try:
                timestamp = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            except Exception:
                timestamp = datetime.utcnow()
            
            subject = thread.get("subject", "")
            domain = self._infer_domain(sender_email, subject)
            
            return {
                "external_id": f"gmail:{thread_id}",
                "source": "gmail",
                "thread_id": thread_id,
                "sender_name": sender_name,
                "sender_id": sender_email,
                "subject": subject,
                "body": subject,  # gog search doesn't return body
                "timestamp": timestamp,
                "domain": domain,
                "urgency": "medium",
                "is_read": "UNREAD" not in thread.get("labels", [])
            }
        except Exception:
            return None
    
    def _infer_domain(self, sender: str, subject: str) -> str:
        """Infer domain from sender/subject"""
        combined = f"{sender.lower()} {subject.lower()}"
        
        if any(kw in combined for kw in ["chase", "schwab", "bank", "payment", "invoice", "bill"]):
            return "finance"
        if any(kw in combined for kw in ["repair", "service", "contractor", "maintenance"]):
            return "maintenance"
        if any(kw in combined for kw in ["security", "alert", "suspicious", "password"]):
            return "security"
        
        return "unknown"
    
    def _get_stub_messages(self) -> List[Dict[str, Any]]:
        """Return demo messages when gog CLI is not configured"""
        return [
            {
                "external_id": "gmail:stub1",
                "source": "gmail",
                "thread_id": "stub1",
                "sender_name": "Chase Bank",
                "sender_id": "alerts@chase.com",
                "subject": "Your account statement is ready",
                "body": "Your monthly statement for January is now available.",
                "timestamp": datetime.utcnow(),
                "domain": "finance",
                "urgency": "medium",
                "is_read": False
            },
            {
                "external_id": "gmail:stub2",
                "source": "gmail",
                "thread_id": "stub2",
                "sender_name": "HVAC Service Co",
                "sender_id": "service@hvac.com",
                "subject": "Annual maintenance reminder",
                "body": "Your HVAC system is due for annual maintenance.",
                "timestamp": datetime.utcnow(),
                "domain": "maintenance",
                "urgency": "low",
                "is_read": True
            }
        ]
    
    def send_message(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send email (stub - not implemented)"""
        return {
            "success": False,
            "error": "Email sending not implemented",
            "stub": True
        }
