"""
Backup Agent
Handles database backup and restore operations
"""
import zipfile
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from ..storage.repository import Repository
from ..storage.database import DB_PATH
from ..storage.models import (
    UserSettingsDB, ManagerSettingsDB, BudgetPolicyDB, IncomeSourceDB,
    TransactionDB, TaskDB, ContractorJobDB, EventDB, CostRecordDB,
    InboxMessageDB, ApprovalDB, BackupRecordDB
)
from ..core.utils import calculate_checksum, generate_correlation_id


class BackupAgent:
    """Agent responsible for backup and restore operations"""
    
    def __init__(self, repo: Repository):
        self.repo = repo
        self.backup_dir = Path(__file__).parent.parent.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def export_backup(self, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Export full database backup to a timestamped zip file.
        Returns backup metadata.
        """
        backup_id = generate_correlation_id()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"mycasa_backup_{timestamp}_{backup_id}.zip"
        backup_path = self.backup_dir / filename
        
        try:
            # Create zip with database and metadata
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add database file
                if DB_PATH.exists():
                    zf.write(DB_PATH, "mycasa.db")
                
                # Get record counts
                counts = self._get_record_counts()
                
                # Create metadata
                metadata = {
                    "backup_id": backup_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0.0",
                    "tables_included": list(counts.keys()),
                    "record_counts": counts,
                    "notes": notes
                }
                
                # Add metadata file
                zf.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            # Calculate checksum
            checksum = calculate_checksum(str(backup_path))
            size_bytes = backup_path.stat().st_size
            
            # Record backup in database
            backup_record = BackupRecordDB(
                backup_id=backup_id,
                file_path=str(backup_path),
                checksum=checksum,
                size_bytes=size_bytes,
                tables_included=list(counts.keys()),
                record_counts=counts,
                notes=notes
            )
            self.repo.db.add(backup_record)
            self.repo.db.commit()
            
            # Log event
            self.repo.create_event(
                event_type="backup_created",
                action=f"Created backup: {filename}",
                agent="backup",
                details={
                    "backup_id": backup_id,
                    "filename": filename,
                    "size_bytes": size_bytes,
                    "record_counts": counts
                },
                correlation_id=backup_id
            )
            
            return {
                "success": True,
                "backup_id": backup_id,
                "filename": filename,
                "path": str(backup_path),
                "checksum": checksum,
                "size_bytes": size_bytes,
                "record_counts": counts
            }
            
        except Exception as e:
            return {
                "success": False,
                "errors": [str(e)]
            }
    
    def restore_backup(
        self,
        backup_path: str,
        verify_checksum: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Restore from a backup file.
        
        Args:
            backup_path: Path to backup zip file
            verify_checksum: Whether to verify checksum before restore
            dry_run: If True, only verify without restoring
        """
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            return {"success": False, "errors": ["Backup file not found"]}
        
        try:
            # Extract and verify
            with zipfile.ZipFile(backup_file, 'r') as zf:
                # Read metadata
                metadata = json.loads(zf.read("metadata.json"))
                backup_id = metadata.get("backup_id", "unknown")
                
                if dry_run:
                    return {
                        "success": True,
                        "dry_run": True,
                        "backup_id": backup_id,
                        "metadata": metadata,
                        "message": "Backup verified successfully"
                    }
                
                # Verify checksum if requested
                if verify_checksum:
                    # Find backup record
                    record = self.repo.db.query(BackupRecordDB).filter(
                        BackupRecordDB.backup_id == backup_id
                    ).first()
                    
                    if record:
                        current_checksum = calculate_checksum(backup_path)
                        if current_checksum != record.checksum:
                            return {
                                "success": False,
                                "errors": ["Checksum verification failed"]
                            }
                
                # Create backup of current database before restore
                if DB_PATH.exists():
                    pre_restore_backup = DB_PATH.with_suffix(".db.pre_restore")
                    shutil.copy2(DB_PATH, pre_restore_backup)
                
                # Extract database
                zf.extract("mycasa.db", DB_PATH.parent)
                
                # Rename extracted file
                extracted_db = DB_PATH.parent / "mycasa.db"
                if extracted_db != DB_PATH:
                    shutil.move(extracted_db, DB_PATH)
                
                # Log restore event (after database is restored)
                self.repo.create_event(
                    event_type="backup_restored",
                    action=f"Restored from backup: {backup_id}",
                    agent="backup",
                    details={
                        "backup_id": backup_id,
                        "source": backup_path,
                        "metadata": metadata
                    },
                    correlation_id=generate_correlation_id()
                )
                
                return {
                    "success": True,
                    "backup_id": backup_id,
                    "restored_from": backup_path,
                    "record_counts": metadata.get("record_counts", {}),
                    "message": "Backup restored successfully"
                }
                
        except Exception as e:
            return {
                "success": False,
                "errors": [str(e)]
            }
    
    def verify_backup(self, backup_path: str) -> Dict[str, Any]:
        """Verify backup integrity without restoring"""
        return self.restore_backup(backup_path, verify_checksum=True, dry_run=True)
    
    def _get_record_counts(self) -> Dict[str, int]:
        """Get record counts for all tables"""
        return {
            "user_settings": self.repo.db.query(UserSettingsDB).count(),
            "manager_settings": self.repo.db.query(ManagerSettingsDB).count(),
            "budget_policies": self.repo.db.query(BudgetPolicyDB).count(),
            "income_sources": self.repo.db.query(IncomeSourceDB).count(),
            "transactions": self.repo.db.query(TransactionDB).count(),
            "tasks": self.repo.db.query(TaskDB).count(),
            "contractor_jobs": self.repo.db.query(ContractorJobDB).count(),
            "events": self.repo.db.query(EventDB).count(),
            "cost_records": self.repo.db.query(CostRecordDB).count(),
            "inbox_messages": self.repo.db.query(InboxMessageDB).count(),
            "approvals": self.repo.db.query(ApprovalDB).count(),
        }
    
    def list_backups(self) -> list:
        """List available backups"""
        backups = []
        for f in self.backup_dir.glob("*.zip"):
            try:
                with zipfile.ZipFile(f, 'r') as zf:
                    metadata = json.loads(zf.read("metadata.json"))
                    backups.append({
                        "filename": f.name,
                        "path": str(f),
                        "size_bytes": f.stat().st_size,
                        **metadata
                    })
            except Exception:
                backups.append({
                    "filename": f.name,
                    "path": str(f),
                    "size_bytes": f.stat().st_size,
                    "error": "Could not read metadata"
                })
        
        return sorted(backups, key=lambda x: x.get("timestamp", ""), reverse=True)
