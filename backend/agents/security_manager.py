"""
Security Agent - Aïcha
Monitors security incidents and system health
"""
from typing import Dict, Any, List
from .base import BaseAgent


class SecurityManagerAgent(BaseAgent):
    """
    Security Agent (Aïcha) - monitors security and incidents
    
    Responsibilities:
    - Incident logging and tracking
    - System health monitoring
    - Alert management
    - Access control oversight
    """
    
    def __init__(self):
        super().__init__(
            agent_id="security",
            name="Aïcha",
            description="Security Manager - Incidents and monitoring",
            emoji="🛡️"
        )
        self.start()
    
    def _get_metrics(self) -> Dict[str, Any]:
        """Get security-specific metrics"""
        logs = self.get_recent_logs(50)
        errors = [l for l in logs if l.get("status") == "error"]
        warnings = [l for l in logs if l.get("status") == "warning"]
        return {
            "recent_errors": len(errors),
            "recent_warnings": len(warnings),
            "system_status": "secure" if len(errors) == 0 else "alert",
        }
    
    async def chat(self, message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Handle security-related chat"""
        msg_lower = message.lower()
        
        if "status" in msg_lower or "security" in msg_lower or "incidents" in msg_lower:
            metrics = self._get_metrics()
            logs = self.get_recent_logs(5)
            
            status_icon = "✅" if metrics["system_status"] == "secure" else "⚠️"
            lines = [
                f"{status_icon} **Security Status:** {metrics['system_status'].upper()}",
                f"  • Recent errors: {metrics['recent_errors']}",
                f"  • Recent warnings: {metrics['recent_warnings']}",
            ]
            
            if logs:
                lines.append("\n**Recent Activity:**")
                for l in logs[:3]:
                    icon = "✅" if l.get("status") == "success" else "⚠️"
                    lines.append(f"  {icon} {l.get('action', 'unknown')}")
            
            self.log_action("security_check", "Reported security status")
            return "\n".join(lines) + f"\n\n— Aïcha 🛡️"
        
        return await super().chat(message)
