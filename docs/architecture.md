# Data Architecture

## Overview

The Clergy Abuse Data Platform uses a four-tier storage architecture designed for AI-agent-driven research. The structured data layer (Tier 1) is the primary query surface. Raw documents (Tier 4) serve as source verification for human researchers.

## Storage Tiers

```
Tier 1: Structured Database         49.7 MB    SQLite (dev) / PostgreSQL (prod)
Tier 2: Extracted Text              (planned)   Full-text search index
Tier 3: Vector Embeddings           (planned)   Semantic search
Tier 4: Raw Documents               ~1 GB       PDFs, images, videos on filesystem
```

## Database Schema

### Entity-Relationship Diagram

```
                            ┌──────────────────┐
                            │  accused_clergy   │
                            │──────────────────│
                            │  id (PK)         │
                            │  first_name      │
                            │  last_name       │
                            │  suffix          │
                            │  ordination_year │
                            │  ordination_decade│
                            │  death_year      │
                            │  deceased        │
                            │  status          │
                            │  religious_order  │
                            │  photo_url       │
                            │  narrative       │
                            │  created_at      │
                            │  updated_at      │
                            └────────┬─────────┘
                                     │
          ┌──────────────────┬───────┼────────┬──────────────────┐
          │                  │       │        │                  │
          ▼                  ▼       ▼        ▼                  ▼
┌─────────────────┐ ┌────────────┐ ┌──────────────┐ ┌───────────────┐
│diocese_associations│ │assignments│ │ allegations  │ │ consequences  │
│─────────────────│ │────────────│ │──────────────│ │───────────────│
│ clergy_id (FK)  │ │clergy_id(FK)│ │clergy_id(FK) │ │clergy_id (FK) │
│ diocese_name    │ │institution │ │ year         │ │consequence_type│
│ state           │ │inst_type   │ │ decade       │ │ year          │
│ is_primary      │ │ city       │ │victim_gender │ │sequence_order │
└─────────────────┘ │ state      │ │victim_minor  │ │facility_id(FK)│
                    │ start_year │ │allegation_type│ │from_diocese   │
                    │ end_year   │ │substantiated │ │to_diocese     │
                    │ role       │ │ summary      │ │ details       │
                    └────────────┘ └──────────────┘ └───────┬───────┘
                                                            │
          ┌──────────────────┬──────────────────┐           │
          │                  │                  │           ▼
          ▼                  ▼                  ▼  ┌─────────────────┐
┌─────────────────┐ ┌────────────────┐ ┌────────┐│treatment_facilities│
│ source_records  │ │   documents    │ │church_ ││─────────────────│
│─────────────────│ │────────────────│ │actions ││ id (PK)         │
│ clergy_id (FK)  │ │ clergy_id (FK) │ │────────││ name            │
│ source_name     │ │ doc_type       │ │clergy_id│ aliases (JSON)  │
│ source_url      │ │ title          │ │action_ ││ city            │
│ scraped_at      │ │ url            │ │ type   ││ state           │
│ raw_data (JSON) │ │ local_path     │ │ year   ││ facility_type   │
└─────────────────┘ │ publication_date│ └────────┘│ notes           │
                    └────────────────┘           └─────────────────┘

┌─────────────────┐  ┌──────────────────────────┐
│ state_summaries │  │     clergy_roster        │
│─────────────────│  │──────────────────────────│
│ state (PK)      │  │ id (PK)                  │
│ state_name      │  │ accused_clergy_id (FK)   │
│ region          │  │ first_name, last_name    │
│ population      │  │ diocese_name, state       │
│ catholic_pop    │  │ parish_or_institution    │
│ total_accused   │  │ role                     │
│ convicted_count │  │ roster_year              │
│ deceased_count  │  │ source_name, source_year │
└─────────────────┘  └──────────────────────────┘
```

### Table Counts (as of 2026-04-01)

| Table | Records | Description |
|---|---|---|
| accused_clergy | 10,478 | Deduplicated individuals across all sources |
| diocese_associations | 10,488 | Clergy-to-diocese links (many-to-many) |
| assignments | 4,216 | Parish/institutional assignment records with year ranges |
| allegations | 10,869 | Individual allegation records with victim demographics |
| criminal_outcomes | 9,789 | Criminal justice outcomes (convicted, charged, settled) |
| church_actions | 2,935 | Church disciplinary actions (laicized, removed, suspended) |
| consequences | 32,161 | Ordered consequence timelines per individual |
| treatment_facilities | 13 | Known treatment/retreat facilities |
| clergy_roster | 0 | (Awaiting diocesan roster data) |
| source_records | 10,478 | Provenance tracking with raw JSON preserved |
| documents | 493 | Linked PDFs, videos, court filings |
| state_summaries | 50 | Pre-computed per-state demographics |

