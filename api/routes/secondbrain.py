"""
MyCasa Pro - SecondBrain API Routes
===================================

Endpoints for interacting with the SecondBrain vault.
Includes knowledge graph API for visualization.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import yaml
import re
import hashlib
import tempfile

from config.settings import VAULT_PATH

router = APIRouter(prefix="/secondbrain", tags=["SecondBrain"])

# Vault configuration
VAULT_ROOT = VAULT_PATH


def _parse_note(file_path: Path) -> Optional[Dict[str, Any]]:
    """Parse a SecondBrain note file"""
    try:
        content = file_path.read_text(encoding="utf-8")
        
        # Parse YAML frontmatter
        if content.startswith("---"):
            end_idx = content.find("---", 3)
            if end_idx > 0:
                frontmatter = yaml.safe_load(content[4:end_idx])
                body = content[end_idx + 4:].strip()
                
                return {
                    "id": file_path.stem,
                    "path": str(file_path.relative_to(VAULT_ROOT)),
                    "folder": file_path.parent.name,
                    "frontmatter": frontmatter,
                    "body": body,
                    "body_preview": body[:200] if len(body) > 200 else body,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                }
        
        # No frontmatter
        return {
            "id": file_path.stem,
            "path": str(file_path.relative_to(VAULT_ROOT)),
            "folder": file_path.parent.name,
            "frontmatter": {},
            "body": content,
            "body_preview": content[:200] if len(content) > 200 else content,
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        }
    except Exception as e:
        return None


def _extract_links(content: str) -> List[str]:
    """Extract [[wikilinks]] from content"""
    pattern = r'\[\[([^\]]+)\]\]'
    matches = re.findall(pattern, content)
    return matches


def _get_all_notes() -> List[Dict[str, Any]]:
    """Get all notes in the vault"""
    if not VAULT_ROOT.exists():
        return []
    
    notes = []
    for note_file in VAULT_ROOT.rglob("sb_*.md"):
        parsed = _parse_note(note_file)
        if parsed:
            notes.append(parsed)
    
    return notes


@router.get("/notes")
async def list_notes(
    folder: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List all notes in the SecondBrain vault.
    
    Filters:
    - folder: Filter by folder name
    - type: Filter by note type (from frontmatter)
    """
    notes = _get_all_notes()
    
    # Apply filters
    if folder:
        notes = [n for n in notes if n["folder"] == folder]
    
    if type:
        notes = [n for n in notes if n.get("frontmatter", {}).get("type") == type]
    
    # Sort by modified date (newest first)
    notes.sort(key=lambda x: x.get("modified", ""), reverse=True)
    
    # Pagination
    total = len(notes)
    notes = notes[offset:offset + limit]
    
    return {
        "notes": notes,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/notes/{note_id}")
async def get_note(note_id: str) -> Dict[str, Any]:
    """Get a specific note by ID"""
    for note_file in VAULT_ROOT.rglob(f"{note_id}.md"):
        parsed = _parse_note(note_file)
        if parsed:
            return parsed
    
    raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")


@router.get("/graph")
async def get_knowledge_graph(
    include_body: bool = False,
) -> Dict[str, Any]:
    """
    Get the SecondBrain vault as a knowledge graph.
    
    Returns nodes (notes) and edges (links between notes).
    For visualization with D3.js, react-force-graph, etc.
    """
    if not VAULT_ROOT.exists():
        return {
            "nodes": [],
            "edges": [],
            "stats": {"error": "Vault not found"},
        }
    
    notes = _get_all_notes()
    
    # Build node lookup
    node_ids = {n["id"] for n in notes}
    
    nodes = []
    edges = []
    
    for note in notes:
        # Node data
        node = {
            "id": note["id"],
            "title": note.get("frontmatter", {}).get("title", note["id"]),
            "type": note.get("frontmatter", {}).get("type", "unknown"),
            "folder": note["folder"],
            "agent": note.get("frontmatter", {}).get("agent", "unknown"),
            "modified": note["modified"],
        }
        
        if include_body:
            node["body_preview"] = note["body_preview"]
        
        nodes.append(node)
        
        # Extract links from body
        body = note.get("body", "")
        links = _extract_links(body)
        
        for link in links:
            # Check if link target exists
            target_id = link if link.startswith("sb_") else None
            if target_id and target_id in node_ids:
                edges.append({
                    "source": note["id"],
                    "target": target_id,
                    "type": "references",
                })
        
        # Extract links from frontmatter (if present)
        frontmatter_links = note.get("frontmatter", {}).get("links", [])
        if isinstance(frontmatter_links, list):
            for link_obj in frontmatter_links:
                if isinstance(link_obj, dict) and "target" in link_obj:
                    target_id = link_obj["target"]
                    if target_id in node_ids:
                        edges.append({
                            "source": note["id"],
                            "target": target_id,
                            "type": link_obj.get("type", "related"),
                        })
    
    # Calculate stats
    by_type = {}
    by_folder = {}
    by_agent = {}
    
    for node in nodes:
        note_type = node.get("type", "unknown")
        folder = node.get("folder", "unknown")
        agent = node.get("agent", "unknown")
        
        by_type[note_type] = by_type.get(note_type, 0) + 1
        by_folder[folder] = by_folder.get(folder, 0) + 1
        by_agent[agent] = by_agent.get(agent, 0) + 1
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_notes": len(nodes),
            "total_edges": len(edges),
            "by_type": by_type,
            "by_folder": by_folder,
            "by_agent": by_agent,
        },
    }


