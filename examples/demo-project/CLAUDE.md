# Acme Widget Factory — Claude Rules

## Knowledge System
This project uses a wiki-first knowledge system. Knowledge lives in `docs/wiki/`, not in chat history.

## Session Protocol (mandatory)

### Session Start
1. Read `docs/wiki/index.md` — get the full page list
2. Read `docs/wiki/current-status.md` — know where things stand
3. Read `docs/wiki/log.md` — understand recent session history

### During Work
- New decision made → update the relevant wiki page immediately
- New raw document discovered → register in `manifests/raw_sources.csv`
- Task completed → update `docs/wiki/current-status.md`

### Session End
1. Append one line to `docs/wiki/log.md`
2. Update `docs/wiki/current-status.md`
