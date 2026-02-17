"""
Tenant Identity Manager for MyCasa Pro
======================================

Loads and manages tenant-specific identity files.
Mirrors Galidima's AGENTS.md ritual for every session.

USAGE:
    identity = TenantIdentityManager(tenant_id).load_identity_package()
    
    # Now agent has:
    # - identity['soul'] - Who they are
    # - identity['user'] - Who they're helping
    # - identity['security'] - Trust boundaries
    # - identity['tools'] - Local notes
    # - identity['heartbeat'] - Proactive tasks
    # - identity['memory'] - Long-term context
    # - identity['daily_notes'] - Recent raw logs
"""

from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import logging
import json

from config.settings import DATA_DIR

logger = logging.getLogger("mycasa.tenant_identity")

# Template directory (repo-relative)
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "tenant_identity"


class IdentityError(Exception):
    """Raised when identity loading fails"""
    pass


class TenantIdentityManager:
    """
    Load and manage tenant-specific identity files.
    
    This is the "wake up" ritual that every agent must perform
    before any user-facing action.
    """
    
    REQUIRED_FILES = ['SOUL.md', 'USER.md', 'SECURITY.md']
    OPTIONAL_FILES = ['TOOLS.md', 'HEARTBEAT.md', 'MEMORY.md']
    
    def __init__(self, tenant_id: str, data_dir: Optional[Path] = None):
        """
        Initialize identity manager for a tenant.
        
        Args:
            tenant_id: Unique tenant identifier
            data_dir: Optional custom data directory
        """
        self.tenant_id = tenant_id
        self.data_dir = data_dir or DATA_DIR
        self.tenant_dir = self.data_dir / "tenants" / tenant_id
        
    def load_identity_package(self) -> Dict[str, Any]:
        """
        Load the full identity package before any agent action.
        This is the "wake up" ritual.
        
        Returns:
            Dict with all identity file contents
            
        Raises:
            IdentityError: If required files are missing
        """
        identity = {}
        missing_files = []
        
        logger.info(f"[Identity] Loading identity package for tenant {self.tenant_id}")
        # Ensure structure exists (creates missing templates)
        self.ensure_identity_structure()
        
        # Load required files
        for filename in self.REQUIRED_FILES:
            content = self._read_file(filename, required=True)
            if content is None:
                missing_files.append(filename)
            else:
                identity[filename.replace('.md', '').lower()] = content
        
        # Fail fast if required files missing
        if missing_files:
            raise IdentityError(
                f"Required identity files missing for tenant {self.tenant_id}: {missing_files}. "
                f"Run tenant setup wizard first."
            )
        
        # Load optional files
        for filename in self.OPTIONAL_FILES:
            content = self._read_file(filename, required=False)
            if content:
                identity[filename.replace('.md', '').lower()] = content
        
        # Load recent daily notes (today + yesterday)
        identity['daily_notes'] = self._load_recent_daily_notes(days=2)
        
        # Load heartbeat state if exists
        identity['heartbeat_state'] = self._load_heartbeat_state()
        
        logger.info(f"[Identity] Successfully loaded identity package for tenant {self.tenant_id}")
        
        return identity
    
    def _read_file(self, filename: str, required: bool = False) -> Optional[str]:
        """
        Read a file from tenant directory.
        
        Args:
            filename: Name of file to read
            required: If True, raise error when missing
            
        Returns:
            File contents or None
            
        Raises:
            IdentityError: If required file is missing
        """
        path = self.tenant_dir / filename
        
        if not path.exists():
            if required:
                logger.error(f"[Identity] Required file missing: {path}")
                return None
            else:
                logger.debug(f"[Identity] Optional file not found: {path}")
                return None
        
        try:
            content = path.read_text(encoding='utf-8')
            logger.debug(f"[Identity] Loaded {filename} ({len(content)} chars)")
            return content
        except Exception as e:
            logger.error(f"[Identity] Failed to read {filename}: {e}")
            if required:
                return None
            return None
    
    def _load_recent_daily_notes(self, days: int = 2) -> Dict[str, str]:
        """
        Load recent daily note files.
        
        Args:
            days: Number of days to load (today + previous days)
            
        Returns:
            Dict mapping date strings to note contents
        """
        notes = {}
        memory_dir = self.tenant_dir / "memory"
        
        if not memory_dir.exists():
            return notes
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            note_path = memory_dir / f"{date_str}.md"
            
            if note_path.exists():
                try:
                    notes[date_str] = note_path.read_text(encoding='utf-8')
                    logger.debug(f"[Identity] Loaded daily note {date_str}")
                except Exception as e:
                    logger.warning(f"[Identity] Failed to load daily note {date_str}: {e}")
        
        return notes
    
    def _load_heartbeat_state(self) -> Optional[Dict[str, Any]]:
        """
        Load heartbeat state tracking file.
        
        Returns:
            Heartbeat state dict or None
        """
        state_path = self.tenant_dir / "memory" / "heartbeat-state.json"
        
        if not state_path.exists():
            return None
        
        try:
            state = json.loads(state_path.read_text(encoding='utf-8'))
            logger.debug(f"[Identity] Loaded heartbeat state")
            return state
        except Exception as e:
            logger.warning(f"[Identity] Failed to load heartbeat state: {e}")
            return None
    
    def save_heartbeat_state(self, state: Dict[str, Any]) -> None:
        """
        Save heartbeat state tracking file.
        
        Args:
            state: Heartbeat state dict
        """
        memory_dir = self.tenant_dir / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        
        state_path = memory_dir / "heartbeat-state.json"
        
        try:
            state_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
            logger.debug(f"[Identity] Saved heartbeat state")
        except Exception as e:
            logger.error(f"[Identity] Failed to save heartbeat state: {e}")
    
    def ensure_identity_structure(self) -> None:
        """
        Create tenant directory structure with template files if missing.
        This is used during tenant setup.
        """
        # Create directories
        self.tenant_dir.mkdir(parents=True, exist_ok=True)
        (self.tenant_dir / "memory").mkdir(exist_ok=True)
        
        # Copy templates when missing
        for filename in (self.REQUIRED_FILES + self.OPTIONAL_FILES):
            target = self.tenant_dir / filename
            if target.exists():
                continue
            template = TEMPLATE_DIR / filename
            if template.exists():
                try:
                    target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
                    logger.info(f"[Identity] Created {target} from template")
                except Exception as e:
                    logger.warning(f"[Identity] Failed to write template {filename}: {e}")
            else:
                logger.warning(f"[Identity] Template missing: {template}")

        # Warn if any required files still missing
        missing = [f for f in self.REQUIRED_FILES if not (self.tenant_dir / f).exists()]
        if missing:
            logger.warning(f"[Identity] Tenant {self.tenant_id} missing required files: {missing}")
    
    def get_identity_status(self) -> Dict[str, Any]:
        """
        Get status of identity files for this tenant.
        
        Returns:
            Dict with file status information
        """
        status = {
            'tenant_id': self.tenant_id,
            'tenant_dir_exists': self.tenant_dir.exists(),
            'files': {},
            'ready': True,
            'missing_required': []
        }
        
        if not self.tenant_dir.exists():
            status['ready'] = False
            return status
        
        # Check required files
        for filename in self.REQUIRED_FILES:
            path = self.tenant_dir / filename
            exists = path.exists()
            status['files'][filename] = {
                'exists': exists,
                'size': path.stat().st_size if exists else 0
            }
            if not exists:
                status['ready'] = False
                status['missing_required'].append(filename)
        
        # Check optional files
        for filename in self.OPTIONAL_FILES:
            path = self.tenant_dir / filename
            exists = path.exists()
            status['files'][filename] = {
                'exists': exists,
                'size': path.stat().st_size if exists else 0
            }
        
        return status


def get_identity(tenant_id: str) -> Dict[str, Any]:
    """
    Convenience function to load tenant identity.
    
    Usage:
        identity = get_identity('tenant-123')
        soul = identity['soul']
        user = identity['user']
    
    Args:
        tenant_id: Tenant identifier
        
    Returns:
        Identity package dict
    """
    manager = TenantIdentityManager(tenant_id)
    return manager.load_identity_package()
