"""Consequence timeline and pattern analysis endpoints.

These are the primary research-facing endpoints — designed for an AI agent
to investigate patterns like:
- Treatment → reinstatement pipelines
- Transfer-after-accusation sequences
- "No known action" prevalence
- Posthumous accusation patterns
- Facility funneling across states
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, distinct, and_, or_, case
from sqlalchemy.orm import Session

from src.backend.database import get_session
from src.backend.models import (
    AccusedClergy,
    Consequence,
    DioceseAssociation,
    TreatmentFacility,
)

router = APIRouter()


def get_db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


# --- Timeline endpoints ---

@router.get("/{clergy_id}/timeline")
async def get_consequence_timeline(clergy_id: int, db: Session = Depends(get_db)):
    """Get the full ordered consequence timeline for one individual.

    Returns events in sequence order — the complete story of what happened
    after accusation.
    """
    clergy = db.query(AccusedClergy).filter(AccusedClergy.id == clergy_id).first()
    if not clergy:
        raise HTTPException(status_code=404, detail="Clergy not found")

    consequences = (
        db.query(Consequence)
        .filter(Consequence.clergy_id == clergy_id)
        .order_by(Consequence.sequence_order)
        .all()
    )

    return {
        "clergy_id": clergy_id,
        "name": f"{clergy.first_name} {clergy.last_name}",
        "status": clergy.status,
        "deceased": clergy.deceased,
        "timeline": [
            {
                "sequence": c.sequence_order,
                "type": c.consequence_type,
                "year": c.year,
                "facility_id": c.facility_id,
                "from_diocese": c.from_diocese,
                "to_diocese": c.to_diocese,
                "details": c.details,
            }
            for c in consequences
        ],
        "total_events": len(consequences),
        "final_outcome": consequences[-1].consequence_type if consequences else "unknown",
    }


# --- Pattern search endpoints ---

class PatternQuery(BaseModel):
    """Search for clergy whose consequence timelines match a pattern.

    Pattern is an ordered list of consequence types. Matches clergy
    whose timeline contains this subsequence (not necessarily contiguous).
    """
    pattern: list[str]  # e.g. ["treatment", "reinstated"] or ["no_known_action", "death"]
    state: Optional[str] = None
    diocese: Optional[str] = None
    limit: int = 100
    offset: int = 0


@router.post("/patterns/search")
async def search_consequence_patterns(req: PatternQuery, db: Session = Depends(get_db)):
    """Find clergy whose timelines contain a specific consequence subsequence.

    Example patterns:
    - ["treatment", "reinstated"] — sent to treatment then put back in ministry
    - ["no_known_action", "death"] — faced no consequences, died
    - ["criminal_charges", "acquittal"] — charged but not convicted
    - ["treatment", "transfer"] — treated then moved to new diocese
    - ["suspended", "reinstated"] — suspended then put back
    """
    if not req.pattern:
        raise HTTPException(status_code=400, detail="Pattern must have at least one consequence type")

    # Build subquery: find clergy who have ALL pattern elements in the right order
    # Start with clergy who have the first pattern element
    base_query = (
        db.query(distinct(Consequence.clergy_id))
        .filter(Consequence.consequence_type == req.pattern[0])
    )

    # For each subsequent pattern element, ensure it exists with a higher sequence_order
    # We do this by finding all clergy with each type and intersecting
    candidate_ids = set(r[0] for r in base_query.all())

    for i, ptype in enumerate(req.pattern[1:], 1):
        if not candidate_ids:
            break
        # Find clergy who have this type AND a previous type with lower sequence
        ids_with_type = set(
            r[0] for r in
            db.query(distinct(Consequence.clergy_id))
            .filter(
                Consequence.consequence_type == ptype,
                Consequence.clergy_id.in_(candidate_ids),
            )
            .all()
        )

        # Verify ordering: for remaining candidates, check sequence
        verified = set()
        for cid in ids_with_type:
            timeline = (
                db.query(Consequence.consequence_type, Consequence.sequence_order)
                .filter(Consequence.clergy_id == cid)
                .order_by(Consequence.sequence_order)
                .all()
            )
            types_in_order = [t[0] for t in timeline]
            # Check if pattern[:i+1] is a subsequence
            if _is_subsequence(req.pattern[: i + 1], types_in_order):
                verified.add(cid)
        candidate_ids = verified

    if not candidate_ids:
        return {"pattern": req.pattern, "total": 0, "results": []}

    # Apply state/diocese filters
    query = db.query(AccusedClergy).filter(AccusedClergy.id.in_(candidate_ids))
    if req.state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == req.state.upper())
    if req.diocese:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.diocese_name.ilike(f"%{req.diocese}%"))

    total = query.count()
    results = query.offset(req.offset).limit(req.limit).all()

    return {
        "pattern": req.pattern,
        "total": total,
        "results": [
            {
                "id": c.id,
                "name": f"{c.first_name} {c.last_name}",
                "status": c.status,
                "deceased": c.deceased,
                "ordination_year": c.ordination_year,
            }
            for c in results
        ],
    }


def _is_subsequence(pattern: list[str], sequence: list[str]) -> bool:
    """Check if pattern appears as a subsequence (in order, not necessarily contiguous) in sequence."""
    pi = 0
    for item in sequence:
        if pi < len(pattern) and item == pattern[pi]:
            pi += 1
    return pi == len(pattern)


# --- Aggregate analysis endpoints ---

@router.get("/stats/type-breakdown")
async def consequence_type_breakdown(
    state: Optional[str] = None,
    diocese: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Aggregate consequence counts by type, optionally filtered by state/diocese."""
    query = db.query(
        Consequence.consequence_type,
        func.count().label("count"),
        func.count(distinct(Consequence.clergy_id)).label("unique_clergy"),
    )

    if state or diocese:
        query = query.join(AccusedClergy).join(DioceseAssociation)
        if state:
            query = query.filter(DioceseAssociation.state == state.upper())
        if diocese:
            query = query.filter(DioceseAssociation.diocese_name.ilike(f"%{diocese}%"))

    results = (
        query.group_by(Consequence.consequence_type)
        .order_by(func.count().desc())
        .all()
    )

    total_clergy = db.query(func.count(distinct(Consequence.clergy_id))).scalar()

    return {
        "total_clergy_with_consequences": total_clergy,
        "breakdown": [
            {
                "type": r.consequence_type,
                "count": r.count,
                "unique_clergy": r.unique_clergy,
                "pct_of_accused": round(r.unique_clergy / total_clergy * 100, 1) if total_clergy else 0,
            }
            for r in results
        ],
    }