@router.get("/graph/{note_id}")
async def get_note_connections(note_id: str, depth: int = 1) -> Dict[str, Any]:
    """
    Get a single note and its connections up to specified depth.
    
    Useful for exploring the graph starting from a specific note.
    """
    all_notes = _get_all_notes()
    note_lookup = {n["id"]: n for n in all_notes}
    
    if note_id not in note_lookup:
        raise HTTPException(status_code=404, detail=f"Note not found: {note_id}")
    
    # BFS to find connected notes
    visited = {note_id}
    current_level = {note_id}
    
    for _ in range(depth):
        next_level = set()
        
        for nid in current_level:
            note = note_lookup.get(nid)
            if not note:
                continue
            
            # Find outgoing links
            body = note.get("body", "")
            links = _extract_links(body)
            
            for link in links:
                if link in note_lookup and link not in visited:
                    next_level.add(link)
                    visited.add(link)
            
            # Find incoming links (notes that link to this one)
            for other_id, other_note in note_lookup.items():
                if other_id in visited:
                    continue
                
                other_links = _extract_links(other_note.get("body", ""))
                if nid in other_links:
                    next_level.add(other_id)
                    visited.add(other_id)
        
        current_level = next_level
    
    # Build subgraph
    nodes = []
    edges = []
    
    for nid in visited:
        note = note_lookup[nid]
        nodes.append({
            "id": note["id"],
            "title": note.get("frontmatter", {}).get("title", note["id"]),
            "type": note.get("frontmatter", {}).get("type", "unknown"),
            "folder": note["folder"],
            "is_center": nid == note_id,
        })
        
        # Add edges
        links = _extract_links(note.get("body", ""))
        for link in links:
            if link in visited:
                edges.append({
                    "source": note["id"],
                    "target": link,
                    "type": "references",
                })
    
    return {
        "center": note_id,
        "depth": depth,
        "nodes": nodes,
        "edges": edges,
    }


