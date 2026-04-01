#!/usr/bin/env python3
"""Import all data sources into the unified database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backend.database import init_db, get_session
from src.backend.config import VUETEST_DATA, VUETEST_SUMMARIES, MN_PROFILES_DIR
from src.pipeline.importers.ba_json import import_ba_data, import_state_summaries
from src.pipeline.importers.anderson_json import import_anderson_data
from src.pipeline.importers.anderson_national import import_anderson_national
from src.pipeline.importers.facilities import seed_facilities
from src.pipeline.importers.consequences import extract_consequences
from src.pipeline.normalizer import deduplicate


ANDERSON_NATIONAL_DIR = Path("data/raw/anderson/profiles")
ANDERSON_NATIONAL_PDFS = Path("data/raw/anderson/pdfs")


def main():
    print("=" * 60)
    print("Clergy Abuse Data Import — Full Pipeline")
    print("=" * 60)

    engine = init_db()
    session = get_session(engine)

    step = 0

    # 1. BA.org data
    step += 1
    print(f"\n[{step}] BishopAccountability.org data...")
    if VUETEST_DATA.exists():
        stats = import_ba_data(session)
        print(f"  Imported: {stats['imported']} / {stats['total']}")
    else:
        print(f"  SKIP: {VUETEST_DATA}")

    # 2. State summaries
    step += 1
    print(f"\n[{step}] State summaries...")
    if VUETEST_SUMMARIES.exists():
        count = import_state_summaries(session)
        print(f"  Imported: {count} states")
    else:
        print(f"  SKIP: {VUETEST_SUMMARIES}")

    # 3. Anderson MN deep profiles (from prior project)
    step += 1
    print(f"\n[{step}] Anderson MN profiles (prior project)...")
    if MN_PROFILES_DIR.exists():
        stats = import_anderson_data(session)
        print(f"  Imported: {stats['imported']} / {stats['total']}")
        print(f"  Documents: {stats['documents_linked']}")
    else:
        print(f"  SKIP: {MN_PROFILES_DIR}")

    # 4. Anderson national profiles (new scrape)
    step += 1
    print(f"\n[{step}] Anderson national profiles...")
    if ANDERSON_NATIONAL_DIR.exists():
        stats = import_anderson_national(session, ANDERSON_NATIONAL_DIR, ANDERSON_NATIONAL_PDFS)
        print(f"  Imported: {stats['imported']} / {stats['total']}")
        print(f"  Assignments: {stats['assignments_created']}")
        print(f"  Documents: {stats['documents_linked']}")
    else:
        print(f"  SKIP: {ANDERSON_NATIONAL_DIR}")

    # 5. Deduplication
    step += 1
    print(f"\n[{step}] Deduplication...")
    dedup_stats = deduplicate(session)
    print(f"  Groups: {dedup_stats['groups_found']}, Merged: {dedup_stats['records_merged']}")

    # 6. Seed facilities
    step += 1
    print(f"\n[{step}] Treatment facilities...")
    fac_count = seed_facilities(session)
    print(f"  Seeded: {fac_count}")

    # 7. Extract consequences
    step += 1
    print(f"\n[{step}] Consequence timelines...")
    cons_stats = extract_consequences(session)
    print(f"  Processed: {cons_stats['clergy_processed']}")
    print(f"  Consequences: {cons_stats['consequences_created']}")
    print(f"  Facility refs: {cons_stats['facility_refs_found']}")

    # Final report
    from sqlalchemy import func
    from src.backend.models import (
        AccusedClergy, DioceseAssociation, Assignment, Allegation,
        CriminalOutcome, ChurchAction, Consequence, TreatmentFacility,
        SourceRecord, Document, StateSummary, ClergyRoster
    )

    print("\n" + "=" * 60)
    print("DATABASE SUMMARY")
    print("=" * 60)
    counts = {
        "Accused clergy": session.query(func.count(AccusedClergy.id)).scalar(),
        "Diocese associations": session.query(func.count(DioceseAssociation.id)).scalar(),
        "Assignments": session.query(func.count(Assignment.id)).scalar(),
        "Allegations": session.query(func.count(Allegation.id)).scalar(),
        "Criminal outcomes": session.query(func.count(CriminalOutcome.id)).scalar(),
        "Church actions": session.query(func.count(ChurchAction.id)).scalar(),
        "Consequences": session.query(func.count(Consequence.id)).scalar(),
        "Facilities": session.query(func.count(TreatmentFacility.id)).scalar(),
        "Roster entries": session.query(func.count(ClergyRoster.id)).scalar(),
        "Source records": session.query(func.count(SourceRecord.id)).scalar(),
        "Documents": session.query(func.count(Document.id)).scalar(),
        "State summaries": session.query(func.count(StateSummary.state)).scalar(),
    }
    for label, val in counts.items():
        print(f"  {label:25s} {val:>8,}")

    print("\n  Sources:")
    for source, count in session.query(SourceRecord.source_name, func.count()).group_by(SourceRecord.source_name).order_by(func.count().desc()).all():
        print(f"    {source:30s} {count:>6,}")

    print("\n  Consequence types:")
    for ctype, count in (
        session.query(Consequence.consequence_type, func.count())
        .group_by(Consequence.consequence_type)
        .order_by(func.count().desc())
        .limit(10)
        .all()
    ):
        print(f"    {ctype:30s} {count:>6,}")

    session.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
