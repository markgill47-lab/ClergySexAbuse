"""Clergy CRUD and search endpoints — agent-first design."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session, joinedload

from src.backend.database import get_session, get_engine
from src.backend.models import (
    AccusedClergy,
    Allegation,
    Assignment,
    ChurchAction,
    CriminalOutcome,
    DioceseAssociation,
    Document,
    SourceRecord,
)

router = APIRouter()


def get_db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


# --- Response models ---

class ClergyBrief(BaseModel):
    id: int
    first_name: str
    last_name: str
    suffix: Optional[str] = None
    ordination_year: Optional[int] = None
    deceased: bool = False
    status: Optional[str] = None
    religious_order: Optional[str] = None
    primary_diocese: Optional[str] = None
    primary_state: Optional[str] = None
    source_count: int = 0
    document_count: int = 0

    model_config = {"from_attributes": True}


class ClergyFull(BaseModel):
    id: int
    first_name: str
    last_name: str
    suffix: Optional[str] = None
    ordination_year: Optional[int] = None
    ordination_decade: Optional[str] = None
    death_year: Optional[int] = None
    deceased: bool = False
    status: Optional[str] = None
    religious_order: Optional[str] = None
    photo_url: Optional[str] = None
    narrative: Optional[str] = None
    dioceses: list[dict] = []
    assignments: list[dict] = []
    allegations: list[dict] = []
    criminal_outcomes: list[dict] = []
    church_actions: list[dict] = []
    sources: list[dict] = []
    documents: list[dict] = []

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    diocese: Optional[str] = None
    status: Optional[str] = None
    religious_order: Optional[str] = None
    ordination_decade: Optional[str] = None
    has_documents: Optional[bool] = None
    source: Optional[str] = None
    allegation_type: Optional[str] = None
    limit: int = 50
    offset: int = 0


# --- Endpoints ---

@router.get("", response_model=list[ClergyBrief])
async def list_clergy(
    state: Optional[str] = None,
    diocese: Optional[str] = None,
    status: Optional[str] = None,
    religious_order: Optional[str] = None,
    has_documents: Optional[bool] = None,
    source: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List clergy with filters. Agent-friendly: supports rich filtering."""
    query = db.query(AccusedClergy)

    if state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())
    if diocese:
        query = query.join(DioceseAssociation).filter(
            DioceseAssociation.diocese_name.ilike(f"%{diocese}%")
        )
    if status:
        query = query.filter(AccusedClergy.status == status)
    if religious_order:
        query = query.filter(AccusedClergy.religious_order.ilike(f"%{religious_order}%"))
    if has_documents:
        query = query.filter(AccusedClergy.documents.any())
    if source:
        query = query.join(SourceRecord).filter(SourceRecord.source_name == source)

    total = query.count()
    results = query.order_by(AccusedClergy.last_name, AccusedClergy.first_name).offset(offset).limit(limit).all()

    briefs = []
    for c in results:
        primary = next((d for d in c.diocese_associations if d.is_primary), None)
        briefs.append(ClergyBrief(
            id=c.id,
            first_name=c.first_name,
            last_name=c.last_name,
            suffix=c.suffix,
            ordination_year=c.ordination_year,
            deceased=c.deceased,
            status=c.status,
            religious_order=c.religious_order,
            primary_diocese=primary.diocese_name if primary else None,
            primary_state=primary.state if primary else None,
            source_count=len(c.source_records),
            document_count=len(c.documents),
        ))

    return briefs


@router.get("/{clergy_id}/full", response_model=ClergyFull)
async def get_clergy_full(clergy_id: int, db: Session = Depends(get_db)):
    """Get complete clergy record with all related data in one call.

    This is the primary endpoint for agent consumption — returns everything
    needed to analyze an individual in a single request.
    """
    c = (
        db.query(AccusedClergy)
        .options(
            joinedload(AccusedClergy.diocese_associations),
            joinedload(AccusedClergy.assignments),
            joinedload(AccusedClergy.allegations),
            joinedload(AccusedClergy.criminal_outcomes),
            joinedload(AccusedClergy.church_actions),
            joinedload(AccusedClergy.source_records),
            joinedload(AccusedClergy.documents),
        )
        .filter(AccusedClergy.id == clergy_id)
        .first()
    )

    if not c:
        raise HTTPException(status_code=404, detail="Clergy not found")

    return ClergyFull(
        id=c.id,
        first_name=c.first_name,
        last_name=c.last_name,
        suffix=c.suffix,
        ordination_year=c.ordination_year,
        ordination_decade=c.ordination_decade,
        death_year=c.death_year,
        deceased=c.deceased,
        status=c.status,
        religious_order=c.religious_order,
        photo_url=c.photo_url,
        narrative=c.narrative,
        dioceses=[
            {"diocese_name": d.diocese_name, "state": d.state, "is_primary": d.is_primary}
            for d in c.diocese_associations
        ],
        assignments=[
            {
                "institution_name": a.institution_name,
                "institution_type": a.institution_type,
                "city": a.city,
                "state": a.state,
                "start_year": a.start_year,
                "end_year": a.end_year,
                "role": a.role,
            }
            for a in c.assignments
        ],
        allegations=[
            {
                "year": a.year,
                "decade": a.decade,
                "victim_gender": a.victim_gender,
                "victim_minor": a.victim_minor,
                "allegation_type": a.allegation_type,
                "substantiated": a.substantiated,
                "summary": a.summary,
            }
            for a in c.allegations
        ],
        criminal_outcomes=[
            {"outcome_type": o.outcome_type, "year": o.year, "details": o.details}
            for o in c.criminal_outcomes
        ],
        church_actions=[
            {"action_type": a.action_type, "year": a.year}
            for a in c.church_actions
        ],
        sources=[
            {"source_name": s.source_name, "source_url": s.source_url, "scraped_at": str(s.scraped_at)}
            for s in c.source_records
        ],
        documents=[
            {
                "id": d.id,
                "doc_type": d.doc_type,
                "title": d.title,
                "url": d.url,
                "local_path": d.local_path,
            }
            for d in c.documents
        ],
    )


@router.post("/search")
async def search_clergy(req: SearchRequest, db: Session = Depends(get_db)):
    """Complex multi-field search. Agent-friendly: accepts structured filter object."""
    query = db.query(AccusedClergy)

    if req.name:
        pattern = f"%{req.name}%"
        query = query.filter(
            or_(
                AccusedClergy.first_name.ilike(pattern),
                AccusedClergy.last_name.ilike(pattern),
            )
        )
    if req.state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == req.state.upper())
    if req.diocese:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.diocese_name.ilike(f"%{req.diocese}%"))
    if req.status:
        query = query.filter(AccusedClergy.status == req.status)
    if req.religious_order:
        query = query.filter(AccusedClergy.religious_order.ilike(f"%{req.religious_order}%"))
    if req.ordination_decade:
        query = query.filter(AccusedClergy.ordination_decade == req.ordination_decade)
    if req.has_documents:
        query = query.filter(AccusedClergy.documents.any())
    if req.source:
        query = query.join(SourceRecord).filter(SourceRecord.source_name == req.source)
    if req.allegation_type:
        query = query.join(Allegation).filter(Allegation.allegation_type == req.allegation_type)

    total = query.count()
    results = query.order_by(AccusedClergy.last_name).offset(req.offset).limit(req.limit).all()

    return {
        "total": total,
        "offset": req.offset,
        "limit": req.limit,
        "results": [
            {
                "id": c.id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "status": c.status,
                "ordination_year": c.ordination_year,
                "deceased": c.deceased,
            }
            for c in results
        ],
    }
