"""MCP Server for Clergy Abuse Research Data.

Exposes the full analysis toolkit as MCP tools that appear natively in Claude Code.

Usage:
    python -m src.mcp_server.server

Or add to Claude Code settings:
    {
        "mcpServers": {
            "clergy-abuse-data": {
                "command": "python",
                "args": ["-m", "src.mcp_server.server"],
                "cwd": "/path/to/ClergySexAbuse"
            }
        }
    }
"""

import json
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.backend.database import init_db, get_session
from src.backend.models import *
from sqlalchemy import func, distinct, and_, or_

app = Server("clergy-abuse-data")

# Initialize DB on startup
_engine = init_db()


def _get_db():
    return get_session(_engine)


def _json_response(data) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


# ============================================================
# TOOL DEFINITIONS
# ============================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_clergy",
            description="Search accused clergy by name, state, diocese, status, or religious order. Returns brief profiles with IDs for follow-up queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name search (partial match)"},
                    "state": {"type": "string", "description": "Two-letter state code (e.g., 'MN', 'CA')"},
                    "diocese": {"type": "string", "description": "Diocese name (partial match)"},
                    "status": {"type": "string", "description": "Status filter (e.g., 'Accused', 'Convicted', 'Settled')"},
                    "religious_order": {"type": "string", "description": "Religious order (partial match)"},
                    "has_documents": {"type": "boolean", "description": "Only return clergy with linked documents"},
                    "source": {"type": "string", "description": "Data source filter (e.g., 'bishop_accountability', 'anderson_national')"},
                    "limit": {"type": "integer", "description": "Max results (default 50)", "default": 50},
                    "offset": {"type": "integer", "description": "Pagination offset", "default": 0},
                },
            },
        ),
        Tool(
            name="get_clergy_profile",
            description="Get the COMPLETE profile for one individual: all dioceses, assignments, allegations, consequences, documents, and source records. Use this after search_clergy to drill into a specific person.",
            inputSchema={
                "type": "object",
                "properties": {
                    "clergy_id": {"type": "integer", "description": "Clergy ID from search results"},
                },
                "required": ["clergy_id"],
            },
        ),
        Tool(
            name="get_consequence_timeline",
            description="Get the full ordered consequence timeline for one individual — the complete story of what happened after accusation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "clergy_id": {"type": "integer", "description": "Clergy ID"},
                },
                "required": ["clergy_id"],
            },
        ),
        Tool(
            name="find_consequence_pattern",
            description="Find clergy whose consequence timelines match a specific pattern sequence. E.g., ['treatment', 'reinstated'] finds everyone sent to treatment then put back in ministry. Types: accusation, investigation, treatment, transfer, civil_suit, civil_settlement, criminal_charges, conviction, acquittal, incarceration, suspended, removed_from_ministry, laicized, reinstated, banned_from_property, no_known_action, death, posthumous_accusation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ordered list of consequence types to match as a subsequence",
                    },
                    "state": {"type": "string", "description": "Optional state filter"},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="summary_stats",
            description="High-level summary statistics: total accused, deceased, documents, states, dioceses, sources.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="stats_by_state",
            description="Per-state statistics: total accused, conviction rates, per-capita rates.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="stats_by_diocese",
            description="Per-diocese accused counts, optionally filtered by state.",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "description": "Two-letter state code"},
                    "limit": {"type": "integer", "default": 50},
                },
            },
        ),
        Tool(
            name="final_outcome_stats",
            description="Distribution of FINAL consequence per accused individual — answers 'how did things end?' Shows the rarity of actual accountability.",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "description": "Optional state filter"},
                },
            },
        ),
        Tool(
            name="treatment_outcomes",
            description="For clergy sent to treatment: what happened AFTER? Shows whether treatment led to reinstatement, removal, or nothing.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_facilities",
            description="List known treatment/retreat facilities with referral counts.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="facility_cross_state",
            description="Which treatment facilities received clergy from the most different states? Detects cross-state funneling pipelines.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="facility_clergy",
            description="List all clergy referred to a specific facility and where they came from.",
            inputSchema={
                "type": "object",
                "properties": {
                    "facility_id": {"type": "integer", "description": "Facility ID from list_facilities"},
                },
                "required": ["facility_id"],
            },
        ),
        Tool(
            name="no_accountability_analysis",
            description="Find clergy who faced effectively no consequences: no conviction, no removal, no laicization. The 'got away with it' analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "description": "Optional state filter"},
                },
            },
        ),
        Tool(
            name="reporting_lag_analysis",
            description="Analyze the gap between ordination and first consequence — 'how long did they get away with it?'",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "description": "Optional state filter"},
                },
            },
        ),
        Tool(
            name="transfer_network",
            description="Map the transfer network: which dioceses send clergy to which other dioceses?",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "description": "Optional state filter"},
                    "min_transfers": {"type": "integer", "default": 2},
                },
            },
        ),
        Tool(
            name="temporal_clusters",
            description="Find temporal clusters of a specific consequence type — when did convictions/treatments/etc peak?",
            inputSchema={
                "type": "object",
                "properties": {
                    "consequence_type": {"type": "string", "description": "E.g., 'treatment', 'conviction', 'no_known_action'"},
                    "state": {"type": "string", "description": "Optional state filter"},
                    "bucket_size": {"type": "integer", "default": 5, "description": "Year bucket size"},
                },
                "required": ["consequence_type"],
            },
        ),
        Tool(
            name="consequence_type_breakdown",
            description="Aggregate consequence counts by type, with percentage of accused.",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string", "description": "Optional state filter"},
                    "diocese": {"type": "string", "description": "Optional diocese filter"},
                },
            },
        ),
        Tool(
            name="export_csv",
            description="Export filtered clergy data as CSV. Returns the CSV content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string"},
                    "diocese": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
        ),
    ]