@router.get("/stats")
async def get_vault_stats() -> Dict[str, Any]:
    """Get detailed statistics about the SecondBrain vault"""
    if not VAULT_ROOT.exists():
        return {"error": "Vault not found", "path": str(VAULT_ROOT)}
    
    notes = _get_all_notes()
    
    # Calculate stats
    by_type = {}
    by_folder = {}
    by_agent = {}
    by_date = {}
    total_chars = 0
    total_links = 0
    
    for note in notes:
        note_type = note.get("frontmatter", {}).get("type", "unknown")
        folder = note.get("folder", "unknown")
        agent = note.get("frontmatter", {}).get("agent", "unknown")
        created_at = note.get("frontmatter", {}).get("created_at", "")
        if isinstance(created_at, datetime):
            date = created_at.strftime("%Y-%m-%d")
        elif isinstance(created_at, str):
            date = created_at[:10]  # YYYY-MM-DD
        else:
            date = ""
        
        by_type[note_type] = by_type.get(note_type, 0) + 1
        by_folder[folder] = by_folder.get(folder, 0) + 1
        by_agent[agent] = by_agent.get(agent, 0) + 1
        
        if date:
            by_date[date] = by_date.get(date, 0) + 1
        
        total_chars += len(note.get("body", ""))
        total_links += len(_extract_links(note.get("body", "")))
    
    # Recent notes
    notes.sort(key=lambda x: x.get("modified", ""), reverse=True)
    recent = [
        {"id": n["id"], "title": n.get("frontmatter", {}).get("title", n["id"]), "modified": n["modified"]}
        for n in notes[:5]
    ]
    
    return {
        "vault_path": str(VAULT_ROOT),
        "total_notes": len(notes),
        "total_chars": total_chars,
        "total_links": total_links,
        "avg_note_length": total_chars // len(notes) if notes else 0,
        "by_type": by_type,
        "by_folder": by_folder,
        "by_agent": by_agent,
        "by_date": dict(sorted(by_date.items(), reverse=True)[:7]),  # Last 7 days
        "recent_notes": recent,
    }


@router.get("/folders")
async def list_folders() -> Dict[str, Any]:
    """List all folders in the vault"""
    if not VAULT_ROOT.exists():
        return {"folders": [], "error": "Vault not found"}
    
    folders = []
    for folder in VAULT_ROOT.iterdir():
        if folder.is_dir() and not folder.name.startswith("."):
            note_count = len(list(folder.glob("sb_*.md")))
            folders.append({
                "name": folder.name,
                "path": str(folder.relative_to(VAULT_ROOT)),
                "note_count": note_count,
            })
    
    folders.sort(key=lambda x: x["name"])
    
    return {"folders": folders, "total": len(folders)}


