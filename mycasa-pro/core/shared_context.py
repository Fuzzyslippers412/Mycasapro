"""
MyCasa Pro - Shared Context with Clawdbot/Galidima

This module provides access to the same memory and context that
Galidima (the main Clawdbot agent) has, ensuring the MyCasa Pro
Manager has the same knowledge and history.

Sources:
- ~/clawd/MEMORY.md - Long-term curated memory
- ~/clawd/USER.md - User profile
- ~/clawd/TOOLS.md - Tools and contacts
- ~/clawd/memory/*.md - Daily memory files
- ~/.clawdbot/agents/main/sessions/ - Session history
"""
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import logging

logger = logging.getLogger("mycasa.shared_context")

# Base paths
CLAWD_DIR = Path.home() / "clawd"
CLAWDBOT_DIR = Path.home() / ".clawdbot"


class SharedContext:
    """
    Provides shared context between Clawdbot (Galidima) and MyCasa Pro Manager.
    
    The Manager should have access to:
    - Who the user is (USER.md)
    - Long-term memories (MEMORY.md)
    - Recent activities (daily memory files)
    - Contacts and tools (TOOLS.md)
    - Recent conversation context
    """
    
    def __init__(self, max_memory_days: int = 7):
        self.max_memory_days = max_memory_days
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def _is_cached(self, key: str) -> bool:
        """Check if a key is cached and not expired"""
        if key not in self._cache:
            return False
        if datetime.now() - self._cache_time.get(key, datetime.min) > self._cache_ttl:
            return False
        return True
    
    def _cache_get(self, key: str) -> Any:
        return self._cache.get(key)
    
    def _cache_set(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._cache_time[key] = datetime.now()
    
    def get_user_profile(self) -> str:
        """Get USER.md content"""
        if self._is_cached("user"):
            return self._cache_get("user")
        
        user_path = CLAWD_DIR / "USER.md"
        content = ""
        if user_path.exists():
            content = user_path.read_text()
        
        self._cache_set("user", content)
        return content
    
    def get_long_term_memory(self) -> str:
        """Get MEMORY.md content"""
        if self._is_cached("memory"):
            return self._cache_get("memory")
        
        memory_path = CLAWD_DIR / "MEMORY.md"
        content = ""
        if memory_path.exists():
            content = memory_path.read_text()
        
        self._cache_set("memory", content)
        return content
    
    def get_tools(self) -> str:
        """Get TOOLS.md content (includes contacts)"""
        if self._is_cached("tools"):
            return self._cache_get("tools")
        
        tools_path = CLAWD_DIR / "TOOLS.md"
        content = ""
        if tools_path.exists():
            content = tools_path.read_text()
        
        self._cache_set("tools", content)
        return content
    
    def get_recent_memory(self, days: int = None) -> List[Dict[str, str]]:
        """
        Get recent daily memory files.
        
        Returns list of {date, content} dicts, newest first.
        """
        days = days or self.max_memory_days
        cache_key = f"recent_memory_{days}"
        
        if self._is_cached(cache_key):
            return self._cache_get(cache_key)
        
        memory_dir = CLAWD_DIR / "memory"
        memories = []
        
        if memory_dir.exists():
            today = datetime.now().date()
            for i in range(days):
                date = today - timedelta(days=i)
                # Try both date formats
                for fmt in ["%Y-%m-%d", "%y-%m-%d"]:
                    date_str = date.strftime(fmt)
                    file_path = memory_dir / f"{date_str}.md"
                    if file_path.exists():
                        memories.append({
                            "date": date.isoformat(),
                            "content": file_path.read_text()
                        })
                        break
        
        self._cache_set(cache_key, memories)
        return memories
    
    def get_contacts(self) -> List[Dict[str, str]]:
        """Extract contacts from TOOLS.md"""
        tools = self.get_tools()
        contacts = []
        
        # Parse contact table
        in_contacts = False
        for line in tools.split("\n"):
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
                        contacts.append({
                            "name": name,
                            "relation": relation,
                            "phone": phone,
                            "jid": jid
                        })
            elif in_contacts and not line.startswith("|"):
                in_contacts = False
        
        return contacts
    
    def get_recent_session_messages(self, session_id: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent messages from Clawdbot session history.
        
        This allows the Manager to see recent conversation context.
        
        Clawdbot JSONL format:
        {
            "type": "message",
            "id": "...",
            "timestamp": "...",
            "message": {
                "role": "user" | "assistant",
                "content": [...] or "string"
            }
        }
        """
        sessions_dir = CLAWDBOT_DIR / "agents" / "main" / "sessions"
        
        if not sessions_dir.exists():
            return []
        
        session_file = None
        
        # Find the main session file
        if session_id:
            session_file = sessions_dir / f"{session_id}.jsonl"
        else:
            # Try to find the active session from sessions.json
            sessions_meta = sessions_dir / "sessions.json"
            if sessions_meta.exists():
                try:
                    meta = json.loads(sessions_meta.read_text())
                    # Look for main agent session (agent:main:main)
                    for key, info in meta.items():
                        if "agent:main" in key or "main" in key:
                            sid = info.get("sessionId")
                            if sid:
                                candidate = sessions_dir / f"{sid}.jsonl"
                                if candidate.exists():
                                    session_file = candidate
                                    break
                except Exception as e:
                    logger.warning(f"Failed to parse sessions.json: {e}")
            
            # Fallback: find most recently modified .jsonl file
            if not session_file:
                jsonl_files = [f for f in sessions_dir.glob("*.jsonl") if not f.name.endswith('.lock')]
                if jsonl_files:
                    session_file = max(jsonl_files, key=lambda f: f.stat().st_mtime)
        
        if not session_file or not session_file.exists():
            return []
        
        # Read last N messages from JSONL
        messages = []
        try:
            # Read file and get last N lines
            with open(session_file, 'r') as f:
                lines = f.readlines()
            
            for line in lines[-limit * 3:]:  # Read more lines to filter
                try:
                    entry = json.loads(line.strip())
                    
                    # Handle Clawdbot nested format
                    if entry.get("type") == "message":
                        msg = entry.get("message", {})
                        role = msg.get("role")
                        
                        # Only include user and assistant messages
                        if role in ["user", "assistant"]:
                            content = msg.get("content", "")
                            
                            # Handle content array (Clawdbot format)
                            if isinstance(content, list):
                                # Extract text from content blocks
                                text_parts = []
                                for block in content:
                                    if isinstance(block, dict):
                                        if block.get("type") == "text":
                                            text_parts.append(block.get("text", ""))
                                    elif isinstance(block, str):
                                        text_parts.append(block)
                                content = "\n".join(text_parts)
                            
                            # Skip empty or very long content
                            if content and len(content) < 3000:
                                messages.append({
                                    "role": role,
                                    "content": content[:500] + "..." if len(content) > 500 else content,
                                    "timestamp": entry.get("timestamp")
                                })
                    
                    # Also handle old flat format for backwards compatibility
                    elif entry.get("role") in ["user", "assistant"]:
                        content = entry.get("content", "")
                        if isinstance(content, str) and len(content) < 3000:
                            messages.append({
                                "role": entry.get("role"),
                                "content": content[:500] + "..." if len(content) > 500 else content,
                                "timestamp": entry.get("timestamp")
                            })
                            
                except json.JSONDecodeError:
                    continue
            
            # Return only the last N
            messages = messages[-limit:]
            
        except Exception as e:
            logger.warning(f"Failed to read session file: {e}")
        
        return messages
    
    def get_full_context(self, include_session: bool = True) -> Dict[str, Any]:
        """
        Get full shared context for the Manager.
        
        This provides everything the Manager needs to have the same
        knowledge as Galidima.
        """
        context = {
            "user": self.get_user_profile(),
            "long_term_memory": self.get_long_term_memory(),
            "tools": self.get_tools(),
            "contacts": self.get_contacts(),
            "recent_memory": self.get_recent_memory(days=3),  # Last 3 days
        }
        
        if include_session:
            context["recent_messages"] = self.get_recent_session_messages(limit=10)
        
        return context
    
    def build_context_prompt(self, max_chars: int = 4000) -> str:
        """
        Build a context prompt that can be prepended to Manager responses.
        
        This gives the Manager relevant context from shared memory.
        """
        parts = []
        
        # User info (short)
        user = self.get_user_profile()
        if user:
            # Extract just the key facts
            lines = user.split("\n")
            for line in lines[:10]:
                if line.startswith("- "):
                    parts.append(line)
        
        # Contacts (important for messaging)
        contacts = self.get_contacts()
        if contacts:
            parts.append("\n**Contacts:**")
            for c in contacts[:10]:
                parts.append(f"- {c['name']} ({c.get('relation', 'Contact')}): {c['phone']}")
        
        # Recent memory (very short)
        recent = self.get_recent_memory(days=1)
        if recent and recent[0].get("content"):
            # Just get headers from today
            today_content = recent[0]["content"]
            for line in today_content.split("\n"):
                if line.startswith("## "):
                    parts.append(f"- Today: {line[3:]}")
        
        result = "\n".join(parts)
        
        # Truncate if needed
        if len(result) > max_chars:
            result = result[:max_chars] + "..."
        
        return result


# Singleton instance
_shared_context: Optional[SharedContext] = None


def get_shared_context() -> SharedContext:
    """Get singleton SharedContext instance"""
    global _shared_context
    if _shared_context is None:
        _shared_context = SharedContext()
    return _shared_context
