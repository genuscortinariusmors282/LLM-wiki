"""
Convenience entry point — ALWAYS use this one.

The real implementation lives at:
  skills/knowledge-system-bootstrap/scripts/bootstrap_knowledge_system.py

This wrapper exists so the documented command works after cloning:
  python3 scripts/bootstrap_knowledge_system.py /path/to/project "Name"

DO NOT call the skill script directly unless you know why.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REAL_SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "knowledge-system-bootstrap" / "scripts" / "bootstrap_knowledge_system.py"

if not REAL_SCRIPT.exists():
    print(f"Error: cannot find {REAL_SCRIPT}", file=sys.stderr)
    print("Make sure you cloned the full LLM-wiki repo.", file=sys.stderr)
    sys.exit(1)

os.execv(sys.executable, [sys.executable, str(REAL_SCRIPT)] + sys.argv[1:])