@router.get("/search")
async def search_notes(
    q: str,
    folder: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Search notes by content or title.
    Simple text search (not semantic).
    """
    notes = _get_all_notes()
    q_lower = q.lower()
    
    # Filter by folder/type first
    if folder:
        notes = [n for n in notes if n["folder"] == folder]
    if type:
        notes = [n for n in notes if n.get("frontmatter", {}).get("type") == type]
    
    # Search in title and body
    results = []
    for note in notes:
        title = note.get("frontmatter", {}).get("title", "")
        body = note.get("body", "")
        
        title_match = q_lower in title.lower()
        body_match = q_lower in body.lower()
        
        if title_match or body_match:
            # Calculate simple relevance score
            score = 0
            if title_match:
                score += 10
            if body_match:
                score += body.lower().count(q_lower)
            
            results.append({
                "note": {
                    "id": note["id"],
                    "title": title or note["id"],
                    "type": note.get("frontmatter", {}).get("type"),
                    "folder": note["folder"],
                    "body_preview": note["body_preview"],
                },
                "score": score,
                "match_in_title": title_match,
                "match_in_body": body_match,
            })
    
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:limit]
    
    return {
        "query": q,
        "results": results,
        "total": len(results),
    }


@router.get("/search/semantic")
async def semantic_search(
    q: str,
    folder: Optional[str] = None,
    limit: int = 20,
    min_score: float = 0.3,
    tenant_id: str = "default",
) -> Dict[str, Any]:
    """
    Semantic search using embeddings.
    Returns notes ranked by semantic similarity to the query.
    """
    try:
        from core.semantic_search import get_semantic_search_engine
        
        # Get or create semantic search engine for tenant
        search_engine = get_semantic_search_engine(tenant_id)
        
        # Get all notes for semantic indexing
        notes = _get_all_notes()
        
        # Filter by folder if specified
        if folder:
            notes = [n for n in notes if n["folder"] == folder]
        
        # Build the semantic index if it's empty or needs refresh
        if len(search_engine.documents) == 0:
            # Index all notes
            for note in notes:
                content = f"{note.get('frontmatter', {}).get('title', '')} {note.get('body', '')}"
                metadata = {
                    "type": note.get("frontmatter", {}).get("type", "unknown"),
                    "folder": note["folder"],
                    "id": note["id"],
                    "title": note.get("frontmatter", {}).get("title", note["id"])
                }
                search_engine.add_document(content, doc_id=note["id"], metadata=metadata)
        
        # Perform semantic search
        filters = {"folder": folder} if folder else None
        results = search_engine.search(q, top_k=limit, filters=filters, threshold=min_score)
        
        formatted = []
        for result in results:
            # Get original note details
            original_note = next((n for n in notes if n["id"] == result["id"]), None)
            
            formatted.append({
                "note": {
                    "id": result["id"],
                    "title": result["metadata"].get("title", result["id"]),
                    "type": result["metadata"].get("type", "unknown"),
                    "folder": result["metadata"].get("folder", ""),
                    "body_preview": original_note["body_preview"] if original_note else result["content"][:200],
                },
                "similarity": round(result["similarity"], 4),
                "timestamp": result["timestamp"],
            })
        
        return {
            "query": q,
            "results": formatted,
            "total": len(formatted),
            "semantic": True,
            "index_size": len(search_engine.documents),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {e}")


@router.post("/embeddings/reindex")
async def reindex_embeddings() -> Dict[str, Any]:
    """
    Rebuild the semantic search embeddings index.
    Run this after adding many notes or if search quality degrades.
    """
    try:
        from core.secondbrain.embeddings import get_index
        
        index = get_index(VAULT_ROOT)
        index.reindex_vault()
        
        return {
            "success": True,
            "stats": index.get_stats(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reindex failed: {e}")


@router.get("/embeddings/stats")
async def get_embeddings_stats() -> Dict[str, Any]:
    """Get statistics about the embeddings index"""
    try:
        from core.secondbrain.embeddings import get_index
        
        index = get_index(VAULT_ROOT)
        return index.get_stats()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")


def _extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF using pdfplumber"""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except ImportError:
        raise HTTPException(status_code=500, detail="pdfplumber not installed. Run: pip install pdfplumber")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF text: {e}")


def _extract_text_from_docx(file_path: Path) -> str:
    """Extract text from DOCX using python-docx"""
    try:
        from docx import Document
        doc = Document(file_path)
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return "\n\n".join(text_parts)
    except ImportError:
        raise HTTPException(status_code=500, detail="python-docx not installed. Run: pip install python-docx")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract DOCX text: {e}")


def _chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks for note creation.
    Tries to split on paragraph boundaries.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para_size = len(para)
        
        if current_size + para_size > chunk_size and current_chunk:
            # Save current chunk
            chunk_text = "\n\n".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "char_count": len(chunk_text),
            })
            
            # Start new chunk with overlap (keep last paragraph)
            if overlap > 0 and current_chunk:
                last_para = current_chunk[-1]
                if len(last_para) < overlap:
                    current_chunk = [last_para]
                    current_size = len(last_para)
                else:
                    current_chunk = []
                    current_size = 0
            else:
                current_chunk = []
                current_size = 0
        
        current_chunk.append(para)
        current_size += para_size
    
    # Don't forget the last chunk
    if current_chunk:
        chunk_text = "\n\n".join(current_chunk)
        chunks.append({
            "text": chunk_text,
            "char_count": len(chunk_text),
        })
    
    return chunks


