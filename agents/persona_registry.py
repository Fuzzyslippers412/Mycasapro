"""
Persona Registry for MyCasa Pro

Personas are first-class, modular, replaceable capabilities.

Each persona has:
- system prompt (policy + behavior)
- defined inputs/outputs
- explicit authority boundaries
- enable/disable lifecycle controls

The platform supports:
- adding personas at runtime
- disabling/removing without restart
- versioning and rollback
- observing active personas

AUTHORITY:
- Janitor: audit, recommend add/disable/remove
- Manager (Galidima): final authority to add/remove
- User: ultimate authority via Manager

NO PERSONA IS PERMANENT.
ALL PERSONAS ARE OPTIONAL, COMPOSABLE, AND REVERSIBLE.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import shutil
from dataclasses import dataclass, asdict
from enum import Enum


class PersonaState(Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    REMOVED = "removed"
    PENDING = "pending"  # Awaiting approval


@dataclass
class PersonaVersion:
    """A versioned snapshot of a persona definition"""
    version: int
    soul_md: str
    memory_md: str
    config_yaml: str
    created_at: str
    created_by: str
    reason: str


@dataclass
class PersonaDefinition:
    """Complete persona definition with lifecycle metadata"""
    id: str
    name: str
    description: str
    state: str
    
    # Authority
    authority_boundaries: List[str]
    escalates_to: List[str]
    coordinates_with: List[str]
    
    # I/O Contract
    inputs: List[Dict[str, str]]
    outputs: List[Dict[str, str]]
    
    # Lifecycle
    current_version: int
    versions: List[Dict]
    
    # Metadata
    created_at: str
    created_by: str
    last_modified: str
    enabled_at: Optional[str]
    disabled_at: Optional[str]
    disabled_reason: Optional[str]
    
    # Audit
    effectiveness_score: Optional[float]
    last_audit: Optional[str]
    audit_notes: Optional[str]


class PersonaRegistry:
    """
    Central registry for all MyCasa Pro personas.
    
    Responsibilities:
    - Track all persona definitions and states
    - Support runtime add/disable/remove
    - Maintain version history for rollback
    - Provide observability into active personas
    """
    
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path(__file__).parent
        self.registry_file = self.base_path / "memory" / "persona_registry.json"
        self.personas_dir = self.base_path / "memory"
        self._registry: Dict[str, PersonaDefinition] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from disk"""
        if self.registry_file.exists():
            data = json.loads(self.registry_file.read_text())
            for pid, pdata in data.get("personas", {}).items():
                self._registry[pid] = PersonaDefinition(**pdata)
        else:
            # Initialize with discovered personas
            self._discover_personas()
    
    def _save_registry(self):
        """Persist registry to disk"""
        data = {
            "version": 1,
            "last_updated": datetime.now().isoformat(),
            "personas": {
                pid: asdict(p) for pid, p in self._registry.items()
            }
        }
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.registry_file.write_text(json.dumps(data, indent=2, default=str))
    
    def _discover_personas(self):
        """Discover personas from filesystem"""
        for agent_dir in self.personas_dir.iterdir():
            if agent_dir.is_dir() and (agent_dir / "SOUL.md").exists():
                persona_id = agent_dir.name
                soul_content = (agent_dir / "SOUL.md").read_text()
                
                # Extract name from SOUL.md header
                name = persona_id.replace("-", " ").replace("_", " ").title()
                for line in soul_content.split("\n"):
                    if line.startswith("# SOUL.md"):
                        # Extract name from "# SOUL.md — Name"
                        if "—" in line:
                            name = line.split("—")[1].strip()
                        break
                
                self._registry[persona_id] = PersonaDefinition(
                    id=persona_id,
                    name=name,
                    description=self._extract_description(soul_content),
                    state=PersonaState.ACTIVE.value,
                    authority_boundaries=self._extract_authority(soul_content),
                    escalates_to=self._extract_escalation(soul_content),
                    coordinates_with=self._extract_coordination(soul_content),
                    inputs=[],
                    outputs=[],
                    current_version=1,
                    versions=[{
                        "version": 1,
                        "created_at": datetime.now().isoformat(),
                        "created_by": "discovery",
                        "reason": "Initial discovery"
                    }],
                    created_at=datetime.now().isoformat(),
                    created_by="discovery",
                    last_modified=datetime.now().isoformat(),
                    enabled_at=datetime.now().isoformat(),
                    disabled_at=None,
                    disabled_reason=None,
                    effectiveness_score=None,
                    last_audit=None,
                    audit_notes=None
                )
        
        self._save_registry()
    
    def _extract_description(self, soul_content: str) -> str:
        """Extract description from SOUL.md"""
        lines = soul_content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("## ROLE"):
                # Return next non-empty paragraph
                desc = []
                for j in range(i + 1, min(i + 10, len(lines))):
                    if lines[j].strip() and not lines[j].startswith("#"):
                        desc.append(lines[j].strip())
                    elif lines[j].startswith("#"):
                        break
                return " ".join(desc)[:200]
        return ""
    
    def _extract_authority(self, soul_content: str) -> List[str]:
        """Extract authority boundaries from SOUL.md"""
        boundaries = []
        in_authority = False
        for line in soul_content.split("\n"):
            if "AUTHORITY" in line.upper() and line.startswith("#"):
                in_authority = True
                continue
            if in_authority and line.startswith("#"):
                break
            if in_authority and line.strip().startswith("-"):
                boundaries.append(line.strip()[1:].strip())
        return boundaries[:10]
    
    def _extract_escalation(self, soul_content: str) -> List[str]:
        """Extract escalation targets from SOUL.md"""
        escalates = []
        for line in soul_content.split("\n"):
            lower = line.lower()
            if "escalate" in lower and ("manager" in lower or "galidima" in lower):
                escalates.append("manager")
            if "escalate" in lower and "janitor" in lower:
                escalates.append("janitor")
        return list(set(escalates))
    
    def _extract_coordination(self, soul_content: str) -> List[str]:
        """Extract coordination targets from SOUL.md"""
        coords = []
        for line in soul_content.split("\n"):
            lower = line.lower()
            if "coordinate" in lower or "coordinates with" in lower:
                if "manager" in lower or "galidima" in lower:
                    coords.append("manager")
                if "janitor" in lower:
                    coords.append("janitor")
                if "security" in lower:
                    coords.append("security-manager")
        return list(set(coords))
    
    # ============ QUERY METHODS ============
    
    def list_personas(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """List all personas with their states"""
        result = []
        for pid, persona in self._registry.items():
            if not include_disabled and persona.state == PersonaState.DISABLED.value:
                continue
            if persona.state == PersonaState.REMOVED.value:
                continue
            
            result.append({
                "id": pid,
                "name": persona.name,
                "state": persona.state,
                "version": persona.current_version,
                "description": persona.description[:100],
                "effectiveness_score": persona.effectiveness_score
            })
        return result
    
    def get_persona(self, persona_id: str) -> Optional[PersonaDefinition]:
        """Get full persona definition"""
        return self._registry.get(persona_id)
    
    def get_active_personas(self) -> List[str]:
        """Get list of active persona IDs"""
        return [
            pid for pid, p in self._registry.items()
            if p.state == PersonaState.ACTIVE.value
        ]
    
    def why_active(self, persona_id: str) -> Dict[str, Any]:
        """Explain why a persona is active"""
        persona = self._registry.get(persona_id)
        if not persona:
            return {"error": "Persona not found"}
        
        return {
            "persona_id": persona_id,
            "state": persona.state,
            "enabled_at": persona.enabled_at,
            "created_by": persona.created_by,
            "current_version": persona.current_version,
            "last_audit": persona.last_audit,
            "effectiveness_score": persona.effectiveness_score,
            "reason": f"Enabled by {persona.created_by} on {persona.enabled_at}"
        }
    
    # ============ LIFECYCLE METHODS ============
    
    def add_persona(
        self,
        persona_id: str,
        name: str,
        soul_md: str,
        description: str = "",
        authority_boundaries: List[str] = None,
        escalates_to: List[str] = None,
        coordinates_with: List[str] = None,
        created_by: str = "user",
        auto_enable: bool = False
    ) -> Dict[str, Any]:
        """
        Add a new persona at runtime.
        
        Does NOT require restart.
        Persona starts in PENDING state unless auto_enable=True.
        """
        if persona_id in self._registry:
            return {"success": False, "error": "Persona already exists"}
        
        # Create persona directory and files
        persona_dir = self.personas_dir / persona_id
        persona_dir.mkdir(parents=True, exist_ok=True)
        (persona_dir / "context").mkdir(exist_ok=True)
        
        # Write SOUL.md
        (persona_dir / "SOUL.md").write_text(soul_md)
        
        # Write MEMORY.md
        (persona_dir / "MEMORY.md").write_text(
            f"# MEMORY.md — {name} Agent Long-Term Memory\n\n"
        )
        
        # Create registry entry
        now = datetime.now().isoformat()
        state = PersonaState.ACTIVE.value if auto_enable else PersonaState.PENDING.value
        
        self._registry[persona_id] = PersonaDefinition(
            id=persona_id,
            name=name,
            description=description or self._extract_description(soul_md),
            state=state,
            authority_boundaries=authority_boundaries or self._extract_authority(soul_md),
            escalates_to=escalates_to or ["manager"],
            coordinates_with=coordinates_with or [],
            inputs=[],
            outputs=[],
            current_version=1,
            versions=[{
                "version": 1,
                "created_at": now,
                "created_by": created_by,
                "reason": "Initial creation"
            }],
            created_at=now,
            created_by=created_by,
            last_modified=now,
            enabled_at=now if auto_enable else None,
            disabled_at=None,
            disabled_reason=None,
            effectiveness_score=None,
            last_audit=None,
            audit_notes=None
        )
        
        self._save_registry()
        
        return {
            "success": True,
            "persona_id": persona_id,
            "state": state,
            "message": f"Persona '{name}' added in {state} state"
        }
    
    def enable_persona(self, persona_id: str, enabled_by: str = "manager") -> Dict[str, Any]:
        """Enable a disabled or pending persona"""
        persona = self._registry.get(persona_id)
        if not persona:
            return {"success": False, "error": "Persona not found"}
        
        if persona.state == PersonaState.ACTIVE.value:
            return {"success": True, "message": "Already active"}
        
        if persona.state == PersonaState.REMOVED.value:
            return {"success": False, "error": "Cannot enable removed persona - must re-add"}
        
        persona.state = PersonaState.ACTIVE.value
        persona.enabled_at = datetime.now().isoformat()
        persona.disabled_at = None
        persona.disabled_reason = None
        persona.last_modified = datetime.now().isoformat()
        
        self._save_registry()
        
        return {
            "success": True,
            "persona_id": persona_id,
            "state": persona.state,
            "message": f"Persona '{persona.name}' enabled by {enabled_by}"
        }
    
    def disable_persona(
        self,
        persona_id: str,
        reason: str,
        disabled_by: str = "manager"
    ) -> Dict[str, Any]:
        """
        Disable a persona without removing it.
        
        Persona can be re-enabled later.
        Does NOT require restart.
        """
        persona = self._registry.get(persona_id)
        if not persona:
            return {"success": False, "error": "Persona not found"}
        
        if persona.state == PersonaState.DISABLED.value:
            return {"success": True, "message": "Already disabled"}
        
        persona.state = PersonaState.DISABLED.value
        persona.disabled_at = datetime.now().isoformat()
        persona.disabled_reason = reason
        persona.last_modified = datetime.now().isoformat()
        
        self._save_registry()
        
        return {
            "success": True,
            "persona_id": persona_id,
            "state": persona.state,
            "message": f"Persona '{persona.name}' disabled: {reason}"
        }
    
    def remove_persona(
        self,
        persona_id: str,
        reason: str,
        removed_by: str = "manager",
        archive: bool = True
    ) -> Dict[str, Any]:
        """
        Remove a persona.
        
        If archive=True, persona files are moved to archive (reversible).
        If archive=False, persona files are deleted (irreversible).
        """
        persona = self._registry.get(persona_id)
        if not persona:
            return {"success": False, "error": "Persona not found"}
        
        persona_dir = self.personas_dir / persona_id
        
        if archive and persona_dir.exists():
            # Move to archive
            archive_dir = self.base_path / "memory" / "_archive" / f"{persona_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            archive_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(persona_dir), str(archive_dir))
        elif persona_dir.exists():
            # Delete permanently
            shutil.rmtree(persona_dir)
        
        persona.state = PersonaState.REMOVED.value
        persona.disabled_at = datetime.now().isoformat()
        persona.disabled_reason = f"Removed: {reason}"
        persona.last_modified = datetime.now().isoformat()
        
        self._save_registry()
        
        return {
            "success": True,
            "persona_id": persona_id,
            "archived": archive,
            "message": f"Persona '{persona.name}' removed: {reason}"
        }
    
    # ============ VERSIONING ============
    
    def update_persona(
        self,
        persona_id: str,
        soul_md: str = None,
        description: str = None,
        updated_by: str = "manager",
        reason: str = "Update"
    ) -> Dict[str, Any]:
        """
        Update a persona definition, creating a new version.
        
        Previous version is preserved for rollback.
        """
        persona = self._registry.get(persona_id)
        if not persona:
            return {"success": False, "error": "Persona not found"}
        
        persona_dir = self.personas_dir / persona_id
        
        # Save current version
        current_soul = ""
        if (persona_dir / "SOUL.md").exists():
            current_soul = (persona_dir / "SOUL.md").read_text()
        
        # Create version snapshot
        new_version = persona.current_version + 1
        persona.versions.append({
            "version": new_version,
            "created_at": datetime.now().isoformat(),
            "created_by": updated_by,
            "reason": reason,
            "previous_soul_hash": hash(current_soul)
        })
        
        # Update files
        if soul_md:
            (persona_dir / "SOUL.md").write_text(soul_md)
        
        if description:
            persona.description = description
        
        persona.current_version = new_version
        persona.last_modified = datetime.now().isoformat()
        
        self._save_registry()
        
        return {
            "success": True,
            "persona_id": persona_id,
            "new_version": new_version,
            "message": f"Persona updated to v{new_version}"
        }
    
    def rollback_persona(
        self,
        persona_id: str,
        to_version: int,
        rolled_back_by: str = "manager",
        reason: str = "Rollback"
    ) -> Dict[str, Any]:
        """
        Rollback a persona to a previous version.
        
        Requires archived version files (TODO: implement full snapshots).
        """
        persona = self._registry.get(persona_id)
        if not persona:
            return {"success": False, "error": "Persona not found"}
        
        if to_version >= persona.current_version:
            return {"success": False, "error": "Can only rollback to older versions"}
        
        # For now, just record the rollback intent
        # Full implementation would restore from version snapshots
        persona.versions.append({
            "version": persona.current_version + 1,
            "created_at": datetime.now().isoformat(),
            "created_by": rolled_back_by,
            "reason": f"Rollback to v{to_version}: {reason}",
            "rollback_from": persona.current_version,
            "rollback_to": to_version
        })
        
        persona.current_version += 1
        persona.last_modified = datetime.now().isoformat()
        
        self._save_registry()
        
        return {
            "success": True,
            "persona_id": persona_id,
            "rolled_back_to": to_version,
            "new_version": persona.current_version,
            "message": f"Rollback recorded. Manual restore of v{to_version} SOUL.md required."
        }
    
    # ============ AUDIT SUPPORT ============
    
    def record_audit(
        self,
        persona_id: str,
        effectiveness_score: float,
        notes: str,
        audited_by: str = "janitor"
    ) -> Dict[str, Any]:
        """Record an audit of a persona by the Janitor"""
        persona = self._registry.get(persona_id)
        if not persona:
            return {"success": False, "error": "Persona not found"}
        
        persona.effectiveness_score = effectiveness_score
        persona.last_audit = datetime.now().isoformat()
        persona.audit_notes = notes
        persona.last_modified = datetime.now().isoformat()
        
        self._save_registry()
        
        return {
            "success": True,
            "persona_id": persona_id,
            "effectiveness_score": effectiveness_score,
            "message": f"Audit recorded by {audited_by}"
        }
    
    def get_audit_recommendations(self) -> List[Dict[str, Any]]:
        """Get Janitor's recommendations for persona management"""
        recommendations = []
        
        for pid, persona in self._registry.items():
            if persona.state == PersonaState.REMOVED.value:
                continue
            
            # Check for underperforming personas
            if persona.effectiveness_score is not None and persona.effectiveness_score < 0.3:
                recommendations.append({
                    "persona_id": pid,
                    "recommendation": "disable",
                    "reason": f"Low effectiveness score: {persona.effectiveness_score:.2f}",
                    "severity": "medium"
                })
            
            # Check for stale personas (no audit in 30 days)
            if persona.last_audit:
                audit_date = datetime.fromisoformat(persona.last_audit)
                days_since = (datetime.now() - audit_date).days
                if days_since > 30:
                    recommendations.append({
                        "persona_id": pid,
                        "recommendation": "audit",
                        "reason": f"No audit in {days_since} days",
                        "severity": "low"
                    })
            elif persona.state == PersonaState.ACTIVE.value:
                recommendations.append({
                    "persona_id": pid,
                    "recommendation": "audit",
                    "reason": "Never audited",
                    "severity": "low"
                })
        
        return recommendations


# Singleton instance
_registry: Optional[PersonaRegistry] = None


def get_persona_registry() -> PersonaRegistry:
    """Get the singleton persona registry"""
    global _registry
    if _registry is None:
        _registry = PersonaRegistry()
    return _registry
