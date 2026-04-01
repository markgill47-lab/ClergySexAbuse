---
name: Cross-Reference Source
description: When a new data source arrives, match it against existing records, report overlaps, and identify new information.
user-invocable: true
---

# Cross-Reference New Data Source

A new data source has arrived (CSV, JSON, list of names, document dump, or URL). Your job is to match it against the existing database, identify overlaps, find new records, and report what the new source adds.

## Process

### Step 1: Ingest the new source
Determine what the user is providing:
- **A file** (CSV, JSON, Excel): Read it and parse the records
- **A URL**: Fetch and parse the page
- **A list of names**: Parse them directly
- **A description**: Ask for the actual data

Extract from the new source: names (required), plus whatever else is available (diocese, state, dates, status).

Tell the user: "Let me read this source and see what we're working with..."

Report: "[X] records found in the new source."

### Step 2: Match against existing records
For each record in the new source, search the database:
1. Exact name match: `search_clergy(name="[last name]")`
2. If no exact match, try fuzzy: search with just the last name, then check first names manually

Categorize each record as:
- **MATCH**: Found in existing database (note the clergy_id)
- **POSSIBLE MATCH**: Similar name found but not certain (name variant, different diocese)
- **NEW**: Not found in existing database

### Step 3: Analyze overlaps
For matched records, compare what the new source says vs. what we already have:
- Does the new source add information we don't have? (new allegations, new dates, new documents)
- Does it contradict anything? (different status, different diocese)
- Does it confirm existing data? (independent corroboration has value)

### Step 4: Analyze new records
For records NOT in the database:
- What diocese/state are they from?
- Are they from a geographic area we have poor coverage in?
- Do they represent a new data type we don't currently track?

### Step 5: Report

```
# Cross-Reference Report: [Source Name]

## Source Summary
- Records in new source: [X]
- Matched to existing DB: [X] ([%])
- Possible matches (need review): [X]
- New records not in DB: [X]

## Overlap Analysis
[What the matching records tell us — does the new source confirm, extend, or contradict existing data?]

## New Information
[What the unmatched records add — new individuals, new geography, new data types]

## Notable Findings
[Anything surprising — contradictions, individuals with very different information across sources]

## Recommended Actions
1. [Import X new records]
2. [Update Y existing records with new information]
3. [Flag Z records for manual review]
4. [Investigate contradictions in ...]
```

### Step 6: Offer to import
Ask the user: "Would you like me to import the [X] new records into the database? I can also update the [Y] existing records with new information from this source."

If they say yes, create the appropriate importer script and run it.

$ARGUMENTS
