# Release Notes — v1.2.2

Date: 2026-04-07

`v1.2.2` is the patch that makes `v1.2.x` actually sharp.

`v1.2.0` gave `LLM-wiki` real intake and stale detection.
`v1.2.2` makes that layer more useful in day-to-day work and less stupid under pressure.

## What changed

### 1. Table-shaped raw now gets compact structural diffs

Changed `csv/xlsx/xlsm` sources no longer just say “file changed”.

They now keep cheap local summaries like:

- `rows 1 -> 2`
- `tracked rows: 1 added`
- `sheet Pricebook: rows 2 -> 3; 1 added, 1 changed`

That matters because “this workbook changed” is weak.
“this sheet grew and these tracked rows changed” is actionable.

### 2. Provenance got stricter instead of more decorative

Two things were tightened:

- `provenance_check.py` now fails on unresolved sources instead of pretending they are fresh
- frontmatter semantics now explicitly support `source_hash`, `compiled_at`, and optional `compiled_from`

That means the system is less likely to smile politely while serving you stale garbage.

### 3. Manual delta compile now exists

Projects now get:

```bash
python3 scripts/delta_compile.py --write-drafts
```

It does not auto-overwrite live wiki pages.

It does:

- generate draft stubs for stale pages
- generate draft stubs for new raw that has not been compiled yet
- prefill `source`, `source_hash`, `compiled_at`, and `compiled_from`
- write `manifests/delta_compile_report.md`

That is the correct level of automation.
Drafts are useful. Silent mutation is bullshit.

### 4. Bootstrap, upgrade, docs, and CI now agree on the same world

This release also cleans up repo reality:

- bootstrap output is now **30 files**
- upgrade flow carries `delta_compile.py` forward
- docs point to the new provenance fields and manual delta compile flow
- smoke tests no longer poison their own provenance fixture
- workflow now uses `actions/checkout@v5` instead of carrying the Node 20 deprecation warning like a dead rat

## What was verified

This was reviewed like code that actually has to survive contact with users.

Validated locally:

1. Fresh bootstrap project
   - `30` files generated
   - `wiki_check.py`
   - `raw_manifest_check.py`
   - `untracked_raw_check.py`
   - `provenance_check.py`

2. Ingest + stale + delta flow
   - fresh raw intake
   - changed `csv`
   - changed `xlsx`
   - stale page detection
   - draft generation for stale and new raw
   - unresolved provenance failure

3. Edge cases
   - duplicate files
   - archived manifest rows
   - `--dry-run --write-drafts` writes no drafts

4. Upgrade path
   - upgraded a `v1.2.0` project into `v1.2.2`
   - confirmed `delta_compile.py` lands
   - reran validators successfully

## Why this release is worth tagging

Because it pushes more of the boring work into local scripts without crossing the line into reckless automation.

`LLM-wiki` should:

- detect
- compare
- suggest
- scaffold

It should not quietly rewrite living pages because a spreadsheet changed.

`v1.2.2` is closer to that line.
