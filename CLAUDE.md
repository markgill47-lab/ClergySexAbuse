# Clergy Abuse Data Platform

Unified research platform for clergy sex abuse data across multiple sources.
Designed for AI-agent-driven analysis with an MCP server interface.

## Quick Start (for colleagues)

### 1. Clone and install

```bash
git clone https://github.com/markgill47-lab/ClergySexAbuse.git
cd ClergySexAbuse
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e .
```

### 2. Restart Claude Code in this directory

The MCP server is already configured in `.mcp.json`. When Claude Code starts in this directory, it will detect the server and prompt you to approve it. Accept, and you'll have 18 research tools available.

No manual configuration needed — the `.mcp.json` ships with the repo.

### 3. Use it

Claude now has 18 research tools available. Try:

- "How many accused clergy are in California?"
- "Show me the consequence timeline for Thomas Adamson"
- "Find everyone who was sent to treatment and then reinstated"
- "Which treatment facilities received clergy from the most states?"
- "What percentage of accused clergy faced no consequences?"

Use `/research` for systematic investigations and `/generate-map` for choropleth visualizations.

## Database

The SQLite database (`data/db/clergy_abuse.db`) ships with the repo — 10,500+ accused clergy, pre-loaded.

To rebuild from source data: `python scripts/import_existing.py`
(Requires the raw scraped data in `data/raw/`, which is not in the repo due to size.)

## Data Sources (4 sources, 10,509 records)

- **BishopAccountability.org**: 9,789 accused clergy across all 50 US states
- **Anderson Advocates National**: 604 deep profiles (CA, PA, IL, MN, CO, HI, LA) with assignment histories, PDFs, videos
- **Anderson Advocates MN**: 85 deep profiles with court documents and depositions
- **UNM/CSWR Santa Fe Archive**: 31 clergy with personnel files and depositions from the $121.5M settlement

## Architecture

- `src/mcp_server/` — MCP server (18 tools for Claude Code integration)
- `src/backend/` — SQLAlchemy models, FastAPI REST API
- `src/pipeline/` — Scrapers, importers, normalizers
- `.claude/commands/` — Claude Code skills (research, map generation)
- `data/db/` — SQLite database (ships with repo)
- `docs/` — Architecture, methodology, executive brief

## Skills

- `/research <question>` — Systematic investigation workflow with structured reporting
- `/generate-map <metric>` — Generate interactive US choropleth maps

## Key Analysis Capabilities

- **Consequence timelines**: Track accusation → treatment → transfer → outcome sequences
- **Facility cross-state analysis**: Detect multi-state funneling through treatment centers (Paraclete: 156 clergy from 33 states)
- **No-accountability analysis**: 66.5% of accused faced no known action
- **Reporting lag**: Median 45 years between ordination and first consequence
- **Transfer network**: Map diocese-to-diocese movement patterns
- **Pattern search**: Find clergy matching specific consequence sequences

## Documentation

- `docs/architecture.md` — Schema, storage tiers, MCP tool inventory
- `docs/methodology.md` — Data collection methods, normalization, limitations
- `docs/executive_brief.md` — High-level summary for stakeholders
- `docs/executive_brief.docx` — Word format for distribution
