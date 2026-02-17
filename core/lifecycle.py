"""
MyCasa Pro - System Lifecycle Manager
Single source of truth for system state with idempotent operations.
"""
import json
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field

from core.settings_typed import get_settings_store
from core.events_v2 import get_event_bus, reset_event_bus, EventType, emit_sync


class SystemState(str, Enum):
    """System states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class AgentStatus:
    """Status of a single agent"""
    name: str
    enabled: bool = True
    running: bool = False
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class SystemStatus:
    """Complete system status"""
    state: SystemState = SystemState.STOPPED
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    last_backup: Optional[str] = None
    agents: Dict[str, AgentStatus] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "running": self.state == SystemState.RUNNING,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "last_backup": self.last_backup,
            "error": self.error,
            "agents": {
                name: {
                    "enabled": a.enabled,
                    "running": a.running,
                    "started_at": a.started_at.isoformat() if a.started_at else None,
                    "last_heartbeat": a.last_heartbeat.isoformat() if a.last_heartbeat else None,
                    "error": a.error,
                }
                for name, a in self.agents.items()
            },
        }


class LifecycleManager:
    """
    Manages system lifecycle with:
    - Idempotent startup/shutdown
    - State persistence
    - Agent coordination
    - Backup management
    """
    
    AGENT_NAMES = ["manager", "finance", "maintenance", "contractors", "projects", "security", "janitor", "mail", "backup"]
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.backup_dir = self.data_dir / "backups"
        self.state_file = self.data_dir / "lifecycle_state.json"
        
        self._status = SystemStatus()
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._startup_token: Optional[str] = None  # Prevent duplicate startups
        
        # Initialize agent statuses
        for name in self.AGENT_NAMES:
            self._status.agents[name] = AgentStatus(name=name)
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Load persisted state
        self._load_state()
    
    # ============ STATE PERSISTENCE ============
    
    def _load_state(self):
        """Load persisted state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                
                self._status.last_backup = data.get("last_backup")
                self._status.stopped_at = (
                    datetime.fromisoformat(data["stopped_at"])
                    if data.get("stopped_at") else None
                )
                
                # Restore agent enabled states from settings
                settings = get_settings_store().get()
                for name, enabled in settings.get_enabled_agents().items():
                    if name in self._status.agents:
                        self._status.agents[name].enabled = enabled
                        
            except Exception as e:
                print(f"[Lifecycle] Error loading state: {e}")
    
    def _save_state(self):
        """Persist state to disk"""
        try:
            data = {
                "state": self._status.state.value,
                "started_at": self._status.started_at.isoformat() if self._status.started_at else None,
                "stopped_at": self._status.stopped_at.isoformat() if self._status.stopped_at else None,
                "last_backup": self._status.last_backup,
                "agents_enabled": {
                    name: a.enabled for name, a in self._status.agents.items()
                },
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Lifecycle] Error saving state: {e}")
    
    # ============ LIFECYCLE OPERATIONS ============
    
    def startup(self, force: bool = False) -> Dict[str, Any]:
        """
        Idempotent system startup.
        
        Returns dict with:
        - success: bool
        - already_running: bool (if was already running)
        - agents_started: list of agent names
        - restored_from: datetime of last shutdown
        """
        with self._lock:
            # Idempotency check
            if self._status.state == SystemState.RUNNING:
                return {
                    "success": True,
                    "already_running": True,
                    "message": "System already running",
                    "state": self._status.to_dict(),
                }
            
            # Prevent concurrent startups
            if self._status.state == SystemState.STARTING and not force:
                return {
                    "success": False,
                    "error": "Startup already in progress",
                }
            
            result = {
                "success": True,
                "already_running": False,
                "agents_started": [],
                "restored_from": self._status.stopped_at.isoformat() if self._status.stopped_at else None,
            }
            
            try:
                self._status.state = SystemState.STARTING
                self._status.error = None
                
                # 1. Reset and initialize event bus
                reset_event_bus()
                event_bus = get_event_bus()
                event_bus.start()
                
                # 2. Load settings
                settings = get_settings_store().get()
                settings.system.running = True
                get_settings_store().save(settings)
                
                # 3. Initialize agents
                for name, agent_status in self._status.agents.items():
                    agent_settings = getattr(settings.agents, name, None)
                    if agent_settings and agent_settings.enabled:
                        agent_status.enabled = True
                        agent_status.running = True
                        agent_status.started_at = datetime.now()
                        agent_status.error = None
                        result["agents_started"].append(name)
                        
                        emit_sync(EventType.AGENT_STARTED, f"agent.{name}", {"name": name})
                
                # 4. Mark system as running
                self._status.state = SystemState.RUNNING
                self._status.started_at = datetime.now()
                self._save_state()
                
                emit_sync(EventType.SYSTEM_STARTED, "lifecycle", {
                    "agents_started": len(result["agents_started"]),
                })
                
                result["state"] = self._status.to_dict()
                
            except Exception as e:
                self._status.state = SystemState.ERROR
                self._status.error = str(e)
                result["success"] = False
                result["error"] = str(e)
            
            return result
    
    def shutdown(self, create_backup: bool = True, save_settings: Dict = None) -> Dict[str, Any]:
        """
        Idempotent system shutdown.
        
        Returns dict with:
        - success: bool
        - already_stopped: bool
        - backup: backup info if created
        """
        with self._lock:
            # Idempotency check
            if self._status.state == SystemState.STOPPED:
                return {
                    "success": True,
                    "already_stopped": True,
                    "message": "System already stopped",
                }
            
            # Prevent concurrent shutdowns
            if self._status.state == SystemState.STOPPING:
                return {
                    "success": False,
                    "error": "Shutdown already in progress",
                }
            
            result = {
                "success": True,
                "already_stopped": False,
            }
            
            try:
                self._status.state = SystemState.STOPPING
                
                # 1. Save any provided settings
                if save_settings:
                    settings = get_settings_store().get()
                    # Update agent enabled states
                    if "agents_enabled" in save_settings:
                        for name, enabled in save_settings["agents_enabled"].items():
                            agent_settings = getattr(settings.agents, name, None)
                            if agent_settings:
                                agent_settings.enabled = enabled
                    get_settings_store().save(settings)
                
                # 2. Stop agents
                for name, agent_status in self._status.agents.items():
                    if agent_status.running:
                        agent_status.running = False
                        emit_sync(EventType.AGENT_STOPPED, f"agent.{name}", {"name": name})
                
                # 3. Create backup
                if create_backup:
                    backup_result = self.create_backup()
                    result["backup"] = backup_result
                    if backup_result.get("success"):
                        self._status.last_backup = backup_result["timestamp"]
                
                # 4. Update settings
                settings = get_settings_store().get()
                settings.system.running = False
                get_settings_store().save(settings)
                
                # 5. Stop event bus
                event_bus = get_event_bus()
                event_bus.stop()
                
                # 6. Mark system as stopped
                self._status.state = SystemState.STOPPED
                self._status.stopped_at = datetime.now()
                self._save_state()
                
                result["state"] = self._status.to_dict()
                
            except Exception as e:
                self._status.state = SystemState.ERROR
                self._status.error = str(e)
                result["success"] = False
                result["error"] = str(e)
            
            return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        with self._lock:
            # Sync enabled flags with latest settings (in case updated while running)
            try:
                settings = get_settings_store().get()
                enabled_map = settings.get_enabled_agents()
                for name, agent_status in self._status.agents.items():
                    if name in enabled_map:
                        agent_status.enabled = enabled_map[name]
                    # If disabled, ensure running is false
                    if not agent_status.enabled and agent_status.running:
                        agent_status.running = False
            except Exception:
                pass

            status_dict = self._status.to_dict()
            
            # Add enabled agent counts
            enabled = [a for a in self._status.agents.values() if a.enabled]
            running = [a for a in self._status.agents.values() if a.running]
            
            status_dict["agents_enabled_count"] = len(enabled)
            status_dict["agents_running_count"] = len(running)
            status_dict["agents_enabled"] = {
                name: a.enabled for name, a in self._status.agents.items()
            }
            
            return status_dict

    def set_agent_running(self, agent_id: str, running: bool) -> Dict[str, Any]:
        """Start/stop a single agent without disabling it."""
        with self._lock:
            agent = self._status.agents.get(agent_id)
            if not agent:
                return {"success": False, "error": f"Unknown agent: {agent_id}"}

            # Ensure enabled if starting
            if running:
                agent.enabled = True
                agent.running = True
                if not agent.started_at:
                    agent.started_at = datetime.now()
                agent.error = None
                emit_sync(EventType.AGENT_STARTED, f"agent.{agent_id}", {"name": agent_id})
            else:
                agent.running = False
                emit_sync(EventType.AGENT_STOPPED, f"agent.{agent_id}", {"name": agent_id})

            # Persist enabled state to settings
            try:
                settings = get_settings_store().get()
                agent_settings = getattr(settings.agents, agent_id, None)
                if agent_settings:
                    agent_settings.enabled = agent.enabled
                    get_settings_store().save(settings)
            except Exception:
                pass

            self._save_state()
            return {
                "success": True,
                "agent_id": agent_id,
                "enabled": agent.enabled,
                "running": agent.running,
                "state": self._status.to_dict(),
            }

    def set_agent_enabled(self, agent_id: str, enabled: bool) -> Dict[str, Any]:
        """Enable/disable an agent. Disabling stops it."""
        with self._lock:
            agent = self._status.agents.get(agent_id)
            if not agent:
                return {"success": False, "error": f"Unknown agent: {agent_id}"}

            agent.enabled = enabled
            if not enabled:
                agent.running = False
                emit_sync(EventType.AGENT_STOPPED, f"agent.{agent_id}", {"name": agent_id})
            elif self._status.state == SystemState.RUNNING and not agent.running:
                agent.running = True
                if not agent.started_at:
                    agent.started_at = datetime.now()
                emit_sync(EventType.AGENT_STARTED, f"agent.{agent_id}", {"name": agent_id})

            # Persist enabled state to settings
            try:
                settings = get_settings_store().get()
                agent_settings = getattr(settings.agents, agent_id, None)
                if agent_settings:
                    agent_settings.enabled = enabled
                    get_settings_store().save(settings)
            except Exception:
                pass

            self._save_state()
            return {
                "success": True,
                "agent_id": agent_id,
                "enabled": agent.enabled,
                "running": agent.running,
                "state": self._status.to_dict(),
            }
    
    # ============ BACKUP OPERATIONS ============
    
    def create_backup(self) -> Dict[str, Any]:
        """Create a backup of database and settings"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        result = {
            "success": True,
            "timestamp": timestamp,
            "backup_path": str(backup_path),
            "files": [],
        }
        
        try:
            # Backup lifecycle state
            if self.state_file.exists():
                shutil.copy2(self.state_file, backup_path / "lifecycle_state.json")
                result["files"].append("lifecycle_state.json")
            
            # Backup settings
            settings_file = self.data_dir / "settings.json"
            if settings_file.exists():
                shutil.copy2(settings_file, backup_path / "settings.json")
                result["files"].append("settings.json")
            
            # Backup SQLite database
            db_file = self.data_dir / "mycasa.db"
            if db_file.exists():
                shutil.copy2(db_file, backup_path / "mycasa.db")
                result["files"].append("mycasa.db")
            
            self._status.last_backup = timestamp
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = []
        for backup_dir in sorted(self.backup_dir.iterdir(), reverse=True):
            if backup_dir.is_dir() and backup_dir.name.startswith("backup_"):
                files = list(backup_dir.iterdir())
                backups.append({
                    "name": backup_dir.name,
                    "timestamp": backup_dir.name.replace("backup_", ""),
                    "path": str(backup_dir),
                    "files": [f.name for f in files],
                    "size_bytes": sum(f.stat().st_size for f in files if f.is_file()),
                })
        return backups
    
    def restore_backup(self, backup_name: str) -> Dict[str, Any]:
        """Restore from a backup"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return {"success": False, "error": f"Backup not found: {backup_name}"}
        
        # Must be stopped to restore
        if self._status.state == SystemState.RUNNING:
            return {"success": False, "error": "Cannot restore while running. Stop system first."}
        
        result = {
            "success": True,
            "backup_name": backup_name,
            "restored_files": [],
        }
        
        try:
            # Restore each file
            for file_name in ["lifecycle_state.json", "settings.json", "mycasa.db"]:
                src = backup_path / file_name
                if src.exists():
                    dst = self.data_dir / file_name
                    shutil.copy2(src, dst)
                    result["restored_files"].append(file_name)
            
            # Reload state
            self._load_state()
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    # ============ AGENT OPERATIONS ============
    
    def set_agent_enabled(self, agent_name: str, enabled: bool) -> bool:
        """Enable or disable an agent"""
        with self._lock:
            if agent_name not in self._status.agents:
                return False
            
            self._status.agents[agent_name].enabled = enabled
            
            # Update settings
            settings = get_settings_store().get()
            agent_settings = getattr(settings.agents, agent_name, None)
            if agent_settings:
                agent_settings.enabled = enabled
                get_settings_store().save(settings)
            
            # If system is running and disabling, stop the agent
            if self._status.state == SystemState.RUNNING and not enabled:
                self._status.agents[agent_name].running = False
            
            self._save_state()
            return True
    
    def agent_heartbeat(self, agent_name: str):
        """Record agent heartbeat"""
        with self._lock:
            if agent_name in self._status.agents:
                self._status.agents[agent_name].last_heartbeat = datetime.now()


# ============ SINGLETON ============

_lifecycle_manager: Optional[LifecycleManager] = None
_lifecycle_lock = threading.Lock()

def get_lifecycle_manager() -> LifecycleManager:
    """Get global lifecycle manager instance"""
    global _lifecycle_manager
    with _lifecycle_lock:
        if _lifecycle_manager is None:
            from config.settings import DATA_DIR
            _lifecycle_manager = LifecycleManager(DATA_DIR)
        return _lifecycle_manager
