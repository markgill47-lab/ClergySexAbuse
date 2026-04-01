"""Import Anderson Advocates national data from the new scraper output."""

import json
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from src.backend.models import (
    AccusedClergy,
    Assignment,
    DioceseAssociation,
    Document,
    SourceRecord,
)


STATE_SLUG_TO_ABBREV = {
    "minnesota": "MN", "california": "CA", "pennsylvania": "PA",
    "illinois": "IL", "colorado": "CO", "hawaii": "HI",
    "louisiana": "LA", "wisconsin": "WI", "arizona": "AZ",
    "new-york": "NY", "new-jersey": "NJ", "maryland": "MD",
    "michigan": "MI", "vermont": "VT", "arkansas": "AR",
    "maine": "ME",
}


def _parse_name(name: str) -> tuple[str, str, str | None]:
    """Parse name from Anderson format."""
    name = name.strip()
    # Strip common prefixes
    name = re.sub(r"^(Fr\.|Rev\.|Msgr\.|Br\.|Sr\.|Deacon|Bishop|Father|Brother|Sister)\s+", "", name)

    suffix = None
    suffix_match = re.search(r"\b(Jr\.|Sr\.|III|IV|II)\s*$", name)
    if suffix_match:
        suffix = suffix_match.group(1)
        name = name[: suffix_match.start()].strip()

    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        return parts[1], parts[0], suffix

    parts = name.split()
    if len(parts) == 1:
        return "", parts[0], suffix
    elif len(parts) == 2:
        return parts[0], parts[1], suffix
    else:
        return " ".join(parts[:-1]), parts[-1], suffix


def _extract_ordination_year(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"\b(19\d{2}|20[0-2]\d)\b", text)
    return int(match.group(1)) if match else None


def _parse_assignment(text: str) -> dict | None:
    """Parse an assignment line like '1958-1961: St. Mary's Parish, Rochester, MN'."""
    match = re.match(r"(\d{4})[\s\-–—]+(\d{4})?[:\s]+(.+)", text)
    if not match:
        match = re.match(r"(\d{4})[:\s]+(.+)", text)
        if match:
            return {
                "start_year": int(match.group(1)),
                "end_year": None,
                "description": match.group(2).strip(),
            }
        return None

    return {
        "start_year": int(match.group(1)),
        "end_year": int(match.group(2)) if match.group(2) else None,
        "description": match.group(3).strip(),
    }


def _diocese_slug_to_name(slug: str) -> str:
    """Convert diocese slug to human-readable name."""
    return slug.replace("-", " ").title()


def import_anderson_national(
    session: Session,
    profiles_dir: Path = Path("data/raw/anderson/profiles"),
    pdfs_dir: Path = Path("data/raw/anderson/pdfs"),
) -> dict:
    """Import all Anderson Advocates national profile data.

    Returns stats dict.
    """
    stats = {
        "total": 0,
        "imported": 0,
        "skipped": 0,
        "assignments_created": 0,
        "documents_linked": 0,
    }

    profile_files = sorted(profiles_dir.glob("*.json"))
    profile_files = [f for f in profile_files if not f.name.startswith("_")]
    stats["total"] = len(profile_files)

    for pf in profile_files:
        try:
            with open(pf, "r", encoding="utf-8") as f:
                profile = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            stats["skipped"] += 1
            continue

        name = profile.get("name", "")
        if not name:
            stats["skipped"] += 1
            continue

        first_name, last_name, suffix = _parse_name(name)
        slug = profile.get("slug", pf.stem)
        state_slug = profile.get("state", "")
        state_abbrev = STATE_SLUG_TO_ABBREV.get(state_slug, state_slug.upper()[:2])

        ordination_year = _extract_ordination_year(profile.get("ordination_date"))
        ordination_decade = f"{(ordination_year // 10) * 10}s" if ordination_year else None

        # Build narrative
        narrative_parts = profile.get("narrative", [])
        narrative = "\n\n".join(narrative_parts) if isinstance(narrative_parts, list) else str(narrative_parts or "")

        photo_url = profile.get("image_url")

        clergy = AccusedClergy(
            first_name=first_name,
            last_name=last_name,
            suffix=suffix,
            ordination_year=ordination_year,
            ordination_decade=ordination_decade,
            status=profile.get("status") or "accused",
            religious_order=None,
            photo_url=photo_url,
            narrative=narrative if narrative else None,
        )
        session.add(clergy)
        session.flush()

        # Diocese associations
        all_dioceses = profile.get("all_dioceses", [])
        if not all_dioceses and profile.get("diocese"):
            all_dioceses = [profile["diocese"]]
        for i, diocese_slug in enumerate(all_dioceses):
            session.add(DioceseAssociation(
                clergy_id=clergy.id,
                diocese_name=_diocese_slug_to_name(diocese_slug),
                state=state_abbrev,
                is_primary=(i == 0),
            ))

        # Assignments
        for assignment_text in profile.get("assignments", []):
            parsed = _parse_assignment(assignment_text)
            if parsed:
                session.add(Assignment(
                    clergy_id=clergy.id,
                    institution_name=parsed["description"],
                    start_year=parsed["start_year"],
                    end_year=parsed["end_year"],
                ))
                stats["assignments_created"] += 1

        # Link local PDFs
        local_pdf_dir = pdfs_dir / slug
        if local_pdf_dir.exists():
            for pdf_file in local_pdf_dir.glob("*.pdf"):
                session.add(Document(
                    clergy_id=clergy.id,
                    doc_type="pdf",
                    title=pdf_file.stem.replace("-", " ").replace("_", " "),
                    local_path=str(pdf_file),
                ))
                stats["documents_linked"] += 1

        # Link PDF URLs from profile
        for pdf_info in profile.get("pdfs", []):
            url = pdf_info.get("url", "") if isinstance(pdf_info, dict) else str(pdf_info)
            if url:
                # Avoid duplicating local files already linked
                title = pdf_info.get("title", "") if isinstance(pdf_info, dict) else Path(url).stem
                session.add(Document(
                    clergy_id=clergy.id,
                    doc_type="pdf",
                    title=title,
                    url=url,
                ))
                stats["documents_linked"] += 1

        # Link YouTube videos
        for video in profile.get("youtube_videos", []):
            url = video.get("url", "") if isinstance(video, dict) else str(video)
            title = video.get("title", "YouTube Video") if isinstance(video, dict) else "YouTube Video"
            if url:
                session.add(Document(
                    clergy_id=clergy.id,
                    doc_type="video",
                    title=title,
                    url=url,
                ))
                stats["documents_linked"] += 1

        # Source record
        session.add(SourceRecord(
            clergy_id=clergy.id,
            source_name="anderson_national",
            source_url=profile.get("url"),
            scraped_at=datetime.utcnow(),
            raw_data=profile,
        ))

        stats["imported"] += 1

        # Periodic commit to avoid huge transactions
        if stats["imported"] % 200 == 0:
            session.commit()
            print(f"    ... {stats['imported']} / {stats['total']} imported")

    session.commit()
    return stats
