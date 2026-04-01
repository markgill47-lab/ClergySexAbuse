# Executive Brief: Clergy Abuse Data Platform

## What Is This?

A unified, queryable research database of 10,478 Catholic clergy accused of sexual abuse in the United States, merged from multiple public sources, with AI-powered analysis tools for academic research.

The platform is designed to be used by researchers working with Claude Code (Anthropic's AI coding assistant). Claude connects to the database through 18 specialized research tools and can investigate patterns, generate visualizations, and produce reports on demand.

## What's In The Data?

**10,478 accused individuals** across all 50 states and 208 dioceses, compiled from:
- BishopAccountability.org (9,789 records, national coverage)
- Jeff Anderson & Associates (689 deep profiles across 14 states with court documents, personnel files, and deposition videos)

For each individual, the database tracks:
- Identity, ordination date, diocese affiliations, religious order
- Allegation details and victim demographics
- **Consequence timelines** — the ordered sequence of what happened after accusation: investigation, treatment, transfer, criminal charges, conviction, church discipline, reinstatement, or nothing
- Linked source documents (493 PDFs and videos)
- Provenance back to original sources

## What Does The Data Show?

### Accountability is the exception, not the norm.

- **66.5%** of accused clergy have "no known action" as their final documented outcome
- **4.7%** were convicted
- **0.2%** were laicized (formally expelled from the priesthood) — 16 individuals out of 10,478
- **2.4%** were reinstated to ministry after some form of discipline

### The institution operated a national treatment pipeline.

Three facilities received accused clergy from across the country:

| Facility | Clergy Referred | States |
|---|---|---|
| Servants of the Paraclete (Jemez Springs, NM) | 156 | 33 |
| St. Luke Institute (Silver Spring, MD) | 157 | 27 |
| St. John Vianney Center (Downingtown, PA) | 81 | 18 |

Of 542 clergy sent to treatment, 44.3% had no further consequence. 6.1% were reinstated to ministry afterward.

### Reporting was suppressed for decades.

- Clergy ordained in the 1930s-1950s had a **84-96% no-accountability rate**
- The median time between ordination and first documented consequence is **45 years**
- Reporting activity surged 70% in the 2000s, coinciding with the Boston Globe investigation (2002) and subsequent disclosures
- Clergy ordained in the 2010s still show a 40.7% no-accountability rate

### 171 individuals were accused posthumously.

88 unique clergy had accusations surface only after their deaths, representing cases where institutional knowledge of abuse was never acted upon during the perpetrator's lifetime.

## How Do Researchers Use It?

### Setup (5 minutes)

1. Clone the repository
2. `pip install -e .`
3. Add MCP server to Claude Code configuration
4. Claude now has 18 research tools available

### Example Research Workflows

**Investigation:** "What happened to priests sent to the Servants of the Paraclete?"
Claude pulls facility data, identifies 156 referred clergy from 33 states, traces post-treatment outcomes, names the 5 individuals reinstated after treatment, and flags the connection to the UNM archive for follow-up.

**Visualization:** "Generate a map of conviction rates by state"
Claude pulls state-level statistics, produces a standalone interactive HTML choropleth map file that opens in any browser.

**Pattern search:** "Find everyone who was treated and then reinstated"
Claude queries the consequence timeline database, returns 29 matching clergy with names, statuses, and diocese affiliations.

### Available Analysis Tools

| Tool | Purpose |
|---|---|
| `search_clergy` | Find individuals by name, state, diocese, status |
| `get_clergy_profile` | Complete profile with all related data |
| `get_consequence_timeline` | Ordered sequence of events for one individual |
| `find_consequence_pattern` | Find clergy matching specific consequence sequences |
| `facility_cross_state` | Detect multi-state funneling through treatment centers |
| `no_accountability_analysis` | Identify clergy who faced zero consequences |
| `reporting_lag_analysis` | Measure delay between ordination and first consequence |
| `transfer_network` | Map diocese-to-diocese movement patterns |
| `final_outcome_stats` | Distribution of how cases ended |
| `treatment_outcomes` | What happened after treatment |
| `temporal_clusters` | When did specific consequences peak |
| `stats_by_state` / `stats_by_diocese` | Geographic breakdowns |
| `export_csv` | Export filtered data for external analysis |

## What's Coming Next?

| Data Source | Status | Contribution |
|---|---|---|
| UNM/CSWR Santa Fe Archive | Planned | Internal records of the Paraclete treatment facility — depositions, personnel files from the $121.5M settlement |
| LA Archdiocese Clergy Files | Planned | 128 clergy, 12,000 pages of court-released PDFs |
| Archdiocese of Chicago Documents | Planned | 68 clergy with substantiated allegations |
| Official Catholic Directory | Future | Year-by-year priest rosters enabling transfer detection at population scale |

## Key Scholars

- **Kevin Lewis O'Neill** (University of Toronto) — publishing on the Servants of the Paraclete. Author of "Unforgivable" (UC Press, 2025) on cross-border clergy transfers.
- **Kathleen Holscher** (University of New Mexico) — Endowed Chair of Roman Catholic Studies. "Desolate Country" project mapping abuse in Native America. Connected to the UNM/CSWR archive.

## Contact

This platform was built to serve academic research on institutional accountability. The data documents real harm to real people and should be handled with appropriate care and respect.