# ============================================================
# TOOL IMPLEMENTATIONS
# ============================================================

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    db = _get_db()
    try:
        if name == "search_clergy":
            return _search_clergy(db, **arguments)
        elif name == "get_clergy_profile":
            return _get_clergy_profile(db, **arguments)
        elif name == "get_consequence_timeline":
            return _get_consequence_timeline(db, **arguments)
        elif name == "find_consequence_pattern":
            return _find_consequence_pattern(db, **arguments)
        elif name == "summary_stats":
            return _summary_stats(db)
        elif name == "stats_by_state":
            return _stats_by_state(db)
        elif name == "stats_by_diocese":
            return _stats_by_diocese(db, **arguments)
        elif name == "final_outcome_stats":
            return _final_outcome_stats(db, **arguments)
        elif name == "treatment_outcomes":
            return _treatment_outcomes(db)
        elif name == "list_facilities":
            return _list_facilities(db)
        elif name == "facility_cross_state":
            return _facility_cross_state(db)
        elif name == "facility_clergy":
            return _facility_clergy(db, **arguments)
        elif name == "no_accountability_analysis":
            return _no_accountability(db, **arguments)
        elif name == "reporting_lag_analysis":
            return _reporting_lag(db, **arguments)
        elif name == "transfer_network":
            return _transfer_network(db, **arguments)
        elif name == "temporal_clusters":
            return _temporal_clusters(db, **arguments)
        elif name == "consequence_type_breakdown":
            return _consequence_breakdown(db, **arguments)
        elif name == "export_csv":
            return _export_csv(db, **arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    finally:
        db.close()


def _search_clergy(db, name=None, state=None, diocese=None, status=None,
                   religious_order=None, has_documents=None, source=None,
                   limit=50, offset=0):
    query = db.query(AccusedClergy)
    if name:
        pattern = f"%{name}%"
        query = query.filter(or_(AccusedClergy.first_name.ilike(pattern), AccusedClergy.last_name.ilike(pattern)))
    if state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())
    if diocese:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.diocese_name.ilike(f"%{diocese}%"))
    if status:
        query = query.filter(AccusedClergy.status == status)
    if religious_order:
        query = query.filter(AccusedClergy.religious_order.ilike(f"%{religious_order}%"))
    if has_documents:
        query = query.filter(AccusedClergy.documents.any())
    if source:
        query = query.join(SourceRecord).filter(SourceRecord.source_name == source)

    total = query.count()
    results = query.order_by(AccusedClergy.last_name).offset(offset).limit(limit).all()

    data = {
        "total": total,
        "results": [
            {
                "id": c.id,
                "name": f"{c.first_name} {c.last_name}".strip(),
                "status": c.status,
                "ordination_year": c.ordination_year,
                "deceased": c.deceased,
                "primary_diocese": next((d.diocese_name for d in c.diocese_associations if d.is_primary), None),
                "primary_state": next((d.state for d in c.diocese_associations if d.is_primary), None),
                "source_count": len(c.source_records),
                "document_count": len(c.documents),
            }
            for c in results
        ],
    }
    return _json_response(data)


