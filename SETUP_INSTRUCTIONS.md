# Clergy Abuse Data Platform — Setup Instructions

## For the user

Copy this entire file into a Claude Code chat and say: **"Follow these setup instructions."**

That's it. Claude will handle everything else and explain what's happening along the way.

---

## Instructions for Claude

You are setting up the Clergy Abuse Data Platform for a researcher who may not be technical. Follow these steps IN ORDER. Before each step, explain to the user IN PLAIN LANGUAGE what you're about to do and why. After each step, confirm it worked. If anything fails, stop, explain the problem simply, and help them fix it before continuing.

**Be warm, patient, and thorough in your explanations.** This user may not know what a "virtual environment" or "repository" is. Translate everything into everyday language.

### Step 1: Check prerequisites

Check whether Python and Git are installed:
- Run `python --version` (or `python3 --version`)
- Run `git --version`

**If Python is missing**, tell the user:
"I need Python installed on your computer to run this. Here's what to do:
1. Go to https://python.org/downloads
2. Download the latest version for your computer
3. **IMPORTANT:** During installation, check the box that says 'Add Python to PATH'
4. After it installs, close and reopen Claude Code, paste these instructions again, and I'll pick up where we left off."

**If Git is missing**, tell the user:
"I need Git installed to download the project. Here's what to do:
1. Go to https://git-scm.com/downloads
2. Download and install the version for your computer (just click Next through the defaults)
3. After it installs, close and reopen Claude Code, paste these instructions again, and I'll pick up where we left off."

**If both are installed**, tell the user: "Great news — your computer already has everything I need. Let me download the project."

### Step 2: Download the project

First, check if we're already inside the project (look for `pyproject.toml` or `src/` directory in the current folder, or in a `ClergySexAbuse` subfolder).

**If the project is NOT here yet**, run:
```bash
git clone https://github.com/markgill47-lab/ClergySexAbuse.git
```

Then change into that directory. Use `cd ClergySexAbuse` as a bash command.

Tell the user: "I'm downloading the project from GitHub. This includes a database of 10,500+ accused clergy compiled from public sources — court documents, diocese disclosures, and investigative journalism. It's about 50 MB."

**If the project IS already here**, tell the user: "The project code is already on your computer. Moving to the next step."

### Step 3: Set up the Python environment

Run:
```bash
python -m venv .venv
```

Then activate it. Detect the OS and use the right command:
- **Windows:** `source .venv/Scripts/activate`
- **Mac/Linux:** `source .venv/bin/activate`

Tell the user: "I'm setting up a private workspace for this project. It's like creating a separate room for the software so it doesn't bump into anything else on your computer. This only takes a moment."

### Step 4: Install the software

Run:
```bash
pip install -e .
```

Tell the user: "I'm installing the libraries the platform needs. This takes a couple of minutes — you'll see a lot of text scrolling by, that's normal."

If this fails, check if the venv is activated (look for `(.venv)` in the prompt). If not, re-activate and retry. On Windows PowerShell, you may need to run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.

### Step 5: Verify everything works

Run this to check the database:
```bash
python -c "
import sqlite3, os
db_path = 'data/db/clergy_abuse.db'
if not os.path.exists(db_path):
    print('ERROR: Database not found')
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM accused_clergy')
    clergy = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM documents')
    docs = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM consequences')
    cons = c.fetchone()[0]
    print(f'OK: {clergy} clergy, {docs} documents, {cons} consequence events')
    conn.close()
"
```

Then check the analysis engine:
```bash
python -c "
import sys; sys.path.insert(0, '.')
from src.mcp_server.server import app, list_tools
import asyncio
tools = asyncio.run(list_tools())
print(f'OK: {len(tools)} research tools ready')
"
```

Tell the user: "Let me run a quick health check to make sure everything installed correctly..."

Then report the results: "Everything looks good! The database has [X] accused clergy records and the analysis engine has [X] research tools ready."

If the database is missing, tell the user: "The database file didn't come through. It should be about 50 MB. Please check with the person who shared this project — they may need to send the file separately. It goes at `data/db/clergy_abuse.db`."

### Step 6: Restart instructions

This is the final step. Tell the user EXACTLY this:

---

**Setup is complete!** Here's what happens next:

The project includes a configuration file that gives me direct access to the research database. For that to take effect, you need to restart this session. Here's how:

1. **Type `/exit`** to close this session (or just close the window)
2. **Open Claude Code again** — make sure you're in the `ClergySexAbuse` folder
3. **You'll see a prompt** asking you to approve an "MCP server" called `clergy-abuse-data` — **say yes** (this is what connects me to the database)
4. **That's it!** From now on, I'll have full access to the research tools every time you open Claude Code in this folder

**Once you're back, try asking me any of these:**

- "How many accused clergy are in California?"
- "What happened to priests sent to the Servants of the Paraclete facility?"
- "Show me who was sent to treatment and then reinstated to ministry"
- `/research What are the conviction rates by state?`
- `/generate-map no-accountability rate by state`

**What you now have access to:**

🔍 **18 research tools** — I can search the database, pull complete profiles, track consequence timelines, find patterns, detect facility funneling networks, measure reporting delays, and export data

📊 **2 skills** — `/research` for systematic investigations with structured reports, and `/generate-map` for interactive US maps

📁 **10,500+ records** from 4 sources across all 50 states, with 32,000+ consequence events and 640 linked court documents

This data documents real harm to real people. All records come from public sources — court documents, diocese disclosures, and investigative journalism. Please handle it with care.

---

## Troubleshooting

If something goes wrong during setup, here are common fixes:

**"python not found"** — Python isn't installed or isn't on the PATH. Download from https://python.org/downloads and check "Add Python to PATH" during installation. Then restart Claude Code.

**"git not found"** — Git isn't installed. Download from https://git-scm.com/downloads and install with defaults. Then restart Claude Code.

**"pip install fails"** — The virtual environment probably isn't activated. Look for `(.venv)` in your terminal prompt. If it's missing, run the activate command again (Step 3).

**"database not found"** — The file `data/db/clergy_abuse.db` is missing. Ask the person who shared this project to include it (it's ~50 MB).

**"MCP server not connecting after restart"** — Make sure Claude Code is open in the `ClergySexAbuse` folder (not a parent folder). When prompted to approve the `clergy-abuse-data` server, say yes.

**Windows PowerShell script errors** — Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and try again.
