# LLM Wiki — Universal Setup Guide

> Send this URL to any AI coding assistant. It will know what to do.
>
> https://github.com/Ss1024sS/LLM-wiki

---

## The Problem

- New session starts, AI remembers nothing
- Last week's decision? Buried in 3 hours of chat history
- Docs scattered across 10 places, nobody knows which version is current
- You keep re-explaining the same context every single time

## The Fix

Stop treating AI sessions as Q&A. Treat them as **compilation cycles**.

```
raw/ (source documents, immutable)
  |
  v  [LLM compiles]
  |
wiki/ (current consensus, continuously updated)
  |
  v  [LLM generates]
  |
code/ (compiled output, not the source of truth)
```

Every session: read wiki -> do work -> write back to wiki. Knowledge compounds. Nothing is lost.

---

## 5 Rules (Non-Negotiable)

1. **Compile-first** — Don't just answer questions. Compile raw docs into wiki pages.
2. **Writeback is mandatory** — Every conclusion, decision, or discovery goes back into the wiki. No exceptions.
3. **Wiki before RAG** — Under ~100 documents, direct LLM reading beats vector search. Less infra, better results.
4. **Obsidian is replaceable, the paradigm is not** — The real engine is LLM + filesystem + markdown. Tools come and go.
5. **Ideas outrank Code** — Your wiki (decisions, formulas, constraints) is more valuable than the code it generates.

---

## Setup for Any AI Platform

### Step 1: Create the wiki structure

In your project root, create these files:

```
your-project/
├── docs/wiki/
│   ├── index.md          # Links to all wiki pages
│   ├── log.md            # One line per session (date, topic, outcome)
│   ├── current-status.md # What's done, what's next, what's blocked
│   ├── project-overview.md
│   └── sources-and-data.md
├── manifests/
│   └── raw_sources.csv   # Index of raw docs (not the docs themselves)
└── [your platform config file]
```

Raw files (PDFs, Excel, images) stay **outside Git** in a local `raw/` directory. Only the compiled wiki goes into the repo.

### Step 2: Add the session protocol to your AI config

Copy the protocol below into your platform's config file. This is what makes the AI maintain the wiki automatically.

### Step 3: Start working

That's it. The AI will read the wiki at session start, update it during work, and write a log entry at session end. Knowledge compounds automatically.

---

## Platform-Specific Config Templates

### Claude Code (`CLAUDE.md`)

Create `CLAUDE.md` in your project root:

```markdown
# [Project Name] — Claude Rules

## Knowledge System
This project uses a wiki-first knowledge system. Knowledge lives in `docs/wiki/`, not in chat history.

## Session Protocol (mandatory)

### Session Start
1. Read `docs/wiki/index.md` — get the full page list
2. Read `docs/wiki/current-status.md` — know where things stand
3. Read `docs/wiki/log.md` — understand recent session history
4. Read additional wiki pages as needed for the current task

### During Work
- New decision made → update the relevant wiki page immediately
- New raw document discovered → register in `manifests/raw_sources.csv`, compile key info into wiki
- Task completed → update `docs/wiki/current-status.md`

### Session End
1. Append one line to `docs/wiki/log.md`: date, topic, key outcomes
2. Update `docs/wiki/current-status.md` with latest state
3. If context is running low → generate `CONTINUATION-SUMMARY.md`

### Rules
- compile-first: don't just answer, write conclusions into wiki pages
- writeback is mandatory: if you learned something durable, it goes in the wiki
- raw files (PDF/XLSX/images) stay outside Git, only manifests go in
```

### Codex (`AGENTS.md`)

Create `AGENTS.md` in your project root:

```markdown
# [Project Name] Agent Rules

## Session Protocol

Only tasks that are not pure chat require reading the wiki first:

1. `docs/wiki/index.md`
2. `docs/wiki/current-status.md`
3. `docs/wiki/log.md`

## Default Stance

- `compile-first`
- `writeback` is mandatory
- Wiki before heavy RAG
- Obsidian is optional, markdown is not
- `Idea / Intent` outranks `Code`

## Knowledge Layers

- raw: source documents (outside Git)
- wiki: compiled consensus (in Git)
- code: execution layer (in Git)

Changing code without updating wiki = incomplete work.
```

### Cursor (`.cursorrules`)

Create `.cursorrules` in your project root:

```
This project uses a wiki-first knowledge system.

Before starting any non-trivial task:
1. Read docs/wiki/index.md for the wiki page list
2. Read docs/wiki/current-status.md for project state
3. Read docs/wiki/log.md for recent session history

After completing work:
- Update docs/wiki/current-status.md with new state
- Append a log entry to docs/wiki/log.md (date | topic | outcome)
- If a durable decision was made, write it into the relevant wiki page

Rules:
- Compile raw documents into wiki pages, don't just reference them
- Every conclusion goes back into the wiki (writeback is mandatory)
- Raw files (PDF/XLSX) stay outside Git, only manifests/ indexes go in
```

### Windsurf (`.windsurfrules`)

Same content as `.cursorrules` above. Create `.windsurfrules` in project root.

### ChatGPT / Other (manual)

If your AI doesn't have filesystem access:
1. Paste the contents of `docs/wiki/current-status.md` at the start of each conversation
2. At the end of each conversation, ask the AI to generate updated wiki content
3. Manually copy the updates back into your wiki files

This is slower but still works. The paradigm matters more than the tool.

---

## The Bootstrap Script

For a faster setup, use the included Python script:

```bash
python3 scripts/bootstrap_knowledge_system.py /path/to/your-project "Your Project Name"
```

This generates the full wiki structure, manifest templates, and validation scripts in one command. See `docs/knowledge-system-playbook.md` for the complete rationale.

---

## Quick Test: Is It Working?

After 3 sessions, check:

- [ ] `docs/wiki/log.md` has 3 entries
- [ ] `docs/wiki/current-status.md` reflects the actual project state
- [ ] New session AI can answer "what did we do last time?" without you explaining
- [ ] Decisions from session 1 are still accessible in session 3

If yes, your knowledge system is compiling. If no, check that writeback is actually happening.

---

## Credits

Baseline paradigm from [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). This repo packages it into a reusable, platform-agnostic engineering practice.