@router.get("/stats/final-outcomes")
async def final_outcome_analysis(
    state: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """What was the LAST consequence for each individual?

    This answers: "How did things end?" — conviction, death, reinstatement, nothing?
    Powerful for showing the rarity of actual accountability.
    """
    # Get the max sequence_order per clergy (their final consequence)
    from sqlalchemy import tuple_

    max_seq_subquery = (
        db.query(
            Consequence.clergy_id,
            func.max(Consequence.sequence_order).label("max_seq"),
        )
        .group_by(Consequence.clergy_id)
        .subquery()
    )

    query = (
        db.query(
            Consequence.consequence_type,
            func.count().label("count"),
        )
        .join(
            max_seq_subquery,
            and_(
                Consequence.clergy_id == max_seq_subquery.c.clergy_id,
                Consequence.sequence_order == max_seq_subquery.c.max_seq,
            ),
        )
    )

    if state:
        query = (
            query.join(AccusedClergy)
            .join(DioceseAssociation)
            .filter(DioceseAssociation.state == state.upper())
        )

    results = query.group_by(Consequence.consequence_type).order_by(func.count().desc()).all()
    total = sum(r.count for r in results)

    return {
        "description": "Distribution of final consequence per accused individual",
        "total": total,
        "outcomes": [
            {
                "final_outcome": r.consequence_type,
                "count": r.count,
                "pct": round(r.count / total * 100, 1) if total else 0,
            }
            for r in results
        ],
    }


@router.get("/stats/treatment-to-outcome")
async def treatment_to_outcome(db: Session = Depends(get_db)):
    """For clergy sent to treatment: what happened AFTER treatment?

    Answers: "Does treatment lead to reinstatement, removal, or nothing?"
    """
    # Find all clergy who have a "treatment" consequence
    treated_ids = [
        r[0] for r in
        db.query(distinct(Consequence.clergy_id))
        .filter(Consequence.consequence_type == "treatment")
        .all()
    ]

    if not treated_ids:
        return {"treated_count": 0, "post_treatment_outcomes": []}

    # For each treated clergy member, find what comes AFTER treatment in their timeline
    post_treatment = {}
    for cid in treated_ids:
        timeline = (
            db.query(Consequence)
            .filter(Consequence.clergy_id == cid)
            .order_by(Consequence.sequence_order)
            .all()
        )

        found_treatment = False
        for c in timeline:
            if c.consequence_type == "treatment":
                found_treatment = True
                continue
            if found_treatment:
                post_treatment.setdefault(c.consequence_type, 0)
                post_treatment[c.consequence_type] += 1

    sorted_outcomes = sorted(post_treatment.items(), key=lambda x: -x[1])

    return {
        "treated_count": len(treated_ids),
        "post_treatment_outcomes": [
            {"outcome": outcome, "count": count, "pct": round(count / len(treated_ids) * 100, 1)}
            for outcome, count in sorted_outcomes
        ],
    }


# --- Facility analysis endpoints ---

@router.get("/facilities")
async def list_facilities(db: Session = Depends(get_db)):
    """List all known treatment facilities with usage counts."""
    facilities = db.query(TreatmentFacility).all()

    result = []
    for f in facilities:
        ref_count = (
            db.query(func.count(Consequence.id))
            .filter(Consequence.facility_id == f.id)
            .scalar()
        )
        result.append({
            "id": f.id,
            "name": f.name,
            "aliases": f.aliases,
            "city": f.city,
            "state": f.state,
            "facility_type": f.facility_type,
            "clergy_referred": ref_count,
            "notes": f.notes,
        })

    result.sort(key=lambda x: -x["clergy_referred"])
    return result


@router.get("/facilities/{facility_id}/clergy")
async def facility_clergy(facility_id: int, db: Session = Depends(get_db)):
    """List all clergy referred to a specific facility.

    This is the core query for the cross-state funneling analysis:
    "Show me everyone who went through facility X and where they came from."
    """
    facility = db.query(TreatmentFacility).filter(TreatmentFacility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    consequences = (
        db.query(Consequence)
        .filter(Consequence.facility_id == facility_id)
        .all()
    )

    clergy_ids = [c.clergy_id for c in consequences]
    clergy_map = {
        c.id: c for c in
        db.query(AccusedClergy).filter(AccusedClergy.id.in_(clergy_ids)).all()
    }

    # Get state info for each clergy member
    results = []
    states = set()
    for cons in consequences:
        c = clergy_map.get(cons.clergy_id)
        if not c:
            continue
        primary = next((d for d in c.diocese_associations if d.is_primary), None)
        state = primary.state if primary else None
        if state:
            states.add(state)
        results.append({
            "clergy_id": c.id,
            "name": f"{c.first_name} {c.last_name}",
            "state": state,
            "diocese": primary.diocese_name if primary else None,
            "ordination_year": c.ordination_year,
            "status": c.status,
        })

    return {
        "facility": {
            "id": facility.id,
            "name": facility.name,
            "city": facility.city,
            "state": facility.state,
        },
        "total_referred": len(results),
        "states_represented": sorted(states),
        "state_count": len(states),
        "clergy": results,
    }


@router.get("/facilities/cross-state-analysis")
async def facility_cross_state(db: Session = Depends(get_db)):
    """Which facilities received clergy from the most different states?

    This is the high-level funneling detection query. Facilities that
    draw from many states are the institutional "pipelines."
    """
    # For each facility, count distinct states of referred clergy
    facilities = db.query(TreatmentFacility).all()

    results = []
    for f in facilities:
        clergy_ids = [
            r[0] for r in
            db.query(distinct(Consequence.clergy_id))
            .filter(Consequence.facility_id == f.id)
            .all()
        ]

        if not clergy_ids:
            continue

        states = set()
        for cid in clergy_ids:
            primary = (
                db.query(DioceseAssociation.state)
                .filter(DioceseAssociation.clergy_id == cid, DioceseAssociation.is_primary == True)
                .first()
            )
            if primary and primary.state:
                states.add(primary.state)

        results.append({
            "facility_id": f.id,
            "facility_name": f.name,
            "facility_city": f.city,
            "facility_state": f.state,
            "clergy_count": len(clergy_ids),
            "states_represented": sorted(states),
            "state_count": len(states),
        })

    results.sort(key=lambda x: -x["state_count"])
    return results
