#!/usr/bin/env python3
"""MCP server entry point. Use this in .mcp.json so it works regardless of venv location."""
import subprocess
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent

# Find venv Python
if sys.platform == "win32":
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
else:
    venv_python = project_root / ".venv" / "bin" / "python"

if not venv_python.exists():
    print(f"Virtual environment not found at {venv_python}", file=sys.stderr)
    print("Run: python -m venv .venv && pip install -e .", file=sys.stderr)
    sys.exit(1)

os.execv(str(venv_python), [str(venv_python), "-m", "src.mcp_server"] + sys.argv[1:])
