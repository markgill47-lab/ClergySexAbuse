"""Import Anderson Advocates MN data from the MN-Clergy-Abuse project's profile JSONs."""

import json
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from src.backend.config import MN_PROFILES_DIR, MN_INDEX, MN_PDFS_DIR, MN_IMAGES_DIR, MN_PORTRAITS_DIR
from src.backend.models import (
    AccusedClergy,
    DioceseAssociation,
    Document,
    SourceRecord,
)


DIOCESE_SLUG_TO_NAME = {
    "archdiocese-of-saint-paul-minneapolis": "Archdiocese of Saint Paul and Minneapolis",
    "diocese-of-duluth": "Diocese of Duluth",
    "saint-johns-abbey": "Saint John's Abbey (Order of Saint Benedict)",
    "diocese-of-winona": "Diocese of Winona",
    "oblates-of-mary-immaculate": "Oblates of Mary Immaculate",
    "diocese-of-crookston": "Diocese of Crookston",
    "diocese-of-new-ulm": "Diocese of New Ulm",
    "diocese-of-saint-cloud": "Diocese of Saint Cloud",
}


def parse_anderson_name(name: str) -> tuple[str, str, str | None]:
    """Parse Anderson-format name: 'Last, First' or 'First Last'."""
    name = name.strip()

    # Detect suffix
    suffix = None
    suffix_match = re.search(r"\b(Jr\.|Sr\.|III|IV|II)\s*$", name)
    if suffix_match:
        suffix = suffix_match.group(1)
        name = name[: suffix_match.start()].strip()

    # "Last, First" format (Anderson default)
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        return parts[1], parts[0], suffix

    # "First Last" format
    parts = name.split()
    if len(parts) == 1:
        return "", parts[0], suffix
    elif len(parts) == 2:
        return parts[0], parts[1], suffix
    else:
        return " ".join(parts[:-1]), parts[-1], suffix


def extract_ordination_year(text: str | None) -> int | None:
    """Try to extract an ordination year from narrative text."""
    if not text:
        return None
    match = re.search(r"ordained.*?(\d{4})", text, re.IGNORECASE)
    if match:
        year = int(match.group(1))
        if 1900 <= year <= 2030:
            return year
    # Try just finding a year in the string
    match = re.search(r"\b(19\d{2}|20[0-2]\d)\b", text)
    if match:
        return int(match.group(1))
    return None


def import_anderson_data(session: Session, profiles_dir: Path = MN_PROFILES_DIR) -> dict:
    """Import Anderson Advocates MN profile data.

    Returns stats dict with counts.
    """
    index_path = profiles_dir / "_index.json"
    if not index_path.exists():
        return {"error": f"Index not found: {index_path}"}

    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)

    stats = {
        "total": index.get("total_profiles", 0),
        "imported": 0,
        "skipped": 0,
        "documents_linked": 0,
    }

    for profile_meta in index.get("profiles", []):
        slug = profile_meta["slug"]
        profile_path = profiles_dir / f"{slug}.json"

        if not profile_path.exists():
            stats["skipped"] += 1
            continue

        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)

        name = profile.get("name", "")
        if not name:
            stats["skipped"] += 1
            continue

        first_name, last_name, suffix = parse_anderson_name(name)

        # Build narrative from paragraphs array
        narrative_parts = profile.get("narrative", [])
        narrative = "\n\n".join(narrative_parts) if isinstance(narrative_parts, list) else str(narrative_parts)

        ordination_year = extract_ordination_year(profile.get("ordination_date"))
        ordination_decade = f"{(ordination_year // 10) * 10}s" if ordination_year else None

        # Check for portrait
        photo_url = profile.get("image_url")
        if not photo_url:
            # Check local portraits
            for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                portrait_path = MN_PORTRAITS_DIR / f"{slug}{ext}"
                if portrait_path.exists():
                    photo_url = str(portrait_path)
                    break

        clergy = AccusedClergy(
            first_name=first_name,
            last_name=last_name,
            suffix=suffix,
            ordination_year=ordination_year,
            ordination_decade=ordination_decade,
            status="accused",  # Anderson lists all as accused
            religious_order=None,
            photo_url=photo_url,
            narrative=narrative,
        )
        session.add(clergy)
        session.flush()

        # Diocese associations
        all_dioceses = profile.get("all_dioceses", [profile.get("diocese")])
        for i, diocese_slug in enumerate(all_dioceses):
            if diocese_slug:
                diocese_name = DIOCESE_SLUG_TO_NAME.get(diocese_slug, diocese_slug.replace("-", " ").title())
                session.add(DioceseAssociation(
                    clergy_id=clergy.id,
                    diocese_name=diocese_name,
                    state="MN",
                    is_primary=(i == 0),
                ))

        # Link PDFs as documents
        pdf_dir = MN_PDFS_DIR / slug
        if pdf_dir.exists():
            for pdf_file in pdf_dir.glob("*.pdf"):
                session.add(Document(
                    clergy_id=clergy.id,
                    doc_type="pdf",
                    title=pdf_file.stem.replace("-", " ").replace("_", " "),
                    local_path=str(pdf_file),
                ))
                stats["documents_linked"] += 1

        # Link PDFs from profile data
        for pdf_info in profile.get("pdfs", []):
            url = pdf_info if isinstance(pdf_info, str) else pdf_info.get("url", "")
            if url:
                session.add(Document(
                    clergy_id=clergy.id,
                    doc_type="pdf",
                    title=pdf_info.get("title", "") if isinstance(pdf_info, dict) else Path(url).stem,
                    url=url,
                ))
                stats["documents_linked"] += 1

        # Link YouTube videos
        for video in profile.get("youtube_videos", []):
            url = video if isinstance(video, str) else video.get("url", "")
            if url:
                session.add(Document(
                    clergy_id=clergy.id,
                    doc_type="video",
                    title=video.get("title", "") if isinstance(video, dict) else "YouTube Video",
                    url=url,
                ))
                stats["documents_linked"] += 1

        # Source record
        session.add(SourceRecord(
            clergy_id=clergy.id,
            source_name="anderson_mn",
            source_url=profile.get("url"),
            scraped_at=datetime.utcnow(),
            raw_data=profile,
        ))

        stats["imported"] += 1

    session.commit()
    return stats
