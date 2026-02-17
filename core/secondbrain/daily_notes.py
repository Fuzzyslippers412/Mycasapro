"""
Daily Notes & Tacit Knowledge System
=====================================

Implements Layer 2 & 3 of the memory architecture:
- Daily notes: Dated markdown files (YYYY-MM-DD.md)
- Timeline tracking: Aggregate events, decisions, conversations
- Tacit knowledge: Implicit patterns and preferences learned over time

Daily Note Structure:
---
date: "2026-01-31"
day_of_week: "Friday"
agent: "finance"  # or "global" for shared notes
tags: ["budget", "portfolio"]
---

# Friday, January 31, 2026

## Key Events
- [09:30] Portfolio rebalanced - sold 10 shares of AAPL
- [14:15] Budget warning triggered - 85% of monthly budget used

## Decisions Made
- Approved $500 roof repair quote from Juan
- Deferred new furniture purchase to next month

## Conversations
- User asked about retirement savings strategy
- Discussed tax optimization for 2025

## Tacit Learnings
- User prefers conservative investment approach
- Budget warnings should trigger at 80%, not 90%
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class DailyEntry(BaseModel):
    """A single entry in a daily note"""
    timestamp: str
    entry_type: str  # "event", "decision", "conversation", "learning"
    content: str
    agent: Optional[str] = None
    confidence: float = 1.0
    tags: List[str] = []


class TacitKnowledge(BaseModel):
    """A piece of tacit knowledge"""
    knowledge_id: str
    category: str  # "preference", "pattern", "insight", "heuristic"
    content: str
    confidence: float
    first_observed: str
    last_reinforced: str
    observation_count: int
    examples: List[str] = []
    tags: List[str] = []


class DailyNotesManager:
    """
    Manages daily notes for agents and global memory
    """

    def __init__(self, memory_base: Path, scope: str = "global", agent_id: Optional[str] = None):
        """
        Initialize daily notes manager.

        Args:
            memory_base: Base memory directory
            scope: "agent" or "global"
            agent_id: Agent ID if scope is "agent"
        """
        self.memory_base = memory_base

        if scope == "agent":
            if not agent_id:
                raise ValueError("agent_id required for agent scope")
            self.daily_path = memory_base / "agents" / agent_id / "daily"
        else:
            self.daily_path = memory_base / "global" / "daily"

        self.daily_path.mkdir(parents=True, exist_ok=True)

        # Tacit knowledge file
        if scope == "agent":
            self.tacit_path = memory_base / "agents" / agent_id / "tacit_knowledge.json"
        else:
            self.tacit_path = memory_base / "global" / "tacit_knowledge.json"

    def _get_daily_note_path(self, note_date: date) -> Path:
        """Get path for a specific daily note"""
        # Organize by year/month for better scaling
        year = note_date.strftime("%Y")
        month = note_date.strftime("%m")
        day_file = note_date.strftime("%Y-%m-%d.md")

        note_dir = self.daily_path / year / month
        note_dir.mkdir(parents=True, exist_ok=True)

        return note_dir / day_file

    def get_or_create_daily_note(self, note_date: Optional[date] = None) -> Path:
        """Get or create daily note for a specific date"""
        if note_date is None:
            note_date = date.today()

        note_path = self._get_daily_note_path(note_date)

        if not note_path.exists():
            # Create new note with template
            day_of_week = note_date.strftime("%A")
            formatted_date = note_date.strftime("%B %d, %Y")

            frontmatter = [
                "---",
                f'date: "{note_date.isoformat()}"',
                f'day_of_week: "{day_of_week}"',
                'tags: []',
                "---",
                "",
                f"# {day_of_week}, {formatted_date}",
                "",
                "## Key Events",
                "",
                "",
                "## Decisions Made",
                "",
                "",
                "## Conversations",
                "",
                "",
                "## Tacit Learnings",
                "",
                "",
            ]

            note_path.write_text("\n".join(frontmatter))

        return note_path

    def add_entry(
        self,
        entry_type: str,
        content: str,
        agent: Optional[str] = None,
        tags: List[str] = None,
        note_date: Optional[date] = None
    ) -> str:
        """
        Add an entry to today's daily note.

        Args:
            entry_type: "event", "decision", "conversation", "learning"
            content: Entry content
            agent: Agent that created the entry
            tags: Optional tags
            note_date: Date for the note (defaults to today)

        Returns:
            Path to the updated note
        """
        if note_date is None:
            note_date = date.today()

        note_path = self.get_or_create_daily_note(note_date)
        note_content = note_path.read_text()

        # Determine section to append to
        section_map = {
            "event": "## Key Events",
            "decision": "## Decisions Made",
            "conversation": "## Conversations",
            "learning": "## Tacit Learnings",
        }

        section_header = section_map.get(entry_type, "## Key Events")

        # Create entry line
        timestamp = datetime.now().strftime("%H:%M")
        agent_suffix = f" ({agent})" if agent else ""
        tags_suffix = f" #{' #'.join(tags)}" if tags else ""
        entry_line = f"- [{timestamp}]{agent_suffix} {content}{tags_suffix}"

        # Find section and append
        lines = note_content.split("\n")
        section_idx = None

        for i, line in enumerate(lines):
            if line.strip() == section_header:
                section_idx = i
                break

        if section_idx is not None:
            # Find next section or end of file
            next_section_idx = len(lines)
            for i in range(section_idx + 1, len(lines)):
                if lines[i].startswith("## "):
                    next_section_idx = i
                    break

            # Insert entry before next section
            lines.insert(next_section_idx, entry_line)
            note_path.write_text("\n".join(lines))
        else:
            # Section not found, append at end
            note_content += f"\n\n{section_header}\n{entry_line}\n"
            note_path.write_text(note_content)

        return str(note_path)

    def get_daily_note(self, note_date: Optional[date] = None) -> Optional[str]:
        """Get content of a daily note"""
        if note_date is None:
            note_date = date.today()

        note_path = self._get_daily_note_path(note_date)
        if note_path.exists():
            return note_path.read_text()
        return None

    def list_daily_notes(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        List daily notes within a date range.

        Returns list of {date, path, preview} dicts
        """
        notes = []

        # Walk through year/month directories
        if not self.daily_path.exists():
            return notes

        for year_dir in sorted(self.daily_path.iterdir(), reverse=True):
            if not year_dir.is_dir():
                continue

            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir():
                    continue

                for note_file in sorted(month_dir.glob("*.md"), reverse=True):
                    # Parse date from filename
                    try:
                        note_date = date.fromisoformat(note_file.stem)
                    except ValueError:
                        continue

                    # Apply date filters
                    if start_date and note_date < start_date:
                        continue
                    if end_date and note_date > end_date:
                        continue

                    # Extract preview (first few lines after frontmatter)
                    content = note_file.read_text()
                    lines = content.split("\n")

                    preview_lines = []
                    in_frontmatter = False
                    frontmatter_done = False

                    for line in lines:
                        if line.strip() == "---":
                            if not in_frontmatter:
                                in_frontmatter = True
                            else:
                                frontmatter_done = True
                            continue

                        if frontmatter_done and line.strip():
                            preview_lines.append(line.strip())
                            if len(preview_lines) >= 3:
                                break

                    notes.append({
                        "date": note_date.isoformat(),
                        "path": str(note_file),
                        "preview": " | ".join(preview_lines),
                    })

                    if len(notes) >= limit:
                        return notes

        return notes

    # Tacit Knowledge Management

    def _load_tacit_knowledge(self) -> List[TacitKnowledge]:
        """Load tacit knowledge from file"""
        if not self.tacit_path.exists():
            return []

        data = json.loads(self.tacit_path.read_text())
        return [TacitKnowledge(**item) for item in data]

    def _save_tacit_knowledge(self, knowledge_list: List[TacitKnowledge]) -> None:
        """Save tacit knowledge to file"""
        data = [k.dict() for k in knowledge_list]
        self.tacit_path.write_text(json.dumps(data, indent=2))

    def add_tacit_knowledge(
        self,
        category: str,
        content: str,
        confidence: float = 0.7,
        examples: List[str] = None,
        tags: List[str] = None
    ) -> str:
        """
        Add a new piece of tacit knowledge.

        Args:
            category: "preference", "pattern", "insight", "heuristic"
            content: Knowledge content
            confidence: Confidence level (0-1)
            examples: Example observations that support this knowledge
            tags: Optional tags

        Returns:
            knowledge_id
        """
        knowledge_list = self._load_tacit_knowledge()

        # Check for similar existing knowledge
        for k in knowledge_list:
            if k.content.lower() == content.lower() and k.category == category:
                # Reinforce existing knowledge
                k.last_reinforced = datetime.now().isoformat()
                k.observation_count += 1
                k.confidence = min(1.0, k.confidence + 0.05)  # Increase confidence

                if examples:
                    k.examples.extend(examples)

                self._save_tacit_knowledge(knowledge_list)
                return k.knowledge_id

        # Create new knowledge
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        knowledge_id = f"tacit_{timestamp}"

        knowledge = TacitKnowledge(
            knowledge_id=knowledge_id,
            category=category,
            content=content,
            confidence=confidence,
            first_observed=datetime.now().isoformat(),
            last_reinforced=datetime.now().isoformat(),
            observation_count=1,
            examples=examples or [],
            tags=tags or [],
        )

        knowledge_list.append(knowledge)
        self._save_tacit_knowledge(knowledge_list)

        return knowledge_id

    def get_tacit_knowledge(
        self,
        category: Optional[str] = None,
        min_confidence: float = 0.0,
        tags: Optional[List[str]] = None
    ) -> List[TacitKnowledge]:
        """
        Get tacit knowledge with optional filters.

        Args:
            category: Filter by category
            min_confidence: Minimum confidence threshold
            tags: Filter by tags (any match)

        Returns:
            List of matching tacit knowledge
        """
        knowledge_list = self._load_tacit_knowledge()

        # Apply filters
        filtered = []
        for k in knowledge_list:
            if category and k.category != category:
                continue
            if k.confidence < min_confidence:
                continue
            if tags and not any(tag in k.tags for tag in tags):
                continue

            filtered.append(k)

        # Sort by confidence and recency
        filtered.sort(key=lambda k: (k.confidence, k.last_reinforced), reverse=True)

        return filtered

    def update_tacit_knowledge(
        self,
        knowledge_id: str,
        confidence: Optional[float] = None,
        add_examples: Optional[List[str]] = None,
        add_tags: Optional[List[str]] = None
    ) -> bool:
        """Update an existing piece of tacit knowledge"""
        knowledge_list = self._load_tacit_knowledge()

        for k in knowledge_list:
            if k.knowledge_id == knowledge_id:
                if confidence is not None:
                    k.confidence = max(0.0, min(1.0, confidence))
                if add_examples:
                    k.examples.extend(add_examples)
                if add_tags:
                    k.tags.extend(add_tags)
                    k.tags = list(set(k.tags))  # Deduplicate

                k.last_reinforced = datetime.now().isoformat()
                self._save_tacit_knowledge(knowledge_list)
                return True

        return False

    def decay_tacit_knowledge(self, days_threshold: int = 30, decay_factor: float = 0.05) -> int:
        """
        Decay confidence of tacit knowledge that hasn't been reinforced recently.

        Args:
            days_threshold: Days since last reinforcement to trigger decay
            decay_factor: Amount to reduce confidence

        Returns:
            Number of knowledge items decayed
        """
        knowledge_list = self._load_tacit_knowledge()
        now = datetime.now()
        decayed_count = 0

        for k in knowledge_list:
            last_reinforced = datetime.fromisoformat(k.last_reinforced)
            days_since = (now - last_reinforced).days

            if days_since >= days_threshold:
                k.confidence = max(0.1, k.confidence - decay_factor)
                decayed_count += 1

        if decayed_count > 0:
            self._save_tacit_knowledge(knowledge_list)

        return decayed_count


def get_timeline(
    memory_base: Path,
    start_date: date,
    end_date: date,
    scope: str = "global",
    agent_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get timeline of events across daily notes.

    Returns list of {date, entries} dicts
    """
    manager = DailyNotesManager(memory_base, scope, agent_id)

    timeline = []
    current_date = start_date

    while current_date <= end_date:
        note_content = manager.get_daily_note(current_date)

        if note_content:
            # Parse entries from note
            entries = []
            lines = note_content.split("\n")

            for line in lines:
                if line.strip().startswith("- ["):
                    # Extract timestamp and content
                    entries.append(line.strip())

            if entries:
                timeline.append({
                    "date": current_date.isoformat(),
                    "entries": entries,
                    "count": len(entries),
                })

        # Move to next day
        from datetime import timedelta
        current_date += timedelta(days=1)

    return timeline
