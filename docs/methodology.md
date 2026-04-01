# Data Collection Methodology

## Purpose

This document describes how the Clergy Abuse Data Platform's dataset was assembled: what sources were used, how data was collected, how it was normalized and deduplicated, and what limitations apply.

## Data Sources

### Source 1: BishopAccountability.org

**Description.** BishopAccountability.org is a nonprofit that maintains the largest public database of U.S. Catholic clergy accused of sexually abusing minors. The database includes clergy names, diocese affiliations, ordination dates, status, and narrative summaries compiled from court documents, diocesan disclosures, and media reports.

**Collection method.** A Node.js/Cheerio web scraper (originally developed in the VueTest project) targeted the site's state-by-state listing pages. Each state page contains `<article class="accused">` elements with structured HTML divs. The scraper extracted:
- Name, ordination year, status, death date, diocese, religious order
- Full narrative text
- Victim count and demographics (via 8 regex patterns)
- Allegation types (sexual abuse, rape, fondling, pornography, etc.)
- Criminal outcomes (convicted, charged, settled, no known action)
- Church actions (laicized, removed, suspended, reinstated, etc.)
- Treatment facility references (19 keyword patterns)
- All years mentioned in the narrative

**Coverage.** All 50 U.S. states. 8,026 individual records collected.

**Rate limiting.** 2-3 requests per second with academic research User-Agent header.

**Data quality.** BishopAccountability.org is the most comprehensive public source but has limitations. Narratives vary in detail — some are a single sentence, others are multi-paragraph case summaries. Structured fields (victim count, allegation types) are extracted via regex from narrative text and may miss non-standard phrasings. The site's editorial team updates entries as new information surfaces, so the dataset represents a point-in-time snapshot.

### Source 2: Anderson Advocates (Minnesota Deep Profiles)

**Description.** Jeff Anderson & Associates is the law firm most prominently associated with clergy abuse litigation in the United States. Their Minnesota pages contain deep profiles of accused clergy across 5 dioceses and 2 religious orders in Minnesota, including assignment histories, links to court-released personnel files, and deposition videos.

**Collection method.** A Python/BeautifulSoup scraper (originally developed in the MN-Clergy-Abuse project) crawled diocese index pages on andersonadvocates.com, extracted profile URLs, then scraped each profile page for:
- Name, date of birth, ordination date, status
- Assignment history (parsed from `<li>` elements with year-range patterns)
- Narrative paragraphs
- PDF document links (court filings, personnel files, timelines)
- YouTube video links (depositions, news clips)
- Portrait images

PDFs were downloaded via streaming HTTP with retry logic. 133 PDF files totaling 205 MB were collected for 52 profiles.

**Coverage.** Minnesota only. 169 profiles across: Archdiocese of Saint Paul and Minneapolis (113), Diocese of Duluth (32), Saint John's Abbey (22), Diocese of Winona (19), Oblates of Mary Immaculate (10).

### Source 3: Anderson Advocates (National)

**Description.** The same law firm maintains accused clergy pages for 13 additional states beyond Minnesota. The scraper was generalized from the Minnesota version to crawl all available states.

**Collection method.** A two-phase approach:
1. **Discovery.** The scraper probes known state URL patterns (`/abused-in-{state}/`) and crawls the firm's locations page to dynamically discover all states and diocese sub-pages.
2. **Profile crawling.** Each diocese index page is scraped for profile links. Individual profiles are parsed identically to the Minnesota scraper. Profiles are deduplicated by URL slug across dioceses (clergy who served in multiple dioceses appear once with all dioceses tracked).
3. **PDF download.** All linked PDFs are downloaded with streaming, retry logic, and a manifest for resume support.

**Coverage.** 14 states, 56 dioceses. 1,873 profiles collected. 351 PDFs (1 GB), 545 YouTube videos referenced. States covered: California (673), Pennsylvania (542), Illinois (267), Minnesota (169), Colorado (87), Hawaii (76), Louisiana (59), plus Wisconsin, Arizona, Arkansas, Maryland, Michigan, Vermont, Maine (varying counts).

**Rate limiting.** 0.4-second delay between requests. 3 retries with exponential backoff on failure. Academic research User-Agent header.

## Normalization

All three sources feed into a single normalized SQLite database through source-specific importers.

### Field Mapping

