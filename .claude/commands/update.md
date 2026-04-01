---
name: Update Platform
description: Pull the latest skills, data, and code from the repository. Handles git pull, dependency updates, database updates, and skill syncing.
user-invocable: true
---

# Update Clergy Abuse Data Platform

The user wants to update to the latest version of the platform. This pulls new skills, updated data, code improvements, and database changes from the repository.

## Process

### Step 1: Check current state

Tell the user: "Let me check what version you're on and whether there are updates available."

Run:
```bash
git log --oneline -1
```

Then check for remote updates:
```bash
git fetch origin
git log --oneline HEAD..origin/master
```

If there are no new commits, tell the user: "You're already up to date!" and stop.

If there ARE new commits, tell the user how many updates are available and give a brief summary of what changed:
```bash
git log --oneline HEAD..origin/master
```

### Step 2: Pull updates

Tell the user: "Pulling [X] updates from the repository..."

```bash
git pull origin master
```

If this fails due to local changes, tell the user:
"You have local changes that conflict with the update. I can either:
1. Save your changes and apply the update (recommended)
2. Show you what's different so you can decide

Which would you prefer?"

If they choose option 1:
```bash
git stash
git pull origin master
git stash pop
```

### Step 3: Update dependencies

Check if pyproject.toml changed:
```bash
git diff HEAD~[number_of_new_commits] HEAD -- pyproject.toml
```

If it changed, update dependencies:
```bash
pip install -e .
```

Tell the user: "Some software dependencies were updated. Installing them now..."

If it didn't change, skip and tell the user: "No dependency changes needed."

### Step 4: Check for database updates

Check if the database file was updated:
```bash
git diff HEAD~[number_of_new_commits] HEAD --name-only -- data/db/
```

If the database was updated, tell the user: "The research database has been updated with new records." Run a quick count:
```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/db/clergy_abuse.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM accused_clergy')
print(f'Database now has {c.fetchone()[0]} accused clergy records')
conn.close()
"
```

### Step 5: Sync skills to global location

The skills need to be in ~/.claude/commands/ for the desktop app. Copy any new or updated skills:

```bash
cp .claude/commands/*.md ~/.claude/commands/
```

Tell the user: "Updated [X] research skills."

List any NEW skills that were added (files in the new commits that weren't there before):
```bash
git diff HEAD~[number_of_new_commits] HEAD --name-only --diff-filter=A -- .claude/commands/
```

If new skills were added, tell the user what they are and what they do.

### Step 6: Summary

Tell the user:

"Update complete! Here's what changed:
- [X] code updates pulled
- [Dependencies updated / No dependency changes]
- [Database updated to X records / No database changes]
- [X skills synced, Y new skills added]

[If new skills were added, list them with one-line descriptions]

You may want to restart this Claude Code session to ensure the MCP server picks up any code changes."

$ARGUMENTS
