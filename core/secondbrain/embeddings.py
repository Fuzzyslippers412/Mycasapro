"""
SecondBrain Semantic Search - Local Embeddings
Uses sentence-transformers for semantic similarity when ENSUE unavailable.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np

# Lazy load sentence-transformers (heavy import)
_model = None
_embeddings_cache: Dict[str, np.ndarray] = {}


def _get_model():
    """Lazy load the embedding model"""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        # all-MiniLM-L6-v2 is fast and good for semantic search
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def _compute_embedding(text: str) -> np.ndarray:
    """Compute embedding for text, with caching"""
    text_hash = hashlib.md5(text.encode()).hexdigest()
    
    if text_hash not in _embeddings_cache:
        model = _get_model()
        _embeddings_cache[text_hash] = model.encode(text, convert_to_numpy=True)
    
    return _embeddings_cache[text_hash]


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


class EmbeddingsIndex:
    """
    Local embeddings index for semantic search.
    Stores embeddings in a JSON file alongside the vault.
    """
    
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.index_file = vault_path / "_index" / "embeddings.json"
        self.index: Dict[str, Dict[str, Any]] = {}
        self._load_index()
    
    def _load_index(self):
        """Load existing index from disk"""
        if self.index_file.exists():
            try:
                data = json.loads(self.index_file.read_text())
                # Convert lists back to numpy arrays
                for note_id, entry in data.items():
                    if "embedding" in entry:
                        entry["embedding"] = np.array(entry["embedding"])
                    self.index[note_id] = entry
            except Exception as e:
                print(f"[Embeddings] Failed to load index: {e}")
                self.index = {}
    
    def _save_index(self):
        """Save index to disk"""
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert numpy arrays to lists for JSON serialization
        serializable = {}
        for note_id, entry in self.index.items():
            entry_copy = entry.copy()
            if "embedding" in entry_copy and isinstance(entry_copy["embedding"], np.ndarray):
                entry_copy["embedding"] = entry_copy["embedding"].tolist()
            serializable[note_id] = entry_copy
        
        self.index_file.write_text(json.dumps(serializable, indent=2))
    
    def index_note(
        self,
        note_id: str,
        title: str,
        body: str,
        folder: str,
        metadata: Optional[Dict] = None
    ):
        """Add or update a note in the index"""
        # Combine title and body for embedding
        text = f"{title}\n\n{body}"[:2000]  # Truncate for efficiency
        
        embedding = _compute_embedding(text)
        
        self.index[note_id] = {
            "title": title,
            "folder": folder,
            "embedding": embedding,
            "text_preview": body[:300],
            "indexed_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self._save_index()
    
    def remove_note(self, note_id: str):
        """Remove a note from the index"""
        if note_id in self.index:
            del self.index[note_id]
            self._save_index()
    
    def search(
        self,
        query: str,
        scope: Optional[List[str]] = None,
        limit: int = 10,
        min_score: float = 0.3
    ) -> List[Tuple[str, float, Dict]]:
        """
        Semantic search across indexed notes.
        
        Args:
            query: Search query
            scope: List of folders to search (None = all)
            limit: Max results
            min_score: Minimum similarity threshold
        
        Returns:
            List of (note_id, score, entry) tuples, sorted by relevance
        """
        if not self.index:
            return []
        
        query_embedding = _compute_embedding(query)
        
        results = []
        for note_id, entry in self.index.items():
            # Filter by scope
            if scope and entry.get("folder") not in scope:
                continue
            
            if "embedding" not in entry:
                continue
            
            embedding = entry["embedding"]
            if isinstance(embedding, list):
                embedding = np.array(embedding)
            
            score = _cosine_similarity(query_embedding, embedding)
            
            if score >= min_score:
                results.append((note_id, score, entry))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    def reindex_vault(self):
        """Reindex all notes in the vault"""
        self.index = {}
        
        for folder in self.vault_path.iterdir():
            if not folder.is_dir() or folder.name.startswith("_"):
                continue
            
            for file_path in folder.glob("*.md"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    
                    # Extract title and body
                    title = file_path.stem
                    body = content
                    
                    # Try to extract title from H1
                    import re
                    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                    if title_match:
                        title = title_match.group(1)
                    
                    # Remove YAML frontmatter from body
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            body = parts[2].strip()
                    
                    self.index_note(
                        note_id=file_path.stem,
                        title=title,
                        body=body,
                        folder=folder.name
                    )
                    
                except Exception as e:
                    print(f"[Embeddings] Failed to index {file_path}: {e}")
        
        print(f"[Embeddings] Indexed {len(self.index)} notes")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        folders = {}
        for entry in self.index.values():
            folder = entry.get("folder", "unknown")
            folders[folder] = folders.get(folder, 0) + 1
        
        return {
            "total_notes": len(self.index),
            "by_folder": folders,
            "index_file": str(self.index_file),
            "index_size_kb": self.index_file.stat().st_size // 1024 if self.index_file.exists() else 0
        }


# Module-level index instance (per vault)
_indexes: Dict[str, EmbeddingsIndex] = {}


def get_index(vault_path: Path) -> EmbeddingsIndex:
    """Get or create an embeddings index for a vault"""
    key = str(vault_path)
    if key not in _indexes:
        _indexes[key] = EmbeddingsIndex(vault_path)
    return _indexes[key]
