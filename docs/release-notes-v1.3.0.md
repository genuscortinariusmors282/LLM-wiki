# v1.3.0 — Maintainability & honest claims

This release is mostly internal: the bootstrap script stops being a 2.6k-line
god object full of escaped string literals, the project ships as a Claude
plugin, and the "wiki before RAG" claim becomes a measurable threshold
instead of vibes.

## Why it matters

- Editing a generated script no longer requires fighting with `\\\\[` in
  string-embedded regexes. Every script and config is a real file under
  `templates/` that you can lint, test, diff, and PR-review.
- 35 pytest cases catch the obvious regressions before they ship.
- The Claude Code marketplace can install LLM-wiki directly via plugin.
- `--force` no longer silently destroys customized files.
- The manifest can evolve schemas without breaking every existing project.
- CI knows which checks need raw files and which don't, so the workflow
  doesn't half-fail on a clean checkout.

## What changed

### Refactored
- `bootstrap_knowledge_system.py` shrank from 2633 LOC to ~240 LOC. All
  embedded scripts and markdown templates moved to
  `skills/knowledge-system-bootstrap/templates/`. Bootstrap is now a thin
  renderer that walks a (template, target) table and substitutes three
  sentinels: `__PROJECT_NAME__`, `__RAW_ROOT_NAME__`, `__TODAY__`.

### Fixed
- `.gitignore` template stored literal `\\n` characters instead of
  newlines. Pre-1.3.0 projects got a single-line `.gitignore` that didn't
  ignore anything. Re-run bootstrap with `--force` to regenerate (your old
  `.gitignore` is backed up — see below).
- `wiki_check.py` used substring matching for the index.md reference
  check. A page named `policy.md` falsely passed whenever index.md
  mentioned `pricing-policy.md`. Now uses real markdown link parsing.
- `wiki_check.py` also validated links inside fenced code blocks and
  inline code; illustrative `[example](./fake.md)` snippets caused
  spurious "broken link" failures. Code regions are now skipped.

### Added
- **Claude plugin packaging**: `.claude-plugin/plugin.json` +
  `marketplace.json` + two slash commands (`/llm-wiki-bootstrap`,
  `/llm-wiki-status`). Install via `claude plugin install
  Ss1024sS/llm-wiki`.
- **`--force` is now safe**: existing files are copied to
  `<file>.bak.<YYYYMMDD-HHMMSS>` before being overwritten. Pass
  `--no-backup` to opt out. Files whose generated content matches the
  existing file count as "unchanged" and are not touched.
- **Manifest schema versioning**: new `manifests/raw_sources.meta.json`
  sidecar declares `schema_version`, `columns`, and `allowed_status`.
  `raw_manifest_check.py` reads the meta if present, falls back to a v1
  default for legacy projects, and SKIPs (exit 0) if it sees a future
  schema_version it doesn't understand — so a v2 manifest doesn't break
  old CI on a stale clone.
- **`wiki_size_report.py`**: estimates total wiki tokens (chars/4) and
  buckets it as GREEN <30k / YELLOW <80k / RED <200k / PURPLE ≥200k,
  with actionable advice per bucket. The "wiki before RAG" claim is now
  measurable instead of folkloric. Supports `--json` for tooling.
- **Runtime profile per script**: every script declares
  `# runtime: ci-safe (...)` or `# runtime: dev-only (...)`. New wiki
  page `docs/wiki/runtime-profile.md` documents which checks need raw
  files mounted vs. which run anywhere.
- **`provenance_check.py --ci`**: structural-only mode that verifies
  every non-session page has a `source_hash` field without trying to
  resolve raw files. Auto-detects via `CI=true` env var.
- **End-to-end pytest harness**: 35 tests under `tests/` cover
  bootstrap output, every check's pass/fail behavior on poisoned
  fixtures, plugin manifests, backup behavior, schema compat, and CI
  workflow constraints.

### Changed
- `.github/workflows/wiki-lint.yml` now runs the full ci-safe set:
  `wiki_check`, `raw_manifest_check`, `untracked_raw_check`,
  `wiki_size_report`, `provenance_check --ci`. Previously called
  `provenance_check` without `--ci`, which fails in CI without raw files.
- Bootstrap output is now **32 files** (was 30: +runtime-profile.md
  +raw_sources.meta.json +wiki_size_report.py).

## Upgrade path

```bash
cd /path/to/your-project
bash scripts/upgrade.sh
```

Validation scripts and CI are updated in place. Wiki content and
customized configs are not touched.

If you previously hand-edited `CLAUDE.md`, `AGENTS.md`, etc., re-running
bootstrap with `--force` now creates `.bak.<timestamp>` copies before
overwriting. To audit:

```bash
python3 scripts/bootstrap_knowledge_system.py . "Project Name" --dry-run
```

## Verified
- 35/35 pytest cases green
- Bootstrap output byte-identical to v1.2.2 for all 30 pre-existing files
  (only difference: the `.gitignore` newline bug fix)
- Round-trip: bootstrap fresh project → all checks green → poison each
  check → all checks fail with the right error
