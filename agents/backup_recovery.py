"""
MyCasa Pro - Backup & Recovery Agent
Resilience and continuity agent for snapshots, restore, and system resurrection.

ROLE: Ensure the entire system can be rebuilt, restored, or rolled back safely
while preserving user preferences and patterns.

Coordinates with:
- Galidima (Manager) - approval authority
- Janitor - validation and integrity checks
- Security Manager - encryption and access control
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pathlib import Path
from enum import Enum
import json
import hashlib
import shutil
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base import BaseAgent


class BackupType(Enum):
    """Types of backups"""
    FULL = "full"              # System + data + patterns
    INCREMENTAL = "incremental" # Changes only
    CONFIG = "config"          # Personas, settings only
    PATTERN = "pattern"        # User preferences only


class RecoveryMode(Enum):
    """Recovery modes"""
    SOFT = "soft"              # Restore data/config, keep runtime
    ROLLBACK = "rollback"      # Revert to previous snapshot
    FULL_REBUILD = "rebuild"   # Fresh install + rehydrate
    SELECTIVE = "selective"    # Restore specific domain only


class BackupRecoveryAgent(BaseAgent):
    """
    Backup & Recovery Agent for MyCasa Pro.
    
    Responsibilities:
    - Create and manage system backups
    - Restore from known-good states
    - Preserve user operating patterns
    - Verify integrity after restore
    
    Authority:
    - MAY create backups, verify integrity, simulate restores
    - MUST obtain approval before destructive restores
    - MUST NOT overwrite live data without approval
    """
    
    def __init__(self):
        super().__init__("backup-recovery")
        self.backup_dir = Path(__file__).parent.parent / "data" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._registry: Dict[str, Dict] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load backup registry from disk"""
        registry_file = self.backup_dir / "registry.json"
        if registry_file.exists():
            self._registry = json.loads(registry_file.read_text())
    
    def _save_registry(self):
        """Save backup registry to disk"""
        registry_file = self.backup_dir / "registry.json"
        registry_file.write_text(json.dumps(self._registry, indent=2, default=str))
    
    def get_status(self) -> Dict[str, Any]:
        """Get backup agent status"""
        backups = list(self._registry.values())
        last_backup = max(backups, key=lambda b: b["timestamp"]) if backups else None
        
        return {
            "agent": "backup-recovery",
            "status": "active",
            "metrics": {
                "total_backups": len(backups),
                "last_backup": last_backup["timestamp"] if last_backup else None,
                "last_backup_type": last_backup["type"] if last_backup else None,
                "storage_used_mb": self._get_storage_used(),
                "oldest_backup": min(backups, key=lambda b: b["timestamp"])["timestamp"] if backups else None
            }
        }
    
    def _get_storage_used(self) -> float:
        """Calculate storage used by backups in MB"""
        total = 0
        for f in self.backup_dir.glob("**/*"):
            if f.is_file():
                total += f.stat().st_size
        return round(total / (1024 * 1024), 2)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BACKUP CREATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_backup(
        self,
        backup_type: BackupType = BackupType.FULL,
        notes: str = None,
        created_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Create a new backup.
        
        Args:
            backup_type: Type of backup (full, incremental, config, pattern)
            notes: Optional notes about this backup
            created_by: Who initiated the backup
        
        Returns:
            Backup metadata including ID and integrity hash
        """
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{backup_type.value}"
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)
        
        manifest = {
            "id": backup_id,
            "type": backup_type.value,
            "timestamp": datetime.now().isoformat(),
            "created_by": created_by,
            "notes": notes,
            "components": [],
            "integrity_hash": None,
            "version_compat": "1.0"
        }
        
        # Backup based on type
        if backup_type in [BackupType.FULL, BackupType.CONFIG]:
            manifest["components"].extend(self._backup_config(backup_path))
        
        if backup_type in [BackupType.FULL, BackupType.INCREMENTAL]:
            manifest["components"].extend(self._backup_data(backup_path))
        
        if backup_type in [BackupType.FULL, BackupType.PATTERN]:
            manifest["components"].extend(self._backup_patterns(backup_path))
        
        # Calculate integrity hash
        manifest["integrity_hash"] = self._calculate_integrity(backup_path)
        manifest["size_bytes"] = sum(
            f.stat().st_size for f in backup_path.glob("**/*") if f.is_file()
        )
        
        # Save manifest
        (backup_path / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
        
        # Update registry
        self._registry[backup_id] = manifest
        self._save_registry()
        
        return manifest
    
    def _backup_config(self, backup_path: Path) -> List[str]:
        """Backup configuration files"""
        components = []
        config_dir = backup_path / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Backup agent SOULs
        souls_dir = Path(__file__).parent / "memory"
        if souls_dir.exists():
            shutil.copytree(souls_dir, config_dir / "agent_souls", dirs_exist_ok=True)
            components.append("agent_souls")
        
        # Backup persona registry
        registry_file = souls_dir / "persona_registry.json"
        if registry_file.exists():
            shutil.copy(registry_file, config_dir / "persona_registry.json")
            components.append("persona_registry")
        
        # Backup app config
        app_config = Path(__file__).parent.parent / "config"
        if app_config.exists():
            shutil.copytree(app_config, config_dir / "app_config", dirs_exist_ok=True)
            components.append("app_config")
        
        return components
    
    def _backup_data(self, backup_path: Path) -> List[str]:
        """Backup data (database)"""
        components = []
        data_dir = backup_path / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Backup SQLite database
        db_path = Path(__file__).parent.parent / "data" / "mycasa.db"
        if db_path.exists():
            shutil.copy(db_path, data_dir / "mycasa.db")
            components.append("database")
        
        # Backup inbox messages cache
        inbox_cache = Path(__file__).parent.parent / "data" / "inbox_cache.json"
        if inbox_cache.exists():
            shutil.copy(inbox_cache, data_dir / "inbox_cache.json")
            components.append("inbox_cache")
        
        return components
    
    def _backup_patterns(self, backup_path: Path) -> List[str]:
        """Backup user operating patterns"""
        components = []
        patterns_dir = backup_path / "patterns"
        patterns_dir.mkdir(exist_ok=True)
        
        patterns = {
            "approval_thresholds": self._get_pattern("approval_thresholds"),
            "notification_preferences": self._get_pattern("notification_preferences"),
            "payment_rails": self._get_pattern("payment_rails"),
            "autonomy_tolerances": self._get_pattern("autonomy_tolerances"),
            "interaction_style": self._get_pattern("interaction_style")
        }
        
        (patterns_dir / "user_patterns.json").write_text(
            json.dumps(patterns, indent=2, default=str)
        )
        components.append("user_patterns")
        
        return components
    
    def _get_pattern(self, pattern_name: str) -> Any:
        """Get a user operating pattern from settings"""
        # TODO: Pull from actual settings
        # For now, return defaults
        defaults = {
            "approval_thresholds": {"cost": 500, "disruption": "medium"},
            "notification_preferences": {"batch": True, "urgent_only_night": True},
            "payment_rails": ["ach", "card"],
            "autonomy_tolerances": {"maintenance": "high", "finance": "low"},
            "interaction_style": "concise"
        }
        return defaults.get(pattern_name)
    
    def _calculate_integrity(self, backup_path: Path) -> str:
        """Calculate integrity hash for backup"""
        hasher = hashlib.sha256()
        for f in sorted(backup_path.glob("**/*")):
            if f.is_file():
                hasher.update(f.read_bytes())
        return hasher.hexdigest()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BACKUP LISTING & VERIFICATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def list_backups(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = sorted(
            self._registry.values(),
            key=lambda b: b["timestamp"],
            reverse=True
        )
        return backups[:limit]
    
    def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """Verify backup integrity"""
        if backup_id not in self._registry:
            return {"valid": False, "error": "Backup not found"}
        
        backup_path = self.backup_dir / backup_id
        if not backup_path.exists():
            return {"valid": False, "error": "Backup files missing"}
        
        manifest = self._registry[backup_id]
        current_hash = self._calculate_integrity(backup_path)
        
        valid = current_hash == manifest.get("integrity_hash")
        
        return {
            "valid": valid,
            "backup_id": backup_id,
            "expected_hash": manifest.get("integrity_hash"),
            "actual_hash": current_hash,
            "components": manifest.get("components", []),
            "verified_at": datetime.now().isoformat()
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RESTORE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def restore_preview(self, backup_id: str, mode: RecoveryMode = RecoveryMode.SOFT) -> Dict[str, Any]:
        """
        Preview what a restore would do (dry run).
        
        Returns detailed plan without making changes.
        """
        if backup_id not in self._registry:
            return {"error": "Backup not found"}
        
        verification = self.verify_backup(backup_id)
        if not verification["valid"]:
            return {"error": "Backup integrity check failed", "details": verification}
        
        manifest = self._registry[backup_id]
        
        plan = {
            "backup_id": backup_id,
            "backup_date": manifest["timestamp"],
            "mode": mode.value,
            "components_to_restore": manifest.get("components", []),
            "estimated_downtime": "< 1 minute" if mode == RecoveryMode.SOFT else "2-5 minutes",
            "requires_approval": True,
            "risks": [],
            "rollback_available": True
        }
        
        if mode == RecoveryMode.FULL_REBUILD:
            plan["risks"].append("All current data will be replaced")
            plan["estimated_downtime"] = "5-10 minutes"
        
        return plan
    
    def restore(
        self,
        backup_id: str,
        mode: RecoveryMode = RecoveryMode.SOFT,
        approved_by: str = None
    ) -> Dict[str, Any]:
        """
        Execute restore from backup.
        
        REQUIRES: approved_by must be set (Manager approval needed)
        """
        if not approved_by:
            return {"error": "Restore requires Manager approval", "approved_by": None}
        
        if backup_id not in self._registry:
            return {"error": "Backup not found"}
        
        verification = self.verify_backup(backup_id)
        if not verification["valid"]:
            return {"error": "Backup integrity check failed"}
        
        backup_path = self.backup_dir / backup_id
        manifest = self._registry[backup_id]
        
        restored = []
        errors = []
        
        # Create pre-restore backup
        pre_restore = self.create_backup(
            backup_type=BackupType.FULL,
            notes=f"Pre-restore backup before restoring {backup_id}",
            created_by="backup-recovery"
        )
        
        try:
            if mode in [RecoveryMode.SOFT, RecoveryMode.FULL_REBUILD]:
                # Restore config
                if "agent_souls" in manifest.get("components", []):
                    souls_backup = backup_path / "config" / "agent_souls"
                    souls_target = Path(__file__).parent / "memory"
                    if souls_backup.exists():
                        shutil.copytree(souls_backup, souls_target, dirs_exist_ok=True)
                        restored.append("agent_souls")
                
                # Restore database
                if "database" in manifest.get("components", []):
                    db_backup = backup_path / "data" / "mycasa.db"
                    db_target = Path(__file__).parent.parent / "data" / "mycasa.db"
                    if db_backup.exists():
                        shutil.copy(db_backup, db_target)
                        restored.append("database")
                
                # Restore patterns
                if "user_patterns" in manifest.get("components", []):
                    patterns_backup = backup_path / "patterns" / "user_patterns.json"
                    if patterns_backup.exists():
                        # TODO: Apply patterns to settings
                        restored.append("user_patterns")
        
        except Exception as e:
            errors.append(str(e))
            # Rollback on error
            self.restore(pre_restore["id"], RecoveryMode.SOFT, approved_by="auto-rollback")
        
        return {
            "success": len(errors) == 0,
            "backup_id": backup_id,
            "mode": mode.value,
            "restored_components": restored,
            "errors": errors,
            "pre_restore_backup": pre_restore["id"],
            "approved_by": approved_by,
            "timestamp": datetime.now().isoformat()
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCHEDULED OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def schedule_backup(self, cadence: str = "daily") -> Dict[str, Any]:
        """Set up scheduled backups"""
        # TODO: Integrate with scheduler
        return {
            "scheduled": True,
            "cadence": cadence,
            "next_run": (datetime.now() + timedelta(days=1)).isoformat()
        }
    
    def cleanup_old_backups(self, keep_count: int = 10, keep_days: int = 30) -> Dict[str, Any]:
        """Remove old backups beyond retention policy"""
        backups = sorted(
            self._registry.items(),
            key=lambda x: x[1]["timestamp"],
            reverse=True
        )
        
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        removed = []
        
        for i, (backup_id, manifest) in enumerate(backups):
            backup_date = datetime.fromisoformat(manifest["timestamp"])
            
            # Keep recent backups and those within retention period
            if i >= keep_count and backup_date < cutoff_date:
                backup_path = self.backup_dir / backup_id
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                del self._registry[backup_id]
                removed.append(backup_id)
        
        self._save_registry()
        
        return {
            "removed_count": len(removed),
            "removed_backups": removed,
            "remaining_count": len(self._registry)
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BASE AGENT INTERFACE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a backup/recovery task"""
        task_type = task.get("type")
        
        if task_type == "create_backup":
            return self.create_backup(
                backup_type=BackupType(task.get("backup_type", "full")),
                notes=task.get("notes"),
                created_by=task.get("created_by", "task")
            )
        elif task_type == "verify":
            return self.verify_backup(task.get("backup_id"))
        elif task_type == "restore_preview":
            return self.restore_preview(
                task.get("backup_id"),
                RecoveryMode(task.get("mode", "soft"))
            )
        elif task_type == "restore":
            return self.restore(
                task.get("backup_id"),
                RecoveryMode(task.get("mode", "soft")),
                approved_by=task.get("approved_by")
            )
        elif task_type == "cleanup":
            return self.cleanup_old_backups(
                keep_count=task.get("keep_count", 10),
                keep_days=task.get("keep_days", 30)
            )
        else:
            return {"error": f"Unknown task type: {task_type}"}
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get pending backup tasks"""
        tasks = []
        
        # Check if backup is needed
        backups = self.list_backups(limit=1)
        if not backups:
            tasks.append({
                "type": "backup_needed",
                "title": "No backups exist",
                "priority": "high"
            })
        else:
            last_backup = datetime.fromisoformat(backups[0]["timestamp"])
            if (datetime.now() - last_backup).days > 7:
                tasks.append({
                    "type": "backup_needed",
                    "title": f"Last backup was {(datetime.now() - last_backup).days} days ago",
                    "priority": "medium"
                })
        
        return tasks
