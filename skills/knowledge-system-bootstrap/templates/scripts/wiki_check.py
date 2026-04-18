from __future__ import annotations
# llm-wiki-version: 1.2.2

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI_ROOT = ROOT / "docs" / "wiki"

REQUIRED_FILES = [
    "README.md",
    "SCHEMA.md",
    "index.md",
    "log.md",
    "project-overview.md",
    "current-status.md",
    "sources-and-data.md",
    "github-and-raw-strategy.md",
]

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
LOG_HEADER_RE = re.compile(r"^## \[\d{4}-\d{2}-\d{2}\] .+ \| .+$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
FRONTMATTER_EXEMPT = {"index.md", "log.md", "README.md", "SCHEMA.md"}
REQUIRED_FRONTMATTER_KEYS = {"title", "source", "created"}


def check_frontmatter(path: Path, text: str) -> list[str]:
    errs: list[str] = []
    rel = path.name
    if rel in FRONTMATTER_EXEMPT:
        return errs
    m = FRONTMATTER_RE.match(text)
    if not m:
        errs.append(f"missing frontmatter: {path.relative_to(ROOT)}")
        return errs
    body = m.group(1)
    found_keys: set[str] = set()
    for line in body.splitlines():
        if ":" in line:
            key = line.split(":", 1)[0].strip()
            found_keys.add(key)
    missing = REQUIRED_FRONTMATTER_KEYS - found_keys
    if missing:
        errs.append(f"missing frontmatter keys in {path.relative_to(ROOT)}: {', '.join(sorted(missing))}")
    return errs


def resolve_link(source_file: Path, target: str) -> Path | None:
    if target.startswith(("http://", "https://", "mailto:")):
        return None
    if target.startswith("#"):
        return None
    target = target.split("#", 1)[0]
    if not target:
        return None
    return (source_file.parent / target).resolve()


def main() -> int:
    errors: list[str] = []
    if not WIKI_ROOT.exists():
        print("wiki_check: docs/wiki does not exist")
        return 1

    for rel in REQUIRED_FILES:
        path = WIKI_ROOT / rel
        if not path.exists():
            errors.append(f"missing required file: docs/wiki/{rel}")

    md_files = sorted(WIKI_ROOT.rglob("*.md"))
    index_text = (WIKI_ROOT / "index.md").read_text(encoding="utf-8") if (WIKI_ROOT / "index.md").exists() else ""

    fm_ok = 0
    for path in md_files:
        text = path.read_text(encoding="utf-8")

        # Frontmatter check
        fm_errors = check_frontmatter(path, text)
        errors.extend(fm_errors)
        if not fm_errors and path.name not in FRONTMATTER_EXEMPT:
            fm_ok += 1

        if path.name == "log.md":
            headers = [line for line in text.splitlines() if line.startswith("## ")]
            for header in headers:
                if not LOG_HEADER_RE.match(header):
                    errors.append(f"bad log header format in {path.relative_to(ROOT)}: {header}")

        rel = path.relative_to(WIKI_ROOT).as_posix()
        if path.name != "index.md" and rel not in {"README.md", "SCHEMA.md", "log.md"}:
            if rel not in index_text:
                errors.append(f"index.md does not reference docs/wiki/{rel}")

        for match in LINK_RE.finditer(text):
            raw_target = match.group(1).strip()
            resolved = resolve_link(path, raw_target)
            if resolved is None:
                continue
            if not resolved.exists():
                errors.append(f"broken link in {path.relative_to(ROOT)} -> {raw_target}")

    if errors:
        print("wiki_check: FAILED")
        for item in errors:
            print(f"- {item}")
        return 1

    print("wiki_check: OK")
    print(f"- markdown files: {len(md_files)}")
    print(f"- required files: {len(REQUIRED_FILES)}")
    print(f"- frontmatter valid: {fm_ok}")
    print(f"- wiki root: {WIKI_ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
