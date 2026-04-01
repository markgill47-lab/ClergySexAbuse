from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Date,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Index,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class AccusedClergy(Base):
    __tablename__ = "accused_clergy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    suffix = Column(Text)
    ordination_year = Column(Integer)
    ordination_decade = Column(Text)  # Fallback: "1970s"
    death_year = Column(Integer)
    deceased = Column(Boolean, default=False)
    status = Column(Text)  # accused, convicted, acquitted, removed, laicized, etc.
    religious_order = Column(Text)
    photo_url = Column(Text)
    narrative = Column(Text)  # Full narrative text from sources
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    diocese_associations = relationship("DioceseAssociation", back_populates="clergy", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="clergy", cascade="all, delete-orphan")
    allegations = relationship("Allegation", back_populates="clergy", cascade="all, delete-orphan")
    criminal_outcomes = relationship("CriminalOutcome", back_populates="clergy", cascade="all, delete-orphan")
    church_actions = relationship("ChurchAction", back_populates="clergy", cascade="all, delete-orphan")
    consequences = relationship("Consequence", back_populates="clergy", cascade="all, delete-orphan")
    source_records = relationship("SourceRecord", back_populates="clergy", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="clergy", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_clergy_name", "last_name", "first_name"),
        Index("ix_clergy_status", "status"),
        Index("ix_clergy_order", "religious_order"),
    )


class DioceseAssociation(Base):
    __tablename__ = "diocese_associations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clergy_id = Column(Integer, ForeignKey("accused_clergy.id", ondelete="CASCADE"), nullable=False)
    diocese_name = Column(Text, nullable=False)
    state = Column(Text)  # Two-letter code
    is_primary = Column(Boolean, default=False)

    clergy = relationship("AccusedClergy", back_populates="diocese_associations")

    __table_args__ = (
        Index("ix_diocese_state", "state"),
        Index("ix_diocese_name", "diocese_name"),
    )


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clergy_id = Column(Integer, ForeignKey("accused_clergy.id", ondelete="CASCADE"), nullable=False)
    institution_name = Column(Text)
    institution_type = Column(Text)  # parish, school, hospital, other
    city = Column(Text)
    state = Column(Text)
    start_year = Column(Integer)
    end_year = Column(Integer)
    role = Column(Text)

    clergy = relationship("AccusedClergy", back_populates="assignments")


class Allegation(Base):
    __tablename__ = "allegations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clergy_id = Column(Integer, ForeignKey("accused_clergy.id", ondelete="CASCADE"), nullable=False)
    year = Column(Integer)
    decade = Column(Text)  # Fallback: "1970s"
    victim_gender = Column(Text)
    victim_minor = Column(Boolean)
    allegation_type = Column(Text)  # sexualAbuse, rape, fondling, etc.
    substantiated = Column(Text)  # substantiated, unsubstantiated, unknown
    summary = Column(Text)

    clergy = relationship("AccusedClergy", back_populates="allegations")

    __table_args__ = (
        Index("ix_allegation_type", "allegation_type"),
        Index("ix_allegation_year", "year"),
    )


class CriminalOutcome(Base):
    __tablename__ = "criminal_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clergy_id = Column(Integer, ForeignKey("accused_clergy.id", ondelete="CASCADE"), nullable=False)
    outcome_type = Column(Text, nullable=False)  # convicted, charged, settled, noKnownAction
    year = Column(Integer)
    details = Column(Text)

    clergy = relationship("AccusedClergy", back_populates="criminal_outcomes")


class ChurchAction(Base):
    __tablename__ = "church_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clergy_id = Column(Integer, ForeignKey("accused_clergy.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(Text, nullable=False)  # laicized, removed, suspended, resigned, etc.
    year = Column(Integer)

    clergy = relationship("AccusedClergy", back_populates="church_actions")


