"""Cross-reference engine for pattern detection across clergy records.

Designed for an AI agent to investigate connections:
- Shared dioceses in overlapping time windows
- Common facility referrals
- Transfer network mapping
- Temporal clustering of accusations
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, distinct, and_, or_
from sqlalchemy.orm import Session

from src.backend.database import get_session
from src.backend.models import (
    AccusedClergy,
    Assignment,
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


@router.get("/shared-diocese")
async def find_shared_diocese_clergy(
    diocese: str = Query(..., description="Diocese name (partial match)"),
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Find all clergy associated with a diocese, optionally within a time window.

    Useful for: "Who else was in this diocese when accused priest X was there?"
    """
    query = (
        db.query(AccusedClergy)
        .join(DioceseAssociation)
        .filter(DioceseAssociation.diocese_name.ilike(f"%{diocese}%"))
    )

    # If time window specified, filter by ordination year as a proxy
    # (full assignment dates would be better when roster data is available)
    if start_year:
        query = query.filter(
            or_(
                AccusedClergy.ordination_year >= start_year - 10,  # Active in window
                AccusedClergy.ordination_year.is_(None),
            )
        )
    if end_year:
        query = query.filter(
            or_(
                AccusedClergy.ordination_year <= end_year,
                AccusedClergy.ordination_year.is_(None),
            )
        )

    results = query.order_by(AccusedClergy.ordination_year).all()

    return {
        "diocese_filter": diocese,
        "time_window": {"start": start_year, "end": end_year} if start_year or end_year else None,
        "total": len(results),
        "clergy": [
            {
                "id": c.id,
                "name": f"{c.first_name} {c.last_name}",
                "ordination_year": c.ordination_year,
                "status": c.status,
                "deceased": c.deceased,
                "consequence_count": len(c.consequences),
            }
            for c in results
        ],
    }


@router.get("/transfer-network")
async def transfer_network(
    state: Optional[str] = None,
    min_transfers: int = Query(2, description="Minimum transfers to include a diocese pair"),
    db: Session = Depends(get_db),
):
    """Map the transfer network: which dioceses send clergy to which other dioceses?

    Based on clergy with multiple diocese associations. When roster data is
    available, this will use year-over-year diffs for precise transfer detection.

    Currently uses multi-diocese associations as a proxy for transfers.
    """
    # Find clergy with multiple diocese associations (evidence of transfer)
    multi_diocese = (
        db.query(
            DioceseAssociation.clergy_id,
            func.count(distinct(DioceseAssociation.diocese_name)).label("diocese_count"),
        )
        .group_by(DioceseAssociation.clergy_id)
        .having(func.count(distinct(DioceseAssociation.diocese_name)) > 1)
        .all()
    )

    # Build edge list: diocese_a → diocese_b
    edges = {}
    for row in multi_diocese:
        cid = row.clergy_id
        dioceses = (
            db.query(DioceseAssociation)
            .filter(DioceseAssociation.clergy_id == cid)
            .order_by(DioceseAssociation.is_primary.desc())
            .all()
        )

        if state:
            dioceses = [d for d in dioceses if d.state == state.upper()]

        diocese_names = [d.diocese_name for d in dioceses]
        # Create edges between all pairs (primary → others)
        for i in range(len(diocese_names)):
            for j in range(i + 1, len(diocese_names)):
                edge_key = tuple(sorted([diocese_names[i], diocese_names[j]]))
                if edge_key not in edges:
                    edges[edge_key] = {"clergy_ids": [], "count": 0}
                edges[edge_key]["clergy_ids"].append(cid)
                edges[edge_key]["count"] += 1

    # Filter by minimum transfers
    filtered = [
        {
            "diocese_a": k[0],
            "diocese_b": k[1],
            "transfer_count": v["count"],
            "clergy_ids": v["clergy_ids"],
        }
        for k, v in edges.items()
        if v["count"] >= min_transfers
    ]
    filtered.sort(key=lambda x: -x["transfer_count"])

    return {
        "total_multi_diocese_clergy": len(multi_diocese),
        "diocese_pairs": len(filtered),
        "transfers": filtered,
    }


