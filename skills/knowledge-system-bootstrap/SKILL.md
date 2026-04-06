---
name: knowledge-system-bootstrap
description: Bootstrap a compile-first project knowledge system with repo-local wiki, raw manifests, a local raw-root workflow, and a memory-repo export path. Use when a user wants to make project context durable across sessions, set up wiki-first rules, split GitHub from raw storage, or replicate this operating model into another repository.
---

# Knowledge System Bootstrap

Use this when the user wants a project to stop relying on chat memory and start behaving like a sane system.

## What this skill does

It scaffolds a reusable operating model:

- repo-local `docs/wiki/`
- `manifests/raw_sources.csv`
- repo-level `AGENTS.md`
- local raw-root convention outside Git
- validation scripts
- memory-repo export script

This is the default stance:

- `compile-first`
- `writeback` is mandatory
- medium-sized projects use `wiki` before heavy `RAG`
- Obsidian is optional, markdown is not
- `Idea / Intent` outranks `Code`

## When to use it

Use it when the user wants to:

- set up a durable project memory layer
- stop losing context between sessions
- separate GitHub knowledge from raw binary junk
- create a repeatable wiki/raw/manifests structure for a new repo
- migrate an existing repo toward this model

Do not use it for tiny throwaway demos. That would be cosplay.

## Workflow

1. Identify the target repo root and the project name.
2. Decide the default local raw-root name. Keep raw outside Git.
3. Run the bundled bootstrap script:

```bash
python3 scripts/bootstrap_knowledge_system.py /path/to/repo "Project Name"
```

4. In the target repo, initialize the local raw root:

```bash
cd /path/to/repo
python3 scripts/init_raw_root.py
```

5. Validate the generated knowledge layer:

```bash
python3 scripts/wiki_check.py
python3 scripts/raw_manifest_check.py
```

6. If the project also wants a separate GitHub memory repo, export the managed surface:

```bash
python3 scripts/export_memory_repo.py /path/to/memory-repo-checkout
```

## Existing repo migration rule

If the repo already has scattered docs or raw:

- do not duplicate raw into Git
- centralize raw into one local raw root
- register it in `manifests/raw_sources.csv`
- compile the stable conclusions into wiki pages

If you skip writeback, you did not finish the job.

## Bundled resources

- Script: `scripts/bootstrap_knowledge_system.py`
- Reference: `references/playbook.md`

Read `references/playbook.md` when you need the fuller rationale, GitHub/raw split, or operating model language.
