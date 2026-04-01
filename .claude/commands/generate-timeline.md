---
name: Generate Timeline
description: Create an interactive visual timeline for an individual or institution showing chronological events.
user-invocable: true
---

# Generate Timeline Visualization

You are creating a standalone interactive HTML timeline visualization. It shows the chronological sequence of events for either one individual or one institution (diocese/facility).

## Process

### Step 1: Determine the subject
Parse the user's request. Is this:
- **An individual?** Use `search_clergy` to find them, then `get_clergy_profile` and `get_consequence_timeline` for full data.
- **A diocese?** Use `search_clergy` filtered by diocese, plus `consequence_type_breakdown` for the diocese.
- **A facility?** Use `facility_clergy` to get all referred clergy and their timelines.

### Step 2: Gather timeline events
For individuals, the events are the consequence timeline: ordination, each consequence event, death.
For institutions, the events are aggregated: years with accusations, key policy changes, notable cases.

### Step 3: Generate the HTML

Create a standalone HTML file with an interactive vertical timeline. Use this structure:

```html
<!DOCTYPE html>
<html>
<head>
<style>
  body { background: #1a1a2e; color: #e0e0e0; font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 24px; }
  h1 { color: #fff; } .subtitle { color: #999; }
  .timeline { position: relative; padding-left: 40px; }
  .timeline::before { content: ''; position: absolute; left: 16px; top: 0; bottom: 0; width: 2px; background: #42b883; }
  .event { position: relative; margin-bottom: 24px; padding: 12px 16px; background: #16213e; border-radius: 6px; border-left: 3px solid #42b883; }
  .event::before { content: ''; position: absolute; left: -30px; top: 16px; width: 10px; height: 10px; border-radius: 50%; background: #42b883; }
  .event.negative { border-left-color: #e74c3c; } .event.negative::before { background: #e74c3c; }
  .event.neutral { border-left-color: #666; } .event.neutral::before { background: #666; }
  .event .year { font-weight: bold; color: #42b883; font-size: 0.9rem; }
  .event .type { font-size: 0.75rem; text-transform: uppercase; color: #999; margin-top: 2px; }
  .event .detail { margin-top: 6px; font-size: 0.9rem; }
  .source { font-size: 0.75rem; color: #666; margin-top: 24px; }
</style>
</head>
<body>
<h1>[TITLE]</h1>
<p class="subtitle">[SUBTITLE]</p>
<div class="timeline">
  <!-- For each event: -->
  <div class="event [negative|neutral]">
    <div class="year">[YEAR or "Date unknown"]</div>
    <div class="type">[CONSEQUENCE TYPE]</div>
    <div class="detail">[DETAILS]</div>
  </div>
</div>
<p class="source">Source: Clergy Abuse Data Platform</p>
</body>
</html>
```

Color coding:
- **Green (default)**: ordination, appointments
- **Red (negative)**: accusations, criminal charges, conviction
- **Grey (neutral)**: no known action, death, unknown dates

### Step 4: Write and report
Save to `data/exports/timeline_[subject_slug].html`
Tell the user where it is and that they can open it in any browser.

$ARGUMENTS
