#!/usr/bin/env bash
set -euo pipefail

INSTALLER="${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py"
DEST_DIR="${CODEX_HOME:-$HOME/.codex}/skills/knowledge-system-bootstrap"
SKILL_URL="https://github.com/Ss1024sS/LLM-wiki/tree/main/skills/knowledge-system-bootstrap"

if [[ ! -f "$INSTALLER" ]]; then
  echo "Codex skill-installer not found: $INSTALLER" >&2
  echo "Use Codex and run: Use \$skill-installer to install $SKILL_URL" >&2
  exit 1
fi

if [[ -d "$DEST_DIR" ]]; then
  echo "knowledge-system-bootstrap is already installed at $DEST_DIR"
  echo "Restart Codex if it is not showing up yet."
  exit 0
fi

python3 "$INSTALLER" --url "$SKILL_URL"
echo "Installed knowledge-system-bootstrap. Restart Codex to pick up new skills."
