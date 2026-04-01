---
name: Investigate Diocese
description: Autonomous deep-dive investigation of a specific diocese. Produces a structured report with findings, patterns, and anomalies.
user-invocable: true
---

# Diocese Investigation

You are conducting an autonomous deep-dive investigation of a specific diocese. You will systematically gather data, identify patterns, compare to baselines, and produce a structured research report.

## Process

### Phase 1: Census
Use `search_clergy` filtered to the target diocese. Get the full list. Count total accused, statuses, ordination decades. Then use `stats_by_diocese` and `stats_by_state` to establish how this diocese compares to its state and national averages.

Tell the user: "Starting with a census of [diocese]. Let me pull all records and establish the baseline."

### Phase 2: Consequence Analysis
Use `consequence_type_breakdown` filtered to this diocese. Compare the distribution to the national breakdown. Flag any consequence types that are significantly over- or under-represented.

Use `final_outcome_stats` for the diocese's state. Calculate what percentage of THIS diocese's clergy had each final outcome vs. the state average.

Look for: unusually high reinstatement rates, unusually low conviction rates, absence of treatment referrals, or concentration of "no known action."

### Phase 3: Facility Connections
Use `facility_cross_state` to see if any treatment facilities received clergy from this diocese's state. Then use `facility_clergy` for each relevant facility and check how many came from THIS diocese specifically.

### Phase 4: Timeline Patterns
Use `search_clergy` to get ordination years for all accused in the diocese. Look for clustering — were there decades with disproportionately many accused clergy ordained? Does this correlate with specific bishops' tenures?

### Phase 5: Notable Individuals
Use `get_clergy_profile` for the 3-5 most significant cases (most consequences, most documents, convicted individuals, or those with treatment + reinstatement patterns). Summarize each.

### Phase 6: Cross-Reference
Use `search_clergy` with `has_documents=true` to find individuals with linked court filings, personnel files, or depositions. These are the cases with the deepest available evidence.

Check for connections to other dioceses via `transfer_network`.

### Phase 7: Report

Structure your output as:

```
# Diocese Investigation: [Name]

## Overview
[1-2 paragraph summary of key findings]

## By The Numbers
| Metric | Diocese | State Avg | National Avg |
|---|---|---|---|
| Total accused | | | |
| Conviction rate | | | |
| No-accountability rate | | | |
| Treatment referrals | | | |
| Reinstated | | | |

## Consequence Patterns
[What happened to accused clergy in this diocese? How does it differ from norms?]

## Facility Connections
[Which treatment facilities received clergy from here? How many?]

## Timeline
[When were most accused clergy ordained? Are there clustering patterns?]

## Notable Cases
[3-5 individual profiles with consequence timelines]

## Anomalies & Red Flags
[Anything that stands out as unusual compared to baselines]

## Limitations
[Data depth, source coverage, what we can't see]

## Suggested Follow-Up
[What questions does this investigation raise?]
```

$ARGUMENTS
