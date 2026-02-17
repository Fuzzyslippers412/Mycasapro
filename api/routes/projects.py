"""
Projects API - CRUD for home projects.
"""
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth.dependencies import require_auth
from database import get_db
from database.models import Project

router = APIRouter(prefix="/projects", tags=["Projects"])


class ProjectPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = Field(default="planning")
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    budget: Optional[float] = None
    spent: Optional[float] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    budget: Optional[float] = None
    spent: Optional[float] = None
    notes: Optional[str] = None


def _to_dict(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "category": project.category,
        "status": project.status,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "target_end_date": project.target_end_date.isoformat() if project.target_end_date else None,
        "actual_end_date": project.actual_end_date.isoformat() if project.actual_end_date else None,
        "budget": project.budget,
        "spent": project.spent,
        "notes": project.notes,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


@router.get("", dependencies=[Depends(require_auth)])
def list_projects(limit: int = 50, db: Session = Depends(get_db)):
    items = (
        db.query(Project)
        .order_by(Project.updated_at.desc())
        .limit(limit)
        .all()
    )
    return {"projects": [_to_dict(p) for p in items]}


@router.post("", dependencies=[Depends(require_auth)])
def create_project(payload: ProjectPayload, db: Session = Depends(get_db)):
    project = Project(
        name=payload.name.strip(),
        description=payload.description,
        category=payload.category,
        status=payload.status or "planning",
        start_date=payload.start_date,
        target_end_date=payload.target_end_date,
        budget=payload.budget,
        spent=payload.spent or 0,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_dict(project)


@router.get("/{project_id}", dependencies=[Depends(require_auth)])
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _to_dict(project)


@router.patch("/{project_id}", dependencies=[Depends(require_auth)])
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    update_dict = payload.model_dump(exclude_none=True)
    for key, value in update_dict.items():
        if hasattr(project, key):
            setattr(project, key, value)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_dict(project)


@router.delete("/{project_id}", dependencies=[Depends(require_auth)])
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"success": True}