| Normalized Field | BA.org Source | Anderson Source |
|---|---|---|
| first_name, last_name | Parsed from `name` (prefix-stripped, suffix-detected) | Parsed from `name` (handles "Last, First" format) |
| ordination_year | `ordained` field | Regex extraction from `ordination_date` text |
| status | `status` field | `status` field or default "accused" |
| diocese | `diocese` field | `diocese` slug converted to full name |
| narrative | `narrative` field | `narrative` paragraphs joined |
| allegations | Derived from `victimDemographics` + `allegationTypes` | Not separately structured |
| criminal_outcomes | `criminalOutcome` field | Not separately structured |
| church_actions | `churchActions` array | Not separately structured |
| assignments | Not available | Parsed from `<li>` year-range patterns |
| documents | Not available | PDF links + YouTube links |

### Consequence Extraction

After initial import, a consequence extraction pass scans all records to build ordered consequence timelines:

1. **Criminal outcomes** are mapped to consequence types (e.g., `convicted` becomes `conviction`, `charged` becomes `criminal_charges`).
2. **Church actions** are mapped (e.g., `removedFromMinistry` becomes `removed_from_ministry`).
3. **Narrative text** is scanned for treatment facility keywords (19 facility names/aliases plus generic terms like "sent for treatment"). Matches are linked to facility records where possible.
4. **Death** is recorded as a consequence event.
5. **Posthumous accusations** are detected via keywords ("posthumous", "after his death").
6. All consequences are sorted by year (where available) and assigned a `sequence_order` for timeline reconstruction.

### Deduplication

Clergy appearing in multiple sources are identified by normalized (last_name, first_name) matching. When a match is found across sources:
- The record with richer data is kept as primary
- Scalar fields are merged (prefer non-null)
- Narratives are concatenated with a separator
- All child records (allegations, consequences, documents, source records) are combined
- Both source records are preserved for provenance

**Results.** Of the 10,068 raw records imported (8,026 BA.org + 169 Anderson MN + 1,873 Anderson National), 8,713 cross-source matches were identified and merged, yielding 10,478 unique individuals.

### Treatment Facility Seeding

13 known treatment facilities were seeded from published research and the VueTest scraper's keyword list. Each facility has a canonical name, known aliases, city, state, and facility type. Consequence records reference facilities by ID where narrative keyword matching succeeds.

## Known Limitations

1. **Narrative-dependent extraction.** Most structured fields for BA.org data are extracted from free-text narratives via regex. Non-standard phrasings, abbreviations, or editorial variations may cause missed extractions.

2. **Temporal data is sparse.** Only 20.7% of consequence records have a year attached. Temporal analysis relies on `yearsReferenced` (all years mentioned in narratives), which conflates abuse dates, reporting dates, lawsuit dates, and media coverage dates.

3. **Source depth asymmetry.** Anderson states (CA, PA, IL, MN, CO, HI, LA) have deep profiles with assignment histories, PDFs, and videos. The remaining 36 states have only BA.org narrative-level data. Patterns detectable in Anderson states may not be visible in BA.org-only states due to data depth, not absence of the pattern.

4. **Point-in-time snapshot.** Both source websites are periodically updated. This dataset represents scrape dates of March-April 2026.

5. **Deduplication imperfections.** Name matching may produce false positives (different individuals with the same name) or false negatives (same individual with variant name spellings across sources). Ordination year is used as a secondary signal where available.

6. **Accusation, not adjudication.** The database records accusations and their outcomes. Inclusion in the database does not imply guilt. Status fields reflect the documented outcome (accused, convicted, acquitted, settled), not a determination of fact.

7. **Survivor data is minimal.** Victim demographics (gender, minor status) are available for some records but victim identities are never included. Victim counts are estimated from narrative text and may undercount.

## Planned Data Sources

| Source | Status | Expected Contribution |
|---|---|---|
| UNM/CSWR Santa Fe Institutional Abuse Collection | Planned | Paraclete facility internal records, depositions, personnel files |
| LA Archdiocese Clergy Files | Planned | 128 clergy, ~12,000 pages of court-released PDFs |
| Archdiocese of Chicago Documents | Planned | ~68 clergy with substantiated allegations |
| Official Catholic Directory | Future | Year-by-year priest rosters for transfer detection |
| Internet Archive Historical Directories | Future | 150 years of scanned/OCR'd directories |
