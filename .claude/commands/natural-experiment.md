---
name: Natural Experiment
description: Analyze the impact of an external event (SOL reform, grand jury, media investigation) by comparing data before and after.
user-invocable: true
---

# Natural Experiment Analysis

The user wants to evaluate the impact of an external event on clergy abuse reporting, prosecution, or accountability. You will use a before/after comparison with the event as the dividing line.

## Process

### Step 1: Identify the event and its parameters
Parse the user's request for:
- **What event?** (SOL reform, grand jury report, media investigation, institutional policy change)
- **Where?** (specific state, diocese, or national)
- **When?** (exact year, or ask the user)

If the user doesn't specify the date, look it up or ask. Common events:
- Boston Globe Spotlight investigation: January 2002
- Pennsylvania Grand Jury Report: August 2018
- Minnesota Child Victims Act: May 2013
- Dallas Charter (USCCB): June 2002
- Various state SOL reforms: varies by state

Tell the user what event and date you're analyzing.

### Step 2: Define the comparison windows
Choose equal-length windows before and after the event. Default: 10 years before, 10 years after. Adjust if the event is too recent for a full post-window.

### Step 3: Gather "before" data
Use MCP tools to pull all relevant metrics for the pre-event window in the relevant geography. Metrics to collect:
- Number of accused clergy with consequence events in this period
- Consequence type distribution
- Conviction count and rate
- Civil settlement count
- Treatment referrals
- "No known action" cases

Since consequence year data is sparse, use `yearsReferenced` from narratives via a direct database query if needed.

### Step 4: Gather "after" data
Same metrics for the post-event window.

### Step 5: Calculate the change
For each metric:
- Absolute change (after minus before)
- Relative change (percentage increase/decrease)
- Rate change (per-accused-clergy in each period)

### Step 6: Control comparison
If possible, compare the change in the affected geography to the change in a control geography. For example, if analyzing MN's SOL reform, compare MN's before/after change to neighboring states (WI, IA, SD) that didn't reform SOL in the same period.

### Step 7: Report

```
# Natural Experiment: Impact of [Event]

## Event
[What happened, where, when]

## Comparison Design
- Before window: [year range]
- After window: [year range]
- Geography: [state/diocese]
- Control group: [comparison geography, if applicable]

## Results

| Metric | Before | After | Change | % Change |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## Key Findings
[What changed the most? What didn't change?]

## Control Comparison
[Did the control geography show the same change? If so, the event may not be the cause.]

## Interpretation
[What does this suggest about the event's impact?]

## Caveats
- [Data limitations]
- [Confounding events in the same period]
- [Reporting lag effects — post-event activity may reflect pre-event abuse]

## Implications for Policy
[What does this suggest about the effectiveness of similar interventions?]
```

$ARGUMENTS
