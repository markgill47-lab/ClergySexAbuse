---
name: Find Anomalies
description: Scan the dataset for statistical outliers and surprising patterns without being told what to look for.
user-invocable: true
---

# Anomaly Detection

You are scanning the clergy abuse dataset for anomalies — things that deviate significantly from expected patterns. You are NOT looking for something specific. You are exploring the data and reporting anything that looks unusual.

## Process

### Scan 1: State-Level Outliers
Use `stats_by_state`. Calculate mean and standard deviation for key metrics:
- Conviction rate
- Per-capita accused rate
- Per-Catholic accused rate

Flag any state more than 1.5 standard deviations from the mean in either direction. Report both unusually high AND unusually low values — a state with an abnormally LOW conviction rate is as interesting as one with a high rate.

### Scan 2: Consequence Distribution Anomalies
Use `consequence_type_breakdown` for the top 10 states by accused count (individually). Compare each state's consequence distribution to the national average. Flag states where any consequence type is >2x or <0.5x the national rate.

### Scan 3: Facility Anomalies
Use `facility_cross_state`. Check for:
- States that sent clergy to treatment facilities at disproportionate rates
- States with many accused but NO treatment facility references (why not?)
- Facilities that drew from geographically distant states (e.g., a NM facility receiving clergy from Alaska)

### Scan 4: Temporal Anomalies
Use `reporting_lag_analysis`. Look for individuals with unusually short lags (rapid consequence — why was this one caught quickly?) and unusually long lags (>60 years — how did this persist?).

### Scan 5: Pattern Anomalies
Run `find_consequence_pattern` for unusual sequences:
- `["reinstated", "conviction"]` — reinstated then convicted (the system put them back and they were STILL prosecuted)
- `["treatment", "treatment"]` — sent to treatment twice
- `["acquittal"]` — acquitted cases (rare — what made these different?)

### Scan 6: Diocese Outliers
Use `stats_by_diocese` for the top 20 dioceses. Calculate accused per diocese. Flag any diocese with a count significantly above or below what its state average would predict.

### Report

```
# Anomaly Scan Report

## Summary
[How many anomalies found, across which dimensions]

## State-Level Outliers
[Table of outlier states with the specific metric and how far from the mean]

## Consequence Anomalies
[States or dioceses with unusual consequence distributions]

## Facility Anomalies
[Unusual facility referral patterns]

## Temporal Anomalies
[Unusual reporting lags — both fast and slow]

## Pattern Anomalies
[Unusual consequence sequences found]

## Diocese Outliers
[Dioceses that deviate from state norms]

## Most Interesting Findings
[Rank the top 3-5 anomalies by research significance. What should a researcher dig into first?]
```

If the user provides a focus area (e.g., "find anomalies in California" or "look for facility anomalies"), narrow the scan accordingly but still be thorough within that scope.

$ARGUMENTS
