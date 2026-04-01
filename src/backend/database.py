from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from src.backend.config import DATABASE_URL, DB_DIR
from src.backend.models import Base


def get_engine(url: str = DATABASE_URL):
    DB_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, echo=False)
    # Enable WAL mode and foreign keys for SQLite
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def init_db(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session(engine=None) -> Session:
    if engine is None:
        engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
