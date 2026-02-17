"""
Core Memory Manager
Provides atomic operations for the three-layer memory system with comprehensive error handling
"""
import os
import json
import shutil
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
import logging

try:
    from .schemas import (
        AtomicFact, Entity, MemoryContext, ConversationLog,
        EntityNotFoundError, MemoryWriteError, CorruptedDataError,
        ValidationError, validate_fact, validate_entity_id,
        calculate_decay_tier, DataclassJSONEncoder
    )
except ImportError:
    from schemas import (
        AtomicFact, Entity, MemoryContext, ConversationLog,
        EntityNotFoundError, MemoryWriteError, CorruptedDataError,
        ValidationError, validate_fact, validate_entity_id,
        calculate_decay_tier, DataclassJSONEncoder
    )


logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Core memory manager with atomic operations and god-level error handling

    Principles:
    1. No data loss - all operations are atomic with rollback
    2. Graceful degradation - continue with reduced functionality on error
    3. Detailed logging - every operation logged
    4. Auto-recovery - attempt recovery before failing
    5. User transparency - errors reported clearly
    """

    def __init__(self, base_path: str = "memory"):
        """
        Initialize memory manager

        Args:
            base_path: Root path for memory storage
        """
        self.base_path = Path(base_path)
        self.backup_path = self.base_path / ".backups"
        self.global_path = self.base_path / "global"
        self.agents_path = self.base_path / "agents"

        # Locks for concurrent access to entities
        self._entity_locks = {}
        self._locks_lock = asyncio.Lock()

        # Ensure directories exist
        self._ensure_directories()

        # Action log for debugging
        self.action_log = []

    def _ensure_directories(self):
        """Ensure all required directories exist"""
        try:
            directories = [
                self.base_path,
                self.backup_path,
                self.global_path,
                self.global_path / "life",
                self.global_path / "daily",
                self.agents_path,
            ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            raise MemoryWriteError(f"Could not initialize memory system: {e}")

    def log_action(self, action: str, details: str, **kwargs):
        """Log an action for debugging"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            **kwargs
        }
        self.action_log.append(entry)
        logger.info(f"[Memory] {action}: {details}")

    def log_error(self, action: str, error: str, **kwargs):
        """Log an error"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "error": error,
            "level": "ERROR",
            **kwargs
        }
        self.action_log.append(entry)
        logger.error(f"[Memory] {action}: {error}")

    async def _get_entity_lock(self, entity_id: str) -> asyncio.Lock:
        """Get or create a lock for an entity"""
        async with self._locks_lock:
            if entity_id not in self._entity_locks:
                self._entity_locks[entity_id] = asyncio.Lock()
            return self._entity_locks[entity_id]

    # ==================== ENTITY OPERATIONS ====================

    def _get_entity_path(self, entity_id: str) -> Path:
        """Get file path for an entity"""
        valid, error = validate_entity_id(entity_id)
        if not valid:
            raise ValidationError(f"Invalid entity ID: {error}")

        return self.global_path / "life" / entity_id

    def _get_summary_path(self, entity_id: str) -> Path:
        """Get path to entity's summary.md"""
        return self._get_entity_path(entity_id) / "summary.md"

    def _get_items_path(self, entity_id: str) -> Path:
        """Get path to entity's items.json"""
        return self._get_entity_path(entity_id) / "items.json"

    async def entity_exists(self, entity_id: str) -> bool:
        """Check if an entity exists"""
        try:
            entity_path = self._get_entity_path(entity_id)
            return entity_path.exists() and entity_path.is_dir()
        except Exception:
            return False

    async def create_entity(self, entity_id: str, metadata: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Create a new entity

        Args:
            entity_id: Entity identifier (e.g., "projects/product-launch")
            metadata: Optional metadata for the entity

        Returns:
            (success: bool, message: str)
        """
        try:
            # Validate entity ID
            valid, error = validate_entity_id(entity_id)
            if not valid:
                return False, f"Invalid entity ID: {error}"

            # Create directory (exist_ok=True for concurrent creation)
            entity_path = self._get_entity_path(entity_id)
            entity_path.mkdir(parents=True, exist_ok=True)

            # Create empty summary.md (if it doesn't exist)
            summary_path = self._get_summary_path(entity_id)
            if not summary_path.exists():
                async with aiofiles.open(summary_path, 'w') as f:
                    await f.write(f"# {entity_id.split('/')[-1]}\n\nNo summary yet.\n")

            # Create empty items.json (if it doesn't exist)
            items_path = self._get_items_path(entity_id)
            if not items_path.exists():
                async with aiofiles.open(items_path, 'w') as f:
                    await f.write("[]")

            # If we got here and files exist, entity was created (possibly by concurrent call)
            self.log_action("entity_created", f"Created entity: {entity_id}", metadata=metadata)
            return True, f"Entity created: {entity_id}"

        except Exception as e:
            error_msg = f"Failed to create entity {entity_id}: {str(e)}"
            self.log_error("entity_create_failed", error_msg)
            return False, error_msg

    async def delete_entity(self, entity_id: str) -> Tuple[bool, str]:
        """
        Delete an entity (moves to archives, doesn't actually delete)

        Args:
            entity_id: Entity to delete

        Returns:
            (success: bool, message: str)
        """
        try:
            if not await self.entity_exists(entity_id):
                return False, f"Entity not found: {entity_id}"

            # Move to archives
            parts = entity_id.split('/')
            if parts[0] == "archives":
                return False, "Entity already in archives"

            # Create archive entity ID
            archive_id = f"archives/{parts[-1]}"

            # Ensure archives directory exists
            archive_path = self._get_entity_path(archive_id)
            archive_path.parent.mkdir(parents=True, exist_ok=True)

            # Move the entity
            source_path = self._get_entity_path(entity_id)
            shutil.move(str(source_path), str(archive_path))

            self.log_action("entity_archived", f"Moved {entity_id} to {archive_id}")
            return True, f"Entity archived: {entity_id} → {archive_id}"

        except Exception as e:
            error_msg = f"Failed to archive entity {entity_id}: {str(e)}"
            self.log_error("entity_archive_failed", error_msg)
            return False, error_msg

    # ==================== FACT OPERATIONS ====================

    async def _backup_entity(self, entity_id: str) -> Optional[Path]:
        """
        Create a backup of an entity before modification

        Returns:
            Path to backup file, or None if backup failed
        """
        try:
            if not await self.entity_exists(entity_id):
                return None

            # Create backup directory
            self.backup_path.mkdir(parents=True, exist_ok=True)

            # Backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_id = entity_id.replace('/', '_')
            backup_file = self.backup_path / f"{safe_id}_{timestamp}.json"

            # Load current facts
            facts = await self._load_facts(entity_id)

            # Write backup
            async with aiofiles.open(backup_file, 'w') as f:
                await f.write(json.dumps(facts, indent=2, cls=DataclassJSONEncoder))

            return backup_file

        except Exception as e:
            logger.warning(f"Failed to create backup for {entity_id}: {e}")
            return None

    async def _restore_from_backup(self, entity_id: str, backup_path: Path):
        """Restore entity from backup"""
        try:
            async with aiofiles.open(backup_path, 'r') as f:
                content = await f.read()
                facts = json.loads(content)

            items_path = self._get_items_path(entity_id)
            async with aiofiles.open(items_path, 'w') as f:
                await f.write(json.dumps(facts, indent=2))

            self.log_action("entity_restored", f"Restored {entity_id} from backup")

        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            raise MemoryWriteError(f"Restore failed: {e}")

    async def _load_facts(self, entity_id: str) -> List[Dict]:
        """Load facts from entity's items.json"""
        try:
            items_path = self._get_items_path(entity_id)

            if not items_path.exists():
                return []

            async with aiofiles.open(items_path, 'r') as f:
                content = await f.read()
                facts = json.loads(content)

            return facts

        except json.JSONDecodeError as e:
            raise CorruptedDataError(f"Corrupted facts file for {entity_id}: {e}")
        except Exception as e:
            raise MemoryWriteError(f"Failed to load facts for {entity_id}: {e}")

    async def _atomic_write(self, file_path: Path, data: Any):
        """
        Atomic write operation - write to temp file, then rename

        Args:
            file_path: Target file path
            data: Data to write (will be JSON-encoded)
        """
        temp_path = file_path.with_suffix('.tmp')

        try:
            # Write to temp file
            async with aiofiles.open(temp_path, 'w') as f:
                await f.write(json.dumps(data, indent=2, cls=DataclassJSONEncoder))

            # Atomic rename
            temp_path.replace(file_path)

        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise MemoryWriteError(f"Atomic write failed: {e}")

    async def _verify_write(self, entity_id: str, fact_id: str) -> bool:
        """Verify a fact was written successfully"""
        try:
            facts = await self._load_facts(entity_id)
            return any(f.get('id') == fact_id for f in facts)
        except Exception:
            return False

    async def write_fact(self, entity_id: str, fact: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Write a fact to an entity with full error handling

        Args:
            entity_id: Entity to write to
            fact: Fact dictionary

        Returns:
            (success: bool, message: str)
        """
        # Get lock for this entity to serialize writes
        lock = await self._get_entity_lock(entity_id)

        async with lock:
            backup_path = None

            try:
                # Validate fact
                valid, error = validate_fact(fact)
                if not valid:
                    return False, f"Invalid fact: {error}"

                # Ensure entity exists (with retries for concurrent creation)
                max_retries = 3
                for attempt in range(max_retries):
                    if await self.entity_exists(entity_id):
                        break
                    if attempt < max_retries - 1:
                        # Try to create entity
                        success, msg = await self.create_entity(entity_id)
                        if success:
                            break
                        # If creation failed, it might be because another process created it
                        # Wait a bit and check again
                        await asyncio.sleep(0.01)
                    else:
                        # Final attempt to create
                        success, msg = await self.create_entity(entity_id)
                        if not success:
                            # Check one more time if it exists (race condition)
                            if not await self.entity_exists(entity_id):
                                return False, f"Failed to create entity: {msg}"

                # Create backup before modification
                backup_path = await self._backup_entity(entity_id)

                # Load existing facts
                existing_facts = await self._load_facts(entity_id)

                # Create AtomicFact object
                fact_obj = AtomicFact.from_dict(fact)

                # Add to list
                existing_facts.append(fact_obj.to_dict())

                # Write atomically
                items_path = self._get_items_path(entity_id)
                await self._atomic_write(items_path, existing_facts)

                # Verify write
                verified = await self._verify_write(entity_id, fact_obj.id)
                if not verified:
                    raise MemoryWriteError("Write verification failed")

                # Clean up backup on success
                if backup_path and backup_path.exists():
                    backup_path.unlink()

                self.log_action("fact_written", f"Entity: {entity_id}, Fact: {fact_obj.id}")
                return True, f"Fact written successfully: {fact_obj.id}"

            except EntityNotFoundError:
                # Try to create entity and retry
                success, msg = await self.create_entity(entity_id)
                if success:
                    return await self.write_fact(entity_id, fact)  # Retry
                else:
                    return False, f"Could not create entity: {msg}"

            except MemoryWriteError as e:
                # Restore from backup
                if backup_path and backup_path.exists():
                    try:
                        await self._restore_from_backup(entity_id, backup_path)
                    except Exception as restore_error:
                        logger.error(f"Restore failed: {restore_error}")

                error_msg = f"Failed to write fact: {str(e)}"
                self.log_error("fact_write_failed", error_msg, entity_id=entity_id)
                return False, error_msg

            except Exception as e:
                # Unexpected error - restore and report
                if backup_path and backup_path.exists():
                    try:
                        await self._restore_from_backup(entity_id, backup_path)
                    except Exception as restore_error:
                        logger.error(f"Restore failed: {restore_error}")

                error_msg = f"Unexpected error writing fact: {type(e).__name__}: {str(e)}"
                self.log_error("unexpected_error", error_msg, entity_id=entity_id)
                return False, error_msg

    async def supersede_fact(self, entity_id: str, old_fact_id: str, new_fact: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Supersede an existing fact with a new one

        Args:
            entity_id: Entity containing the fact
            old_fact_id: ID of fact to supersede
            new_fact: New fact data

        Returns:
            (success: bool, message: str)
        """
        backup_path = None

        try:
            if not await self.entity_exists(entity_id):
                return False, f"Entity not found: {entity_id}"

            # Validate new fact
            valid, error = validate_fact(new_fact)
            if not valid:
                return False, f"Invalid new fact: {error}"

            # Create backup
            backup_path = await self._backup_entity(entity_id)

            # Load existing facts
            facts = await self._load_facts(entity_id)

            # Find old fact
            old_fact = None
            for i, f in enumerate(facts):
                if f.get('id') == old_fact_id:
                    old_fact = f
                    break

            if not old_fact:
                return False, f"Fact not found: {old_fact_id}"

            # Create new fact
            new_fact_obj = AtomicFact.from_dict(new_fact)

            # Mark old fact as superseded
            old_fact['status'] = 'superseded'
            old_fact['supersededBy'] = new_fact_obj.id

            # Add new fact
            facts.append(new_fact_obj.to_dict())

            # Write atomically
            items_path = self._get_items_path(entity_id)
            await self._atomic_write(items_path, facts)

            # Clean up backup
            if backup_path and backup_path.exists():
                backup_path.unlink()

            self.log_action("fact_superseded", f"Old: {old_fact_id}, New: {new_fact_obj.id}")
            return True, f"Fact superseded: {old_fact_id} → {new_fact_obj.id}"

        except Exception as e:
            if backup_path and backup_path.exists():
                try:
                    await self._restore_from_backup(entity_id, backup_path)
                except Exception as restore_error:
                    logger.error(f"Restore failed: {restore_error}")

            error_msg = f"Failed to supersede fact: {str(e)}"
            self.log_error("fact_supersede_failed", error_msg)
            return False, error_msg

    async def access_fact(self, entity_id: str, fact_id: str) -> Tuple[bool, str]:
        """
        Mark a fact as accessed (updates lastAccessed and accessCount)

        Args:
            entity_id: Entity containing the fact
            fact_id: Fact ID to mark as accessed

        Returns:
            (success: bool, message: str)
        """
        try:
            if not await self.entity_exists(entity_id):
                return False, f"Entity not found: {entity_id}"

            # Load facts
            facts = await self._load_facts(entity_id)

            # Find and update fact
            found = False
            for fact in facts:
                if fact.get('id') == fact_id:
                    fact['lastAccessed'] = datetime.now().isoformat()
                    fact['accessCount'] = fact.get('accessCount', 0) + 1
                    found = True
                    break

            if not found:
                return False, f"Fact not found: {fact_id}"

            # Write back
            items_path = self._get_items_path(entity_id)
            await self._atomic_write(items_path, facts)

            return True, f"Fact accessed: {fact_id}"

        except Exception as e:
            error_msg = f"Failed to mark fact access: {str(e)}"
            self.log_error("fact_access_failed", error_msg)
            return False, error_msg

    async def get_facts(self, entity_id: str, status: str = "active", tier: Optional[str] = None) -> List[AtomicFact]:
        """
        Get facts from an entity

        Args:
            entity_id: Entity to retrieve from
            status: Filter by status ("active" or "superseded")
            tier: Filter by decay tier ("hot", "warm", "cold")

        Returns:
            List of AtomicFact objects
        """
        try:
            if not await self.entity_exists(entity_id):
                return []

            facts_data = await self._load_facts(entity_id)
            facts = [AtomicFact.from_dict(f) for f in facts_data]

            # Filter by status
            if status:
                facts = [f for f in facts if f.status == status]

            # Filter by tier
            if tier:
                facts = [f for f in facts if calculate_decay_tier(f) == tier]

            return facts

        except Exception as e:
            self.log_error("get_facts_failed", str(e), entity_id=entity_id)
            return []

    # ==================== SUMMARY OPERATIONS ====================

    async def update_summary(self, entity_id: str, summary: str) -> Tuple[bool, str]:
        """
        Update an entity's summary.md

        Args:
            entity_id: Entity to update
            summary: New summary text

        Returns:
            (success: bool, message: str)
        """
        try:
            if not await self.entity_exists(entity_id):
                return False, f"Entity not found: {entity_id}"

            summary_path = self._get_summary_path(entity_id)

            # Write atomically
            async with aiofiles.open(summary_path, 'w') as f:
                await f.write(summary)

            self.log_action("summary_updated", f"Entity: {entity_id}")
            return True, f"Summary updated for {entity_id}"

        except Exception as e:
            error_msg = f"Failed to update summary: {str(e)}"
            self.log_error("summary_update_failed", error_msg)
            return False, error_msg

    async def get_summary(self, entity_id: str) -> Optional[str]:
        """Get an entity's summary"""
        try:
            if not await self.entity_exists(entity_id):
                return None

            summary_path = self._get_summary_path(entity_id)
            async with aiofiles.open(summary_path, 'r') as f:
                return await f.read()

        except Exception as e:
            self.log_error("get_summary_failed", str(e), entity_id=entity_id)
            return None

    # ==================== DAILY NOTES ====================

    async def append_daily_note(self, content: str, agent_id: Optional[str] = None, note_date: Optional[date] = None) -> Tuple[bool, str]:
        """
        Append to daily notes

        Args:
            content: Content to append
            agent_id: Agent ID for agent-specific notes (None for global)
            note_date: Date for the note (defaults to today)

        Returns:
            (success: bool, message: str)
        """
        try:
            if note_date is None:
                note_date = date.today()

            # Determine path
            if agent_id:
                daily_path = self.agents_path / agent_id / "daily"
            else:
                daily_path = self.global_path / "daily"

            daily_path.mkdir(parents=True, exist_ok=True)

            # File path
            note_file = daily_path / f"{note_date.isoformat()}.md"

            # Append content
            timestamp = datetime.now().strftime("%H:%M:%S")
            entry = f"\n## {timestamp}\n\n{content}\n"

            async with aiofiles.open(note_file, 'a') as f:
                await f.write(entry)

            self.log_action("daily_note_written", f"Date: {note_date}, Agent: {agent_id or 'global'}")
            return True, f"Daily note appended for {note_date}"

        except Exception as e:
            error_msg = f"Failed to write daily note: {str(e)}"
            self.log_error("daily_note_failed", error_msg)
            return False, error_msg

    async def get_daily_notes(self, days: int = 7, agent_id: Optional[str] = None) -> str:
        """
        Get recent daily notes

        Args:
            days: Number of days to retrieve
            agent_id: Agent ID for agent-specific notes (None for global)

        Returns:
            Concatenated daily notes
        """
        try:
            if agent_id:
                daily_path = self.agents_path / agent_id / "daily"
            else:
                daily_path = self.global_path / "daily"

            if not daily_path.exists():
                return ""

            notes = []
            for i in range(days):
                note_date = date.today() - timedelta(days=i)
                note_file = daily_path / f"{note_date.isoformat()}.md"

                if note_file.exists():
                    async with aiofiles.open(note_file, 'r') as f:
                        content = await f.read()
                        notes.append(f"# {note_date}\n{content}")

            return "\n\n---\n\n".join(notes)

        except Exception as e:
            self.log_error("get_daily_notes_failed", str(e))
            return ""


# Global singleton instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get global memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
