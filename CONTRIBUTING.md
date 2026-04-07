# Contributing to LLM-wiki

## Quick Start

```bash
git clone https://github.com/Ss1024sS/LLM-wiki.git
cd LLM-wiki

# Test your changes
python3 scripts/bootstrap_knowledge_system.py /tmp/test-project "Test" --dry-run
python3 scripts/bootstrap_knowledge_system.py /tmp/test-project "Test"
cd /tmp/test-project && python3 scripts/wiki_check.py && python3 scripts/raw_manifest_check.py && python3 scripts/untracked_raw_check.py
```

## Where Things Live

```
scripts/bootstrap_knowledge_system.py    <-- entry point (wrapper)
skills/.../scripts/bootstrap_knowledge_system.py  <-- real implementation
```

Always test via the root wrapper. The skill script is the Codex internal copy.

## What to Change

**Wiki templates** — edit the string constants in `skills/.../scripts/bootstrap_knowledge_system.py`. They're Python string constants, not separate files. Yes, it's a bit ugly. But it keeps the bootstrap as a single zero-dependency script.

**Platform configs** — AGENTS.md, CLAUDE.md, .cursorrules, .windsurfrules templates are all in the same bootstrap script. If you add a platform, add it there + in UNIVERSAL.md + in the demo project.

**Validation scripts** — wiki_check.py, raw_manifest_check.py, untracked_raw_check.py are also string constants in the bootstrap. The generated copies are standalone Python with zero dependencies.

## Rules

1. Every PR must pass the smoke test (`.github/workflows/wiki-lint.yml`)
2. If you add a generated file, update the `--dry-run` count check in CI
3. If you change the SCHEMA, update `wiki_check.py` to validate it
4. If you add a platform, add: template in bootstrap + section in UNIVERSAL.md + file in demo

## Commit Style

```
Short description of what changed

Why this matters for the user.
What was wrong before, what's better now.
```

No prefixes (feat:, fix:, chore:). Just say what you did.