def _create_note_file(
    folder: str,
    title: str,
    content: str,
    note_type: str = "document",
    source_file: str = None,
    chunk_index: int = None,
    total_chunks: int = None,
    tags: List[str] = None,
) -> Dict[str, Any]:
    """Create a SecondBrain note file"""
    folder_path = VAULT_ROOT / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # Generate unique note ID
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    content_hash = hashlib.md5(content.encode()).hexdigest()[:6]
    note_id = f"sb_{timestamp}_{content_hash}"
    
    if chunk_index is not None:
        note_id = f"{note_id}_chunk{chunk_index}"
    
    # Build frontmatter
    frontmatter = {
        "id": note_id,
        "type": note_type,
        "title": title,
        "created_at": datetime.utcnow().isoformat(),
        "agent": "system",
    }
    
    if source_file:
        frontmatter["source_file"] = source_file
    
    if chunk_index is not None:
        frontmatter["chunk_index"] = chunk_index
        frontmatter["total_chunks"] = total_chunks
    
    if tags:
        frontmatter["tags"] = tags
    
    # Write note file
    note_path = folder_path / f"{note_id}.md"
    note_content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

{content}
"""
    note_path.write_text(note_content, encoding="utf-8")
    
    return {
        "id": note_id,
        "path": str(note_path.relative_to(VAULT_ROOT)),
        "title": title,
        "char_count": len(content),
    }


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    folder: str = Form(default="documents"),
    chunk_size: int = Form(default=2000),
    tags: str = Form(default=""),
) -> Dict[str, Any]:
    """
    Upload a document (PDF, DOCX, TXT, MD) and create SecondBrain notes.
    
    Large documents are chunked into multiple notes with links between them.
    
    Args:
        file: Document file to upload
        folder: Target folder in SecondBrain (default: documents)
        chunk_size: Max characters per chunk (default: 2000)
        tags: Comma-separated tags to apply to notes
    
    Returns:
        Upload result with created notes
    """
    # Validate file type
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    
    supported_types = {".pdf", ".docx", ".txt", ".md", ".markdown"}
    if ext not in supported_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(supported_types)}"
        )
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    
    try:
        # Extract text based on file type
        if ext == ".pdf":
            text = _extract_text_from_pdf(tmp_path)
        elif ext == ".docx":
            text = _extract_text_from_docx(tmp_path)
        else:  # .txt, .md, .markdown
            text = tmp_path.read_text(encoding="utf-8")
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text content found in document")
        
        # Parse tags
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        tag_list.append("uploaded")
        
        # Chunk text
        chunks = _chunk_text(text, chunk_size=chunk_size)
        
        # Create notes
        created_notes = []
        base_title = Path(filename).stem
        
        if len(chunks) == 1:
            # Single note
            note = _create_note_file(
                folder=folder,
                title=base_title,
                content=chunks[0]["text"],
                note_type="document",
                source_file=filename,
                tags=tag_list,
            )
            created_notes.append(note)
        else:
            # Multiple chunks - create linked notes
            for i, chunk in enumerate(chunks):
                chunk_title = f"{base_title} (Part {i + 1}/{len(chunks)})"
                note = _create_note_file(
                    folder=folder,
                    title=chunk_title,
                    content=chunk["text"],
                    note_type="document",
                    source_file=filename,
                    chunk_index=i + 1,
                    total_chunks=len(chunks),
                    tags=tag_list,
                )
                created_notes.append(note)
        
        return {
            "success": True,
            "filename": filename,
            "total_chars": len(text),
            "chunks": len(chunks),
            "folder": folder,
            "notes": created_notes,
        }
        
    finally:
        # Cleanup temp file
        tmp_path.unlink(missing_ok=True)


@router.post("/notes")
async def create_note(
    title: str = Form(...),
    content: str = Form(...),
    folder: str = Form(default="inbox"),
    note_type: str = Form(default="note"),
    tags: str = Form(default=""),
) -> Dict[str, Any]:
    """
    Create a new SecondBrain note manually.
    
    Args:
        title: Note title
        content: Note content (markdown)
        folder: Target folder (default: inbox)
        note_type: Note type (note, decision, task, etc.)
        tags: Comma-separated tags
    
    Returns:
        Created note info
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    
    note = _create_note_file(
        folder=folder,
        title=title,
        content=content,
        note_type=note_type,
        tags=tag_list,
    )
    
    return {
        "success": True,
        "note": note,
    }


