---
name: Generate Report
description: Produce a formatted research report (Word document) on a topic with data, tables, citations, and methodology notes.
user-invocable: true
---

# Generate Research Report

You are producing a professional research report as a Word document (.docx). The report should be suitable for sharing with a department chair, including in a grant application, or distributing to stakeholders.

## Process

### Step 1: Understand the topic
Parse the user's request. What is the report about? A state? A diocese? A pattern? A facility? A comparison?

If unclear, ask one clarifying question. Then proceed.

### Step 2: Gather all relevant data
Use the MCP tools exhaustively. Pull:
- Summary statistics relevant to the topic
- Consequence breakdowns
- Facility connections
- Notable individual cases (3-5 examples)
- Comparisons to baselines (state vs. national, diocese vs. state)

Do NOT generate the report until you have all the data. Collect first, write second.

### Step 3: Write the report content
Structure as:

1. **Executive Summary** (1 paragraph, key findings)
2. **Introduction** (scope, what was analyzed)
3. **Data Sources & Methodology** (which sources, how many records, limitations)
4. **Findings** (organized by theme, with specific numbers)
5. **Notable Cases** (3-5 individual profiles summarized)
6. **Discussion** (what the findings mean, caveats)
7. **Appendix: Data Tables** (raw numbers for reference)

### Step 4: Generate the Word document
Use the docx skill (invoke `/docx`) to create a professional Word document. Include:
- Proper heading hierarchy
- Formatted tables with headers
- Page numbers
- Source attribution footer

Save to `data/exports/report_[topic_slug].docx`

Tell the user where the file is.

$ARGUMENTS
