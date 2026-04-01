"""Export endpoints — CSV and Excel downloads."""

import io
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.backend.database import get_session
from src.backend.models import AccusedClergy, DioceseAssociation, Allegation, CriminalOutcome, ChurchAction

router = APIRouter()


def get_db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def build_clergy_query(db: Session, state: Optional[str], diocese: Optional[str], status: Optional[str]):
    query = db.query(AccusedClergy)
    if state:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.state == state.upper())
    if diocese:
        query = query.join(DioceseAssociation).filter(DioceseAssociation.diocese_name.ilike(f"%{diocese}%"))
    if status:
        query = query.filter(AccusedClergy.status == status)
    return query.order_by(AccusedClergy.last_name, AccusedClergy.first_name)


@router.get("/csv")
async def export_csv(
    state: Optional[str] = None,
    diocese: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Export filtered clergy data as CSV."""
    import csv

    query = build_clergy_query(db, state, diocese, status)
    results = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "first_name", "last_name", "suffix", "ordination_year", "ordination_decade",
        "death_year", "deceased", "status", "religious_order", "primary_diocese", "primary_state",
    ])

    for c in results:
        primary = next((d for d in c.diocese_associations if d.is_primary), None)
        writer.writerow([
            c.id, c.first_name, c.last_name, c.suffix or "", c.ordination_year or "",
            c.ordination_decade or "", c.death_year or "", c.deceased, c.status or "",
            c.religious_order or "",
            primary.diocese_name if primary else "",
            primary.state if primary else "",
        ])

    output.seek(0)
    filename = "clergy_export"
    if state:
        filename += f"_{state}"
    filename += ".csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/xlsx")
async def export_xlsx(
    state: Optional[str] = None,
    diocese: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Export filtered clergy data as Excel workbook with multiple sheets."""
    try:
        import openpyxl
    except ImportError:
        return {"error": "openpyxl not installed. Run: pip install openpyxl"}

    wb = openpyxl.Workbook()

    # Sheet 1: Clergy list
    ws = wb.active
    ws.title = "Accused Clergy"
    headers = [
        "ID", "First Name", "Last Name", "Suffix", "Ordination Year", "Ordination Decade",
        "Death Year", "Deceased", "Status", "Religious Order", "Primary Diocese", "State",
    ]
    ws.append(headers)

    query = build_clergy_query(db, state, diocese, status)
    for c in query.all():
        primary = next((d for d in c.diocese_associations if d.is_primary), None)
        ws.append([
            c.id, c.first_name, c.last_name, c.suffix or "", c.ordination_year,
            c.ordination_decade or "", c.death_year, c.deceased, c.status or "",
            c.religious_order or "",
            primary.diocese_name if primary else "",
            primary.state if primary else "",
        ])

    # Sheet 2: Summary stats
    ws2 = wb.create_sheet("Summary")
    ws2.append(["Metric", "Value"])
    total = query.count()
    ws2.append(["Total Records", total])
    deceased_count = query.filter(AccusedClergy.deceased == True).count()
    ws2.append(["Deceased", deceased_count])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = "clergy_export"
    if state:
        filename += f"_{state}"
    filename += ".xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
