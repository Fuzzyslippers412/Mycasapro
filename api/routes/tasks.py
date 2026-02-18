"""
MyCasa Pro API - Tasks Routes
Maintenance tasks and to-do management endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from enum import Enum
from api.helpers.auth import require_auth

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ============ SCHEMAS ============

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskCategory(str, Enum):
    MAINTENANCE = "maintenance"
    FINANCE = "finance"
    CONTRACTORS = "contractors"
    PROJECTS = "projects"
    GENERAL = "general"

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: TaskCategory = TaskCategory.MAINTENANCE
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[date] = None
    assigned_to: Optional[str] = None
    estimated_duration_hours: Optional[float] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[TaskCategory] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[date] = None
    assigned_to: Optional[str] = None
    status: Optional[TaskStatus] = None
    estimated_duration_hours: Optional[float] = None

class TaskComplete(BaseModel):
    completion_notes: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: TaskCategory
    priority: TaskPriority
    status: TaskStatus
    due_date: Optional[date]
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int = 1
    limit: int = 50


# ============ ROUTES ============

@router.get("")
async def list_tasks(
    user: dict = Depends(require_auth),
    category: Optional[TaskCategory] = None,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    assigned_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List maintenance tasks with optional filters"""
    from api.main import get_manager
    from core.events_v2 import emit_sync, EventType
    
    manager = get_manager()
    maintenance = manager.maintenance
    
    if not maintenance:
        raise HTTPException(status_code=503, detail="Maintenance agent not available")
    
    # Apply filters
    filters = {}
    if category:
        filters['category'] = category.value
    if status:
        filters['status'] = status.value
    if priority:
        filters['priority'] = priority.value
    if assigned_to:
        filters['assigned_to'] = assigned_to
    
    tasks = maintenance.list_tasks(filters=filters, limit=limit, offset=offset)
    
    # Emit event
    emit_sync(EventType.TASK_LIST_VIEWED, {
        "user_id": user.get("id"),
        "filters": filters,
        "count": len(tasks)
    })
    
    return TaskListResponse(
        tasks=tasks[:limit],
        total=len(tasks),
        page=(offset // limit) + 1,
        limit=limit
    )


@router.post("")
async def create_task(
    task: TaskCreate,
    user: dict = Depends(require_auth),
    background_tasks: BackgroundTasks = None
):
    """Create a new maintenance task"""
    from api.main import get_manager
    from core.events_v2 import emit_sync, EventType
    
    manager = get_manager()
    maintenance = manager.maintenance
    
    if not maintenance:
        raise HTTPException(status_code=503, detail="Maintenance agent not available")
    
    result = maintenance.add_task(
        title=task.title,
        description=task.description,
        category=task.category,
        priority=task.priority,
        due_date=task.due_date,
        assigned_to=task.assigned_to,
        estimated_duration_hours=task.estimated_duration_hours
    )
    
    # Emit event
    emit_sync(EventType.TASK_CREATED, {
        "user_id": user.get("id"),
        "task_id": result.get("id") if isinstance(result, dict) else getattr(result, 'id', None),
        "title": task.title,
        "category": task.category
    })
    
    return result


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    user: dict = Depends(require_auth)
):
    """Get a specific task by ID"""
    from api.main import get_manager
    from core.events_v2 import emit_sync, EventType
    
    manager = get_manager()
    maintenance = manager.maintenance
    
    if not maintenance:
        raise HTTPException(status_code=503, detail="Maintenance agent not available")
    
    task = maintenance.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Emit event
    emit_sync(EventType.TASK_VIEWED, {
        "user_id": user.get("id"),
        "task_id": task_id
    })
    
    return task


@router.patch("/{task_id}")
async def update_task(
    task_id: int,
    update: TaskUpdate,
    user: dict = Depends(require_auth)
):
    """Update a task"""
    from api.main import get_manager
    from core.events_v2 import emit_sync, EventType
    
    manager = get_manager()
    maintenance = manager.maintenance
    
    if not maintenance:
        raise HTTPException(status_code=503, detail="Maintenance agent not available")
    
    result = maintenance.update_task(
        task_id=task_id,
        title=update.title,
        description=update.description,
        category=update.category,
        priority=update.priority,
        due_date=update.due_date,
        assigned_to=update.assigned_to,
        status=update.status,
        estimated_duration_hours=update.estimated_duration_hours
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Emit event
    emit_sync(EventType.TASK_UPDATED, {
        "user_id": user.get("id"),
        "task_id": task_id,
        "updates": update.dict(exclude_unset=True)
    })
    
    return result


@router.patch("/{task_id}/complete")
async def complete_task(
    task_id: int,
    body: TaskComplete = None,
    user: dict = Depends(require_auth),
    background_tasks: BackgroundTasks = None
):
    """Mark a task as complete"""
    from api.main import get_manager
    from core.events_v2 import emit_sync, EventType
    
    manager = get_manager()
    maintenance = manager.maintenance
    
    if not maintenance:
        raise HTTPException(status_code=503, detail="Maintenance agent not available")
    
    result = maintenance.complete_task(
        task_id=task_id,
        completion_notes=body.completion_notes if body else None
    )
    if not result or result.get("error"):
        raise HTTPException(status_code=404, detail=result.get("error", "Task not found"))
    
    # Emit event
    emit_sync(EventType.TASK_COMPLETED, {
        "user_id": user.get("id"),
        "task_id": task_id,
        "completion_notes": body.completion_notes if body else None
    })

    # Notify originating chat session if available
    try:
        from core.chat_store import add_message
        from database.models import ChatConversation
        from database import get_db

        conversation_id = result.get("conversation_id")
        if conversation_id:
            with get_db() as db:
                convo = (
                    db.query(ChatConversation)
                    .filter(ChatConversation.id == conversation_id, ChatConversation.user_id == user.get("id"))
                    .first()
                )
                if convo:
                    title = result.get("title") or f"Task #{task_id}"
                    add_message(db, convo, "assistant", f"Task \"{title}\" marked complete.")
    except Exception:
        pass
    
    return result


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    user: dict = Depends(require_auth)
):
    """Delete a task"""
    from api.main import get_manager
    from core.events_v2 import emit_sync, EventType
    
    manager = get_manager()
    maintenance = manager.maintenance
    
    if not maintenance:
        raise HTTPException(status_code=503, detail="Maintenance agent not available")
    
    result = maintenance.remove_task(task_id)
    if not result or result.get("error"):
        raise HTTPException(status_code=404, detail=result.get("error", "Task not found"))
    
    # Emit event
    emit_sync(EventType.TASK_DELETED, {
        "user_id": user.get("id"),
        "task_id": task_id
    })

    # Notify originating chat session if available
    try:
        from core.chat_store import add_message
        from database.models import ChatConversation
        from database import get_db

        task_payload = result.get("task") or {}
        conversation_id = task_payload.get("conversation_id")
        if conversation_id:
            with get_db() as db:
                convo = (
                    db.query(ChatConversation)
                    .filter(ChatConversation.id == conversation_id, ChatConversation.user_id == user.get("id"))
                    .first()
                )
                if convo:
                    title = task_payload.get("title") or f"Task #{task_id}"
                    add_message(db, convo, "assistant", f"Task \"{title}\" removed.")
    except Exception:
        pass
    
    return {"success": True, "message": "Task deleted successfully"}
