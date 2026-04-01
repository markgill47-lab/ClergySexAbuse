"""Deduplication and cross-source matching logic."""

import re
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.backend.models import AccusedClergy, DioceseAssociation, SourceRecord


def normalize_name(name: str) -> str:
    """Normalize a name for comparison: lowercase, strip punctuation, collapse whitespace."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def find_duplicates(session: Session) -> list[list[int]]:
    """Find potential duplicate clergy entries across sources.

    Returns list of groups, where each group is a list of clergy IDs that likely refer
    to the same person.
    """
    # Build lookup by normalized (last_name, first_name)
    all_clergy = session.query(AccusedClergy).all()
    name_groups: dict[str, list[AccusedClergy]] = defaultdict(list)

    for c in all_clergy:
        key = f"{normalize_name(c.last_name)}|{normalize_name(c.first_name)}"
        name_groups[key].append(c)

    duplicate_groups = []
    for key, group in name_groups.items():
        if len(group) < 2:
            continue

        # Check if they come from different sources
        sources_per_member = {}
        for c in group:
            src = session.query(SourceRecord.source_name).filter(SourceRecord.clergy_id == c.id).first()
            sources_per_member[c.id] = src[0] if src else "unknown"

        unique_sources = set(sources_per_member.values())
        if len(unique_sources) > 1:
            # Cross-source duplicate — high confidence match
            duplicate_groups.append([c.id for c in group])
        elif len(group) > 1:
            # Same source — check if ordination year and state also match
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    if a.ordination_year and b.ordination_year and a.ordination_year == b.ordination_year:
                        duplicate_groups.append([a.id, b.id])

    return duplicate_groups


def merge_clergy(session: Session, keep_id: int, remove_id: int):
    """Merge two clergy records, keeping the one with keep_id.

    Moves all child records from remove_id to keep_id, then merges
    fields (preferring non-null values from remove_id if keep_id is null).
    """
    keep = session.get(AccusedClergy, keep_id)
    remove = session.get(AccusedClergy, remove_id)
    if not keep or not remove:
        return

    # Merge scalar fields (prefer keep, fill gaps from remove)
    for field in ["ordination_year", "ordination_decade", "death_year", "status",
                   "religious_order", "photo_url"]:
        if getattr(keep, field) is None and getattr(remove, field) is not None:
            setattr(keep, field, getattr(remove, field))

    # Merge narrative (append if different)
    if remove.narrative and keep.narrative and remove.narrative not in keep.narrative:
        keep.narrative = keep.narrative + "\n\n---\n\n" + remove.narrative
    elif remove.narrative and not keep.narrative:
        keep.narrative = remove.narrative

    if remove.deceased and not keep.deceased:
        keep.deceased = True

    # Move all child records
    for rel_name in ["diocese_associations", "assignments", "allegations",
                      "criminal_outcomes", "church_actions", "source_records", "documents"]:
        for child in getattr(remove, rel_name):
            child.clergy_id = keep_id

    session.delete(remove)
    session.flush()


def deduplicate(session: Session) -> dict:
    """Find and merge duplicate clergy records.

    Returns stats about what was merged.
    """
    groups = find_duplicates(session)
    stats = {"groups_found": len(groups), "records_merged": 0}

    for group_ids in groups:
        if len(group_ids) < 2:
            continue
        # Keep the first one (typically the one with more data)
        keep_id = group_ids[0]
        for remove_id in group_ids[1:]:
            merge_clergy(session, keep_id, remove_id)
            stats["records_merged"] += 1

    session.commit()
    return stats
