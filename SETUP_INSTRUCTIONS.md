# Clergy Abuse Data Platform — Setup Instructions

Hello! These instructions will set up the Clergy Abuse Data Platform on your machine. This is a research database of 10,500+ Catholic clergy accused of sexual abuse in the United States, with AI-powered analysis tools.

**To get started:** Open Claude Code in this folder and say: "Follow the instructions in SETUP_INSTRUCTIONS.md"

Claude will walk you through each step and explain what's happening.

---

## Instructions for Claude

You are setting up the Clergy Abuse Data Platform for a researcher. Follow these steps IN ORDER. After each step, explain to the user what you just did and what's coming next in plain language. If any step fails, stop and help the user troubleshoot before continuing.

### Step 1: Check prerequisites

Before starting, verify the user has:
- Python 3.11 or newer: run `python --version` or `python3 --version`
- Git: run `git --version`
- pip: run `pip --version` or `pip3 --version`

If any are missing, stop and tell the user what they need to install and where to get it:
- Python: https://python.org/downloads (check "Add Python to PATH" during install)
- Git: https://git-scm.com/downloads

Tell the user: "I'm checking that your computer has the software we need..."

### Step 2: Clone the repository

Run:
```bash
git clone https://github.com/markgill47-lab/ClergySexAbuse.git
cd ClergySexAbuse
```

**NOTE:** If the repo URL above doesn't work, ask the user for the correct repository URL or if they have the files already.

If the repo has already been cloned (you can tell because there's a `pyproject.toml` and `src/` directory present), skip this step and tell the user: "Looks like the code is already here. Moving on to setup."

Tell the user: "I'm downloading the project code. This includes the database with 10,500+ records of accused clergy compiled from public sources like BishopAccountability.org and Jeff Anderson & Associates."

### Step 3: Create a Python virtual environment

Run:
```bash
python -m venv .venv
```

Then activate it. The command depends on the operating system:
- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **Windows (cmd/Git Bash):** `.venv\Scripts\activate` or `source .venv/Scripts/activate`
- **Mac/Linux:** `source .venv/bin/activate`

Tell the user: "I'm creating an isolated Python environment so the project's dependencies don't interfere with anything else on your computer. Think of it like a sandbox."

### Step 4: Install dependencies

Run:
```bash
pip install -e .
```

This will take a minute or two. The main packages being installed are:
- SQLAlchemy (database access)
- FastAPI (the API framework)
- MCP SDK (the protocol that lets me talk to the database)
- httpx and BeautifulSoup (for web scraping, if you want to refresh the data later)

Tell the user: "I'm installing the software libraries the platform needs. This takes a couple minutes..."

### Step 5: Verify the database

Run a quick check to make sure the database file exists and has data:

```python
python -c "
import sqlite3
conn = sqlite3.connect('data/db/clergy_abuse.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM accused_clergy')
clergy = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM documents')
docs = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM consequences')
cons = c.fetchone()[0]
c.execute('SELECT COUNT(DISTINCT source_name) FROM source_records')
sources = c.fetchone()[0]
print(f'Database OK: {clergy} accused clergy, {docs} documents, {cons} consequence events, {sources} data sources')
conn.close()
"
```

Tell the user the results. It should show approximately 10,500 clergy, 640 documents, 32,000 consequence events, and 4 data sources.

If the database file is missing, tell the user: "The database file isn't here. This might mean it wasn't included in your copy of the project. Check with the person who shared this with you — the file should be at data/db/clergy_abuse.db and is about 50 MB."

### Step 6: Verify the MCP server

Test that the MCP server (the bridge between me and the database) loads correctly:

```python
python -c "
import sys
sys.path.insert(0, '.')
from src.mcp_server.server import app, list_tools
import asyncio
tools = asyncio.run(list_tools())
print(f'MCP server OK: {len(tools)} research tools available')
for t in tools[:5]:
    print(f'  - {t.name}')
print(f'  ... and {len(tools)-5} more')
"
```

Tell the user: "The analysis engine is working. I now have access to 18 specialized research tools for querying the database."

### Step 7: Explain the MCP connection

Tell the user:

"The project includes a file called `.mcp.json` that tells Claude Code how to connect to the database. **You need to restart this Claude Code session** for it to take effect.

Here's what to do:
1. Close this Claude Code session (type /exit or close the window)
2. Open Claude Code again in this same folder (ClergySexAbuse)
3. Claude Code will ask you to approve a new MCP server called 'clergy-abuse-data' — say yes
4. That's it! I'll have the research tools available automatically from now on

When you come back, try asking me:
- 'How many accused clergy are in California?'
- '/research What happened to priests sent to treatment facilities?'
- '/generate-map conviction rate by state'
"

### Step 8: What you now have

After restarting, explain to the user what they have access to:

"You now have a research platform with:

**18 analysis tools** that I can use automatically:
- Search for clergy by name, state, diocese, or status
- Pull complete profiles with all related data
- Track consequence timelines (what happened after each accusation)
- Find patterns like 'sent to treatment then reinstated'
- Detect cross-state funneling through treatment facilities
- Identify clergy who faced zero consequences
- Measure how long it took for consequences to occur
- Map transfer networks between dioceses
- Export data as CSV for your own analysis

**2 research skills** (slash commands):
- `/research <your question>` — I'll do a systematic investigation and produce a structured report
- `/generate-map <metric>` — I'll create an interactive map of the US showing any metric you want

**The data covers:**
- 10,500+ accused clergy across all 50 states
- 4 data sources (BishopAccountability.org, Anderson Advocates, UNM Santa Fe Archive)
- 32,000+ consequence events tracking what happened to each individual
- 640 linked documents (court filings, personnel files, depositions)

**Key findings already in the data:**
- 66.5% of accused clergy had 'no known action' as their final outcome
- Only 4.7% were convicted
- The Servants of the Paraclete facility in New Mexico received 156 clergy from 33 states
- Median time from ordination to first consequence: 45 years

This is sensitive subject matter. The data documents real harm to real people. All records come from public sources — court documents, diocese disclosures, and investigative journalism."

---

## Troubleshooting

If something goes wrong during setup, here are common issues:

**"python not found"** — Python isn't installed or isn't on the PATH. Download from python.org and make sure to check "Add Python to PATH" during installation.

**"pip install fails"** — Make sure the virtual environment is activated (you should see `(.venv)` in your terminal prompt). If on Windows and using PowerShell, you may need to run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.

**"database not found"** — The SQLite database file should be at `data/db/clergy_abuse.db`. If it's missing, the person who shared this project may need to include it separately (it's ~50 MB).

**"MCP server not connecting"** — Make sure you restarted Claude Code after setup. The `.mcp.json` file in the project root tells Claude Code how to find the server. If Claude Code asks you to approve the server, say yes.

**"ModuleNotFoundError"** — The virtual environment isn't activated, or `pip install -e .` didn't complete. Re-activate the venv and try the install again.
