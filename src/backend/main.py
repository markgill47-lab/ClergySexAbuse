"""FastAPI application — unified clergy abuse data platform."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.database import init_db, get_engine
from src.backend.routes import clergy, analytics, consequences, crossref, export, documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = init_db()
    app.state.engine = engine
    yield


app = FastAPI(
    title="Clergy Abuse Data API",
    description="Agent-first API for querying normalized clergy sex abuse data across multiple sources.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clergy.router, prefix="/api/v1/clergy", tags=["clergy"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(consequences.router, prefix="/api/v1/consequences", tags=["consequences"])
app.include_router(crossref.router, prefix="/api/v1/crossref", tags=["crossref"])
app.include_router(export.router, prefix="/api/v1/export", tags=["export"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/info")
async def info():
    from sqlalchemy import func
    from src.backend.database import get_session
    from src.backend.models import AccusedClergy, SourceRecord, Document, StateSummary

    session = get_session(app.state.engine)
    try:
        total_clergy = session.query(func.count(AccusedClergy.id)).scalar()
        source_counts = dict(
            session.query(SourceRecord.source_name, func.count())
            .group_by(SourceRecord.source_name)
            .all()
        )
        total_documents = session.query(func.count(Document.id)).scalar()
        total_states = session.query(func.count(StateSummary.state)).scalar()

        return {
            "total_clergy": total_clergy,
            "total_documents": total_documents,
            "states_covered": total_states,
            "sources": source_counts,
        }
    finally:
        session.close()
