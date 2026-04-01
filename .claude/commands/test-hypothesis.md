---
name: Test Hypothesis
description: Operationalize and test a research hypothesis against the data. Reports whether the data supports or contradicts the claim.
user-invocable: true
---

# Hypothesis Testing

The user has stated a hypothesis about clergy abuse patterns. Your job is to operationalize it, gather the relevant data, test it, and report whether the evidence supports or contradicts the claim.

## Process

### Step 1: Restate the hypothesis formally
Take the user's natural-language claim and restate it as a testable proposition with:
- **Independent variable** (what is claimed to cause or correlate)
- **Dependent variable** (what is claimed to be affected)
- **Expected direction** (positive, negative, higher, lower)

Example: "Dioceses that sent more clergy to treatment had lower conviction rates"
→ IV: treatment referral rate per diocese, DV: conviction rate per diocese, Expected: negative correlation

Tell the user: "Let me restate your hypothesis in testable form..."

### Step 2: Operationalize the variables
Define exactly how you'll measure each variable using the available MCP tools. Be explicit about what you're using as a proxy and what limitations that introduces.

### Step 3: Gather the data
Pull the data for both variables across the relevant population. Use `stats_by_state`, `stats_by_diocese`, `consequence_type_breakdown`, `search_clergy`, or other tools as needed.

### Step 4: Test the hypothesis
Compare the data. Depending on the hypothesis:
- **Comparison claims** ("A is higher than B"): Pull both values, calculate the difference, calculate relative difference as percentage
- **Correlation claims** ("X correlates with Y"): Pull paired data points, calculate whether they trend together
- **Threshold claims** ("Most X have Y"): Count and calculate the percentage, compare to 50% or whatever "most" implies
- **Temporal claims** ("X increased after Y"): Pull before/after data, compare

### Step 5: Consider alternative explanations
For every finding, ask: could this be explained by something other than the hypothesis?
- Data coverage differences (Anderson states vs. BA.org-only states)
- Population differences (larger states have more of everything)
- Temporal confounds (things that changed over time for other reasons)

### Step 6: Report

```
# Hypothesis Test

## Hypothesis
[Formal restatement]

## Operationalization
- IV: [what you measured and how]
- DV: [what you measured and how]
- Population: [what units you compared across]

## Data
[Table or summary of the relevant data]

## Result: [SUPPORTED / CONTRADICTED / INCONCLUSIVE]

## Evidence
[What the data shows, with specific numbers]

## Alternative Explanations
[What else could explain this pattern?]

## Confidence Level
[How confident should we be? Strong evidence? Weak? Limited by data?]

## Suggested Next Steps
[What additional data or analysis would strengthen or refine this finding?]
```

$ARGUMENTS