@router.get("/temporal-clusters")
async def temporal_clusters(
    consequence_type: str = Query(..., description="e.g., 'treatment', 'conviction', 'no_known_action'"),
    state: Optional[str] = None,
    bucket_size: int = Query(5, description="Year bucket size for clustering"),
    db: Session = Depends(get_db),
):
    """Find temporal clusters of a specific consequence type.

    Answers: "When did most treatments happen?" or "When did convictions peak?"
    Useful for correlating with external events (media investigations, SOL reforms).
    """
    query = db.query(Consequence).filter(
        Consequence.consequence_type == consequence_type,
        Consequence.year.isnot(None),
    )

    if state:
        query = (
            query.join(AccusedClergy)
            .join(DioceseAssociation)
            .filter(DioceseAssociation.state == state.upper())
        )

    results = query.all()

    # Bucket by year ranges
    buckets = {}
    for c in results:
        bucket_start = (c.year // bucket_size) * bucket_size
        bucket_key = f"{bucket_start}-{bucket_start + bucket_size - 1}"
        if bucket_key not in buckets:
            buckets[bucket_key] = {"count": 0, "clergy_ids": []}
        buckets[bucket_key]["count"] += 1
        buckets[bucket_key]["clergy_ids"].append(c.clergy_id)

    sorted_buckets = sorted(buckets.items(), key=lambda x: x[0])

    return {
        "consequence_type": consequence_type,
        "bucket_size_years": bucket_size,
        "total_with_year": len(results),
        "clusters": [
            {"period": k, "count": v["count"], "clergy_ids": v["clergy_ids"]}
            for k, v in sorted_buckets
        ],
    }


@router.get("/reporting-lag")
async def reporting_lag_analysis(
    state: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Analyze the gap between ordination (proxy for start of ministry) and consequences.

    A rough measure of "how long did they get away with it?" since we often
    don't have exact abuse dates, but ordination year → first consequence year
    gives the minimum active period before any action.
    """
    query = db.query(AccusedClergy).filter(AccusedClergy.ordination_year.isnot(None))

    if state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())

    clergy = query.all()

    lag_data = []
    for c in clergy:
        # Find earliest consequence with a year
        earliest = (
            db.query(func.min(Consequence.year))
            .filter(
                Consequence.clergy_id == c.id,
                Consequence.year.isnot(None),
                Consequence.consequence_type != "death",
            )
            .scalar()
        )
        if earliest and c.ordination_year:
            lag = earliest - c.ordination_year
            if 0 <= lag <= 80:  # Sanity check
                lag_data.append({
                    "clergy_id": c.id,
                    "ordination_year": c.ordination_year,
                    "first_consequence_year": earliest,
                    "lag_years": lag,
                    "status": c.status,
                    "deceased": c.deceased,
                })

    if not lag_data:
        return {"total_analyzed": 0, "lag_distribution": []}

    # Bucket lags
    lag_buckets = {}
    for d in lag_data:
        bucket = (d["lag_years"] // 10) * 10
        bucket_key = f"{bucket}-{bucket + 9} years"
        lag_buckets[bucket_key] = lag_buckets.get(bucket_key, 0) + 1

    avg_lag = sum(d["lag_years"] for d in lag_data) / len(lag_data)
    median_lag = sorted(d["lag_years"] for d in lag_data)[len(lag_data) // 2]

    return {
        "total_analyzed": len(lag_data),
        "average_lag_years": round(avg_lag, 1),
        "median_lag_years": median_lag,
        "lag_distribution": sorted(lag_buckets.items(), key=lambda x: x[0]),
        "longest_lags": sorted(lag_data, key=lambda x: -x["lag_years"])[:20],
    }


@router.get("/no-accountability")
async def no_accountability_analysis(
    state: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Find clergy who faced effectively no consequences.

    Identifies the "got away with it" cases: no conviction, no removal,
    possibly not even treatment. Includes both living and deceased.
    """
    # Consequence types that represent actual accountability
    accountability_types = {
        "conviction", "incarceration", "criminal_charges",
        "removed_from_ministry", "laicized", "banned_from_property",
    }

    query = db.query(AccusedClergy)
    if state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())

    all_clergy = query.all()

    no_accountability = []
    minimal_accountability = []

    for c in all_clergy:
        consequence_types = {cons.consequence_type for cons in c.consequences}
        has_accountability = bool(consequence_types & accountability_types)

        if not has_accountability:
            entry = {
                "id": c.id,
                "name": f"{c.first_name} {c.last_name}",
                "ordination_year": c.ordination_year,
                "deceased": c.deceased,
                "death_year": c.death_year,
                "status": c.status,
                "consequences": list(consequence_types),
            }
            if consequence_types <= {"no_known_action", "death", "posthumous_accusation"}:
                no_accountability.append(entry)
            else:
                minimal_accountability.append(entry)

    return {
        "total_accused": len(all_clergy),
        "no_accountability": {
            "count": len(no_accountability),
            "pct": round(len(no_accountability) / len(all_clergy) * 100, 1) if all_clergy else 0,
            "description": "No criminal charges, no removal, no laicization. Consequence was death or nothing.",
            "sample": no_accountability[:20],
        },
        "minimal_accountability": {
            "count": len(minimal_accountability),
            "pct": round(len(minimal_accountability) / len(all_clergy) * 100, 1) if all_clergy else 0,
            "description": "Some action taken (suspension, treatment, civil suit) but no criminal or permanent church consequence.",
            "sample": minimal_accountability[:20],
        },
        "actual_accountability": {
            "count": len(all_clergy) - len(no_accountability) - len(minimal_accountability),
            "pct": round((len(all_clergy) - len(no_accountability) - len(minimal_accountability)) / len(all_clergy) * 100, 1) if all_clergy else 0,
        },
    }