@router.get("/search/hybrid")
async def hybrid_search(
    q: str,
    folder: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 20,
    min_score: float = 0.3,
    keyword_weight: float = 0.3,
    semantic_weight: float = 0.7,
    tenant_id: str = "default",
) -> Dict[str, Any]:
    """
    Hybrid search combining keyword and semantic search.
    Uses both traditional text matching and semantic similarity.
    """
    try:
        from core.semantic_search import get_semantic_search_engine
        
        # Get semantic search engine
        search_engine = get_semantic_search_engine(tenant_id)
        
        # Get all notes
        notes = _get_all_notes()
        
        # Apply initial filters
        filtered_notes = notes
        if folder:
            filtered_notes = [n for n in filtered_notes if n["folder"] == folder]
        if type:
            filtered_notes = [n for n in filtered_notes if n.get("frontmatter", {}).get("type") == type]
        
        # Build semantic index if needed
        if len(search_engine.documents) == 0:
            for note in filtered_notes:
                content = f"{note.get('frontmatter', {}).get('title', '')} {note.get('body', '')}"
                metadata = {
                    "type": note.get("frontmatter", {}).get("type", "unknown"),
                    "folder": note["folder"],
                    "id": note["id"],
                    "title": note.get("frontmatter", {}).get("title", note["id"])
                }
                search_engine.add_document(content, doc_id=note["id"], metadata=metadata)
        
        # Perform keyword search first
        q_lower = q.lower()
        keyword_results = []
        for note in filtered_notes:
            title = note.get("frontmatter", {}).get("title", "")
            body = note.get("body", "")
            
            title_match = q_lower in title.lower()
            body_match = q_lower in body.lower()
            
            if title_match or body_match:
                # Calculate simple relevance score
                score = 0
                if title_match:
                    score += 10
                if body_match:
                    score += body.lower().count(q_lower)
                
                keyword_results.append({
                    "note": {
                        "id": note["id"],
                        "title": title or note["id"],
                        "type": note.get("frontmatter", {}).get("type"),
                        "folder": note["folder"],
                        "body_preview": note["body_preview"],
                    },
                    "score": score,
                    "match_in_title": title_match,
                    "match_in_body": body_match,
                })
        
        # Sort keyword results by score
        keyword_results.sort(key=lambda x: x["score"], reverse=True)
        keyword_results = keyword_results[:limit]
        
        # Get keyword-only scores for hybrid combination
        keyword_only_results = []
        for kr in keyword_results:
            keyword_only_results.append({
                "id": kr["note"]["id"],
                "content": f"{kr['note']['title']} {kr['note']['body_preview']}",
                "metadata": {
                    "type": kr["note"]["type"],
                    "folder": kr["note"]["folder"],
                    "title": kr["note"]["title"]
                },
                "score": kr["score"] / 100.0  # Normalize for combination
            })
        
        # Perform semantic search
        filters = {"folder": folder} if folder else None
        semantic_results = search_engine.search(q, top_k=limit, filters=filters, threshold=min_score)
        
        # Combine results using hybrid search
        combined_results = search_engine.hybrid_search(
            q, keyword_only_results, top_k=limit, 
            keyword_weight=keyword_weight, semantic_weight=semantic_weight
        )
        
        # Format results
        formatted = []
        for result in combined_results:
            # Get original note details
            original_note = next((n for n in notes if n["id"] == result["id"]), None)
            
            formatted.append({
                "note": {
                    "id": result["id"],
                    "title": result["metadata"].get("title", result["id"]),
                    "type": result["metadata"].get("type", "unknown"),
                    "folder": result["metadata"].get("folder", ""),
                    "body_preview": original_note["body_preview"] if original_note else result.get("content", "")[:200],
                },
                "combined_score": round(result["combined_score"], 4),
                "keyword_score": round(result["keyword_score"], 4),
                "semantic_score": round(result["semantic_score"], 4),
                "similarity": round(result.get("semantic_score", 0), 4),
            })
        
        return {
            "query": q,
            "results": formatted,
            "total": len(formatted),
            "hybrid": True,
            "keyword_results_count": len(keyword_results),
            "semantic_results_count": len(semantic_results),
            "index_size": len(search_engine.documents),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {e}")