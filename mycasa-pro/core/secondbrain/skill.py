"""
SecondBrain Skill - Core Implementation
========================================

Guarded write access to the Obsidian-compatible vault.
All agent memory operations MUST go through this skill.
"""

import re
import json
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union

from .models import (
    NoteType, NotePayload, NoteMetadata, AgentType, SourceType,
    Confidence, SearchResult, GraphNode, GraphEdge, GraphResult,
    PreferenceNote, PreferenceCategory, PatternNote, PatternType,
    RelationshipNote, TranscriptNote, AgentWorkspace
)
from .exceptions import (
    SecondBrainError, ValidationError, NoteNotFoundError
)
from .embeddings import get_index


class SecondBrain:
    """
    SecondBrain Skill for MyCasa Pro agents.
    
    Provides guarded write access to the Obsidian-compatible vault.
    Integrates with ENSUE API for indexing and retrieval.
    """
    
    VAULT_BASE = Path.home() / "moltbot" / "vaults"
    ENSUE_SCRIPT = Path.home() / "clawd" / "skills" / "second-brain" / "scripts" / "ensue-api.sh"
    
    def __init__(
        self,
        tenant_id: str,
        agent: Optional[Union[AgentType, str]] = None,
        correlation_id: Optional[str] = None
    ):
        self.tenant_id = tenant_id
        # Convert string agent to AgentType if needed
        if isinstance(agent, str):
            try:
                agent = AgentType(agent)
            except ValueError:
                agent = None  # Invalid agent name, use default
        self.default_agent = agent
        self.correlation_id = correlation_id or self._generate_correlation_id()
        self.vault_path = self.VAULT_BASE / tenant_id / "secondbrain"
        
        # Ensure vault exists
        if not self.vault_path.exists():
            raise SecondBrainError(f"Vault not found: {self.vault_path}")
        
        # Daily sequence counter (in-memory, reset on new day)
        self._sequence_date = date.today()
        self._sequence_counter = self._get_initial_sequence()
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{self.tenant_id}:{timestamp}".encode()).hexdigest()[:12]
    
    def _get_initial_sequence(self) -> int:
        """Get the next sequence number for today"""
        today_str = self._sequence_date.strftime("%Y_%m_%d")
        pattern = f"sb_{today_str}_*.md"
        
        max_seq = 0
        for folder in self.vault_path.iterdir():
            if folder.is_dir() and not folder.name.startswith("_"):
                for file in folder.glob(pattern):
                    match = re.search(r'sb_\d{4}_\d{2}_\d{2}_(\d+)\.md$', file.name)
                    if match:
                        seq = int(match.group(1))
                        max_seq = max(max_seq, seq)
        
        return max_seq + 1
    
    def _get_next_id(self) -> str:
        """Generate the next note ID"""
        today = date.today()
        
        # Reset sequence if new day
        if today != self._sequence_date:
            self._sequence_date = today
            self._sequence_counter = 1
        
        note_id = f"sb_{today.strftime('%Y_%m_%d')}_{self._sequence_counter:03d}"
        self._sequence_counter += 1
        
        return note_id
    
    async def write_note(
        self,
        type: Union[NoteType, str],
        title: str,
        body: str,
        agent: Optional[Union[AgentType, str]] = None,
        source: Union[SourceType, str] = SourceType.SYSTEM,
        folder: Optional[str] = None,
        refs: Optional[List[str]] = None,
        entities: Optional[List[str]] = None,
        confidence: Union[Confidence, str] = Confidence.MEDIUM,
        pii: bool = False,
    ) -> str:
        """
        Create a new note in the vault.
        
        Args:
            type: Note type (decision, event, entity, etc.)
            title: Note title (becomes H1 header)
            body: Markdown body content
            agent: Agent creating the note (uses default if not specified)
            source: Source of the information
            folder: Override default folder
            refs: List of referenced note IDs
            entities: List of entity IDs mentioned
            confidence: Confidence level
            pii: Whether note contains PII (requires explicit flag)
        
        Returns:
            The new note's ID
        
        Raises:
            ValidationError: If payload validation fails
            PermissionError: If agent lacks permission
        """
        # Normalize enums
        if isinstance(type, str):
            type = NoteType(type)
        
        # Handle agent - can be string, AgentType, or None
        if agent is None:
            agent = self.default_agent
        if agent is None:
            agent = AgentType.MANAGER
        if isinstance(agent, str):
            agent = AgentType(agent)
        
        if isinstance(source, str):
            source = SourceType(source)
        if isinstance(confidence, str):
            confidence = Confidence(confidence)
        
        # Build payload
        payload = NotePayload(
            type=type,
            title=title,
            body=body,
            agent=agent,
            source=source,
            folder=folder,
            refs=refs or [],
            entities=entities or [],
            confidence=confidence,
            correlation_id=self.correlation_id,
            pii=pii,
        )
        
        # Validate
        errors = payload.validate()
        if errors:
            raise ValidationError(f"Validation failed: {'; '.join(errors)}")
        
        # Generate ID and metadata
        note_id = self._get_next_id()
        metadata = NoteMetadata(
            id=note_id,
            type=type,
            tenant=self.tenant_id,
            agent=agent,
            created_at=datetime.now(),
            source=source,
            refs=payload.refs,
            entities=payload.entities,
            confidence=confidence,
            correlation_id=self.correlation_id,
            pii=pii,
        )
        
        # Build markdown content
        content = f"{metadata.to_yaml()}\n\n# {title}\n\n{body}\n"
        
        # Write file
        target_folder = self.vault_path / payload.get_folder()
        target_folder.mkdir(parents=True, exist_ok=True)
        
        file_path = target_folder / f"{note_id}.md"
        file_path.write_text(content, encoding="utf-8")
        
        # Index with ENSUE (async, non-blocking)
        asyncio.create_task(self._index_note(note_id, metadata, title, body))
        
        return note_id
    
    async def append(
        self,
        note_id: str,
        content: str,
        agent: Optional[Union[AgentType, str]] = None,
    ) -> bool:
        """
        Append content to an existing note.
        
        Args:
            note_id: ID of the note to append to
            content: Content to append (markdown)
            agent: Agent performing the append
        
        Returns:
            True if successful
        
        Raises:
            NoteNotFoundError: If note doesn't exist
            PermissionError: If agent lacks permission
        """
        # Find the note
        file_path = self._find_note(note_id)
        if not file_path:
            raise NoteNotFoundError(f"Note not found: {note_id}")
        
        # Normalize agent
        if agent is None:
            agent = self.default_agent
        if agent is None:
            agent = AgentType.MANAGER
        if isinstance(agent, str):
            agent = AgentType(agent)
        
        # Build append block with timestamp
        timestamp = datetime.now().isoformat()
        append_block = f"\n\n---\n_Appended by {agent.value} at {timestamp}_\n\n{content}"
        
        # Append to file
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(append_block)
        
        # Update ENSUE index
        asyncio.create_task(self._update_index(note_id))
        
        return True
    
    async def link(
        self,
        from_id: str,
        to_id: str,
        relation: str,
    ) -> bool:
        """
        Create a relationship between two notes/entities.
        
        Args:
            from_id: Source note/entity ID
            to_id: Target note/entity ID
            relation: Relationship type (MENTIONS, OWNS, PAID, etc.)
        
        Returns:
            True if successful
        """
        # Validate both IDs exist
        from_exists = self._find_note(from_id) or to_id.startswith("ent_")
        to_exists = self._find_note(to_id) or to_id.startswith("ent_")
        
        if not from_exists:
            raise NoteNotFoundError(f"Source not found: {from_id}")
        
        # Store relationship in _index/links.md
        links_file = self.vault_path / "_index" / "links.md"
        
        timestamp = datetime.now().isoformat()
        link_entry = f"- [{from_id}] --{relation}--> [{to_id}] @ {timestamp}\n"
        
        with open(links_file, "a", encoding="utf-8") as f:
            f.write(link_entry)
        
        # Update ENSUE graph
        asyncio.create_task(self._index_link(from_id, to_id, relation))
        
        return True
    
    async def search(
        self,
        query: str,
        scope: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        Search notes using ENSUE semantic search.
        
        Args:
            query: Search query
            scope: List of folders to search (None = all)
            limit: Maximum results
        
        Returns:
            List of SearchResult objects
        """
        try:
            args = {
                "query": f"{self.tenant_id} {query}",
                "limit": limit
            }
            
            result = await self._ensue_call("discover_memories", args)
            
            results = []
            for item in result.get("results", []):
                # Parse the key_name to extract note info
                key = item.get("key_name", "")
                
                # Filter by scope if specified
                if scope:
                    folder = key.split("/")[-2] if "/" in key else ""
                    if folder not in scope:
                        continue
                
                results.append(SearchResult(
                    note_id=key.split("/")[-1] if "/" in key else key,
                    file_path=key,
                    relevance=item.get("relevance", 0.0),
                    snippet=item.get("value", "")[:200],
                    metadata=item.get("metadata", {})
                ))
            
            return results[:limit]
        
        except Exception as e:
            # Fallback to local grep search
            return await self._local_search(query, scope, limit)
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an entity by ID.
        
        Args:
            entity_id: Entity ID (e.g., ent_contractor_juan)
        
        Returns:
            Entity data dict or None
        """
        # Check entities folder
        entities_folder = self.vault_path / "entities"
        entity_file = entities_folder / f"{entity_id}.md"
        
        if entity_file.exists():
            content = entity_file.read_text(encoding="utf-8")
            return self._parse_note(content)
        
        # Search ENSUE
        try:
            args = {"key_names": [f"entities/{entity_id}"]}
            result = await self._ensue_call("get_memory", args)
            if result.get("results"):
                return result["results"][0]
        except Exception:
            pass
        
        return None
    
    async def get_graph(
        self,
        seed_id: str,
        depth: int = 2,
    ) -> GraphResult:
        """
        Traverse knowledge graph from a seed node.
        
        Args:
            seed_id: Starting note/entity ID
            depth: Traversal depth
        
        Returns:
            GraphResult with nodes and edges
        """
        nodes = []
        edges = []
        visited = set()
        
        async def traverse(node_id: str, current_depth: int):
            if current_depth > depth or node_id in visited:
                return
            
            visited.add(node_id)
            
            # Add node
            if node_id.startswith("sb_"):
                note_path = self._find_note(node_id)
                if note_path:
                    content = note_path.read_text(encoding="utf-8")
                    meta = self._parse_note(content)
                    nodes.append(GraphNode(
                        id=node_id,
                        type="note",
                        label=meta.get("title", node_id),
                        properties=meta
                    ))
                    
                    # Traverse refs
                    for ref in meta.get("refs", []):
                        edges.append(GraphEdge(
                            from_id=node_id,
                            to_id=ref,
                            relation="REFERENCES"
                        ))
                        await traverse(ref, current_depth + 1)
                    
                    # Traverse entities
                    for ent in meta.get("entities", []):
                        edges.append(GraphEdge(
                            from_id=node_id,
                            to_id=ent,
                            relation="MENTIONS"
                        ))
                        await traverse(ent, current_depth + 1)
            
            elif node_id.startswith("ent_"):
                entity = await self.get_entity(node_id)
                if entity:
                    nodes.append(GraphNode(
                        id=node_id,
                        type="entity",
                        label=entity.get("name", node_id),
                        properties=entity
                    ))
        
        await traverse(seed_id, 0)
        
        return GraphResult(nodes=nodes, edges=edges)
    
    def _find_note(self, note_id: str) -> Optional[Path]:
        """Find a note file by ID"""
        for folder in self.vault_path.iterdir():
            if folder.is_dir():
                file_path = folder / f"{note_id}.md"
                if file_path.exists():
                    return file_path
        return None
    
    def _parse_note(self, content: str) -> Dict[str, Any]:
        """Parse note content into dict"""
        result = {}
        
        # Extract YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                yaml_content = parts[1].strip()
                
                # Parse YAML properly (handle lists)
                current_key = None
                current_list = None
                
                for line in yaml_content.split("\n"):
                    stripped = line.strip()
                    
                    # List item
                    if stripped.startswith("- "):
                        if current_key and current_list is not None:
                            current_list.append(stripped[2:])
                    # Key-value pair
                    elif ":" in line and not line.startswith(" "):
                        # Save previous list if any
                        if current_key and current_list is not None:
                            result[current_key] = current_list
                        
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if value:
                            # Simple key: value
                            result[key] = value
                            current_key = None
                            current_list = None
                        else:
                            # Key with list to follow
                            current_key = key
                            current_list = []
                
                # Don't forget the last list
                if current_key and current_list is not None:
                    result[current_key] = current_list
                
                body = parts[2].strip()
                # Extract title from first H1
                title_match = re.search(r'^#\s+(.+)$', body, re.MULTILINE)
                if title_match:
                    result["title"] = title_match.group(1)
                result["body"] = body
        
        return result
    
    async def _index_note(
        self,
        note_id: str,
        metadata: NoteMetadata,
        title: str,
        body: str
    ):
        """Index note with ENSUE"""
        try:
            folder = self._find_note(note_id).parent.name if self._find_note(note_id) else "memory"
            key = f"{self.tenant_id}/{folder}/{note_id}"
            
            args = {
                "items": [{
                    "key_name": key,
                    "description": f"{metadata.type.value}: {title}",
                    "value": body[:5000],  # Truncate for embedding
                    "embed": True
                }]
            }
            
            await self._ensue_call("create_memory", args)
        except Exception as e:
            # Log but don't fail - indexing is async
            print(f"[SecondBrain] Index error for {note_id}: {e}")
    
    async def _update_index(self, note_id: str):
        """Update ENSUE index for a note"""
        try:
            file_path = self._find_note(note_id)
            if file_path:
                content = file_path.read_text(encoding="utf-8")
                meta = self._parse_note(content)
                
                key = f"{self.tenant_id}/{file_path.parent.name}/{note_id}"
                args = {
                    "key_name": key,
                    "value": meta.get("body", "")[:5000]
                }
                
                await self._ensue_call("update_memory", args)
        except Exception as e:
            print(f"[SecondBrain] Update index error for {note_id}: {e}")
    
    async def _index_link(self, from_id: str, to_id: str, relation: str):
        """Index relationship with ENSUE"""
        try:
            key = f"{self.tenant_id}/_graph/{from_id}__{relation}__{to_id}"
            args = {
                "items": [{
                    "key_name": key,
                    "description": f"Relationship: {from_id} --{relation}--> {to_id}",
                    "value": json.dumps({
                        "from": from_id,
                        "to": to_id,
                        "relation": relation,
                        "tenant": self.tenant_id
                    }),
                    "embed": False
                }]
            }
            
            await self._ensue_call("create_memory", args)
        except Exception as e:
            print(f"[SecondBrain] Link index error: {e}")
    
    async def _ensue_call(self, method: str, args: Dict) -> Dict:
        """Call ENSUE API"""
        if not self.ENSUE_SCRIPT.exists():
            raise SecondBrainError("ENSUE API script not found")
        
        cmd = [str(self.ENSUE_SCRIPT), method, json.dumps(args)]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise SecondBrainError(f"ENSUE call failed: {stderr.decode()}")
        
        try:
            response = json.loads(stdout.decode())
            if "result" in response:
                content = response["result"].get("content", [])
                if content and "text" in content[0]:
                    return json.loads(content[0]["text"])
            return response
        except json.JSONDecodeError:
            return {"raw": stdout.decode()}
    
    async def _local_search(
        self,
        query: str,
        scope: Optional[List[str]],
        limit: int
    ) -> List[SearchResult]:
        """Semantic search using local embeddings (fallback when ENSUE unavailable)"""
        try:
            # Use semantic embeddings
            index = get_index(self.vault_path)
            
            # Build index if empty
            if not index.index:
                index.reindex_vault()
            
            semantic_results = index.search(query, scope=scope, limit=limit)
            
            results = []
            for note_id, score, entry in semantic_results:
                file_path = self._find_note(note_id)
                
                results.append(SearchResult(
                    note_id=note_id,
                    file_path=f"{entry.get('folder', '')}/{note_id}.md",
                    relevance=score,
                    snippet=entry.get("text_preview", "")[:200],
                    metadata=entry.get("metadata", {})
                ))
            
            return results
            
        except Exception as e:
            # Final fallback: basic grep
            print(f"[SecondBrain] Semantic search failed, using grep: {e}")
            return await self._grep_search(query, scope, limit)
    
    async def _grep_search(
        self,
        query: str,
        scope: Optional[List[str]],
        limit: int
    ) -> List[SearchResult]:
        """Basic grep search (last resort fallback)"""
        results = []
        
        folders = scope or [
            f.name for f in self.vault_path.iterdir()
            if f.is_dir() and not f.name.startswith("_")
        ]
        
        for folder_name in folders:
            folder = self.vault_path / folder_name
            if not folder.exists():
                continue
            
            for file_path in folder.glob("*.md"):
                content = file_path.read_text(encoding="utf-8")
                
                if query.lower() in content.lower():
                    meta = self._parse_note(content)
                    results.append(SearchResult(
                        note_id=file_path.stem,
                        file_path=str(file_path.relative_to(self.vault_path)),
                        relevance=0.5,  # Basic match
                        snippet=content[:200],
                        metadata=meta
                    ))
                
                if len(results) >= limit:
                    break
        
        return results[:limit]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # AGENT WORKSPACE METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_agent_workspace(self, agent_id: str) -> AgentWorkspace:
        """
        Load an agent's workspace files.
        
        Args:
            agent_id: Agent identifier (e.g., 'finance', 'maintenance')
        
        Returns:
            AgentWorkspace with all config files
        """
        workspace_path = self.vault_path / "agents" / agent_id
        
        workspace = AgentWorkspace(agent_id=agent_id)
        
        files = {
            "SOUL.md": "soul",
            "IDENTITY.md": "identity",
            "TOOLS.md": "tools",
            "MEMORY.md": "memory",
            "HEARTBEAT.md": "heartbeat",
        }
        
        for filename, attr in files.items():
            file_path = workspace_path / filename
            if file_path.exists():
                setattr(workspace, attr, file_path.read_text(encoding="utf-8"))
        
        return workspace
    
    def save_agent_workspace(self, workspace: AgentWorkspace) -> bool:
        """
        Save an agent's workspace files.
        
        Args:
            workspace: AgentWorkspace to save
        
        Returns:
            True if successful
        """
        workspace_path = self.vault_path / "agents" / workspace.agent_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        for filename, content in workspace.to_files().items():
            file_path = workspace_path / filename
            file_path.write_text(content, encoding="utf-8")
        
        return True
    
    def init_agent_workspace(self, agent_id: str, agent_name: str, description: str) -> AgentWorkspace:
        """
        Initialize a new agent workspace with default templates.
        """
        workspace = AgentWorkspace(
            agent_id=agent_id,
            soul=f"""# Soul - {agent_name}

This agent is responsible for {description.lower()}.

## Core Behaviors
- Be helpful and proactive
- Respect user preferences
- Document decisions and learnings
""",
            identity=f"""# Identity - {agent_name}

**Name:** {agent_name}
**Role:** {agent_id}
**Type:** MyCasa Pro Agent

## Responsibilities
{description}
""",
            tools=f"""# Tools - {agent_name}

Local tool notes and conventions.
""",
            memory=f"""# Memory - {agent_name}

Persistent learnings and context.
""",
            heartbeat=f"""# Heartbeat - {agent_name}

Periodic check configuration.
"""
        )
        
        self.save_agent_workspace(workspace)
        return workspace
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PREFERENCE LEARNING
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def learn_preference(
        self,
        key: str,
        value: Any,
        category: Union[PreferenceCategory, str] = PreferenceCategory.GENERAL,
        context: Optional[str] = None,
        learned_from: Optional[str] = None,
        examples: Optional[List[str]] = None,
        agent: Optional[Union[AgentType, str]] = None,
    ) -> str:
        """Learn and store a user preference."""
        if isinstance(category, str):
            category = PreferenceCategory(category)
        
        existing = await self._find_preference(key)
        
        pref = PreferenceNote(
            key=key,
            value=value,
            category=category,
            context=context,
            learned_from=learned_from,
            strength=1.0 if not existing else min(1.0, existing.get("strength", 0.5) + 0.2),
            examples=examples or [],
        )
        
        if existing:
            await self.append(
                existing["id"],
                f"\n## Updated {datetime.now().isoformat()}\n\n{pref.to_markdown()}",
                agent=agent
            )
            return existing["id"]
        else:
            return await self.write_note(
                type=NoteType.PREFERENCE,
                title=f"Preference: {key}",
                body=pref.to_markdown(),
                agent=agent,
                source=SourceType.LEARNING,
                folder="preferences",
            )
    
    async def get_preferences(self, category: Optional[PreferenceCategory] = None) -> List[Dict[str, Any]]:
        """Get all learned preferences."""
        prefs = []
        prefs_folder = self.vault_path / "preferences"
        
        if not prefs_folder.exists():
            return prefs
        
        for file_path in prefs_folder.glob("*.md"):
            content = file_path.read_text(encoding="utf-8")
            meta = self._parse_note(content)
            
            if category and meta.get("category") != category.value:
                continue
            
            prefs.append({"id": file_path.stem, **meta})
        
        return prefs
    
    async def _find_preference(self, key: str) -> Optional[Dict[str, Any]]:
        """Find existing preference by key"""
        prefs_folder = self.vault_path / "preferences"
        if not prefs_folder.exists():
            return None
        
        for file_path in prefs_folder.glob("*.md"):
            content = file_path.read_text(encoding="utf-8")
            if f"`{key}`" in content or f"Preference: {key}" in content:
                meta = self._parse_note(content)
                meta["id"] = file_path.stem
                return meta
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PATTERN RECOGNITION
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def record_pattern(
        self,
        name: str,
        pattern_type: Union[PatternType, str],
        behavior: str,
        trigger: Optional[str] = None,
        frequency: Optional[str] = None,
        observations: Optional[List[str]] = None,
        agent: Optional[Union[AgentType, str]] = None,
    ) -> str:
        """Record a behavioral pattern."""
        if isinstance(pattern_type, str):
            pattern_type = PatternType(pattern_type)
        
        pattern = PatternNote(
            name=name,
            pattern_type=pattern_type,
            trigger=trigger,
            behavior=behavior,
            frequency=frequency,
            observations=observations or [],
        )
        
        return await self.write_note(
            type=NoteType.PATTERN,
            title=f"Pattern: {name}",
            body=pattern.to_markdown(),
            agent=agent,
            source=SourceType.LEARNING,
            folder="patterns",
        )
    
    async def get_patterns(self, pattern_type: Optional[PatternType] = None) -> List[Dict[str, Any]]:
        """Get all recorded patterns."""
        patterns = []
        patterns_folder = self.vault_path / "patterns"
        
        if not patterns_folder.exists():
            return patterns
        
        for file_path in patterns_folder.glob("*.md"):
            content = file_path.read_text(encoding="utf-8")
            meta = self._parse_note(content)
            patterns.append({"id": file_path.stem, **meta})
        
        return patterns
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RELATIONSHIP NOTES
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def remember_person(
        self,
        name: str,
        relation: Optional[str] = None,
        context: Optional[str] = None,
        contact_info: Optional[Dict[str, str]] = None,
        preferences: Optional[Dict[str, str]] = None,
        notes: Optional[List[str]] = None,
        agent: Optional[Union[AgentType, str]] = None,
    ) -> str:
        """Remember information about a person."""
        existing = await self._find_person(name)
        
        relationship = RelationshipNote(
            name=name,
            relation=relation,
            context=context,
            contact_info=contact_info or {},
            preferences=preferences or {},
            notes=notes or [],
            last_interaction=datetime.now(),
        )
        
        if existing:
            await self.append(
                existing["id"],
                f"\n## Updated {datetime.now().isoformat()}\n\n{relationship.to_markdown()}",
                agent=agent
            )
            return existing["id"]
        else:
            return await self.write_note(
                type=NoteType.RELATIONSHIP,
                title=f"Person: {name}",
                body=relationship.to_markdown(),
                agent=agent,
                source=SourceType.USER,
                folder="relationships",
                entities=[f"ent_person_{name.lower().replace(' ', '_')}"],
            )
    
    async def get_person(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a person by name."""
        return await self._find_person(name)
    
    async def _find_person(self, name: str) -> Optional[Dict[str, Any]]:
        """Find person by name"""
        rel_folder = self.vault_path / "relationships"
        if not rel_folder.exists():
            return None
        
        name_lower = name.lower()
        for file_path in rel_folder.glob("*.md"):
            content = file_path.read_text(encoding="utf-8")
            if name_lower in content.lower():
                meta = self._parse_note(content)
                meta["id"] = file_path.stem
                return meta
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TRANSCRIPT SAVING
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def save_transcript(
        self,
        session_id: str,
        channel: str,
        messages: List[Dict[str, Any]],
        summary: Optional[str] = None,
        key_decisions: Optional[List[str]] = None,
        action_items: Optional[List[str]] = None,
        agent: Optional[Union[AgentType, str]] = None,
    ) -> str:
        """Save a conversation transcript to prevent amnesia."""
        start_time = datetime.now()
        if messages:
            first_ts = messages[0].get("timestamp")
            if first_ts:
                try:
                    start_time = datetime.fromisoformat(first_ts)
                except Exception:
                    pass
        
        transcript = TranscriptNote(
            session_id=session_id,
            channel=channel,
            start_time=start_time,
            end_time=datetime.now(),
            message_count=len(messages),
            summary=summary,
            key_decisions=key_decisions or [],
            action_items=action_items or [],
            messages=messages,
        )
        
        return await self.write_note(
            type=NoteType.TRANSCRIPT,
            title=f"Transcript: {session_id[:8]} ({channel})",
            body=transcript.to_markdown(),
            agent=agent,
            source=SourceType.SESSION,
            folder="transcripts",
        )
    
    async def get_recent_transcripts(self, channel: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transcripts."""
        transcripts = []
        trans_folder = self.vault_path / "transcripts"
        
        if not trans_folder.exists():
            return transcripts
        
        files = sorted(trans_folder.glob("*.md"), reverse=True)
        
        for file_path in files[:limit * 2]:
            content = file_path.read_text(encoding="utf-8")
            meta = self._parse_note(content)
            
            if channel and channel.lower() not in content.lower():
                continue
            
            transcripts.append({"id": file_path.stem, **meta})
            
            if len(transcripts) >= limit:
                break
        
        return transcripts
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MEMORY RECALL (Check before asking)
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def recall(
        self,
        query: str,
        include_preferences: bool = True,
        include_patterns: bool = True,
        include_relationships: bool = True,
        include_transcripts: bool = False,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Recall relevant memories before responding.
        "Checks memory before asking you to repeat yourself."
        """
        results = {
            "general": [],
            "preferences": [],
            "patterns": [],
            "relationships": [],
            "transcripts": [],
        }
        
        # General search
        general = await self.search(query, limit=limit)
        results["general"] = [
            {"id": r.note_id, "snippet": r.snippet, "relevance": r.relevance}
            for r in general
        ]
        
        query_lower = query.lower()
        
        # Preference search
        if include_preferences:
            prefs_folder = self.vault_path / "preferences"
            if prefs_folder.exists():
                for file_path in prefs_folder.glob("*.md"):
                    content = file_path.read_text(encoding="utf-8")
                    if query_lower in content.lower():
                        meta = self._parse_note(content)
                        results["preferences"].append({
                            "id": file_path.stem,
                            "key": meta.get("title", "").replace("Preference: ", ""),
                            "snippet": content[:200],
                        })
                        if len(results["preferences"]) >= limit:
                            break
        
        # Pattern search
        if include_patterns:
            patterns_folder = self.vault_path / "patterns"
            if patterns_folder.exists():
                for file_path in patterns_folder.glob("*.md"):
                    content = file_path.read_text(encoding="utf-8")
                    if query_lower in content.lower():
                        results["patterns"].append({
                            "id": file_path.stem,
                            "snippet": content[:200],
                        })
                        if len(results["patterns"]) >= limit:
                            break
        
        # Relationship search
        if include_relationships:
            rel_folder = self.vault_path / "relationships"
            if rel_folder.exists():
                for file_path in rel_folder.glob("*.md"):
                    content = file_path.read_text(encoding="utf-8")
                    if query_lower in content.lower():
                        meta = self._parse_note(content)
                        results["relationships"].append({
                            "id": file_path.stem,
                            "name": meta.get("title", "").replace("Person: ", ""),
                            "snippet": content[:200],
                        })
                        if len(results["relationships"]) >= limit:
                            break
        
        # Transcript search
        if include_transcripts:
            trans_folder = self.vault_path / "transcripts"
            if trans_folder.exists():
                for file_path in sorted(trans_folder.glob("*.md"), reverse=True)[:20]:
                    content = file_path.read_text(encoding="utf-8")
                    if query_lower in content.lower():
                        results["transcripts"].append({
                            "id": file_path.stem,
                            "snippet": content[:200],
                        })
                        if len(results["transcripts"]) >= limit:
                            break
        
        return results
    
    async def has_memory_of(self, topic: str) -> bool:
        """
        Quick check if we have any memory of a topic.
        Use before asking user to repeat themselves.
        """
        recall = await self.recall(topic, limit=1)
        
        return any([
            recall["general"],
            recall["preferences"],
            recall["patterns"],
            recall["relationships"],
        ])
