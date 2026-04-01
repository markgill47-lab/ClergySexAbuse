"""Import UNM/CSWR Santa Fe archive metadata into the unified database."""

import json
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from src.backend.models import (
    AccusedClergy,
    DioceseAssociation,
    Document,
    SourceRecord,
)


def _parse_clergy_name(name: str) -> tuple[str, str, str | None]:
    """Parse clergy name from Santa Fe archive format."""
    name = name.strip()
    # Strip prefixes
    name = re.sub(r"^(Fr\.|Msgr\.|Br\.|Dn\.|Archbishop|Bishop|Rev\.|Father)\s+", "", name)

    suffix = None
    suffix_match = re.search(r"\b(Jr\.|Sr\.|III|IV|II)\s*$", name)
    if suffix_match:
        suffix = suffix_match.group(1)
        name = name[: suffix_match.start()].strip()

    parts = name.split()
    if len(parts) == 1:
        return "", parts[0], suffix
    elif len(parts) == 2:
        return parts[0], parts[1], suffix
    else:
        return " ".join(parts[:-1]), parts[-1], suffix


def import_santa_fe(
    session: Session,
    index_path: Path = Path("data/raw/santa_fe/_index.json"),
) -> dict:
    """Import Santa Fe archive data.

    Creates clergy records for personnel files (one per individual),
    and links all documents (depositions, timelines, etc.) to their
    corresponding clergy records.
    """
    if not index_path.exists():
        return {"error": f"Index not found: {index_path}"}

    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    stats = {
        "total_items": len(index.get("items", [])),
        "clergy_created": 0,
        "documents_linked": 0,
        "skipped": 0,
    }

    # Group items by clergy name
    clergy_items: dict[str, list[dict]] = {}
    unlinked_items: list[dict] = []

    for item in index.get("items", []):
        clergy_name = item.get("clergy_name")
        if clergy_name:
            normalized = clergy_name.lower().strip()
            clergy_items.setdefault(normalized, []).append(item)
        else:
            unlinked_items.append(item)

    # Create clergy records from personnel files first, then link other docs
    clergy_id_map: dict[str, int] = {}  # normalized_name → clergy_id

    for normalized_name, items in clergy_items.items():
        # Find the "richest" item (personnel file preferred) to create the clergy record from
        personnel_items = [i for i in items if i.get("doc_type") == "personnel_file"]
        primary = personnel_items[0] if personnel_items else items[0]

        name = primary["clergy_name"]
        first_name, last_name, suffix = _parse_clergy_name(name)

        # Check if this clergy already exists in the DB (from BA.org or Anderson)
        from sqlalchemy import func
        existing = (
            session.query(AccusedClergy)
            .filter(
                func.lower(AccusedClergy.last_name) == last_name.lower(),
                func.lower(AccusedClergy.first_name).like(f"%{first_name.lower().split()[0] if first_name else ''}%"),
            )
            .first()
        )

        if existing:
            clergy_id = existing.id
        else:
            # Create new clergy record
            clergy = AccusedClergy(
                first_name=first_name,
                last_name=last_name,
                suffix=suffix,
                status="accused",
            )
            session.add(clergy)
            session.flush()
            clergy_id = clergy.id

            # Add diocese association
            session.add(DioceseAssociation(
                clergy_id=clergy_id,
                diocese_name="Archdiocese of Santa Fe",
                state="NM",
                is_primary=True,
            ))

            # Source record
            session.add(SourceRecord(
                clergy_id=clergy_id,
                source_name="santa_fe_archive",
                source_url=primary.get("item_url"),
                scraped_at=datetime.utcnow(),
                raw_data=primary,
            ))

            stats["clergy_created"] += 1

        clergy_id_map[normalized_name] = clergy_id

        # Link ALL items for this clergy as documents
        for item in items:
            session.add(Document(
                clergy_id=clergy_id,
                doc_type=item.get("doc_type", "archive_document"),
                title=item.get("full_title") or item.get("title", ""),
                url=item.get("pdf_url") or item.get("item_url"),
                local_path=item.get("local_path"),
            ))
            stats["documents_linked"] += 1

    # Link unlinked items (institutional documents without a specific clergy name)
    # These are policies, surveys, and institutional depositions
    for item in unlinked_items:
        # Store as documents without a clergy link — we'll need a general documents table later
        # For now, skip them but count them
        stats["skipped"] += 1

    session.commit()
    return stats
