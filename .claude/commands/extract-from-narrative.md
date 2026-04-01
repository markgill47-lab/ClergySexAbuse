---
name: Extract From Narrative
description: Use AI to extract a specific structured field from all clergy narratives that regex missed (settlement amounts, parish names, bishop names, etc).
user-invocable: true
---

# Narrative Extraction

The user wants to extract a specific piece of structured information from the narrative text of clergy records. The narratives are free-text summaries compiled from court documents, media reports, and diocese disclosures. Regex has already extracted what it can — your job is to use language understanding to find what regex missed.

## Process

### Step 1: Understand what to extract
The user will specify a field. Common requests:
- Settlement dollar amounts
- Parish/institution names
- Bishop names (who authorized transfers)
- Specific dates (abuse dates vs. report dates)
- Victim counts beyond what regex captured
- Geographic locations of abuse
- Names of co-accused or collaborators

Tell the user: "I'll scan the narratives and extract [field]. Let me start with a sample to calibrate, then run the full extraction."

### Step 2: Calibrate on a sample
Pull 5-10 clergy records with `search_clergy` (pick ones likely to have the target field — e.g., for settlement amounts, use `status=Settled`). Use `get_clergy_profile` to get their narratives.

Read each narrative and attempt the extraction. Show the user your first results:
- What you found
- What format it's in
- Any ambiguities

Ask the user if the extraction looks right before proceeding to the full run.

### Step 3: Full extraction
Query the database directly (via Bash/Python) to iterate through all narratives. For each narrative:
- Use your language understanding to find the target field
- Record: clergy_id, extracted value, confidence level, relevant quote snippet

Write results to a CSV file at `data/exports/extraction_[field_name].csv`.

**Important:** For large-scale extraction (10,000+ records), process in batches and save incrementally. Tell the user progress at regular intervals.

### Step 4: Report
Summarize what was found:
- How many records had the target field
- Distribution of values (for amounts: min, max, median; for names: most frequent)
- Examples of ambiguous cases
- Suggested next steps (manual review of edge cases)

```python
# Example extraction template (run via Bash)
import sqlite3, csv, json

conn = sqlite3.connect('data/db/clergy_abuse.db')
c = conn.cursor()
c.execute('SELECT id, first_name, last_name, narrative FROM accused_clergy WHERE narrative IS NOT NULL')

results = []
for row in c.fetchall():
    clergy_id, first, last, narrative = row
    # Your extraction logic here — this is the part you adapt per field
    # For settlement amounts:
    import re
    amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|M))?', narrative)
    if amounts:
        results.append({'clergy_id': clergy_id, 'name': f'{first} {last}', 'amounts': amounts})

with open('data/exports/extraction_[field].csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['clergy_id', 'name', 'amounts'])
    writer.writeheader()
    writer.writerows(results)

print(f'Found {len(results)} records with [field]')
```

Adapt the extraction logic to the specific field requested. Use regex where patterns are consistent, language understanding where they're not.

$ARGUMENTS
