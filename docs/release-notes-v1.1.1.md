# Release Notes — v1.1.1

Date: 2026-04-07

This is a cleanup patch. No new paradigm, no fake drama. Just fixing the parts that still looked a bit half-baked after `v1.1.0`.

## What changed

### 1. Markdown template bug fixed

`UNIVERSAL.md` no longer nests a triple-backtick YAML block inside a triple-backtick Markdown block.

That old version worked in some renderers and blew up in others. Now the Claude template uses a safer outer fence, so people can copy it without Markdown eating itself.

### 2. Team merge guidance is finally concrete

The old version basically said: "Git handles conflicts."

That was lazy.

Now both `UNIVERSAL.md` and the playbook spell out an actual strategy:

1. one session, one primary deep page owner at a time
2. specific pages beat summary pages
3. `log.md` is append-only
4. conflicts are resolved manually using better source backing, not "accept both"
5. post-merge checks are mandatory

### 3. Release docs are back in sync

The last round had a stupid doc drift problem:

- some places said `22 files`
- some said `24`
- bootstrap actually generated `27`

That is fixed now.

Current truth:

- bootstrap generates **27 files**
- `README.md` says `27`
- `SKILL.md` says `27`
- release notes stop contradicting the repo

### 4. Upgrade path docs no longer point to the old flow

The old release note still told users to fetch `upgrade_knowledge_system.py` with `curl`.

That is now replaced with the real supported flow:

- from a bootstrapped project:

```bash
bash scripts/upgrade.sh
```

- from a clone of `LLM-wiki`:

```bash
bash scripts/upgrade.sh /path/to/your-project
```

## What did not change

- bootstrap output is still `27` files
- CI smoke test is still the same 9-check suite
- provenance model is unchanged from the latest `main`
- no runtime logic was changed; this is a docs/release cleanup patch

## Recommended upgrade

If you already use `LLM-wiki`, you do **not** need to rebuild anything from scratch.

Just use the normal upgrade path:

```bash
cd /path/to/your-project
bash scripts/upgrade.sh
```

If the project is old enough that it does not have `scripts/upgrade.sh` yet:

```bash
git clone https://github.com/Ss1024sS/LLM-wiki.git
cd LLM-wiki
bash scripts/upgrade.sh /path/to/your-project
```

## Bottom line

`v1.1.1` makes the project look less like a clever prototype and more like a tool you can hand to other people without apologizing for it.
