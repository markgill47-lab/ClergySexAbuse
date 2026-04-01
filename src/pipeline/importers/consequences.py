"""Extract consequence sequences from existing imported data.

Transforms the flat criminal_outcomes and church_actions into ordered
consequence timelines, and links treatment facility references.
"""

import re
from sqlalchemy.orm import Session

from src.backend.models import (
    AccusedClergy,
    ChurchAction,
    Consequence,
    CriminalOutcome,
    TreatmentFacility,
)


# Map existing church_actions to consequence types
CHURCH_ACTION_MAP = {
    "laicized": "laicized",
    "removedFromMinistry": "removed_from_ministry",
    "suspended": "suspended",
    "resigned": "resigned",
    "reinstated": "reinstated",
    "banned": "banned_from_property",
    "permanentlyRemoved": "removed_from_ministry",
}

# Map existing criminal outcomes to consequence types
CRIMINAL_OUTCOME_MAP = {
    "convicted": "conviction",
    "charged": "criminal_charges",
    "noKnownAction": "no_known_action",
    "civilSettlement": "civil_settlement",
    "civilSuit": "civil_suit",
    "noConviction": "acquittal",
}

# Treatment facility keywords to search narratives for
FACILITY_KEYWORDS = [
    "paraclete", "via coeli", "jemez", "st. luke", "saint luke",
    "institute of living", "hartford", "southdown", "guest house",
    "vianney", "seton", "menninger", "shalom center", "john xxiii",
    "treatment center", "treatment facility", "treatment program",
    "sent for treatment", "underwent treatment", "residential treatment",
    "retreat", "psychiatric", "therapy program",
]


def extract_consequences(session: Session) -> dict:
    """Build consequence timelines from existing criminal_outcomes, church_actions, and narratives."""
    stats = {"clergy_processed": 0, "consequences_created": 0, "facility_refs_found": 0}

    # Load facility lookup
    facilities = session.query(TreatmentFacility).all()
    facility_lookup = {}
    for f in facilities:
        facility_lookup[f.name.lower()] = f.id
        for alias in (f.aliases or []):
            if alias:
                facility_lookup[alias.lower()] = f.id

    all_clergy = session.query(AccusedClergy).all()

    for clergy in all_clergy:
        seq = 0
        consequences = []

        # 1. Criminal outcomes → consequences
        for outcome in clergy.criminal_outcomes:
            ctype = CRIMINAL_OUTCOME_MAP.get(outcome.outcome_type, outcome.outcome_type)
            consequences.append(Consequence(
                clergy_id=clergy.id,
                consequence_type=ctype,
                year=outcome.year,
                details=outcome.details,
            ))

        # 2. Church actions → consequences
        for action in clergy.church_actions:
            ctype = CHURCH_ACTION_MAP.get(action.action_type, action.action_type)
            consequences.append(Consequence(
                clergy_id=clergy.id,
                consequence_type=ctype,
                year=action.year,
            ))

        # 3. Scan narrative for treatment facility references
        narrative = clergy.narrative or ""
        narrative_lower = narrative.lower()
        matched_facilities = set()

        for keyword in FACILITY_KEYWORDS:
            if keyword in narrative_lower:
                # Try to match to a specific facility
                for fname, fid in facility_lookup.items():
                    if fname in narrative_lower and fid not in matched_facilities:
                        matched_facilities.add(fid)
                        consequences.append(Consequence(
                            clergy_id=clergy.id,
                            consequence_type="treatment",
                            facility_id=fid,
                            details=f"Narrative mentions {fname}",
                        ))
                        stats["facility_refs_found"] += 1

                # Generic treatment reference if no specific facility matched
                if not matched_facilities and any(
                    kw in narrative_lower
                    for kw in ["sent for treatment", "underwent treatment", "treatment center",
                               "treatment facility", "treatment program", "residential treatment"]
                ):
                    consequences.append(Consequence(
                        clergy_id=clergy.id,
                        consequence_type="treatment",
                        details="Narrative references treatment (facility unidentified)",
                    ))
                break  # One treatment consequence per narrative scan

        # 4. Death as consequence (they got away with it)
        if clergy.deceased:
            consequences.append(Consequence(
                clergy_id=clergy.id,
                consequence_type="death",
                year=clergy.death_year,
            ))

        # 5. Posthumous accusation detection
        # If death_year exists and is before or near the scrape date, and status is still "Accused",
        # this may be a posthumous case. The narrative often contains clues.
        if clergy.deceased and clergy.death_year:
            if "posthumous" in narrative_lower or "after his death" in narrative_lower or "died before" in narrative_lower:
                consequences.append(Consequence(
                    clergy_id=clergy.id,
                    consequence_type="posthumous_accusation",
                    year=clergy.death_year,
                    details="Accused after death",
                ))

        # Assign sequence order (sort by year where available, then type)
        type_priority = {
            "accusation": 0, "investigation": 1, "treatment": 2, "transfer": 3,
            "civil_suit": 4, "civil_settlement": 5, "criminal_charges": 6,
            "conviction": 7, "acquittal": 7, "incarceration": 8, "probation": 8,
            "suspended": 9, "removed_from_ministry": 10, "laicized": 11,
            "reinstated": 12, "banned_from_property": 13,
            "no_known_action": 14, "death": 15, "posthumous_accusation": 16,
        }

        consequences.sort(key=lambda c: (c.year or 9999, type_priority.get(c.consequence_type, 99)))
        for i, cons in enumerate(consequences):
            cons.sequence_order = i + 1
            session.add(cons)

        if consequences:
            stats["clergy_processed"] += 1
            stats["consequences_created"] += len(consequences)

    session.commit()
    return stats