def _get_clergy_profile(db, clergy_id):
    from sqlalchemy.orm import joinedload
    c = (
        db.query(AccusedClergy)
        .options(
            joinedload(AccusedClergy.diocese_associations),
            joinedload(AccusedClergy.assignments),
            joinedload(AccusedClergy.allegations),
            joinedload(AccusedClergy.consequences),
            joinedload(AccusedClergy.source_records),
            joinedload(AccusedClergy.documents),
        )
        .filter(AccusedClergy.id == clergy_id)
        .first()
    )
    if not c:
        return _json_response({"error": "Clergy not found"})

    return _json_response({
        "id": c.id,
        "name": f"{c.first_name} {c.last_name}".strip(),
        "suffix": c.suffix,
        "ordination_year": c.ordination_year,
        "death_year": c.death_year,
        "deceased": c.deceased,
        "status": c.status,
        "religious_order": c.religious_order,
        "narrative": c.narrative[:2000] if c.narrative else None,
        "narrative_length": len(c.narrative) if c.narrative else 0,
        "dioceses": [{"name": d.diocese_name, "state": d.state, "primary": d.is_primary} for d in c.diocese_associations],
        "assignments": [{"institution": a.institution_name, "start": a.start_year, "end": a.end_year, "role": a.role} for a in c.assignments],
        "consequences": [{"type": co.consequence_type, "year": co.year, "seq": co.sequence_order, "details": co.details} for co in sorted(c.consequences, key=lambda x: x.sequence_order or 0)],
        "sources": [{"source": s.source_name, "url": s.source_url} for s in c.source_records],
        "documents": [{"id": d.id, "type": d.doc_type, "title": d.title, "url": d.url} for d in c.documents],
    })


def _get_consequence_timeline(db, clergy_id):
    c = db.query(AccusedClergy).filter(AccusedClergy.id == clergy_id).first()
    if not c:
        return _json_response({"error": "Clergy not found"})

    consequences = db.query(Consequence).filter(Consequence.clergy_id == clergy_id).order_by(Consequence.sequence_order).all()

    return _json_response({
        "clergy_id": clergy_id,
        "name": f"{c.first_name} {c.last_name}",
        "timeline": [{"seq": co.sequence_order, "type": co.consequence_type, "year": co.year, "facility_id": co.facility_id, "details": co.details} for co in consequences],
        "final_outcome": consequences[-1].consequence_type if consequences else "unknown",
    })


