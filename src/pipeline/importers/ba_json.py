"""Import BishopAccountability.org data from the VueTest project's clergy_all_states.json."""

import json
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from src.backend.config import VUETEST_DATA, VUETEST_SUMMARIES
from src.backend.models import (
    AccusedClergy,
    Allegation,
    ChurchAction,
    CriminalOutcome,
    DioceseAssociation,
    SourceRecord,
    StateSummary,
)


def parse_name(full_name: str) -> tuple[str, str, str | None]:
    """Parse a full name into (first_name, last_name, suffix).

    Handles formats like:
    - "Fr. Frances Mary (David) Stone"
    - "John Smith Jr."
    - "Smith, John"
    """
    # Strip common prefixes
    name = re.sub(r"^(Fr\.|Rev\.|Msgr\.|Br\.|Sr\.|Deacon|Bishop|Father|Brother|Sister)\s+", "", full_name.strip())

    # Detect suffix
    suffix = None
    suffix_match = re.search(r"\b(Jr\.|Sr\.|III|IV|II)\s*$", name)
    if suffix_match:
        suffix = suffix_match.group(1)
        name = name[: suffix_match.start()].strip()

    # Handle "Last, First" format
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        return parts[1], parts[0], suffix

    # Handle "First Middle Last" format
    parts = name.split()
    if len(parts) == 1:
        return "", parts[0], suffix
    elif len(parts) == 2:
        return parts[0], parts[1], suffix
    else:
        return " ".join(parts[:-1]), parts[-1], suffix


DEMOGRAPHIC_TO_GENDER = {
    "minorMale": ("male", True),
    "minorFemale": ("female", True),
    "minorUnspecified": (None, True),
    "adult": (None, False),
    "adultMale": ("male", False),
    "adultFemale": ("female", False),
}


def import_ba_data(session: Session, data_path: Path = VUETEST_DATA) -> dict:
    """Import BA.org clergy data from clergy_all_states.json.

    Returns stats dict with counts.
    """
    with open(data_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    stats = {"total": len(entries), "imported": 0, "skipped": 0}

    for entry in entries:
        name = entry.get("name", "").strip()
        if not name:
            stats["skipped"] += 1
            continue

        first_name, last_name, suffix = parse_name(name)

        clergy = AccusedClergy(
            first_name=first_name,
            last_name=last_name,
            suffix=suffix,
            ordination_year=entry.get("ordained"),
            ordination_decade=str(entry["ordinationDecade"]) + "s" if entry.get("ordinationDecade") else None,
            death_year=entry.get("deathYear"),
            deceased=entry.get("deceased", False),
            status=entry.get("status"),
            religious_order=entry.get("order"),
            narrative=entry.get("narrative"),
        )
        session.add(clergy)
        session.flush()  # Get the ID

        # Diocese association
        diocese = entry.get("diocese")
        state = entry.get("state")
        if diocese:
            session.add(DioceseAssociation(
                clergy_id=clergy.id,
                diocese_name=diocese,
                state=state,
                is_primary=True,
            ))

        # Allegations from victim demographics and types
        victim_demographics = entry.get("victimDemographics", [])
        allegation_types = entry.get("allegationTypes", [])

        # Create allegations from demographics
        for demo in victim_demographics:
            gender, is_minor = DEMOGRAPHIC_TO_GENDER.get(demo, (None, None))
            # Pair with each allegation type, or create a generic one
            if allegation_types:
                for atype in allegation_types:
                    session.add(Allegation(
                        clergy_id=clergy.id,
                        victim_gender=gender,
                        victim_minor=is_minor,
                        allegation_type=atype,
                    ))
            else:
                session.add(Allegation(
                    clergy_id=clergy.id,
                    victim_gender=gender,
                    victim_minor=is_minor,
                ))

        # If no demographics but has types, create type-only allegations
        if not victim_demographics and allegation_types:
            for atype in allegation_types:
                session.add(Allegation(
                    clergy_id=clergy.id,
                    allegation_type=atype,
                ))

        # Criminal outcome
        criminal_outcome = entry.get("criminalOutcome")
        if criminal_outcome:
            session.add(CriminalOutcome(
                clergy_id=clergy.id,
                outcome_type=criminal_outcome,
            ))

        # Church actions
        for action in entry.get("churchActions", []):
            session.add(ChurchAction(
                clergy_id=clergy.id,
                action_type=action,
            ))

        # Source record (preserve original data)
        session.add(SourceRecord(
            clergy_id=clergy.id,
            source_name="bishop_accountability",
            scraped_at=datetime.utcnow(),
            raw_data=entry,
        ))

        stats["imported"] += 1

    session.commit()
    return stats


def import_state_summaries(session: Session, summaries_path: Path = VUETEST_SUMMARIES) -> int:
    """Import state summary data from state_summaries.json."""
    with open(summaries_path, "r", encoding="utf-8") as f:
        summaries = json.load(f)

    count = 0
    for entry in summaries:
        summary = StateSummary(
            state=entry.get("code", entry.get("abbr", "")),
            state_name=entry.get("name", ""),
            region=entry.get("region"),
            population=entry.get("pop"),
            catholic_population=entry.get("cathPop"),
            total_accused=entry.get("totalAccused", 0),
            convicted_count=entry.get("convicted", 0),
            deceased_count=entry.get("deceased", 0),
        )
        session.merge(summary)  # merge to handle re-imports
        count += 1

    session.commit()
    return count
