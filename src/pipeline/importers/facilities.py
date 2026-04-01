"""Seed known treatment facilities from research and existing scraper data."""

from sqlalchemy.orm import Session

from src.backend.models import TreatmentFacility


# Known facilities compiled from VueTest scraper keywords + published research
KNOWN_FACILITIES = [
    {
        "name": "Servants of the Paraclete - Jemez Springs",
        "aliases": ["Via Coeli", "Paraclete", "Jemez Springs"],
        "city": "Jemez Springs",
        "state": "NM",
        "facility_type": "treatment_center",
        "notes": "Founded 1947 by Fr. Gerald Fitzgerald. Major clergy treatment facility, closed 1990s. Housed hundreds of accused priests from across the US.",
    },
    {
        "name": "Servants of the Paraclete - Nevis",
        "aliases": ["Nevis facility"],
        "city": "Nevis",
        "state": "MN",
        "facility_type": "treatment_center",
        "notes": "Minnesota branch of the Servants of the Paraclete.",
    },
    {
        "name": "St. Luke Institute",
        "aliases": ["St. Luke's", "Saint Luke Institute"],
        "city": "Silver Spring",
        "state": "MD",
        "facility_type": "treatment_center",
        "notes": "Psychiatric treatment facility for Catholic clergy. Founded 1981.",
    },
    {
        "name": "Institute of Living",
        "aliases": ["Hartford Retreat", "Institute of Living Hartford"],
        "city": "Hartford",
        "state": "CT",
        "facility_type": "treatment_center",
        "notes": "Psychiatric hospital used for clergy treatment programs.",
    },
    {
        "name": "Southdown Institute",
        "aliases": ["Southdown"],
        "city": "Aurora",
        "state": "ON",
        "country": "Canada",
        "facility_type": "treatment_center",
        "notes": "Canadian treatment facility for clergy behavioral issues.",
    },
    {
        "name": "Guest House",
        "aliases": ["Guest House Rochester"],
        "city": "Rochester",
        "state": "MN",
        "facility_type": "treatment_center",
        "notes": "Treatment center for clergy with substance abuse, also treated sexual disorders.",
    },
    {
        "name": "St. John Vianney Center",
        "aliases": ["Vianney Center", "St. John Vianney"],
        "city": "Downingtown",
        "state": "PA",
        "facility_type": "treatment_center",
        "notes": "Treatment facility for clergy and religious.",
    },
    {
        "name": "Seton Psychiatric Institute",
        "aliases": ["Seton Institute"],
        "city": "Baltimore",
        "state": "MD",
        "facility_type": "treatment_center",
    },
    {
        "name": "Menninger Clinic",
        "aliases": ["Menninger Foundation"],
        "city": "Topeka",
        "state": "KS",
        "facility_type": "treatment_center",
    },
    {
        "name": "Our Lady of the Snows",
        "aliases": ["Snows"],
        "city": "Belleville",
        "state": "IL",
        "facility_type": "retreat",
    },
    {
        "name": "Albuquerque Villa",
        "aliases": [],
        "city": "Albuquerque",
        "state": "NM",
        "facility_type": "treatment_center",
    },
    {
        "name": "Shalom Center",
        "aliases": [],
        "city": "Splendora",
        "state": "TX",
        "facility_type": "retreat",
    },
    {
        "name": "John XXIII Center",
        "aliases": ["John 23rd Center"],
        "city": "Hartford",
        "state": "CT",
        "facility_type": "treatment_center",
    },
]


def seed_facilities(session: Session) -> int:
    """Insert known treatment facilities. Skips duplicates."""
    count = 0
    for fac in KNOWN_FACILITIES:
        existing = session.query(TreatmentFacility).filter(TreatmentFacility.name == fac["name"]).first()
        if existing:
            continue
        session.add(TreatmentFacility(
            name=fac["name"],
            aliases=fac.get("aliases"),
            city=fac.get("city"),
            state=fac.get("state"),
            country=fac.get("country", "US"),
            facility_type=fac.get("facility_type"),
            notes=fac.get("notes"),
        ))
        count += 1
    session.commit()
    return count