def _find_consequence_pattern(db, pattern, state=None, limit=50):
    # Find clergy with first pattern element
    candidate_ids = set(
        r[0] for r in db.query(distinct(Consequence.clergy_id)).filter(Consequence.consequence_type == pattern[0]).all()
    )

    for i, ptype in enumerate(pattern[1:], 1):
        if not candidate_ids:
            break
        ids_with_type = set(
            r[0] for r in db.query(distinct(Consequence.clergy_id))
            .filter(Consequence.consequence_type == ptype, Consequence.clergy_id.in_(candidate_ids)).all()
        )
        verified = set()
        for cid in ids_with_type:
            timeline = [t[0] for t in db.query(Consequence.consequence_type).filter(Consequence.clergy_id == cid).order_by(Consequence.sequence_order).all()]
            pi = 0
            for item in timeline:
                if pi < len(pattern[:i+1]) and item == pattern[pi]:
                    pi += 1
            if pi == len(pattern[:i+1]):
                verified.add(cid)
        candidate_ids = verified

    if not candidate_ids:
        return _json_response({"pattern": pattern, "total": 0, "results": []})

    query = db.query(AccusedClergy).filter(AccusedClergy.id.in_(candidate_ids))
    if state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())

    total = query.count()
    results = query.limit(limit).all()

    return _json_response({
        "pattern": pattern,
        "total": total,
        "results": [{"id": c.id, "name": f"{c.first_name} {c.last_name}", "status": c.status, "deceased": c.deceased} for c in results],
    })


def _summary_stats(db):
    total = db.query(func.count(AccusedClergy.id)).scalar()
    deceased = db.query(func.count(AccusedClergy.id)).filter(AccusedClergy.deceased == True).scalar()
    with_docs = db.query(func.count(distinct(Document.clergy_id))).scalar()
    states = db.query(func.count(distinct(DioceseAssociation.state))).filter(DioceseAssociation.state.isnot(None)).scalar()
    dioceses = db.query(func.count(distinct(DioceseAssociation.diocese_name))).scalar()
    total_docs = db.query(func.count(Document.id)).scalar()
    sources = dict(db.query(SourceRecord.source_name, func.count()).group_by(SourceRecord.source_name).all())

    return _json_response({
        "total_accused": total, "deceased": deceased, "with_documents": with_docs,
        "states": states, "dioceses": dioceses, "documents": total_docs, "by_source": sources,
    })


def _stats_by_state(db):
    summaries = db.query(StateSummary).order_by(StateSummary.state).all()
    return _json_response([{
        "state": s.state, "name": s.state_name, "region": s.region,
        "total_accused": s.total_accused, "convicted": s.convicted_count,
        "population": s.population, "catholic_pop": s.catholic_population,
        "per_100k": round(s.total_accused / s.population * 100000, 2) if s.population else None,
        "conviction_rate": round(s.convicted_count / s.total_accused * 100, 1) if s.total_accused else None,
    } for s in summaries])


def _stats_by_diocese(db, state=None, limit=50):
    query = db.query(DioceseAssociation.diocese_name, DioceseAssociation.state, func.count(distinct(DioceseAssociation.clergy_id)).label("count")).group_by(DioceseAssociation.diocese_name, DioceseAssociation.state)
    if state:
        query = query.filter(DioceseAssociation.state == state.upper())
    results = query.order_by(func.count(distinct(DioceseAssociation.clergy_id)).desc()).limit(limit).all()
    return _json_response([{"diocese": r.diocese_name, "state": r.state, "count": r.count} for r in results])


def _final_outcome_stats(db, state=None):
    max_seq = db.query(Consequence.clergy_id, func.max(Consequence.sequence_order).label("max_seq")).group_by(Consequence.clergy_id).subquery()
    query = db.query(Consequence.consequence_type, func.count().label("count")).join(max_seq, and_(Consequence.clergy_id == max_seq.c.clergy_id, Consequence.sequence_order == max_seq.c.max_seq))
    if state:
        query = query.join(AccusedClergy).join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())
    results = query.group_by(Consequence.consequence_type).order_by(func.count().desc()).all()
    total = sum(r.count for r in results)
    return _json_response({"total": total, "outcomes": [{"outcome": r.consequence_type, "count": r.count, "pct": round(r.count / total * 100, 1) if total else 0} for r in results]})


