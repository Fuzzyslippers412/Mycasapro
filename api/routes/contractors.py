"""
Contractors API - CRUD for contractors and jobs.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth.dependencies import require_auth
from database.connection import get_db
from database.models import Contractor, ContractorJob

router = APIRouter(prefix="/contractors", tags=["Contractors"])


class ContractorPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    service_type: Optional[str] = None
    hourly_rate: Optional[float] = None
    rating: Optional[int] = None
    notes: Optional[str] = None
    last_service_date: Optional[date] = None


class ContractorUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    service_type: Optional[str] = None
    hourly_rate: Optional[float] = None
    rating: Optional[int] = None
    notes: Optional[str] = None
    last_service_date: Optional[date] = None


class JobPayload(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    contractor_id: Optional[int] = None
    contractor_name: Optional[str] = None
    estimated_cost: Optional[float] = None
    proposed_start: Optional[date] = None
    confirmed_start: Optional[date] = None


def _contractor_dict(item: Contractor) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "company": item.company,
        "phone": item.phone,
        "email": item.email,
        "service_type": item.service_type,
        "hourly_rate": item.hourly_rate,
        "rating": item.rating,
        "notes": item.notes,
        "last_service_date": item.last_service_date.isoformat() if item.last_service_date else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def _job_dict(job: ContractorJob) -> dict:
    return {
        "id": job.id,
        "description": job.description,
        "contractor_id": job.contractor_id,
        "contractor_name": job.contractor_name,
        "status": job.status,
        "estimated_cost": job.estimated_cost,
        "actual_cost": job.actual_cost,
        "proposed_start": job.proposed_start.isoformat() if job.proposed_start else None,
        "confirmed_start": job.confirmed_start.isoformat() if job.confirmed_start else None,
        "actual_start": job.actual_start.isoformat() if job.actual_start else None,
        "actual_end": job.actual_end.isoformat() if job.actual_end else None,
    }


@router.get("", dependencies=[Depends(require_auth)])
def list_contractors(limit: int = 100, db: Session = Depends(get_db)):
    items = (
        db.query(Contractor)
        .order_by(Contractor.updated_at.desc())
        .limit(limit)
        .all()
    )
    return {"contractors": [_contractor_dict(c) for c in items]}


@router.post("", dependencies=[Depends(require_auth)])
def create_contractor(payload: ContractorPayload, db: Session = Depends(get_db)):
    contractor = Contractor(
        name=payload.name.strip(),
        company=payload.company,
        phone=payload.phone,
        email=payload.email,
        service_type=payload.service_type or "General",
        hourly_rate=payload.hourly_rate,
        rating=payload.rating,
        notes=payload.notes,
        last_service_date=payload.last_service_date,
    )
    db.add(contractor)
    db.commit()
    db.refresh(contractor)
    return _contractor_dict(contractor)


@router.patch("/{contractor_id}", dependencies=[Depends(require_auth)])
def update_contractor(contractor_id: int, payload: ContractorUpdate, db: Session = Depends(get_db)):
    contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")
    update_dict = payload.model_dump(exclude_none=True)
    for key, value in update_dict.items():
        if hasattr(contractor, key):
            setattr(contractor, key, value)
    db.add(contractor)
    db.commit()
    db.refresh(contractor)
    return _contractor_dict(contractor)


@router.delete("/{contractor_id}", dependencies=[Depends(require_auth)])
def delete_contractor(contractor_id: int, db: Session = Depends(get_db)):
    contractor = db.query(Contractor).filter(Contractor.id == contractor_id).first()
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")
    db.delete(contractor)
    db.commit()
    return {"success": True}


@router.get("/jobs", dependencies=[Depends(require_auth)])
def list_jobs(limit: int = 50, db: Session = Depends(get_db)):
    items = (
        db.query(ContractorJob)
        .order_by(ContractorJob.id.desc())
        .limit(limit)
        .all()
    )
    return {"jobs": [_job_dict(j) for j in items]}


@router.post("/jobs", dependencies=[Depends(require_auth)])
def create_job(payload: JobPayload, db: Session = Depends(get_db)):
    contractor_name = payload.contractor_name
    if payload.contractor_id:
        contractor = db.query(Contractor).filter(Contractor.id == payload.contractor_id).first()
        if contractor:
            contractor_name = contractor.name

    job = ContractorJob(
        description=payload.description.strip(),
        contractor_id=payload.contractor_id,
        contractor_name=contractor_name,
        estimated_cost=payload.estimated_cost,
        proposed_start=payload.proposed_start,
        confirmed_start=payload.confirmed_start,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_dict(job)


@router.patch("/jobs/{job_id}/complete", dependencies=[Depends(require_auth)])
def complete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ContractorJob).filter(ContractorJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "completed"
    job.actual_end = date.today()
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_dict(job)
