# Ingest Pipeline

This is the part `LLM-wiki` was missing for too long: raw intake that does not feel like spreadsheet punishment.

## Goal

Turn this:

- a pile of PDFs
- a folder full of Excel files
- screenshots, archives, docs, random client junk

into this:

- a current `manifests/raw_sources.csv`
- a structural lock file with hashes and cheap metadata
- structured diff hints for table-shaped raw
- a report that shows what is new, changed, archived, or duplicated
- a stale report that tells you what wiki pages are now suspect
- optional draft stubs for manual recompilation

Without burning LLM tokens on clerical work.

## The two scripts

### 1. `python3 scripts/ingest_raw.py`

What it does:

1. scans the local raw root
2. computes a SHA-256 prefix for each tracked file
3. detects duplicates by content hash
4. guesses file kind locally
5. updates `manifests/raw_sources.csv`
6. writes `manifests/raw_index.json`
7. writes `manifests/intake_report.md`
8. records compact change summaries for changed CSV/XLSX/XLSM sources

It is local, deterministic, and cheap.

It does **not** call an LLM.

### 2. `python3 scripts/stale_report.py`

What it does:

1. reads wiki frontmatter
2. reads manifest rows
3. reads the raw lock / current raw files
4. compares `source_hash`
5. reports:
   - fresh pages
   - stale pages
   - missing hashes
   - unresolved sources
   - archived source references
   - manifest rows still stuck at `status=new`

This is the default freshness layer.

### 3. `python3 scripts/delta_compile.py --write-drafts`

What it does:

1. reads stale pages and uncompiled raw rows
2. chooses a target page or keeps the existing stale page as target
3. writes a manual draft stub under `docs/wiki/drafts/`
4. pre-fills `source`, `source_hash`, `compiled_at`, and optional `compiled_from`
5. emits `manifests/delta_compile_report.md`

It does **not** overwrite live wiki pages.

## Why this matters

Before this, most projects did one of two dumb things:

- hand-edit the manifest forever
- ignore raw freshness and pretend the wiki was still current

Now the boring parts are local automation:

- raw registration
- hash tracking
- duplicate detection
- stale reporting

LLM tokens can go to synthesis, not janitorial work.

## Supported local parsers

Current local parsing is intentionally cheap:

- `csv/tsv` → row count + headers
- `csv/tsv` changed files → row count, headers, key/value column hints, tracked row-change summary
- `xlsx/xlsm` → workbook sheet names, dimensions, header hints, and per-sheet structural change summary
- `xls` → legacy workbook marker (no fake precision)
- `docx` → paragraph blocks
- `pptx` → slide count
- `pdf` → rough page count
- `image` → dimensions when detectable
- `zip/tar/gz` → archive entry count
- plaintext → first non-empty line

This is not “full semantic understanding”.

Good. It should not be. The goal is to make raw intake cheaper and more reliable before any LLM touches it.

## Default workflow

When a batch of files lands:

```bash
python3 scripts/ingest_raw.py
python3 scripts/raw_manifest_check.py
python3 scripts/stale_report.py
python3 scripts/delta_compile.py --write-drafts
```

Then:

- compile the new or changed sources into the wiki
- add verified examples if the material confirms exact mappings
- rerun checks

## Design stance

- intake is local-first
- parsing is structural-first
- writeback still matters
- stale detection should be routine, not heroics
- LLM work starts **after** the raw surface is cleaned up

If the wiki is the brain, `ingest_raw.py` and `stale_report.py` are the eyes and pulse check.