def _treatment_outcomes(db):
    treated_ids = [r[0] for r in db.query(distinct(Consequence.clergy_id)).filter(Consequence.consequence_type == "treatment").all()]
    if not treated_ids:
        return _json_response({"treated_count": 0, "post_treatment": []})
    post = {}
    for cid in treated_ids:
        timeline = db.query(Consequence).filter(Consequence.clergy_id == cid).order_by(Consequence.sequence_order).all()
        found = False
        for c in timeline:
            if c.consequence_type == "treatment":
                found = True
                continue
            if found:
                post[c.consequence_type] = post.get(c.consequence_type, 0) + 1
    return _json_response({"treated_count": len(treated_ids), "post_treatment": sorted([{"outcome": k, "count": v, "pct": round(v / len(treated_ids) * 100, 1)} for k, v in post.items()], key=lambda x: -x["count"])})


def _list_facilities(db):
    facilities = db.query(TreatmentFacility).all()
    result = []
    for f in facilities:
        count = db.query(func.count(Consequence.id)).filter(Consequence.facility_id == f.id).scalar()
        result.append({"id": f.id, "name": f.name, "city": f.city, "state": f.state, "type": f.facility_type, "clergy_referred": count})
    result.sort(key=lambda x: -x["clergy_referred"])
    return _json_response(result)


def _facility_cross_state(db):
    facilities = db.query(TreatmentFacility).all()
    results = []
    for f in facilities:
        clergy_ids = [r[0] for r in db.query(distinct(Consequence.clergy_id)).filter(Consequence.facility_id == f.id).all()]
        if not clergy_ids:
            continue
        states = set()
        for cid in clergy_ids:
            primary = db.query(DioceseAssociation.state).filter(DioceseAssociation.clergy_id == cid, DioceseAssociation.is_primary == True).first()
            if primary and primary.state:
                states.add(primary.state)
        results.append({"facility": f.name, "city": f.city, "state": f.state, "clergy": len(clergy_ids), "states": sorted(states), "state_count": len(states)})
    results.sort(key=lambda x: -x["state_count"])
    return _json_response(results)


def _facility_clergy(db, facility_id):
    facility = db.query(TreatmentFacility).filter(TreatmentFacility.id == facility_id).first()
    if not facility:
        return _json_response({"error": "Facility not found"})
    consequences = db.query(Consequence).filter(Consequence.facility_id == facility_id).all()
    clergy_ids = [c.clergy_id for c in consequences]
    clergy_map = {c.id: c for c in db.query(AccusedClergy).filter(AccusedClergy.id.in_(clergy_ids)).all()}
    results = []
    for cons in consequences:
        c = clergy_map.get(cons.clergy_id)
        if not c:
            continue
        primary = next((d for d in c.diocese_associations if d.is_primary), None)
        results.append({"id": c.id, "name": f"{c.first_name} {c.last_name}", "state": primary.state if primary else None, "diocese": primary.diocese_name if primary else None})
    return _json_response({"facility": facility.name, "total": len(results), "clergy": results})


def _no_accountability(db, state=None):
    accountability_types = {"conviction", "incarceration", "criminal_charges", "removed_from_ministry", "laicized", "banned_from_property"}
    query = db.query(AccusedClergy)
    if state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())
    all_clergy = query.all()
    no_acc = []
    for c in all_clergy:
        ctypes = {co.consequence_type for co in c.consequences}
        if not (ctypes & accountability_types):
            if ctypes <= {"no_known_action", "death", "posthumous_accusation"}:
                no_acc.append({"id": c.id, "name": f"{c.first_name} {c.last_name}", "deceased": c.deceased, "consequences": list(ctypes)})
    return _json_response({"total_accused": len(all_clergy), "no_accountability_count": len(no_acc), "pct": round(len(no_acc) / len(all_clergy) * 100, 1) if all_clergy else 0, "sample": no_acc[:25]})


