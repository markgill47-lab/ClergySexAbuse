"""Document serving endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from pathlib import Path

from src.backend.database import get_session
from src.backend.models import Document, AccusedClergy

router = APIRouter()


def get_db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


@router.get("")
async def list_documents(
    clergy_id: Optional[int] = None,
    doc_type: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List documents with filters."""
    query = db.query(Document)

    if clergy_id:
        query = query.filter(Document.clergy_id == clergy_id)
    if doc_type:
        query = query.filter(Document.doc_type == doc_type)
    if q:
        query = query.filter(Document.title.ilike(f"%{q}%"))

    total = query.count()
    results = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "results": [
            {
                "id": d.id,
                "clergy_id": d.clergy_id,
                "doc_type": d.doc_type,
                "title": d.title,
                "url": d.url,
                "has_local": bool(d.local_path),
            }
            for d in results
        ],
    }


@router.get("/{doc_id}")
async def get_document(doc_id: int, db: Session = Depends(get_db)):
    """Get document metadata."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "clergy_id": doc.clergy_id,
        "doc_type": doc.doc_type,
        "title": doc.title,
        "url": doc.url,
        "local_path": doc.local_path,
        "publication_date": str(doc.publication_date) if doc.publication_date else None,
    }


@router.get("/{doc_id}/file")
async def serve_document_file(doc_id: int, db: Session = Depends(get_db)):
    """Serve the actual document file (PDF, image, etc.)."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.local_path:
        raise HTTPException(status_code=404, detail="No local file for this document")

    path = Path(doc.local_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found on disk")

    return FileResponse(path)
