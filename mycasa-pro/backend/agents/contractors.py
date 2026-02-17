"""
Contractors Agent - Malik
Manages service providers and contractor directory
"""
from typing import Dict, Any, List
from .base import BaseAgent


class ContractorsAgent(BaseAgent):
    """
    Contractors Agent (Malik) - manages service providers
    
    Responsibilities:
    - Contractor directory management
    - Job scheduling and tracking
    - Reviews and ratings
    - Cost negotiations
    """
    
    def __init__(self):
        super().__init__(
            agent_id="contractors",
            name="Malik",
            description="Contractors Manager - Service provider directory",
            emoji="👷"
        )
        self.start()
    
    def _get_metrics(self) -> Dict[str, Any]:
        """Get contractor-specific metrics"""
        try:
            contractors = self.get_contractors_from_db()
            jobs = self.get_jobs_from_db()
            active_jobs = [j for j in jobs if j.get("status") in ["scheduled", "in_progress"]]
            return {
                "contractor_count": len(contractors),
                "active_jobs": len(active_jobs),
                "total_jobs": len(jobs),
            }
        except Exception:
            return {}
    
    def get_contractors_from_db(self) -> List[Dict[str, Any]]:
        """Get contractors from database"""
        from sqlalchemy import text
        from ..storage.database import get_db_session
        
        db = get_db_session()
        try:
            contractors = db.execute(
                text("SELECT id, name, company, service_type, rating FROM contractors ORDER BY name")
            ).fetchall()
            
            return [
                {"id": c[0], "name": c[1], "company": c[2], "service_type": c[3], "rating": c[4]}
                for c in contractors
            ]
        except Exception:
            return []
        finally:
            db.close()
    
    def get_jobs_from_db(self) -> List[Dict[str, Any]]:
        """Get contractor jobs from database"""
        from sqlalchemy import text
        from ..storage.database import get_db_session
        
        db = get_db_session()
        try:
            jobs = db.execute(
                text("SELECT id, description, contractor_name, status, estimated_cost FROM contractor_jobs ORDER BY id DESC LIMIT 20")
            ).fetchall()
            
            return [
                {"id": j[0], "description": j[1], "contractor": j[2], "status": j[3], "cost": j[4]}
                for j in jobs
            ]
        except Exception:
            return []
        finally:
            db.close()
    
    async def chat(self, message: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Handle contractor-related chat"""
        msg_lower = message.lower()
        
        if "list" in msg_lower or "contractors" in msg_lower or "directory" in msg_lower:
            contractors = self.get_contractors_from_db()
            if contractors:
                lines = ["👷 **Contractor Directory:**"]
                for c in contractors[:10]:
                    rating = f"⭐{c['rating']}" if c.get('rating') else ""
                    lines.append(f"  • {c['name']} ({c['service_type']}) {rating}")
                self.log_action("contractors_viewed", f"Showed {len(contractors)} contractors")
                return "\n".join(lines) + f"\n\n— Malik 👷"
            else:
                return "No contractors in the directory yet. Add some! 👷"
        
        if "jobs" in msg_lower:
            jobs = self.get_jobs_from_db()
            if jobs:
                lines = ["📋 **Recent Jobs:**"]
                for j in jobs[:5]:
                    status_icon = "✅" if j["status"] == "completed" else "🔄" if j["status"] == "in_progress" else "📝"
                    lines.append(f"  {status_icon} {j['description'][:40]}... ({j['status']})")
                self.log_action("jobs_viewed", f"Showed {len(jobs)} jobs")
                return "\n".join(lines) + f"\n\n— Malik 👷"
            else:
                return "No jobs recorded yet. 👷"
        
        return await super().chat(message)
