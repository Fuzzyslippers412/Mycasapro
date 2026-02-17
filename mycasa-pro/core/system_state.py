"""
MyCasa Pro System State Management
Handles ON/OFF state, backups, and restoration
"""
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import STATE_FILE, DATA_DIR, BACKUP_DIR, DATABASE_URL


class SystemStateManager:
    """Manages system state persistence and backups"""
    
    def __init__(self):
        self.state_file = STATE_FILE
        self.data_dir = DATA_DIR
        self.backup_dir = BACKUP_DIR
        self.db_url = DATABASE_URL
        
    def get_state(self) -> Dict[str, Any]:
        """Get current system state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                # Ensure agents_enabled has all expected keys
                agents_enabled = state.get("agents_enabled") or {}
                defaults = {
                    "finance": True,
                    "maintenance": True,
                    "contractors": True,
                    "projects": True,
                    "security": True,
                    "janitor": True,
                    "mail": True,
                    "backup": True,
                }
                changed = False
                for key, value in defaults.items():
                    if key not in agents_enabled:
                        agents_enabled[key] = value
                        changed = True
                if changed:
                    state["agents_enabled"] = agents_enabled
                    self.save_state(state)
                return state
            except Exception:
                pass
        
        # Default state
        return {
            "running": False,
            "last_shutdown": None,
            "last_startup": None,
            "last_backup": None,
            "agents_enabled": {
                "finance": True,
                "maintenance": True,
                "contractors": True,
                "projects": True,
                "security": True,
                "janitor": True,
                "mail": True,
                "backup": True,
            },
            "settings": {}
        }
    
    def save_state(self, state: Dict[str, Any]) -> bool:
        """Save system state to disk"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"[SystemState] Failed to save state: {e}")
            return False
    
    def is_running(self) -> bool:
        """Check if system is marked as running"""
        state = self.get_state()
        return state.get("running", False)
    
    def create_backup(self) -> Dict[str, Any]:
        """Create a backup of the database and state"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        result = {
            "success": True,
            "timestamp": timestamp,
            "backup_path": str(backup_path),
            "files": []
        }
        
        try:
            # Backup state file
            if self.state_file.exists():
                shutil.copy2(self.state_file, backup_path / "system_state.json")
                result["files"].append("system_state.json")
            
            # Backup SQLite database
            if "sqlite" in self.db_url.lower():
                db_path = self.db_url.replace("sqlite:///", "")
                if Path(db_path).exists():
                    shutil.copy2(db_path, backup_path / "mycasa.db")
                    result["files"].append("mycasa.db")
            
            # For PostgreSQL, create a pg_dump
            elif "postgresql" in self.db_url.lower():
                dump_file = backup_path / "mycasa_pg_dump.sql"
                try:
                    # Extract connection details
                    # Format: postgresql://user:pass@host:port/dbname
                    import re
                    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', self.db_url)
                    if match:
                        user, password, host, port, dbname = match.groups()
                        env = {"PGPASSWORD": password}
                        cmd = ["pg_dump", "-h", host, "-p", port, "-U", user, "-d", dbname, "-f", str(dump_file)]
                        subprocess.run(cmd, env={**subprocess.os.environ, **env}, check=True, capture_output=True)
                        result["files"].append("mycasa_pg_dump.sql")
                except Exception as e:
                    result["pg_dump_error"] = str(e)
            
            # Update state with backup info
            state = self.get_state()
            state["last_backup"] = timestamp
            self.save_state(state)
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    def list_backups(self) -> list:
        """List all available backups"""
        backups = []
        for backup_dir in sorted(self.backup_dir.iterdir(), reverse=True):
            if backup_dir.is_dir() and backup_dir.name.startswith("backup_"):
                files = list(backup_dir.iterdir())
                backups.append({
                    "name": backup_dir.name,
                    "timestamp": backup_dir.name.replace("backup_", ""),
                    "path": str(backup_dir),
                    "files": [f.name for f in files],
                    "size_bytes": sum(f.stat().st_size for f in files if f.is_file())
                })
        return backups
    
    def restore_backup(self, backup_name: str) -> Dict[str, Any]:
        """Restore from a backup"""
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            return {"success": False, "error": f"Backup not found: {backup_name}"}
        
        result = {
            "success": True,
            "backup_name": backup_name,
            "restored_files": []
        }
        
        try:
            # Restore state file
            state_backup = backup_path / "system_state.json"
            if state_backup.exists():
                shutil.copy2(state_backup, self.state_file)
                result["restored_files"].append("system_state.json")
            
            # Restore SQLite database
            if "sqlite" in self.db_url.lower():
                db_backup = backup_path / "mycasa.db"
                if db_backup.exists():
                    db_path = self.db_url.replace("sqlite:///", "")
                    shutil.copy2(db_backup, db_path)
                    result["restored_files"].append("mycasa.db")
            
            # For PostgreSQL, restore from pg_dump
            elif "postgresql" in self.db_url.lower():
                dump_file = backup_path / "mycasa_pg_dump.sql"
                if dump_file.exists():
                    try:
                        import re
                        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', self.db_url)
                        if match:
                            user, password, host, port, dbname = match.groups()
                            env = {"PGPASSWORD": password}
                            cmd = ["psql", "-h", host, "-p", port, "-U", user, "-d", dbname, "-f", str(dump_file)]
                            subprocess.run(cmd, env={**subprocess.os.environ, **env}, check=True, capture_output=True)
                            result["restored_files"].append("mycasa_pg_dump.sql")
                    except Exception as e:
                        result["pg_restore_error"] = str(e)
                        
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
        
        return result
    
    def shutdown(self, save_settings: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Graceful system shutdown
        - Saves current state
        - Creates backup
        - Marks system as stopped
        """
        result = {"success": True, "timestamp": datetime.now().isoformat()}
        
        # Get current state
        state = self.get_state()
        
        # Merge agent settings at top level if provided
        if save_settings:
            # Extract agents_enabled to top level
            if "agents_enabled" in save_settings:
                state["agents_enabled"] = {
                    **state.get("agents_enabled", {}),
                    **save_settings.pop("agents_enabled")
                }
            # Store remaining settings
            state["settings"] = {**state.get("settings", {}), **save_settings}
        
        # Save state before backup so backup includes latest state
        state["running"] = True  # Still running until backup completes
        self.save_state(state)
        
        # Create backup
        backup_result = self.create_backup()
        result["backup"] = backup_result
        
        if not backup_result.get("success"):
            result["warning"] = "Backup failed but proceeding with shutdown"
        
        # Re-read state after backup (create_backup updates last_backup)
        state = self.get_state()
        
        # Update state to stopped
        state["running"] = False
        state["last_shutdown"] = datetime.now().isoformat()
        
        if not self.save_state(state):
            result["success"] = False
            result["error"] = "Failed to save state"
        
        return result
    
    def startup(self, restore_latest: bool = True) -> Dict[str, Any]:
        """
        System startup
        - Restores last state if available
        - Marks system as running
        """
        result = {"success": True, "timestamp": datetime.now().isoformat()}
        
        state = self.get_state()
        
        # Mark as running
        state["running"] = True
        state["last_startup"] = datetime.now().isoformat()
        
        # Include restored state info
        result["restored_from"] = state.get("last_shutdown")
        result["agents_enabled"] = state.get("agents_enabled", {})
        result["settings"] = state.get("settings", {})
        result["last_backup"] = state.get("last_backup")
        
        if not self.save_state(state):
            result["success"] = False
            result["error"] = "Failed to save state"
        
        return result
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {
            "type": "postgresql" if "postgresql" in self.db_url.lower() else "sqlite",
            "url": self.db_url.split("@")[-1] if "postgresql" in self.db_url else "local",
            "size_formatted": "Unknown",
            "last_backup": None
        }
        
        # Get last backup time from state
        state = self.get_state()
        stats["last_backup"] = state.get("last_backup")
        
        # Get size for SQLite
        if "sqlite" in self.db_url.lower():
            db_path = Path(self.db_url.replace("sqlite:///", ""))
            if db_path.exists():
                size_bytes = db_path.stat().st_size
                if size_bytes < 1024:
                    stats["size_formatted"] = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    stats["size_formatted"] = f"{size_bytes / 1024:.1f} KB"
                else:
                    stats["size_formatted"] = f"{size_bytes / (1024 * 1024):.1f} MB"
        
        return stats


# Singleton instance
_state_manager: Optional[SystemStateManager] = None

def get_state_manager() -> SystemStateManager:
    global _state_manager
    if _state_manager is None:
        _state_manager = SystemStateManager()
    return _state_manager
