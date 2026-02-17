"""
Projects Agent - Zainab
Tracks home improvement projects
"""
from typing import Dict, Any, List
from .base import BaseAgent


class ProjectsAgent(BaseAgent):
    """
    Projects Agent (Zainab) - tracks home improvements
    
    Responsibilities:
    - Project planning and tracking
    - Budget allocation for projects
    - Progress monitoring
    - Milestone management
    """
    
    def __init__(self):
        super().__init__(
            agent_id="projects",
            name="Zainab",
            description="Projects Manager - Home improvement tracking",
            emoji="📋"
        )
        self.start()
    
    def _get_metrics(self) -> Dict[str, Any]:
        """Get project-specific metrics"""
        # Projects would come from a projects table
        return {
            "active_projects": len(self._pending_tasks),
            "completed_projects": 0,
        }
    
    async def chat(self, message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Handle project-related chat"""
        msg_lower = message.lower()
        
        if "projects" in msg_lower or "status" in msg_lower:
            tasks = self.get_pending_tasks()
            if tasks:
                lines = ["📋 **Active Projects:**"]
                for t in tasks[:5]:
                    lines.append(f"  • {t.get('title', 'Untitled')} - {t.get('status', 'pending')}")
                self.log_action("projects_viewed", f"Showed {len(tasks)} projects")
                return "\n".join(lines) + f"\n\n— Zainab 📋"
            else:
                return "No active projects. Ready to plan something new? 📋"
        
        return await super().chat(message)
