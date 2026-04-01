#!/bin/bash
# Quick setup for Clergy Abuse Data Platform
set -e

echo "=== Clergy Abuse Data Platform Setup ==="

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv || python -m venv .venv
fi

# Activate
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

# Install
echo "Installing dependencies..."
pip install -e . --quiet

# Verify DB exists
if [ -f "data/db/clergy_abuse.db" ]; then
    echo "Database found: data/db/clergy_abuse.db"
    python -c "
import sqlite3
conn = sqlite3.connect('data/db/clergy_abuse.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM accused_clergy')
print(f'  {c.fetchone()[0]} accused clergy records')
c.execute('SELECT COUNT(*) FROM documents')
print(f'  {c.fetchone()[0]} linked documents')
conn.close()
"
else
    echo "WARNING: Database not found. Run: python scripts/import_existing.py"
fi

echo ""
echo "=== Setup complete ==="
echo "Start Claude Code in this directory. The MCP server will connect automatically."
echo "Try: /research What happened to priests in California?"
