"""Analytics and aggregation endpoints — designed for agent consumption."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case, distinct
from sqlalchemy.orm import Session

from src.backend.database import get_session
from src.backend.models import (
    AccusedClergy,
    Allegation,
    ChurchAction,
    CriminalOutcome,
    DioceseAssociation,
    Document,
    SourceRecord,
    StateSummary,
)

router = APIRouter()


def get_db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@router.get("/by-state")
async def analytics_by_state(db: Session = Depends(get_db)):
    """Aggregate statistics by state. Returns counts, rates, and demographics."""
    summaries = db.query(StateSummary).order_by(StateSummary.state).all()

    return [
        {
            "state": s.state,
            "state_name": s.state_name,
            "region": s.region,
            "population": s.population,
            "catholic_population": s.catholic_population,
            "total_accused": s.total_accused,
            "convicted_count": s.convicted_count,
            "deceased_count": s.deceased_count,
            "accused_per_100k": round(s.total_accused / s.population * 100000, 2) if s.population else None,
            "accused_per_100k_catholic": round(s.total_accused / s.catholic_population * 100000, 2) if s.catholic_population else None,
            "conviction_rate": round(s.convicted_count / s.total_accused * 100, 1) if s.total_accused else None,
        }
        for s in summaries
    ]


@router.get("/by-diocese")
async def analytics_by_diocese(
    state: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    """Aggregate statistics by diocese."""
    query = (
        db.query(
            DioceseAssociation.diocese_name,
            DioceseAssociation.state,
            func.count(distinct(DioceseAssociation.clergy_id)).label("count"),
        )
        .group_by(DioceseAssociation.diocese_name, DioceseAssociation.state)
    )

    if state:
        query = query.filter(DioceseAssociation.state == state.upper())

    results = query.order_by(func.count(distinct(DioceseAssociation.clergy_id)).desc()).limit(limit).all()

    return [
        {"diocese_name": r.diocese_name, "state": r.state, "accused_count": r.count}
        for r in results
    ]


@router.get("/by-decade")
async def analytics_by_decade(db: Session = Depends(get_db)):
    """Aggregate by ordination decade."""
    results = (
        db.query(
            AccusedClergy.ordination_decade,
            func.count().label("count"),
        )
        .filter(AccusedClergy.ordination_decade.isnot(None))
        .group_by(AccusedClergy.ordination_decade)
        .order_by(AccusedClergy.ordination_decade)
        .all()
    )

    return [{"decade": r.ordination_decade, "count": r.count} for r in results]


@router.get("/by-status")
async def analytics_by_status(state: Optional[str] = None, db: Session = Depends(get_db)):
    """Aggregate by status (accused, convicted, acquitted, etc.)."""
    query = db.query(AccusedClergy.status, func.count().label("count"))

    if state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())

    results = query.group_by(AccusedClergy.status).order_by(func.count().desc()).all()

    return [{"status": r.status or "unknown", "count": r.count} for r in results]


@router.get("/by-allegation-type")
async def analytics_by_allegation_type(state: Optional[str] = None, db: Session = Depends(get_db)):
    """Aggregate by allegation type."""
    query = db.query(Allegation.allegation_type, func.count().label("count"))

    if state:
        query = (
            query.join(AccusedClergy)
            .join(DioceseAssociation)
            .filter(DioceseAssociation.state == state.upper())
        )

    results = (
        query.filter(Allegation.allegation_type.isnot(None))
        .group_by(Allegation.allegation_type)
        .order_by(func.count().desc())
        .all()
    )

    return [{"allegation_type": r.allegation_type, "count": r.count} for r in results]


@router.get("/by-criminal-outcome")
async def analytics_by_criminal_outcome(state: Optional[str] = None, db: Session = Depends(get_db)):
    """Aggregate by criminal outcome type."""
    query = db.query(CriminalOutcome.outcome_type, func.count().label("count"))

    if state:
        query = (
            query.join(AccusedClergy)
            .join(DioceseAssociation)
            .filter(DioceseAssociation.state == state.upper())
        )

    results = query.group_by(CriminalOutcome.outcome_type).order_by(func.count().desc()).all()

    return [{"outcome_type": r.outcome_type, "count": r.count} for r in results]


@router.get("/by-church-action")
async def analytics_by_church_action(state: Optional[str] = None, db: Session = Depends(get_db)):
    """Aggregate by church action type."""
    query = db.query(ChurchAction.action_type, func.count().label("count"))

    if state:
        query = (
            query.join(AccusedClergy)
            .join(DioceseAssociation)
            .filter(DioceseAssociation.state == state.upper())
        )

    results = query.group_by(ChurchAction.action_type).order_by(func.count().desc()).all()

    return [{"action_type": r.action_type, "count": r.count} for r in results]


@router.get("/cross-reference")
async def cross_reference(
    clergy_ids: str = Query(..., description="Comma-separated clergy IDs"),
    db: Session = Depends(get_db),
):
    """Cross-reference multiple clergy: find shared dioceses, overlapping timelines, etc.

    Designed for agent-driven investigation workflows.
    """
    ids = [int(x.strip()) for x in clergy_ids.split(",") if x.strip().isdigit()]

    profiles = []
    for cid in ids:
        c = db.query(AccusedClergy).filter(AccusedClergy.id == cid).first()
        if not c:
            continue
        dioceses = [d.diocese_name for d in c.diocese_associations]
        profiles.append({
            "id": c.id,
            "name": f"{c.first_name} {c.last_name}",
            "ordination_year": c.ordination_year,
            "status": c.status,
            "dioceses": dioceses,
            "assignment_count": len(c.assignments),
            "allegation_count": len(c.allegations),
            "document_count": len(c.documents),
        })

    # Find shared dioceses
    if len(profiles) >= 2:
        all_dioceses = [set(p["dioceses"]) for p in profiles]
        shared = set.intersection(*all_dioceses) if all_dioceses else set()
    else:
        shared = set()

    return {
        "profiles": profiles,
        "shared_dioceses": list(shared),
        "total_profiles": len(profiles),
    }


@router.get("/summary")
async def analytics_summary(db: Session = Depends(get_db)):
    """High-level summary statistics. Designed for dashboard and agent overview queries."""
    total = db.query(func.count(AccusedClergy.id)).scalar()
    deceased = db.query(func.count(AccusedClergy.id)).filter(AccusedClergy.deceased == True).scalar()
    with_docs = (
        db.query(func.count(distinct(Document.clergy_id)))
        .scalar()
    )

    states = (
        db.query(func.count(distinct(DioceseAssociation.state)))
        .filter(DioceseAssociation.state.isnot(None))
        .scalar()
    )
    dioceses = db.query(func.count(distinct(DioceseAssociation.diocese_name))).scalar()
    total_docs = db.query(func.count(Document.id)).scalar()

    source_counts = dict(
        db.query(SourceRecord.source_name, func.count())
        .group_by(SourceRecord.source_name)
        .all()
    )

    return {
        "total_accused": total,
        "deceased": deceased,
        "with_documents": with_docs,
        "states_represented": states,
        "dioceses_represented": dioceses,
        "total_documents": total_docs,
        "by_source": source_counts,
    }
