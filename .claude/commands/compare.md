---
name: Compare
description: Systematic comparison of two entities (states, dioceses, decades, facilities). Produces a structured side-by-side analysis.
user-invocable: true
---

# Comparative Analysis

You are conducting a rigorous side-by-side comparison of two entities. The entities can be states, dioceses, decades, facilities, or any other dimension in the data.

## Process

### Step 1: Identify what's being compared
Parse the user's request. Determine the two entities and the comparison dimension. If ambiguous, ask for clarification.

Examples:
- "California vs Pennsylvania" → two states
- "Archdiocese of LA vs Archdiocese of Chicago" → two dioceses
- "1960s vs 1980s" → two ordination decades
- "Paraclete vs St. Luke" → two facilities

### Step 2: Pull parallel data
For each entity, gather the same metrics using the same MCP tools. Always include:
- Total accused count
- Consequence type breakdown
- Final outcome distribution
- Any entity-specific data (per-capita rates for states, facility referral counts, etc.)

### Step 3: Normalize for comparison
Raw counts mislead when populations differ. Always calculate rates:
- Per capita (per 100k population for states)
- Per Catholic population (per 100k Catholic pop for states)
- As percentage of the entity's own total (for consequence breakdowns)

### Step 4: Identify divergences
For each metric, calculate the difference. Flag metrics where the two entities diverge significantly (>50% relative difference or >10 percentage points absolute difference).

### Step 5: Look for explanatory patterns
When you find a divergence, dig one level deeper. If State A has 3x the conviction rate of State B, check:
- Does State A have deeper data coverage (Anderson vs. BA.org only)?
- Did State A reform its statute of limitations earlier?
- Does State A have a history of AG investigations?

### Step 6: Report

```
# Comparison: [Entity A] vs [Entity B]

## Summary
[2-3 sentence overview of the most important differences]

## Side-by-Side Metrics
| Metric | [Entity A] | [Entity B] | Difference |
|---|---|---|---|
| ... | ... | ... | ... |

## Key Divergences
[For each significant difference, explain what's different and hypothesize why]

## Similarities
[What do they have in common? Shared patterns matter too.]

## Data Quality Note
[Are the two entities comparable? Different data sources? Different coverage depth?]

## Implications
[What does this comparison suggest for broader research?]
```

$ARGUMENTS