def _reporting_lag(db, state=None):
    query = db.query(AccusedClergy).filter(AccusedClergy.ordination_year.isnot(None))
    if state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())
    lags = []
    for c in query.all():
        earliest = db.query(func.min(Consequence.year)).filter(Consequence.clergy_id == c.id, Consequence.year.isnot(None), Consequence.consequence_type != "death").scalar()
        if earliest and c.ordination_year and 0 <= earliest - c.ordination_year <= 80:
            lags.append(earliest - c.ordination_year)
    if not lags:
        return _json_response({"total": 0})
    lags.sort()
    return _json_response({"total": len(lags), "avg_years": round(sum(lags) / len(lags), 1), "median_years": lags[len(lags) // 2], "min": lags[0], "max": lags[-1]})


def _transfer_network(db, state=None, min_transfers=2):
    multi = db.query(DioceseAssociation.clergy_id, func.count(distinct(DioceseAssociation.diocese_name)).label("cnt")).group_by(DioceseAssociation.clergy_id).having(func.count(distinct(DioceseAssociation.diocese_name)) > 1).all()
    edges = {}
    for row in multi:
        dioceses = db.query(DioceseAssociation).filter(DioceseAssociation.clergy_id == row.clergy_id).all()
        if state:
            dioceses = [d for d in dioceses if d.state == state.upper()]
        names = [d.diocese_name for d in dioceses]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                key = tuple(sorted([names[i], names[j]]))
                edges[key] = edges.get(key, 0) + 1
    filtered = [{"from": k[0], "to": k[1], "count": v} for k, v in edges.items() if v >= min_transfers]
    filtered.sort(key=lambda x: -x["count"])
    return _json_response({"multi_diocese_clergy": len(multi), "transfers": filtered[:50]})


def _temporal_clusters(db, consequence_type, state=None, bucket_size=5):
    query = db.query(Consequence).filter(Consequence.consequence_type == consequence_type, Consequence.year.isnot(None))
    if state:
        query = query.join(AccusedClergy).join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())
    buckets = {}
    for c in query.all():
        start = (c.year // bucket_size) * bucket_size
        key = f"{start}-{start + bucket_size - 1}"
        buckets[key] = buckets.get(key, 0) + 1
    return _json_response({"type": consequence_type, "clusters": sorted([{"period": k, "count": v} for k, v in buckets.items()], key=lambda x: x["period"])})


def _consequence_breakdown(db, state=None, diocese=None):
    query = db.query(Consequence.consequence_type, func.count().label("count"), func.count(distinct(Consequence.clergy_id)).label("unique"))
    if state or diocese:
        query = query.join(AccusedClergy).join(DioceseAssociation)
        if state:
            query = query.filter(DioceseAssociation.state == state.upper())
        if diocese:
            query = query.filter(DioceseAssociation.diocese_name.ilike(f"%{diocese}%"))
    results = query.group_by(Consequence.consequence_type).order_by(func.count().desc()).all()
    total = db.query(func.count(distinct(Consequence.clergy_id))).scalar()
    return _json_response({"total_clergy": total, "breakdown": [{"type": r.consequence_type, "count": r.count, "unique_clergy": r.unique, "pct": round(r.unique / total * 100, 1) if total else 0} for r in results]})


def _export_csv(db, state=None, diocese=None, status=None):
    import csv, io
    query = db.query(AccusedClergy)
    if state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())
    if diocese:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.diocese_name.ilike(f"%{diocese}%"))
    if status:
        query = query.filter(AccusedClergy.status == status)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "first_name", "last_name", "ordination_year", "deceased", "status", "diocese", "state"])
    for c in query.order_by(AccusedClergy.last_name).limit(1000).all():
        primary = next((d for d in c.diocese_associations if d.is_primary), None)
        writer.writerow([c.id, c.first_name, c.last_name, c.ordination_year or "", c.deceased, c.status or "", primary.diocese_name if primary else "", primary.state if primary else ""])
    return [TextContent(type="text", text=output.getvalue())]


# ============================================================
# MAIN
# ============================================================

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