class SourceRecord(Base):
    __tablename__ = "source_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clergy_id = Column(Integer, ForeignKey("accused_clergy.id", ondelete="CASCADE"), nullable=False)
    source_name = Column(Text, nullable=False)  # "bishop_accountability", "anderson_mn"
    source_url = Column(Text)
    scraped_at = Column(DateTime)
    raw_data = Column(JSON)  # Original scraped fields preserved

    clergy = relationship("AccusedClergy", back_populates="source_records")

    __table_args__ = (
        Index("ix_source_name", "source_name"),
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clergy_id = Column(Integer, ForeignKey("accused_clergy.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(Text)  # pdf, news_article, court_filing, video, image
    title = Column(Text)
    url = Column(Text)
    local_path = Column(Text)  # For downloaded PDFs/images
    publication_date = Column(Date)

    clergy = relationship("AccusedClergy", back_populates="documents")

    __table_args__ = (
        Index("ix_doc_type", "doc_type"),
    )


class Consequence(Base):
    """Tracks the full sequence of consequences for an accused individual.

    Each row is one event in the consequence chain:
    accusation → investigation → treatment → transfer → civil_suit →
    criminal_charges → conviction → church_discipline → reinstatement → ...

    The sequence_order field allows reconstructing the timeline.
    """
    __tablename__ = "consequences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clergy_id = Column(Integer, ForeignKey("accused_clergy.id", ondelete="CASCADE"), nullable=False)
    consequence_type = Column(Text, nullable=False)
    # Types: accusation, investigation, treatment, transfer, civil_suit, civil_settlement,
    #        criminal_charges, conviction, acquittal, incarceration, probation,
    #        laicized, removed_from_ministry, suspended, resigned, reinstated,
    #        banned_from_property, pension_continued, no_known_action, death
    year = Column(Integer)
    sequence_order = Column(Integer)  # Order within this clergy member's timeline
    facility_id = Column(Integer, ForeignKey("treatment_facilities.id"))
    from_diocese = Column(Text)  # For transfers: where they came from
    to_diocese = Column(Text)  # For transfers: where they went
    details = Column(Text)

    clergy = relationship("AccusedClergy", back_populates="consequences")
    facility = relationship("TreatmentFacility")

    __table_args__ = (
        Index("ix_consequence_type", "consequence_type"),
        Index("ix_consequence_year", "year"),
        Index("ix_consequence_facility", "facility_id"),
    )


class TreatmentFacility(Base):
    """Known treatment/retreat facilities where accused clergy were sent."""
    __tablename__ = "treatment_facilities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False, unique=True)
    aliases = Column(JSON)  # Alternative names / spelling variations
    city = Column(Text)
    state = Column(Text)
    country = Column(Text, default="US")
    facility_type = Column(Text)  # treatment_center, retreat, monastery, hospital
    notes = Column(Text)

    __table_args__ = (
        Index("ix_facility_name", "name"),
        Index("ix_facility_state", "state"),
    )


class ClergyRoster(Base):
    """Year-by-year priest assignments from official church records.

    Populated from tax-exempt filings, Official Catholic Directory, and other
    institutional sources. Covers ALL clergy, not just accused — enabling
    transfer detection and population-level analysis.
    """
    __tablename__ = "clergy_roster"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # May or may not link to accused_clergy — most roster entries are non-accused
    accused_clergy_id = Column(Integer, ForeignKey("accused_clergy.id"), nullable=True)
    # Name fields for matching (roster names may not match accused list exactly)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    suffix = Column(Text)
    # Assignment details
    diocese_name = Column(Text, nullable=False)
    state = Column(Text)
    parish_or_institution = Column(Text)
    role = Column(Text)  # pastor, associate pastor, administrator, etc.
    # Temporal
    roster_year = Column(Integer, nullable=False)  # Which year's roster this is from
    # Source
    source_name = Column(Text)  # "official_catholic_directory", "tax_filing_990", etc.
    source_year = Column(Integer)  # Publication year of the source document

    accused = relationship("AccusedClergy", foreign_keys=[accused_clergy_id])

    __table_args__ = (
        Index("ix_roster_year", "roster_year"),
        Index("ix_roster_name", "last_name", "first_name"),
        Index("ix_roster_diocese", "diocese_name"),
        Index("ix_roster_state", "state"),
        Index("ix_roster_accused", "accused_clergy_id"),
        # For transfer detection: find where a name appears across years
        Index("ix_roster_name_year", "last_name", "first_name", "roster_year"),
    )


class StateSummary(Base):
    __tablename__ = "state_summaries"

    state = Column(Text, primary_key=True)  # Two-letter code
    state_name = Column(Text, nullable=False)
    region = Column(Text)  # Northeast, Midwest, South, West
    population = Column(Integer)  # Census 2020
    catholic_population = Column(Integer)  # CARA estimates
    total_accused = Column(Integer, default=0)
    convicted_count = Column(Integer, default=0)
    deceased_count = Column(Integer, default=0)
