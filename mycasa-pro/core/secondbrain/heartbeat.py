"""
Memory Heartbeat & Decay System
================================

Implements automated memory management:
- Access tracking (lastAccessed, accessCount)
- Recency tiers (Hot/Warm/Cold)
- Periodic synthesis and cleanup
- Fact extraction from conversations
- Automated archiving of stale entities

Heartbeat runs periodically (e.g., daily) to:
1. Decay confidence of stale tacit knowledge
2. Update recency tiers for entities
3. Extract facts from recent conversations
4. Synthesize summaries for active entities
5. Archive inactive projects

Recency Tiers:
- **Hot**: Accessed in last 7 days
- **Warm**: Accessed 8-30 days ago
- **Cold**: Accessed 31+ days ago
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from enum import Enum

from .daily_notes import DailyNotesManager
from .para import PARAKnowledgeGraph, PARACategory, PARAEntity


class RecencyTier(str, Enum):
    """Recency classification"""
    HOT = "hot"      # Last 7 days
    WARM = "warm"    # 8-30 days ago
    COLD = "cold"    # 31+ days ago


class MemoryHeartbeat:
    """
    Automated memory management and maintenance
    """

    def __init__(self, memory_base: Path):
        """
        Initialize heartbeat manager.

        Args:
            memory_base: Base memory directory
        """
        self.memory_base = memory_base
        self.heartbeat_log_path = memory_base / "heartbeat_log.json"

    def _load_heartbeat_log(self) -> Dict[str, Any]:
        """Load heartbeat execution log"""
        if not self.heartbeat_log_path.exists():
            return {
                "last_run": None,
                "runs": [],
            }

        return json.loads(self.heartbeat_log_path.read_text())

    def _save_heartbeat_log(self, log: Dict[str, Any]) -> None:
        """Save heartbeat execution log"""
        self.heartbeat_log_path.write_text(json.dumps(log, indent=2))

    def run_heartbeat(
        self,
        decay_tacit: bool = True,
        update_recency: bool = True,
        synthesize: bool = True,
        auto_archive: bool = False
    ) -> Dict[str, Any]:
        """
        Run full heartbeat cycle.

        Args:
            decay_tacit: Decay stale tacit knowledge
            update_recency: Update recency tiers
            synthesize: Synthesize entity summaries
            auto_archive: Auto-archive completed projects

        Returns:
            Dict with heartbeat results
        """
        start_time = datetime.now()
        results = {
            "started_at": start_time.isoformat(),
            "operations": {},
        }

        # 1. Decay tacit knowledge (global and all agents)
        if decay_tacit:
            tacit_results = self._decay_all_tacit_knowledge()
            results["operations"]["tacit_decay"] = tacit_results

        # 2. Update recency tiers
        if update_recency:
            recency_results = self._update_recency_tiers()
            results["operations"]["recency_update"] = recency_results

        # 3. Synthesize summaries
        if synthesize:
            synthesis_results = self._synthesize_summaries()
            results["operations"]["synthesis"] = synthesis_results

        # 4. Auto-archive completed projects
        if auto_archive:
            archive_results = self._auto_archive_completed()
            results["operations"]["auto_archive"] = archive_results

        end_time = datetime.now()
        results["completed_at"] = end_time.isoformat()
        results["duration_seconds"] = (end_time - start_time).total_seconds()

        # Log the run
        log = self._load_heartbeat_log()
        log["last_run"] = results
        log["runs"].append({
            "timestamp": start_time.isoformat(),
            "duration": results["duration_seconds"],
        })
        # Keep last 30 runs
        log["runs"] = log["runs"][-30:]
        self._save_heartbeat_log(log)

        return results

    def _decay_all_tacit_knowledge(self) -> Dict[str, int]:
        """Decay tacit knowledge for global and all agents"""
        results = {}

        # Global tacit knowledge
        global_manager = DailyNotesManager(self.memory_base, scope="global")
        global_decayed = global_manager.decay_tacit_knowledge(days_threshold=30, decay_factor=0.05)
        results["global"] = global_decayed

        # Agent tacit knowledge
        agents_dir = self.memory_base / "agents"
        if agents_dir.exists():
            for agent_dir in agents_dir.iterdir():
                if agent_dir.is_dir():
                    agent_id = agent_dir.name
                    agent_manager = DailyNotesManager(
                        self.memory_base,
                        scope="agent",
                        agent_id=agent_id
                    )
                    decayed = agent_manager.decay_tacit_knowledge(days_threshold=30, decay_factor=0.05)
                    results[agent_id] = decayed

        return results

    def _update_recency_tiers(self) -> Dict[str, Any]:
        """Update recency tiers for all entities"""
        results = {
            "hot": 0,
            "warm": 0,
            "cold": 0,
        }

        now = datetime.now()

        # Update for all agent workspaces
        agents_dir = self.memory_base / "agents"
        if agents_dir.exists():
            for agent_dir in agents_dir.iterdir():
                if not agent_dir.is_dir():
                    continue

                workspace_path = agent_dir / "workspace"
                if not workspace_path.exists():
                    continue

                kg = PARAKnowledgeGraph(workspace_path)

                # Check all entities across all categories
                for category in PARACategory:
                    entity_ids = kg.list_entities(category)

                    for entity_id in entity_ids:
                        entity = kg.get_entity(entity_id, category)
                        if not entity:
                            continue

                        # Get metadata
                        metadata = entity._read_metadata()
                        updated_at = datetime.fromisoformat(metadata.updated_at)

                        # Calculate days since last access
                        days_since = (now - updated_at).days

                        # Classify tier
                        if days_since <= 7:
                            tier = RecencyTier.HOT
                            results["hot"] += 1
                        elif days_since <= 30:
                            tier = RecencyTier.WARM
                            results["warm"] += 1
                        else:
                            tier = RecencyTier.COLD
                            results["cold"] += 1

                        # Update metadata with tier
                        # (Could store this in metadata if needed)

        return results

    def _synthesize_summaries(self) -> Dict[str, int]:
        """Synthesize/rewrite summaries for active entities"""
        results = {
            "entities_synthesized": 0,
        }

        # For now, summaries are auto-generated when facts are added
        # This could be enhanced to do weekly full rewrites using LLM

        return results

    def _auto_archive_completed(self) -> Dict[str, Any]:
        """Auto-archive completed projects"""
        results = {
            "archived_count": 0,
            "archived_entities": [],
        }

        # Check all agent workspaces for completed projects
        agents_dir = self.memory_base / "agents"
        if not agents_dir.exists():
            return results

        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue

            workspace_path = agent_dir / "workspace"
            if not workspace_path.exists():
                continue

            kg = PARAKnowledgeGraph(workspace_path)

            # Get all projects
            project_ids = kg.list_entities(PARACategory.PROJECTS)

            for project_id in project_ids:
                entity = kg.get_entity(project_id, PARACategory.PROJECTS)
                if not entity:
                    continue

                metadata = entity._read_metadata()

                # Check if marked as completed
                if metadata.status == "completed":
                    # Archive it
                    try:
                        archived_entity = entity.move_to_archive()
                        results["archived_count"] += 1
                        results["archived_entities"].append(project_id)
                    except Exception as e:
                        # Already archived or error
                        pass

        return results

    def extract_facts_from_conversations(
        self,
        agent_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[str]:
        """
        Extract facts from agent conversations in daily notes.

        This is a placeholder for LLM-based fact extraction.
        In production, would use Claude to analyze conversations
        and extract key facts to add to relevant entities.

        Args:
            agent_id: Agent to analyze
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of extracted facts
        """
        # TODO: Implement LLM-based fact extraction
        # 1. Get agent's daily notes in range
        # 2. Extract conversation entries
        # 3. Use Claude to identify key facts
        # 4. Return structured facts for entity addition

        return []

    def get_hot_entities(self, agent_id: str) -> List[str]:
        """Get list of hot (recently accessed) entities for an agent"""
        workspace_path = self.memory_base / "agents" / agent_id / "workspace"
        if not workspace_path.exists():
            return []

        kg = PARAKnowledgeGraph(workspace_path)
        hot_entities = []
        now = datetime.now()

        for category in PARACategory:
            entity_ids = kg.list_entities(category)

            for entity_id in entity_ids:
                entity = kg.get_entity(entity_id, category)
                if not entity:
                    continue

                metadata = entity._read_metadata()
                updated_at = datetime.fromisoformat(metadata.updated_at)

                # Hot = last 7 days
                if (now - updated_at).days <= 7:
                    hot_entities.append({
                        "entity_id": entity_id,
                        "name": metadata.name,
                        "category": category.value,
                        "last_updated": metadata.updated_at,
                    })

        return hot_entities

    def get_stale_entities(self, agent_id: str, days_threshold: int = 90) -> List[str]:
        """Get list of stale entities that haven't been accessed recently"""
        workspace_path = self.memory_base / "agents" / agent_id / "workspace"
        if not workspace_path.exists():
            return []

        kg = PARAKnowledgeGraph(workspace_path)
        stale_entities = []
        now = datetime.now()

        for category in [PARACategory.PROJECTS, PARACategory.RESOURCES]:  # Don't check Areas or Archives
            entity_ids = kg.list_entities(category)

            for entity_id in entity_ids:
                entity = kg.get_entity(entity_id, category)
                if not entity:
                    continue

                metadata = entity._read_metadata()
                updated_at = datetime.fromisoformat(metadata.updated_at)

                # Stale = not accessed in threshold days
                days_since = (now - updated_at).days
                if days_since >= days_threshold:
                    stale_entities.append({
                        "entity_id": entity_id,
                        "name": metadata.name,
                        "category": category.value,
                        "last_updated": metadata.updated_at,
                        "days_since_update": days_since,
                    })

        return stale_entities


def schedule_heartbeat(memory_base: Path, interval_hours: int = 24) -> None:
    """
    Schedule heartbeat to run periodically.

    This is a placeholder - in production would integrate with
    a proper scheduler like APScheduler or cron.

    Args:
        memory_base: Base memory directory
        interval_hours: Hours between heartbeat runs
    """
    # TODO: Integrate with APScheduler or background task system
    pass