### Key Design Decisions

**Consequence timeline model.** Rather than tracking criminal outcomes and church actions in separate tables (which we also do for backward compatibility), the `consequences` table provides an ordered sequence of events per individual. Each row has a `sequence_order` field that allows reconstructing the complete narrative: accusation, investigation, treatment, transfer, civil suit, criminal charges, conviction, church discipline, reinstatement, death. This enables pattern queries like "find everyone whose timeline includes treatment followed by reinstatement."

**Treatment facility as first-class entity.** Facilities are not just text in narratives but queryable entities with geographic data. Consequence records link to facilities via `facility_id`, enabling cross-state funneling analysis (e.g., "which facilities received clergy from the most states?").

**Clergy roster table (future).** Designed to hold year-by-year priest-to-diocese assignments from the Official Catholic Directory or tax-exempt filings. This will enable transfer detection by diffing rosters year-over-year, and prevalence analysis by providing a total priest population as denominator. The table allows linking roster entries to accused clergy records where matches are found.

**Provenance tracking.** Every imported record retains its original scraped data as JSON in `source_records.raw_data`. This allows re-extraction if the normalization logic improves, and supports auditing claims back to source.

**Deduplication.** Clergy appearing in multiple sources are matched by normalized (last_name, first_name) with ordination year as a secondary signal. When matched, records are merged: scalar fields prefer non-null values from the richer source, narratives are concatenated with a separator, and all child records (allegations, consequences, documents) are combined under one ID.

## MCP Server Interface

The database is exposed through an MCP (Model Context Protocol) server with 18 tools:

| Category | Tools |
|---|---|
| Search & Profiles | `search_clergy`, `get_clergy_profile`, `get_consequence_timeline` |
| Pattern Detection | `find_consequence_pattern`, `temporal_clusters`, `transfer_network`, `facility_cross_state`, `facility_clergy` |
| Aggregations | `summary_stats`, `stats_by_state`, `stats_by_diocese`, `final_outcome_stats`, `treatment_outcomes`, `consequence_type_breakdown`, `no_accountability_analysis`, `reporting_lag_analysis` |
| Export | `export_csv` |

All tools return structured JSON. The MCP server connects to Claude Code via stdio protocol and is configured in `.mcp.json`.

## File Layout

```
ClergySexAbuse/
├── .mcp.json                    # MCP server configuration
├── .claude/
│   ├── commands/                # Claude Code skills
│   │   ├── research.md          # Research investigation workflow
│   │   └── generate-map.md     # Choropleth map generation
│   └── settings.json
├── src/
│   ├── backend/
│   │   ├── models.py            # SQLAlchemy ORM (12 tables)
│   │   ├── database.py          # Engine, session management
│   │   ├── config.py            # Paths, constants
│   │   ├── main.py              # FastAPI application
│   │   ├── routes/              # REST API endpoints
│   │   └── rag/                 # (Planned) Vector search
│   ├── mcp_server/
│   │   ├── server.py            # MCP server (18 tools)
│   │   └── __main__.py          # Entry point
│   └── pipeline/
│       ├── scrapers/
│       │   └── anderson.py      # Anderson Advocates national scraper
│       ├── importers/
│       │   ├── ba_json.py       # BishopAccountability.org importer
│       │   ├── anderson_json.py # Anderson MN importer (prior project)
│       │   ├── anderson_national.py # Anderson national importer
│       │   ├── facilities.py    # Treatment facility seeder
│       │   └── consequences.py  # Consequence timeline extractor
│       └── normalizer.py        # Deduplication engine
├── data/
│   ├── db/clergy_abuse.db       # SQLite database (49.7 MB)
│   ├── raw/anderson/            # Scraped profile JSON + PDFs
│   └── exports/                 # Generated maps, CSVs
├── scripts/
│   ├── import_existing.py       # Full import pipeline
│   └── scrape_anderson.py       # Anderson national scraper CLI
└── docs/                        # This documentation
```
