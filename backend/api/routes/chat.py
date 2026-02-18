"""
Chat API Routes
Handles conversation with Galidima (Manager Agent) including file attachments
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import json
import os
import base64
from pathlib import Path

router = APIRouter(prefix="/api/chat", tags=["chat"])

# In-memory storage (would be DB in production)
_conversations: Dict[str, Dict[str, Any]] = {}
_messages: Dict[str, List[Dict[str, Any]]] = {}
_uploads_dir = Path(__file__).parent.parent.parent / "data" / "chat_uploads"
_uploads_dir.mkdir(parents=True, exist_ok=True)
_manager_instance: Optional[Any] = None


def _get_manager():
    global _manager_instance
    if _manager_instance is None:
        from ...agents import ManagerAgent
        _manager_instance = ManagerAgent()
    return _manager_instance


# ==================== MODELS ====================

class SendMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    attachments: Optional[List[str]] = None  # List of file IDs from upload


class ForkRequest(BaseModel):
    source_conversation_id: str
    from_message_id: str
    new_conversation_name: Optional[str] = None


class ConversationInfo(BaseModel):
    id: str
    name: str
    created_at: str
    message_count: int
    last_message: Optional[str] = None
    parent_id: Optional[str] = None
    is_branch: bool = False


# ==================== HELPER FUNCTIONS ====================

def get_or_create_conversation(conversation_id: Optional[str] = None) -> str:
    """Get existing conversation or create a new one"""
    if conversation_id and conversation_id in _conversations:
        return conversation_id
    
    # Create new conversation
    new_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    _conversations[new_id] = {
        "id": new_id,
        "name": f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "created_at": datetime.now().isoformat(),
        "parent_id": None,
        "is_branch": False,
    }
    _messages[new_id] = []
    return new_id


def add_message(conversation_id: str, role: str, content: str, attachments: List[Dict] = None, reasoning_log: List[str] = None) -> Dict[str, Any]:
    """Add a message to a conversation"""
    if conversation_id not in _messages:
        _messages[conversation_id] = []
    
    message = {
        "id": f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "attachments": attachments or [],
        "reasoning_log": reasoning_log,
    }
    
    _messages[conversation_id].append(message)
    return message


# ==================== FILE UPLOAD ====================

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
):
    """
    Upload a file for chat attachment.
    Returns a file_id that can be used when sending a message.
    
    Supported types: images, PDFs, text files, documents
    Max size: 10MB
    """
    # Validate file size (10MB max)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    
    # Get file info
    filename = file.filename or "unnamed"
    content_type = file.content_type or "application/octet-stream"
    
    # Determine file type
    ext = Path(filename).suffix.lower()
    allowed_extensions = {
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg',
        # Documents
        '.pdf', '.doc', '.docx', '.txt', '.md', '.rtf',
        # Data
        '.json', '.csv', '.xml', '.yaml', '.yml',
        # Code
        '.py', '.js', '.ts', '.html', '.css',
    }
    
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Generate file ID and save
    file_id = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = _uploads_dir / file_id
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    # Create metadata
    metadata = {
        "id": file_id,
        "original_name": filename,
        "content_type": content_type,
        "size": len(content),
        "uploaded_at": datetime.now().isoformat(),
        "path": str(file_path),
    }
    
    # For images, include base64 preview
    if ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}:
        metadata["preview"] = f"data:{content_type};base64,{base64.b64encode(content).decode()}"
    
    # Save metadata
    meta_path = _uploads_dir / f"{file_id}.meta.json"
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return {
        "file_id": file_id,
        "filename": filename,
        "content_type": content_type,
        "size": len(content),
        "preview": metadata.get("preview"),
    }


@router.get("/uploads/{file_id}")
async def get_upload(file_id: str):
    """Get uploaded file metadata"""
    meta_path = _uploads_dir / f"{file_id}.meta.json"
    
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    with open(meta_path) as f:
        return json.load(f)


@router.delete("/uploads/{file_id}")
async def delete_upload(file_id: str):
    """Delete an uploaded file"""
    file_path = _uploads_dir / file_id
    meta_path = _uploads_dir / f"{file_id}.meta.json"
    
    deleted = False
    if file_path.exists():
        os.remove(file_path)
        deleted = True
    if meta_path.exists():
        os.remove(meta_path)
        deleted = True
    
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {"deleted": True, "file_id": file_id}


# ==================== SEND MESSAGE ====================

@router.post("/send")
async def send_message(request: SendMessageRequest):
    """
    Send a message to Galidima (Manager Agent).
    Optionally include file attachments by their file_ids.
    """
    conversation_id = get_or_create_conversation(request.conversation_id)
    
    # Process attachments
    attachments = []
    attachment_context = ""
    
    if request.attachments:
        for file_id in request.attachments:
            meta_path = _uploads_dir / f"{file_id}.meta.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                    attachments.append({
                        "id": file_id,
                        "name": meta["original_name"],
                        "type": meta["content_type"],
                        "size": meta["size"],
                    })
                    
                    # Add file content to context for text files
                    ext = Path(meta["original_name"]).suffix.lower()
                    if ext in {'.txt', '.md', '.json', '.csv', '.py', '.js', '.yaml', '.yml'}:
                        file_path = _uploads_dir / file_id
                        if file_path.exists():
                            try:
                                with open(file_path, 'r', encoding='utf-8') as file:
                                    file_content = file.read()
                                    # Truncate very large files
                                    if len(file_content) > 10000:
                                        file_content = file_content[:10000] + "\n... (truncated)"
                                    attachment_context += f"\n\n[Attached file: {meta['original_name']}]\n```\n{file_content}\n```\n"
                            except Exception as e:
                                attachment_context += f"\n\n[Attached file: {meta['original_name']} - could not read: {e}]\n"
                    elif ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp'}:
                        attachment_context += f"\n\n[Attached image: {meta['original_name']}]\n"
                    else:
                        attachment_context += f"\n\n[Attached file: {meta['original_name']} ({meta['content_type']})]\n"
    
    # Build full message with attachment context
    full_message = request.message
    if attachment_context:
        full_message = request.message + attachment_context
    
    # Add user message
    user_msg = add_message(
        conversation_id, 
        "user", 
        request.message,  # Store original message
        attachments=attachments
    )
    
    # Get response from Manager
    reasoning_log = []
    
    try:
        manager = _get_manager()
        
        # Build reasoning log
        reasoning_log.append(f"Received message in conversation {conversation_id[:20]}...")
        
        if attachments:
            reasoning_log.append(f"Processing {len(attachments)} attachment(s)")
            for att in attachments:
                reasoning_log.append(f"   - {att['name']} ({att['type']})")
        
        # Check for team routing
        routing = manager.get_team_for_request(full_message)
        if routing:
            reasoning_log.append(f"Detected complex request - suggesting team: {routing}")
        else:
            # Simple routing
            route_to = manager.route_to_appropriate_agent(full_message)
            if route_to:
                reasoning_log.append(f"Routing to agent: {route_to}")
            else:
                reasoning_log.append("Handling directly")
        
        reasoning_log.append("Generating response...")
        
        # Get AI response
        response = await manager.chat(full_message)
        
        reasoning_log.append("Response generated")
        
    except Exception as e:
        response = f"Sorry, I encountered an error: {str(e)}"
        reasoning_log.append(f"Error: {str(e)}")

    try:
        from core.response_formatting import normalize_agent_response
        response = normalize_agent_response("manager", response)
    except Exception:
        pass
    
    # Add assistant message
    assistant_msg = add_message(
        conversation_id,
        "assistant",
        response,
        reasoning_log=reasoning_log
    )
    
    return {
        "conversation_id": conversation_id,
        "message_id": assistant_msg["id"],
        "response": response,
        "reasoning_log": reasoning_log,
        "attachments_processed": len(attachments),
    }


# ==================== CONVERSATION MANAGEMENT ====================

@router.get("/history")
async def get_history(conversation_id: Optional[str] = None):
    """Get chat history for current or specified conversation"""
    if conversation_id:
        if conversation_id not in _conversations:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conv_id = conversation_id
    else:
        # Get most recent conversation
        if not _conversations:
            return {"messages": [], "conversation_id": None}
        conv_id = max(_conversations.keys(), key=lambda k: _conversations[k]["created_at"])
    
    return {
        "conversation_id": conv_id,
        "conversation": _conversations.get(conv_id),
        "messages": _messages.get(conv_id, []),
    }


@router.post("/clear")
async def clear_history(conversation_id: Optional[str] = None):
    """Clear chat history for current or specified conversation"""
    if conversation_id:
        if conversation_id in _messages:
            _messages[conversation_id] = []
        if conversation_id in _conversations:
            del _conversations[conversation_id]
        return {"cleared": True, "conversation_id": conversation_id}
    else:
        # Clear all
        _conversations.clear()
        _messages.clear()
        return {"cleared": True, "all": True}


@router.get("/conversations")
async def list_conversations():
    """List all conversations"""
    conversations = []
    for conv_id, conv in _conversations.items():
        msgs = _messages.get(conv_id, [])
        conversations.append({
            "id": conv_id,
            "name": conv["name"],
            "created_at": conv["created_at"],
            "message_count": len(msgs),
            "last_message": msgs[-1]["content"][:100] if msgs else None,
            "is_branch": conv.get("is_branch", False),
            "parent_id": conv.get("parent_id"),
        })
    
    # Sort by created_at descending
    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {"conversations": conversations}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    del _conversations[conversation_id]
    if conversation_id in _messages:
        del _messages[conversation_id]
    
    return {"deleted": True, "conversation_id": conversation_id}


# ==================== BRANCHING ====================

@router.post("/fork")
async def fork_conversation(request: ForkRequest):
    """Create a branch from an existing conversation at a specific message"""
    if request.source_conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="Source conversation not found")
    
    source_msgs = _messages.get(request.source_conversation_id, [])
    
    # Find the message index
    msg_idx = None
    for i, msg in enumerate(source_msgs):
        if msg["id"] == request.from_message_id:
            msg_idx = i
            break
    
    if msg_idx is None:
        raise HTTPException(status_code=404, detail="Message not found in conversation")
    
    # Create new branch
    branch_id = f"branch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    branch_name = request.new_conversation_name or f"Branch from {_conversations[request.source_conversation_id]['name']}"
    
    _conversations[branch_id] = {
        "id": branch_id,
        "name": branch_name,
        "created_at": datetime.now().isoformat(),
        "parent_id": request.source_conversation_id,
        "from_message_id": request.from_message_id,
        "is_branch": True,
    }
    
    # Copy messages up to and including the fork point
    _messages[branch_id] = [msg.copy() for msg in source_msgs[:msg_idx + 1]]
    
    return {
        "branch_id": branch_id,
        "name": branch_name,
        "message_count": len(_messages[branch_id]),
        "parent_id": request.source_conversation_id,
    }


@router.get("/branches/{conversation_id}")
async def get_branches(conversation_id: str):
    """Get branch information for a conversation"""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv = _conversations[conversation_id]
    
    # Find children (branches from this conversation)
    children = []
    for cid, c in _conversations.items():
        if c.get("parent_id") == conversation_id:
            children.append({
                "conversation_id": cid,
                "from_message_id": c.get("from_message_id"),
                "created_at": c["created_at"],
                "name": c["name"],
            })
    
    # Get parent info if this is a branch
    parent = None
    if conv.get("parent_id"):
        parent_conv = _conversations.get(conv["parent_id"])
        if parent_conv:
            parent = {
                "parent": conv["parent_id"],
                "from_message_id": conv.get("from_message_id"),
                "created_at": conv["created_at"],
            }
    
    return {
        "conversation_id": conversation_id,
        "parent": parent,
        "children": children,
    }
