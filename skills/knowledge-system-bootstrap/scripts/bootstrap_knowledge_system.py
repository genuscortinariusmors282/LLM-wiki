from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

__version__ = "1.2.2"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "project"


WIKI_CHECK = """from __future__ import annotations
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

LINK_RE = re.compile(r"\\[[^\\]]+\\]\\(([^)]+)\\)")
LOG_HEADER_RE = re.compile(r"^## \\[\\d{4}-\\d{2}-\\d{2}\\] .+ \\| .+$")
FRONTMATTER_RE = re.compile(r"^---\\n(.*?)\\n---", re.DOTALL)
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
"""


RAW_MANIFEST_CHECK = """from __future__ import annotations
# llm-wiki-version: 1.2.2

import csv
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "raw_sources.csv"
EXPECTED_COLUMNS = [
    "source_id",
    "company",
    "vendor",
    "kind",
    "filename",
    "raw_rel_path",
    "status",
    "compiled_into",
    "notes",
]
ALLOWED_STATUS = {"new", "compiled", "archived"}


def main() -> int:
    errors: list[str] = []
    if not MANIFEST.exists():
        print(f"raw_manifest_check: missing {MANIFEST}")
        return 1

    raw_root_env = os.environ.get("PROJECT_RAW_ROOT")
    raw_root = Path(raw_root_env).expanduser().resolve() if raw_root_env else None

    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_COLUMNS:
            errors.append(f"manifest columns mismatch: expected {EXPECTED_COLUMNS}, got {reader.fieldnames}")
        seen_ids: set[str] = set()
        for idx, row in enumerate(reader, start=2):
            source_id = (row.get("source_id") or "").strip()
            filename = (row.get("filename") or "").strip()
            raw_rel_path = (row.get("raw_rel_path") or "").strip()
            status = (row.get("status") or "").strip()
            compiled_into = (row.get("compiled_into") or "").strip()

            if not source_id:
                errors.append(f"row {idx}: empty source_id")
            elif source_id in seen_ids:
                errors.append(f"row {idx}: duplicate source_id {source_id}")
            else:
                seen_ids.add(source_id)

            if not filename:
                errors.append(f"row {idx}: empty filename")
            if not raw_rel_path:
                errors.append(f"row {idx}: empty raw_rel_path")
            if status not in ALLOWED_STATUS:
                errors.append(f"row {idx}: bad status {status}")

            if raw_root and raw_rel_path:
                candidate = (raw_root / raw_rel_path).resolve()
                if not candidate.exists():
                    errors.append(f"row {idx}: missing local raw file {candidate}")

            if status == "compiled" and not compiled_into:
                errors.append(f"row {idx}: status {status} requires compiled_into")

    if errors:
        print("raw_manifest_check: FAILED")
        for item in errors:
            print(f"- {item}")
        return 1

    print("raw_manifest_check: OK")
    print(f"- manifest: {MANIFEST}")
    if raw_root:
        print(f"- PROJECT_RAW_ROOT: {raw_root}")
    else:
        print("- PROJECT_RAW_ROOT: not set, existence checks skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""


INGEST_RAW = """from __future__ import annotations
# llm-wiki-version: 1.2.2

import argparse
import csv
import hashlib
import json
import os
import re
import tarfile
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "raw_sources.csv"
LOCK_FILE = ROOT / "manifests" / "raw_index.json"
REPORT_FILE = ROOT / "manifests" / "intake_report.md"
DEFAULT_RAW_ROOT = (ROOT.parent / "__RAW_ROOT_NAME__").resolve()
EXPECTED_COLUMNS = [
    "source_id",
    "company",
    "vendor",
    "kind",
    "filename",
    "raw_rel_path",
    "status",
    "compiled_into",
    "notes",
]
TRACKED_EXTENSIONS = {
    ".pdf", ".md", ".txt",
    ".xlsx", ".xls", ".xlsm", ".csv", ".tsv",
    ".doc", ".docx", ".ppt", ".pptx",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
    ".zip", ".rar", ".7z", ".tar", ".gz",
}
SKIP_DIRS = {
    ".git", ".svn", "__pycache__", ".DS_Store",
    "node_modules", ".venv", "venv",
}
KEY_COLUMN_HINTS = ("sku", "part", "item", "model", "spec", "code", "pn", "material", "id", "series")
VALUE_COLUMN_HINTS = ("price", "cost", "amount", "qty", "quantity", "lead", "currency", "discount", "rate")
MAX_HEADERS = 8
MAX_ROW_WIDTH = 12
MAX_TRACKED_ROWS = 2000
MAX_SHEETS = 6


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_prefix(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def safe_read_text(path: Path, limit: int = 2000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except Exception:
        return ""


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip(" #\t-")
        if stripped:
            return stripped[:120]
    return ""


def detect_kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".xlsx", ".xls", ".xlsm", ".csv", ".tsv"}:
        return "spreadsheet"
    if ext in {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".md", ".txt"}:
        return "document"
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}:
        return "image"
    if ext in {".zip", ".rar", ".7z", ".tar", ".gz"}:
        return "archive"
    return "raw"


def clean_cells(values: list[str], *, limit: int = MAX_ROW_WIDTH) -> list[str]:
    cleaned = [
        str(value or "").replace("\\n", " ").replace("\\r", " ").strip()[:80]
        for value in values[:limit]
    ]
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return cleaned


def guess_key_column(headers: list[str]) -> str:
    lowered = [(header, header.lower()) for header in headers if header]
    for hint in KEY_COLUMN_HINTS:
        for original, value in lowered:
            if hint in value:
                return original
    return headers[0] if headers else ""


def suspicious_columns(headers: list[str]) -> list[str]:
    flagged: list[str] = []
    for header in headers:
        lowered = header.lower()
        if any(hint in lowered for hint in KEY_COLUMN_HINTS + VALUE_COLUMN_HINTS):
            flagged.append(header)
    return flagged[:6]


def row_signature(cells: list[str]) -> str:
    payload = "|".join(clean_cells(cells, limit=MAX_ROW_WIDTH))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compare_named_lists(before: list[str], after: list[str]) -> tuple[list[str], list[str]]:
    old = set(before)
    new = set(after)
    return sorted(new - old), sorted(old - new)


def compare_row_signatures(before: dict[str, str], after: dict[str, str]) -> str:
    if not before or not after:
        return ""
    old_keys = set(before)
    new_keys = set(after)
    added = len(new_keys - old_keys)
    removed = len(old_keys - new_keys)
    changed = len([key for key in old_keys & new_keys if before[key] != after[key]])
    parts: list[str] = []
    if added:
        parts.append(f"{added} added")
    if removed:
        parts.append(f"{removed} removed")
    if changed:
        parts.append(f"{changed} changed")
    return ", ".join(parts)


def summarize_delimited(path: Path, delimiter: str, parser: str) -> dict[str, object]:
    headers: list[str] = []
    key_column = ""
    key_index = -1
    row_count = 0
    column_count = 0
    tracked_rows: dict[str, str] = {}
    sample_rows: list[str] = []
    truncated = False
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for raw_row in reader:
            cleaned = clean_cells(raw_row)
            if not cleaned:
                continue
            column_count = max(column_count, len(cleaned))
            if not headers:
                headers = [cell[:60] for cell in cleaned[:MAX_HEADERS]]
                key_column = guess_key_column(headers)
                key_index = headers.index(key_column) if key_column in headers else -1
                continue
            row_count += 1
            if len(sample_rows) < 3:
                sample_rows.append(" | ".join(cleaned[:MAX_HEADERS]))
            if row_count > MAX_TRACKED_ROWS:
                truncated = True
                continue
            if key_index >= 0 and key_index < len(cleaned):
                key = cleaned[key_index]
                if key:
                    tracked_rows[key] = row_signature(cleaned)
    return {
        "parser": parser,
        "summary": (
            f"{row_count} data row(s); {column_count} column(s); "
            f"headers: {', '.join(headers) if headers else 'none'}"
        ),
        "metadata": {
            "row_count": row_count,
            "column_count": column_count,
            "headers": headers,
            "delimiter": delimiter,
            "key_column": key_column,
            "suspicious_columns": suspicious_columns(headers),
            "sample_rows": sample_rows,
            "tracked_rows": tracked_rows,
            "truncated": truncated,
        },
    }


def summarize_csv(path: Path) -> dict[str, object]:
    delimiter = "," if path.suffix.lower() == ".csv" else "\\t"
    return summarize_delimited(path, delimiter, "csv-local")


def normalize_zip_path(base: str, target: str) -> str:
    parts = [part for part in (Path(base).parent / target).as_posix().split("/") if part not in {"", "."}]
    normalized: list[str] = []
    for part in parts:
        if part == "..":
            if normalized:
                normalized.pop()
            continue
        normalized.append(part)
    return "/".join(normalized)


def spreadsheet_column_index(label: str) -> int:
    total = 0
    for char in label.upper():
        if not char.isalpha():
            break
        total = total * 26 + (ord(char) - 64)
    return total


def parse_sheet_dimension(ref: str) -> tuple[int, int]:
    if not ref:
        return 0, 0
    tail = ref.split(":")[-1]
    letters = "".join(char for char in tail if char.isalpha())
    digits = "".join(char for char in tail if char.isdigit())
    return int(digits or 0), spreadsheet_column_index(letters)


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        with zf.open("xl/sharedStrings.xml") as handle:
            root = ET.fromstring(handle.read())
        return ["".join(node.itertext()).strip() for node in root.findall(".//{*}si")]
    except Exception:
        return []


def read_workbook_sheets(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    with zf.open("xl/workbook.xml") as handle:
        workbook_root = ET.fromstring(handle.read())
    rel_map: dict[str, str] = {}
    try:
        with zf.open("xl/_rels/workbook.xml.rels") as handle:
            rel_root = ET.fromstring(handle.read())
        for node in rel_root.findall(".//{*}Relationship"):
            rel_id = node.attrib.get("Id", "")
            target = node.attrib.get("Target", "")
            if rel_id and target:
                rel_map[rel_id] = normalize_zip_path("xl/workbook.xml", target)
    except Exception:
        rel_map = {}
    sheets: list[tuple[str, str]] = []
    for node in workbook_root.findall(".//{*}sheet"):
        name = node.attrib.get("name", "")
        rel_id = ""
        for key, value in node.attrib.items():
            if key.endswith("}id") or key == "id":
                rel_id = value
                break
        target = rel_map.get(rel_id, "")
        if name and target:
            sheets.append((name, target))
    return sheets


def resolve_xlsx_cell(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(cell.itertext()).strip()
    value = cell.findtext("{*}v", default="").strip()
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except Exception:
            return value
    if cell_type == "b":
        return "TRUE" if value == "1" else "FALSE"
    if value:
        return value
    return "".join(cell.itertext()).strip()


def summarize_xlsx_sheet(zf: zipfile.ZipFile, sheet_name: str, sheet_path: str, shared_strings: list[str]) -> dict[str, object]:
    with zf.open(sheet_path) as handle:
        root = ET.fromstring(handle.read())
    dimension_node = root.find("{*}dimension")
    dim_rows, dim_cols = parse_sheet_dimension(dimension_node.attrib.get("ref", "") if dimension_node is not None else "")
    headers: list[str] = []
    key_column = ""
    key_index = -1
    row_count = 0
    column_count = 0
    tracked_rows: dict[str, str] = {}
    sample_rows: list[str] = []
    truncated = False
    for row_node in root.findall(".//{*}sheetData/{*}row"):
        cells_by_index: dict[int, str] = {}
        for cell in row_node.findall("{*}c"):
            ref = cell.attrib.get("r", "")
            letters = "".join(char for char in ref if char.isalpha())
            index = spreadsheet_column_index(letters) or (len(cells_by_index) + 1)
            cells_by_index[index] = resolve_xlsx_cell(cell, shared_strings)
        if not cells_by_index:
            continue
        max_index = min(max(cells_by_index), MAX_ROW_WIDTH)
        cleaned = clean_cells([cells_by_index.get(idx, "") for idx in range(1, max_index + 1)])
        if not cleaned:
            continue
        column_count = max(column_count, len(cleaned))
        if not headers:
            headers = [cell[:60] for cell in cleaned[:MAX_HEADERS]]
            key_column = guess_key_column(headers)
            key_index = headers.index(key_column) if key_column in headers else -1
            continue
        row_count += 1
        if len(sample_rows) < 3:
            sample_rows.append(" | ".join(cleaned[:MAX_HEADERS]))
        if row_count > MAX_TRACKED_ROWS:
            truncated = True
            continue
        if key_index >= 0 and key_index < len(cleaned):
            key = cleaned[key_index]
            if key:
                tracked_rows[key] = row_signature(cleaned)
    return {
        "name": sheet_name,
        "row_count": row_count or dim_rows,
        "column_count": column_count or dim_cols,
        "headers": headers,
        "key_column": key_column,
        "suspicious_columns": suspicious_columns(headers),
        "sample_rows": sample_rows,
        "tracked_rows": tracked_rows,
        "truncated": truncated,
    }


def summarize_xlsx(path: Path) -> dict[str, object]:
    sheets: list[dict[str, object]] = []
    try:
        with zipfile.ZipFile(path) as zf:
            shared_strings = read_shared_strings(zf)
            for sheet_name, sheet_path in read_workbook_sheets(zf)[:MAX_SHEETS]:
                try:
                    sheets.append(summarize_xlsx_sheet(zf, sheet_name, sheet_path, shared_strings))
                except Exception:
                    sheets.append({
                        "name": sheet_name,
                        "row_count": 0,
                        "column_count": 0,
                        "headers": [],
                        "key_column": "",
                        "suspicious_columns": [],
                        "sample_rows": [],
                        "tracked_rows": {},
                        "truncated": False,
                    })
    except Exception:
        sheets = []
    sheet_names = [sheet["name"] for sheet in sheets]
    summary_bits = [
        f"{sheet['name']}[{sheet.get('row_count', 0)}x{sheet.get('column_count', 0)}]"
        for sheet in sheets[:4]
    ]
    return {
        "parser": "xlsx-local",
        "summary": f"{len(sheet_names)} sheet(s): {', '.join(summary_bits) if summary_bits else 'unknown'}",
        "metadata": {"sheet_names": sheet_names, "sheets": sheets},
    }


def summarize_docx(path: Path) -> dict[str, object]:
    paragraph_count = 0
    try:
        with zipfile.ZipFile(path) as zf:
            with zf.open("word/document.xml") as handle:
                root = ET.fromstring(handle.read())
            paragraph_count = len(root.findall(".//{*}p"))
    except Exception:
        pass
    return {
        "parser": "docx-local",
        "summary": f"{paragraph_count} paragraph block(s)",
        "metadata": {"paragraph_blocks": paragraph_count},
    }


def summarize_pptx(path: Path) -> dict[str, object]:
    slide_count = 0
    try:
        with zipfile.ZipFile(path) as zf:
            slide_count = len([name for name in zf.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")])
    except Exception:
        pass
    return {
        "parser": "pptx-local",
        "summary": f"{slide_count} slide(s)",
        "metadata": {"slide_count": slide_count},
    }


def summarize_pdf(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    page_count = raw.count(b"/Type /Page")
    return {
        "parser": "pdf-local",
        "summary": f"{page_count or 'unknown'} page(s)",
        "metadata": {"page_count": int(page_count)},
    }


def image_size(path: Path) -> tuple[int | None, int | None]:
    raw = path.read_bytes()[:64]
    if raw.startswith(b"\\x89PNG\\r\\n\\x1a\\n") and len(raw) >= 24:
        return int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
    if raw[:6] in {b"GIF87a", b"GIF89a"} and len(raw) >= 10:
        return int.from_bytes(raw[6:8], "little"), int.from_bytes(raw[8:10], "little")
    if raw.startswith(b"BM") and len(raw) >= 26:
        return int.from_bytes(raw[18:22], "little"), int.from_bytes(raw[22:26], "little")
    if raw.startswith(b"\\xff\\xd8"):
        with path.open("rb") as handle:
            handle.read(2)
            while True:
                marker_prefix = handle.read(1)
                if marker_prefix != b"\\xff":
                    break
                marker = handle.read(1)
                while marker == b"\\xff":
                    marker = handle.read(1)
                if marker in {b"\\xc0", b"\\xc1", b"\\xc2", b"\\xc3", b"\\xc5", b"\\xc6", b"\\xc7", b"\\xc9", b"\\xca", b"\\xcb", b"\\xcd", b"\\xce", b"\\xcf"}:
                    _length = int.from_bytes(handle.read(2), "big")
                    handle.read(1)
                    height = int.from_bytes(handle.read(2), "big")
                    width = int.from_bytes(handle.read(2), "big")
                    return width, height
                if marker in {b"\\xd8", b"\\xd9"}:
                    continue
                seg_length = int.from_bytes(handle.read(2), "big")
                handle.seek(seg_length - 2, 1)
    return None, None


def summarize_image(path: Path) -> dict[str, object]:
    width, height = image_size(path)
    dims = f"{width}x{height}" if width and height else "unknown"
    return {
        "parser": "image-local",
        "summary": f"dimensions: {dims}",
        "metadata": {"width": width, "height": height},
    }


def summarize_archive(path: Path) -> dict[str, object]:
    ext = path.suffix.lower()
    entry_count = None
    parser = "archive-local"
    try:
        if ext == ".zip":
            with zipfile.ZipFile(path) as zf:
                entry_count = len(zf.namelist())
        elif ext in {".tar", ".gz"} or path.name.endswith(".tar.gz"):
            with tarfile.open(path) as tf:
                entry_count = len(tf.getmembers())
    except Exception:
        entry_count = None
    return {
        "parser": parser,
        "summary": f"archive entries: {entry_count if entry_count is not None else 'unknown'}",
        "metadata": {"entry_count": entry_count, "format": ext.lstrip('.')},
    }


def summarize_plaintext(path: Path) -> dict[str, object]:
    text = safe_read_text(path)
    summary = first_nonempty_line(text) or "no preview"
    return {
        "parser": "text-local",
        "summary": summary,
        "metadata": {"preview": summary},
    }


def summarize_xls_legacy(path: Path) -> dict[str, object]:
    return {
        "parser": "xls-legacy",
        "summary": "legacy .xls workbook (sheet metadata unavailable without extra parser)",
        "metadata": {"format": "xls", "size_bytes": path.stat().st_size},
    }


def summarize_csv_change(previous: dict[str, object], current: dict[str, object]) -> list[str]:
    notes: list[str] = []
    prev_headers = [str(item) for item in previous.get("headers", [])]
    curr_headers = [str(item) for item in current.get("headers", [])]
    added_headers, removed_headers = compare_named_lists(prev_headers, curr_headers)
    if added_headers:
        notes.append(f"headers added: {', '.join(added_headers[:4])}")
    if removed_headers:
        notes.append(f"headers removed: {', '.join(removed_headers[:4])}")
    prev_rows = int(previous.get("row_count", 0) or 0)
    curr_rows = int(current.get("row_count", 0) or 0)
    if prev_rows != curr_rows:
        notes.append(f"rows {prev_rows} -> {curr_rows}")
    prev_key = str(previous.get("key_column", "") or "")
    curr_key = str(current.get("key_column", "") or "")
    if prev_key != curr_key and curr_key:
        notes.append(f"key column {prev_key or 'none'} -> {curr_key}")
    row_changes = compare_row_signatures(
        {str(k): str(v) for k, v in dict(previous.get("tracked_rows", {})).items()},
        {str(k): str(v) for k, v in dict(current.get("tracked_rows", {})).items()},
    )
    if row_changes:
        notes.append(f"tracked rows: {row_changes}")
    if not notes:
        notes.append("content changed; structural summary unchanged")
    return notes


def summarize_xlsx_change(previous: dict[str, object], current: dict[str, object]) -> list[str]:
    notes: list[str] = []
    prev_sheets = {str(sheet.get("name", "")): sheet for sheet in previous.get("sheets", []) if sheet.get("name")}
    curr_sheets = {str(sheet.get("name", "")): sheet for sheet in current.get("sheets", []) if sheet.get("name")}
    added_sheets, removed_sheets = compare_named_lists(list(prev_sheets), list(curr_sheets))
    if added_sheets:
        notes.append(f"sheets added: {', '.join(added_sheets[:4])}")
    if removed_sheets:
        notes.append(f"sheets removed: {', '.join(removed_sheets[:4])}")
    for sheet_name in sorted(prev_sheets.keys() & curr_sheets.keys())[:4]:
        before = prev_sheets[sheet_name]
        after = curr_sheets[sheet_name]
        sheet_notes: list[str] = []
        if int(before.get("row_count", 0) or 0) != int(after.get("row_count", 0) or 0):
            sheet_notes.append(f"rows {before.get('row_count', 0)} -> {after.get('row_count', 0)}")
        if int(before.get("column_count", 0) or 0) != int(after.get("column_count", 0) or 0):
            sheet_notes.append(f"cols {before.get('column_count', 0)} -> {after.get('column_count', 0)}")
        added_headers, removed_headers = compare_named_lists(
            [str(item) for item in before.get("headers", [])],
            [str(item) for item in after.get("headers", [])],
        )
        if added_headers:
            sheet_notes.append(f"headers +{', '.join(added_headers[:3])}")
        if removed_headers:
            sheet_notes.append(f"headers -{', '.join(removed_headers[:3])}")
        row_changes = compare_row_signatures(
            {str(k): str(v) for k, v in dict(before.get("tracked_rows", {})).items()},
            {str(k): str(v) for k, v in dict(after.get("tracked_rows", {})).items()},
        )
        if row_changes:
            sheet_notes.append(row_changes)
        if sheet_notes:
            notes.append(f"sheet {sheet_name}: {'; '.join(sheet_notes)}")
    if not notes:
        notes.append("content changed; workbook structure summary unchanged")
    return notes


def summarize_change(previous_entry: dict[str, object] | None, current_payload: dict[str, object]) -> list[str]:
    if not previous_entry:
        return []
    previous_parser = str(previous_entry.get("parser", ""))
    current_parser = str(current_payload.get("parser", ""))
    previous_meta = dict(previous_entry.get("metadata", {}))
    current_meta = dict(current_payload.get("metadata", {}))
    if previous_parser == current_parser == "csv-local":
        return summarize_csv_change(previous_meta, current_meta)
    if previous_parser == current_parser == "xlsx-local":
        return summarize_xlsx_change(previous_meta, current_meta)
    return [f"summary: {previous_entry.get('summary', 'unknown')} -> {current_payload.get('summary', 'unknown')}"]


def summarize_file(path: Path) -> dict[str, object]:
    ext = path.suffix.lower()
    if ext in {".csv", ".tsv"}:
        return summarize_csv(path)
    if ext in {".xlsx", ".xlsm"}:
        return summarize_xlsx(path)
    if ext == ".xls":
        return summarize_xls_legacy(path)
    if ext == ".docx":
        return summarize_docx(path)
    if ext == ".pptx":
        return summarize_pptx(path)
    if ext == ".pdf":
        return summarize_pdf(path)
    if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}:
        return summarize_image(path)
    if ext in {".zip", ".rar", ".7z", ".tar", ".gz"} or path.name.endswith(".tar.gz"):
        return summarize_archive(path)
    return summarize_plaintext(path)


def load_manifest() -> list[dict[str, str]]:
    if not MANIFEST.exists():
        raise FileNotFoundError(f"manifest missing: {MANIFEST}")
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise ValueError(f"manifest columns mismatch: expected {EXPECTED_COLUMNS}, got {reader.fieldnames}")
        return [{key: (value or "") for key, value in row.items()} for row in reader]


def write_manifest(rows: list[dict[str, str]]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in EXPECTED_COLUMNS})


def load_lock() -> dict[str, object]:
    if not LOCK_FILE.exists():
        return {"files": {}}
    try:
        return json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"files": {}}


def write_lock(payload: dict[str, object]) -> None:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\\n", encoding="utf-8")


def next_source_id(existing_ids: set[str], content_hash: str) -> str:
    base = f"src_{content_hash[:10]}"
    candidate = base
    index = 2
    while candidate in existing_ids:
        candidate = f"{base}_{index}"
        index += 1
    return candidate


def build_report(
    raw_root: Path,
    rows: list[dict[str, str]],
    kinds: Counter[str],
    new_paths: list[str],
    changed_paths: list[str],
    archived_paths: list[str],
    duplicate_paths: list[str],
    change_summaries: dict[str, list[str]],
) -> str:
    def bullets(items: list[str], *, details: dict[str, list[str]] | None = None) -> str:
        if not items:
            return "- none\\n"
        lines: list[str] = []
        for item in items[:20]:
            detail_lines = (details or {}).get(item, [])
            if detail_lines:
                lines.append(f"- `{item}` — {detail_lines[0]}\\n")
                for extra in detail_lines[1:3]:
                    lines.append(f"  - {extra}\\n")
            else:
                lines.append(f"- `{item}`\\n")
        return "".join(lines)

    lines = [
        "# Raw Intake Report",
        "",
        f"- generated_at: `{utc_now()}`",
        f"- raw_root: `{raw_root}`",
        f"- manifest_rows: `{len(rows)}`",
        f"- new: `{len(new_paths)}`",
        f"- changed: `{len(changed_paths)}`",
        f"- archived: `{len(archived_paths)}`",
        f"- duplicates: `{len(duplicate_paths)}`",
        "",
        "## Kind Summary",
        "",
    ]
    if kinds:
        for kind, count in sorted(kinds.items()):
            lines.append(f"- `{kind}`: {count}")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## New Files",
        "",
        bullets(sorted(new_paths)),
        "",
        "## Changed Files",
        "",
        bullets(sorted(changed_paths), details=change_summaries),
        "",
        "## Archived Files",
        "",
        bullets(sorted(archived_paths)),
        "",
        "## Duplicate Files",
        "",
        bullets(sorted(duplicate_paths)),
    ])
    return "\\n".join(lines).rstrip() + "\\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a local raw root, update the manifest, and record low-cost structural metadata.")
    parser.add_argument("--raw-root", default=os.environ.get("PROJECT_RAW_ROOT", str(DEFAULT_RAW_ROOT)), help="Local raw root path")
    parser.add_argument("--report-file", default=str(REPORT_FILE), help="Markdown report output path")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing manifest or lock files")
    args = parser.parse_args()

    raw_root = Path(args.raw_root).expanduser().resolve()
    if not raw_root.exists():
        print(f"ingest_raw: raw root does not exist: {raw_root}")
        return 1

    rows = load_manifest()
    previous_lock = load_lock().get("files", {})
    rows_by_path = {row["raw_rel_path"]: row for row in rows if row.get("raw_rel_path")}
    existing_ids = {row["source_id"] for row in rows if row.get("source_id")}
    seen_paths: set[str] = set()
    kinds: Counter[str] = Counter()
    new_paths: list[str] = []
    changed_paths: list[str] = []
    archived_paths: list[str] = []
    lock_entries: dict[str, object] = {}
    hash_to_primary: dict[str, str] = {}
    duplicate_paths: list[str] = []
    change_summaries: dict[str, list[str]] = {}

    candidates: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(raw_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.startswith("."):
                continue
            path = Path(dirpath) / name
            ext = path.suffix.lower()
            if ext in TRACKED_EXTENSIONS or path.name.endswith(".tar.gz"):
                candidates.append(path)

    for path in sorted(candidates):
        rel = path.relative_to(raw_root).as_posix()
        seen_paths.add(rel)
        content_hash = sha256_prefix(path)
        kind = detect_kind(path)
        kinds[kind] += 1
        summary_payload = summarize_file(path)
        existing = rows_by_path.get(rel)
        old_hash = None
        previous_entry = None
        if isinstance(previous_lock, dict) and rel in previous_lock:
            previous_entry = previous_lock[rel]
            old_hash = previous_entry.get("content_hash")

        if existing is None:
            source_id = next_source_id(existing_ids, content_hash)
            existing_ids.add(source_id)
            row = {
                "source_id": source_id,
                "company": "",
                "vendor": "",
                "kind": kind,
                "filename": path.name,
                "raw_rel_path": rel,
                "status": "new",
                "compiled_into": "",
                "notes": "",
            }
            rows.append(row)
            rows_by_path[rel] = row
            new_paths.append(rel)
            existing = row
        else:
            existing["kind"] = kind
            existing["filename"] = path.name
            if old_hash and old_hash != content_hash and existing.get("status") != "archived":
                existing["status"] = "new"
                changed_paths.append(rel)
                change_summaries[rel] = summarize_change(previous_entry, summary_payload)

        primary = hash_to_primary.setdefault(content_hash, rel)
        duplicate_of = None if primary == rel else rows_by_path[primary]["source_id"]
        if duplicate_of:
            duplicate_paths.append(rel)

        lock_entries[rel] = {
            "source_id": existing["source_id"],
            "filename": path.name,
            "kind": kind,
            "content_hash": content_hash,
            "size_bytes": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat(),
            "parser": summary_payload["parser"],
            "summary": summary_payload["summary"],
            "metadata": summary_payload["metadata"],
            "duplicate_of": duplicate_of,
            "previous_content_hash": old_hash or "",
            "change_summary": change_summaries.get(rel, []),
        }

    for row in rows:
        rel = row.get("raw_rel_path", "")
        if rel and rel not in seen_paths and row.get("status") != "archived":
            row["status"] = "archived"
            archived_paths.append(rel)

    rows.sort(key=lambda row: (row.get("status", ""), row.get("raw_rel_path", "")))
    report_text = build_report(raw_root, rows, kinds, new_paths, changed_paths, archived_paths, duplicate_paths, change_summaries)

    if args.dry_run:
        print("ingest_raw: DRY RUN")
        print(report_text)
        return 0

    write_manifest(rows)
    write_lock({
        "llm_wiki_version": "1.2.2",
        "generated_at": utc_now(),
        "raw_root": str(raw_root),
        "summary": {
            "tracked_files": len(candidates),
            "manifest_rows": len(rows),
            "new": len(new_paths),
            "changed": len(changed_paths),
            "archived": len(archived_paths),
            "duplicates": len(duplicate_paths),
            "kinds": dict(sorted(kinds.items())),
        },
        "files": lock_entries,
    })
    report_path = Path(args.report_file).expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")

    print(f"ingest_raw: OK ({len(candidates)} tracked file(s))")
    print(f"- manifest: {MANIFEST}")
    print(f"- lock: {LOCK_FILE}")
    print(f"- report: {report_path}")
    print(f"- new: {len(new_paths)} | changed: {len(changed_paths)} | archived: {len(archived_paths)} | duplicates: {len(duplicate_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


UNTRACKED_RAW_CHECK = """from __future__ import annotations
# llm-wiki-version: 1.2.2

import csv
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "raw_sources.csv"

# File extensions that should be tracked in the manifest
RAW_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".xlsm", ".csv", ".tsv",
    ".doc", ".docx", ".ppt", ".pptx",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".mp3", ".mp4", ".wav", ".mov",
}

# Directories to skip entirely
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".obsidian", ".next", "dist", "build",
    "manifests",  # manifest CSVs are the index, not raw data
}


def load_manifest_filenames() -> set[str]:
    if not MANIFEST.exists():
        return set()
    names: set[str] = set()
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            fn = (row.get("filename") or "").strip()
            if fn:
                names.add(fn.lower())
    return names


def main() -> int:
    known = load_manifest_filenames()
    scan_roots = [ROOT]

    raw_root_env = os.environ.get("PROJECT_RAW_ROOT")
    if raw_root_env:
        raw_root = Path(raw_root_env).expanduser().resolve()
        if raw_root.exists():
            scan_roots.append(raw_root)

    untracked: list[tuple[str, Path]] = []

    for scan_root in scan_roots:
        for dirpath, dirnames, filenames in os.walk(scan_root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                ext = Path(fn).suffix.lower()
                if ext in RAW_EXTENSIONS and fn.lower() not in known:
                    full = Path(dirpath) / fn
                    rel = full.relative_to(scan_root) if full.is_relative_to(scan_root) else full
                    untracked.append((fn, rel))

    if untracked:
        print(f"untracked_raw_check: FOUND {len(untracked)} untracked raw file(s)")
        print("These files exist in the project but are NOT registered in manifests/raw_sources.csv:")
        print()
        for fn, rel in sorted(untracked, key=lambda x: str(x[1])):
            print(f"  {rel}")
        print()
        print("To fix: add each file to manifests/raw_sources.csv with status 'new',")
        print("then compile its key information into the relevant wiki page.")
        return 1

    print("untracked_raw_check: OK (no untracked raw files found)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""


PROVENANCE_CHECK = """from __future__ import annotations
# llm-wiki-version: 1.2.2

import csv
import hashlib
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI_ROOT = ROOT / "docs" / "wiki"
MANIFEST = ROOT / "manifests" / "raw_sources.csv"

FRONTMATTER_RE = re.compile(r"^---\\n(.*?)\\n---", re.DOTALL)
SOURCE_HASH_RE = re.compile(r"source_hash:\\s*([a-f0-9]{12,})")

SKIP_FILES = {"index.md", "log.md", "README.md", "SCHEMA.md"}


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def load_manifest_paths() -> dict[str, Path]:
    if not MANIFEST.exists():
        return {}
    raw_root_env = os.environ.get("PROJECT_RAW_ROOT")
    raw_root = Path(raw_root_env).expanduser().resolve() if raw_root_env else None
    result: dict[str, Path] = {}
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            sid = (row.get("source_id") or "").strip()
            rel = (row.get("raw_rel_path") or "").strip()
            if sid and rel and raw_root:
                result[sid] = (raw_root / rel).resolve()
    return result


def main() -> int:
    if not WIKI_ROOT.exists():
        print("provenance_check: docs/wiki does not exist")
        return 1

    manifest_paths = load_manifest_paths()
    checked = 0
    fresh = 0
    stale: list[tuple[str, str, str]] = []
    no_hash: list[str] = []
    unresolved: list[str] = []
    session_exempt = 0

    for path in sorted(WIKI_ROOT.rglob("*.md")):
        if path.name in SKIP_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            continue

        fm = m.group(1)
        source_line = ""
        for line in fm.splitlines():
            if line.startswith("source:"):
                source_line = line.split(":", 1)[1].strip()
                break

        if source_line == "session":
            session_exempt += 1
            continue

        hash_match = SOURCE_HASH_RE.search(fm)
        if not hash_match:
            no_hash.append(path.relative_to(ROOT).as_posix())
            continue

        stored_hash = hash_match.group(1)
        checked += 1

        # Find the source file
        if not source_line:
            fresh += 1
            continue

        # Try to resolve source path
        source_path = None
        if source_line.startswith("raw/"):
            candidate = ROOT / source_line
            if candidate.exists():
                source_path = candidate
        for sid, spath in manifest_paths.items():
            if sid in source_line or source_line in str(spath):
                source_path = spath
                break

        if source_path and source_path.exists():
            current = file_hash(source_path)
            if current == stored_hash:
                fresh += 1
            else:
                stale.append((
                    path.relative_to(ROOT).as_posix(),
                    stored_hash,
                    current,
                ))
        else:
            unresolved.append(path.relative_to(ROOT).as_posix())

    if stale:
        print(f"provenance_check: {len(stale)} STALE page(s) detected")
        for page, old, new in stale:
            print(f"  {page}: hash was {old}, source now {new}")
        print()
        print("These wiki pages were compiled from source files that have since changed.")
        print("Recompile them to update the wiki with current information.")

    if no_hash:
        print(f"provenance_check: {len(no_hash)} page(s) without source_hash (required for non-session sources)")
        for page in no_hash:
            print(f"  {page}")

    if unresolved:
        print(f"provenance_check: {len(unresolved)} page(s) with unresolved source")
        for page in unresolved:
            print(f"  {page}")

    if not stale and not no_hash and not unresolved:
        print(
            f"provenance_check: OK ({checked} checked, {fresh} fresh, "
            f"{session_exempt} session-exempt, {len(no_hash)} without hash)"
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
"""


STALE_REPORT = """from __future__ import annotations
# llm-wiki-version: 1.2.2

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI_ROOT = ROOT / "docs" / "wiki"
MANIFEST = ROOT / "manifests" / "raw_sources.csv"
LOCK_FILE = ROOT / "manifests" / "raw_index.json"
REPORT_FILE = ROOT / "manifests" / "stale_report.md"
DEFAULT_RAW_ROOT = (ROOT.parent / "__RAW_ROOT_NAME__").resolve()
FRONTMATTER_RE = re.compile(r"^---\\n(.*?)\\n---", re.DOTALL)
SKIP_FILES = {"index.md", "log.md", "README.md", "SCHEMA.md"}


def sha256_prefix(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def parse_list_field(value: str) -> list[str]:
    raw = value.strip()
    if not raw:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    items = [item.strip().strip("'").strip('"') for item in raw.split(",")]
    return [item for item in items if item]


def load_manifest() -> list[dict[str, str]]:
    if not MANIFEST.exists():
        return []
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{key: (value or "") for key, value in row.items()} for row in csv.DictReader(handle)]


def load_lock() -> dict[str, dict]:
    if not LOCK_FILE.exists():
        return {}
    try:
        data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        files = data.get("files", {})
        return files if isinstance(files, dict) else {}
    except Exception:
        return {}


def resolve_row(source_value: str, rows: list[dict[str, str]]) -> dict[str, str] | None:
    for row in rows:
        if source_value == row.get("source_id") or source_value == row.get("raw_rel_path"):
            return row
    for row in rows:
        if row.get("source_id") and row["source_id"] in source_value:
            return row
        if row.get("raw_rel_path") and source_value.endswith(row["raw_rel_path"]):
            return row
    return None


def build_report(
    raw_root: Path | None,
    session_exempt: int,
    fresh: list[str],
    stale: list[str],
    missing_hash: list[str],
    unresolved: list[str],
    archived_refs: list[str],
    manifest_new: list[str],
) -> str:
    def section(title: str, items: list[str]) -> list[str]:
        lines = ["", f"## {title}", ""]
        if not items:
            lines.append("- none")
        else:
            lines.extend(f"- `{item}`" for item in items[:40])
        return lines

    lines = [
        "# Stale Report",
        "",
        f"- generated_at: `{datetime.now(timezone.utc).replace(microsecond=0).isoformat()}`",
        f"- raw_root: `{raw_root}`" if raw_root else "- raw_root: `not configured`",
        f"- fresh_pages: `{len(fresh)}`",
        f"- stale_pages: `{len(stale)}`",
        f"- missing_hash: `{len(missing_hash)}`",
        f"- unresolved_sources: `{len(unresolved)}`",
        f"- archived_refs: `{len(archived_refs)}`",
        f"- manifest_new: `{len(manifest_new)}`",
        f"- session_exempt: `{session_exempt}`",
    ]
    lines += section("Fresh Pages", fresh)
    lines += section("Pages Needing Recompile (stale)", stale)
    lines += section("Pages Missing source_hash", missing_hash)
    lines += section("Pages With Unresolved source", unresolved)
    lines += section("Pages Pointing At Archived Sources", archived_refs)
    lines += section("Raw Files Still Waiting For First Compile", manifest_new)
    return "\\n".join(lines).rstrip() + "\\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report stale wiki pages and raw files that still need compilation.")
    parser.add_argument("--raw-root", default=os.environ.get("PROJECT_RAW_ROOT", ""), help="Local raw root path. If empty, falls back to the default sibling raw root when present.")
    parser.add_argument("--report-file", default=str(REPORT_FILE), help="Markdown report output path")
    parser.add_argument("--dry-run", action="store_true", help="Print the report without writing it")
    args = parser.parse_args()

    raw_root = None
    if args.raw_root:
        candidate = Path(args.raw_root).expanduser().resolve()
        if candidate.exists():
            raw_root = candidate
    elif DEFAULT_RAW_ROOT.exists():
        raw_root = DEFAULT_RAW_ROOT

    rows = load_manifest()
    lock = load_lock()
    fresh: list[str] = []
    stale: list[str] = []
    missing_hash: list[str] = []
    unresolved: list[str] = []
    archived_refs: list[str] = []
    referenced_source_ids: set[str] = set()
    referenced_paths: set[str] = set()
    session_exempt = 0

    for path in sorted(WIKI_ROOT.rglob("*.md")):
        if path.name in SKIP_FILES:
            continue
        fm = parse_frontmatter(path)
        if not fm:
            continue
        rel = path.relative_to(ROOT).as_posix()
        source = fm.get("source", "")
        compiled_from = parse_list_field(fm.get("compiled_from", ""))
        source_hash = fm.get("source_hash", "")
        if source == "session":
            session_exempt += 1
            continue
        if not source_hash:
            missing_hash.append(rel)
            continue

        row = resolve_row(source, rows)
        if not row:
            unresolved.append(rel)
            continue

        referenced_rows = [row]
        for extra in compiled_from:
            extra_row = resolve_row(extra, rows)
            if not extra_row:
                unresolved.append(f"{rel} <- {extra}")
                continue
            referenced_rows.append(extra_row)

        for referenced_row in referenced_rows:
            if referenced_row.get("source_id"):
                referenced_source_ids.add(referenced_row["source_id"])
            if referenced_row.get("raw_rel_path"):
                referenced_paths.add(referenced_row["raw_rel_path"])

        if row.get("status") == "archived":
            archived_refs.append(rel)
            continue

        for extra_row in referenced_rows[1:]:
            if extra_row.get("status") == "archived" and extra_row.get("raw_rel_path"):
                archived_refs.append(f"{rel} <- {extra_row['raw_rel_path']}")

        current_hash = ""
        if raw_root:
            source_path = raw_root / row["raw_rel_path"]
            if source_path.exists():
                current_hash = sha256_prefix(source_path)
        if not current_hash and row["raw_rel_path"] in lock:
            current_hash = lock[row["raw_rel_path"]].get("content_hash", "")
        if not current_hash:
            unresolved.append(rel)
            continue
        if current_hash != source_hash:
            stale.append(f"{rel} <- {row['raw_rel_path']} ({source_hash} -> {current_hash})")
        else:
            fresh.append(rel)

    manifest_new = [
        row["raw_rel_path"]
        for row in rows
        if row.get("status") == "new"
        and row.get("raw_rel_path")
        and row.get("source_id") not in referenced_source_ids
        and row.get("raw_rel_path") not in referenced_paths
    ]

    report_text = build_report(raw_root, session_exempt, fresh, stale, missing_hash, unresolved, archived_refs, manifest_new)

    if args.dry_run:
        print(report_text)
    else:
        report_path = Path(args.report_file).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding="utf-8")
        print(f"stale_report: wrote {report_path}")

    if stale or missing_hash or unresolved or archived_refs:
        print(
            f"stale_report: ATTENTION ({len(stale)} stale, {len(missing_hash)} missing_hash, "
            f"{len(unresolved)} unresolved, {len(archived_refs)} archived_refs)"
        )
        return 1

    print(
        f"stale_report: OK ({len(fresh)} fresh, {len(manifest_new)} manifest-new, "
        f"{session_exempt} session-exempt)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""


DELTA_COMPILE = """from __future__ import annotations
# llm-wiki-version: 1.2.2

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI_ROOT = ROOT / "docs" / "wiki"
MANIFEST = ROOT / "manifests" / "raw_sources.csv"
LOCK_FILE = ROOT / "manifests" / "raw_index.json"
REPORT_FILE = ROOT / "manifests" / "delta_compile_report.md"
DRAFT_DIR = WIKI_ROOT / "drafts"
DEFAULT_RAW_ROOT = (ROOT.parent / "__RAW_ROOT_NAME__").resolve()
FRONTMATTER_RE = re.compile(r"^---\\n(.*?)\\n---", re.DOTALL)
SKIP_FILES = {"index.md", "log.md", "README.md", "SCHEMA.md"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def sha256_prefix(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "draft"


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def parse_list_field(value: str) -> list[str]:
    raw = value.strip()
    if not raw:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [item.strip().strip("'").strip('"') for item in raw.split(",") if item.strip()]


def load_manifest() -> list[dict[str, str]]:
    if not MANIFEST.exists():
        return []
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{key: (value or "") for key, value in row.items()} for row in csv.DictReader(handle)]


def load_lock() -> dict[str, dict]:
    if not LOCK_FILE.exists():
        return {}
    try:
        data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        files = data.get("files", {})
        return files if isinstance(files, dict) else {}
    except Exception:
        return {}


def resolve_row(source_value: str, rows: list[dict[str, str]]) -> dict[str, str] | None:
    for row in rows:
        if source_value == row.get("source_id") or source_value == row.get("raw_rel_path"):
            return row
    for row in rows:
        if row.get("source_id") and row["source_id"] in source_value:
            return row
        if row.get("raw_rel_path") and source_value.endswith(row["raw_rel_path"]):
            return row
    return None


def choose_target_page(row: dict[str, str]) -> str:
    compiled_into = (row.get("compiled_into") or "").strip()
    if compiled_into:
        first = compiled_into.split(",")[0].strip()
        if first:
            return first
    stem = slugify(Path(row.get("filename") or row.get("raw_rel_path") or row.get("source_id") or "source").stem)
    return f"docs/wiki/{stem}.md"


def draft_path(target_page: str, source_id: str) -> Path:
    stem = slugify(Path(target_page).stem)
    return DRAFT_DIR / f"{stem}--{source_id}.md"


def unique_items(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def render_draft(
    *,
    title: str,
    source_id: str,
    source_hash: str,
    target_page: str,
    raw_rel_path: str,
    source_summary: str,
    change_summary: list[str],
    compiled_from: list[str],
    reason: str,
) -> str:
    compiled_from_values = unique_items(compiled_from or [source_id])
    compiled_from_line = f"[{', '.join(compiled_from_values)}]"
    lines = [
        "---",
        f"title: {title}",
        f"source: {source_id}",
        f"source_hash: {source_hash}",
        f"compiled_at: {utc_now()}",
        f"compiled_from: {compiled_from_line}",
        f"created: {today()}",
        "tags: [draft, delta-compile]",
        "status: draft",
        "---",
        "",
        f"# {title}",
        "",
        "## Why this draft exists",
        "",
        f"- reason: {reason}",
        f"- suggested target page: `{target_page}`",
        f"- raw source: `{raw_rel_path}`",
        "",
        "## Source Summary",
        "",
        f"- {source_summary or 'no summary available'}",
        "",
        "## Structured Change Summary",
        "",
    ]
    if change_summary:
        lines.extend(f"- {item}" for item in change_summary)
    else:
        lines.append("- no prior diff summary available")
    lines.extend([
        "",
        "## Draft Notes",
        "",
        "- Pull confirmed facts from the raw source into the target page.",
        "- Update the target page frontmatter with the current `source_hash` and `compiled_at`.",
        "- Keep this draft until the recompile is merged, then delete it.",
        "",
    ])
    return "\\n".join(lines)


def build_report(stale_items: list[dict[str, object]], new_items: list[dict[str, object]], written_drafts: list[str]) -> str:
    lines = [
        "# Delta Compile Report",
        "",
        f"- generated_at: `{utc_now()}`",
        f"- stale_pages: `{len(stale_items)}`",
        f"- new_raw_sources: `{len(new_items)}`",
        f"- drafts_written: `{len(written_drafts)}`",
        "",
        "> This report suggests recompilation work. It does not auto-overwrite wiki content.",
        "",
        "## Stale Pages",
        "",
    ]
    if stale_items:
        for item in stale_items:
            lines.append(
                f"- `{item['page_rel']}` <- `{item['raw_rel_path']}` "
                f"(target: `{item['target_page']}`)"
            )
            for change in item.get("change_summary", [])[:3]:
                lines.append(f"  - {change}")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## New Raw Sources",
        "",
    ])
    if new_items:
        for item in new_items:
            lines.append(
                f"- `{item['raw_rel_path']}` -> suggested page `{item['target_page']}`"
            )
            lines.append(f"  - {item['source_summary']}")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Draft Files",
        "",
    ])
    if written_drafts:
        lines.extend(f"- `{path}`" for path in written_drafts)
    else:
        lines.append("- none")
    return "\\n".join(lines).rstrip() + "\\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate manual delta-compile suggestions and optional wiki draft stubs.")
    parser.add_argument("--raw-root", default=os.environ.get("PROJECT_RAW_ROOT", ""), help="Local raw root path")
    parser.add_argument("--report-file", default=str(REPORT_FILE), help="Markdown report output path")
    parser.add_argument("--write-drafts", action="store_true", help="Write draft markdown stubs into docs/wiki/drafts/")
    parser.add_argument("--dry-run", action="store_true", help="Print the report without writing files")
    args = parser.parse_args()

    raw_root = None
    if args.raw_root:
        candidate = Path(args.raw_root).expanduser().resolve()
        if candidate.exists():
            raw_root = candidate
    elif DEFAULT_RAW_ROOT.exists():
        raw_root = DEFAULT_RAW_ROOT

    rows = load_manifest()
    lock = load_lock()
    referenced_ids: set[str] = set()
    referenced_paths: set[str] = set()
    stale_items: list[dict[str, object]] = []
    new_items: list[dict[str, object]] = []
    written_drafts: list[str] = []

    for path in sorted(WIKI_ROOT.rglob("*.md")):
        if path.name in SKIP_FILES or "drafts" in path.parts:
            continue
        fm = parse_frontmatter(path)
        if not fm:
            continue
        source = fm.get("source", "")
        if source == "session":
            continue
        row = resolve_row(source, rows)
        if not row:
            continue
        referenced_ids.add(row.get("source_id", ""))
        referenced_paths.add(row.get("raw_rel_path", ""))
        for extra in parse_list_field(fm.get("compiled_from", "")):
            extra_row = resolve_row(extra, rows)
            if extra_row:
                referenced_ids.add(extra_row.get("source_id", ""))
                referenced_paths.add(extra_row.get("raw_rel_path", ""))
        source_hash = fm.get("source_hash", "")
        current_hash = ""
        if raw_root:
            source_path = raw_root / row.get("raw_rel_path", "")
            if source_path.exists():
                current_hash = sha256_prefix(source_path)
        if not current_hash and row.get("raw_rel_path") in lock:
            current_hash = lock[row["raw_rel_path"]].get("content_hash", "")
        if not source_hash or not current_hash or source_hash == current_hash:
            continue
        lock_entry = lock.get(row.get("raw_rel_path", ""), {})
        target_page = path.relative_to(ROOT).as_posix()
        compiled_from = unique_items([row["source_id"]] + parse_list_field(fm.get("compiled_from", "")))
        stale_items.append({
            "page_rel": target_page,
            "target_page": target_page,
            "raw_rel_path": row.get("raw_rel_path", ""),
            "source_id": row.get("source_id", ""),
            "source_hash": current_hash,
            "source_summary": lock_entry.get("summary", ""),
            "change_summary": list(lock_entry.get("change_summary", [])),
            "compiled_from": compiled_from,
            "reason": f"source hash changed ({source_hash} -> {current_hash})",
        })

    for row in rows:
        raw_rel_path = row.get("raw_rel_path", "")
        source_id = row.get("source_id", "")
        if row.get("status") != "new" or not raw_rel_path:
            continue
        if source_id in referenced_ids or raw_rel_path in referenced_paths:
            continue
        lock_entry = lock.get(raw_rel_path, {})
        new_items.append({
            "raw_rel_path": raw_rel_path,
            "source_id": source_id,
            "source_hash": lock_entry.get("content_hash", ""),
            "source_summary": lock_entry.get("summary", ""),
            "change_summary": list(lock_entry.get("change_summary", [])),
            "compiled_from": [source_id],
            "target_page": choose_target_page(row),
            "reason": "new raw source has not been compiled into wiki yet",
        })

    if args.write_drafts and not args.dry_run:
        DRAFT_DIR.mkdir(parents=True, exist_ok=True)
        for item in stale_items + new_items:
            title = f"Draft - {Path(str(item['target_page'])).stem.replace('-', ' ').title()}"
            draft = draft_path(str(item["target_page"]), str(item["source_id"]))
            draft.write_text(
                render_draft(
                    title=title,
                    source_id=str(item["source_id"]),
                    source_hash=str(item["source_hash"]),
                    target_page=str(item["target_page"]),
                    raw_rel_path=str(item["raw_rel_path"]),
                    source_summary=str(item["source_summary"]),
                    change_summary=[str(entry) for entry in item.get("change_summary", [])],
                    compiled_from=[str(entry) for entry in item.get("compiled_from", []) if str(entry)],
                    reason=str(item["reason"]),
                ),
                encoding="utf-8",
            )
            written_drafts.append(draft.relative_to(ROOT).as_posix())

    report_text = build_report(stale_items, new_items, written_drafts)
    if args.dry_run:
        print(report_text)
    else:
        report_path = Path(args.report_file).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding="utf-8")
        print(f"delta_compile: wrote {report_path}")
    print(
        f"delta_compile: OK ({len(stale_items)} stale page(s), "
        f"{len(new_items)} new raw source(s), {len(written_drafts)} draft(s))"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""


VERSION_CHECK = """from __future__ import annotations
# llm-wiki-version: 1.2.2

import json
import re
import sys
import urllib.request
from pathlib import Path

GITHUB_API = "https://api.github.com/repos/Ss1024sS/LLM-wiki/releases/latest"
VERSION_RE = re.compile(r"# llm-wiki-version:\\s*(\\S+)")
SCRIPTS_DIR = Path(__file__).resolve().parent


def parse_version(value: str) -> tuple[int, ...]:
    parts = re.findall(r"\\d+", value)
    return tuple(int(part) for part in parts[:3]) if parts else (0,)


def get_local_version() -> str:
    for script in ["wiki_check.py", "raw_manifest_check.py", "provenance_check.py"]:
        path = SCRIPTS_DIR / script
        if path.exists():
            m = VERSION_RE.search(path.read_text(encoding="utf-8"))
            if m:
                return m.group(1)
    return "unknown"


def get_remote_version() -> tuple[str, str]:
    try:
        req = urllib.request.Request(GITHUB_API, headers={"Accept": "application/vnd.github.v3+json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            tag = data.get("tag_name", "").lstrip("v")
            url = data.get("html_url", "")
            return tag, url
    except Exception:
        return "", ""


def main() -> int:
    local = get_local_version()
    remote, release_url = get_remote_version()
    if not remote:
        return 0
    if local == "unknown":
        print(f"[llm-wiki] Could not detect local version. Latest is v{remote}")
        return 0
    if parse_version(remote) > parse_version(local):
        print(f"[llm-wiki] Update available: v{local} -> v{remote}")
        print(f"[llm-wiki] Run: bash scripts/upgrade.sh")
        if release_url:
            print(f"[llm-wiki] Release notes: {release_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""


INIT_RAW_ROOT = """from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_ROOT = (ROOT.parent / "{raw_root_name}").resolve()

DIRS = [
    "inbox",
    "internal_sources",
    "external_sources",
    "customer_answers",
    "screenshots",
    "extracted_text",
    "archive",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the local raw root directory.")
    parser.add_argument(
        "path",
        nargs="?",
        default=os.environ.get("PROJECT_RAW_ROOT", str(DEFAULT_RAW_ROOT)),
        help="Absolute or relative path for the local raw root",
    )
    args = parser.parse_args()

    raw_root = Path(args.path).expanduser().resolve()
    raw_root.mkdir(parents=True, exist_ok=True)

    for rel in DIRS:
        (raw_root / rel).mkdir(parents=True, exist_ok=True)

    print(f"Initialized raw root: {{raw_root}}")
    for rel in DIRS:
        print(f"- {{raw_root / rel}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


EXPORT_MEMORY_REPO = """from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COPY_FILES = [
    "AGENTS.md",
    "scripts/wiki_check.py",
    "scripts/raw_manifest_check.py",
    "scripts/init_raw_root.py",
]

COPY_DIRS = [
    ("docs/wiki", "docs/wiki"),
    ("manifests", "manifests"),
]

OPTIONAL_COPY_DIRS = [
    ("verified_cases", "verified_cases"),
    ("backend/verified_cases", "verified_cases"),
]


def wipe_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def copy_dir(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the repo memory surface into a dedicated GitHub/wiki repo checkout.")
    parser.add_argument("target_dir", help="Target memory repo checkout directory")
    args = parser.parse_args()

    target = Path(args.target_dir).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    managed_paths = [
        target / "AGENTS.md",
        target / "README.md",
        target / "docs",
        target / "manifests",
        target / "verified_cases",
        target / "scripts",
    ]
    for path in managed_paths:
        wipe_path(path)

    exported_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    readme = f\"\"\"# Memory Repo

This repo is the exported long-term memory surface for a project.

## What belongs here

- `docs/wiki/`
- `manifests/`
- `verified_cases/`
- repo-level operating rules such as `AGENTS.md`

## What does not belong here

- raw PDFs / XLSX / XLS / ZIP / RAR files
- main application runtime code
- build artifacts

## Export time

`{exported_at}`

## Source repo

`{ROOT}`

## Refresh

Run from the source repo:

```bash
python3 scripts/export_memory_repo.py /path/to/memory-repo-checkout
```
\"\"\"
    (target / "README.md").write_text(readme, encoding="utf-8")

    for rel in COPY_FILES:
        src = ROOT / rel
        if src.exists():
            copy_file(src, target / rel)

    for src_rel, dest_rel in COPY_DIRS:
        src = ROOT / src_rel
        if src.exists():
            copy_dir(src, target / dest_rel)

    for src_rel, dest_rel in OPTIONAL_COPY_DIRS:
        src = ROOT / src_rel
        if src.exists():
            copy_dir(src, target / dest_rel)
            break

    print(f"Exported memory repo snapshot to: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a compile-first knowledge system into another repo.")
    parser.add_argument("target_dir", help="Target repository root")
    parser.add_argument("project_name", help="Human-readable project name")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created without writing anything")
    parser.add_argument("--raw-root-name", help="Folder name to use for the default local raw root")
    args = parser.parse_args()

    target = Path(args.target_dir).expanduser().resolve()
    project_name = args.project_name.strip()
    slug = slugify(project_name)
    raw_root_name = args.raw_root_name or f"{slug}_raw"
    today = date.today().isoformat()

    files: dict[Path, str] = {
        target / "AGENTS.md": f"""# {project_name} Agent Rules

这仓库默认走 `wiki-first`，不是 `chat-first`。

## 1. 每个新 session 默认先干嘛

只要任务不是纯闲聊，默认先：

0. `python3 scripts/version_check.py` — 检查更新（有新版才提示，没有就静默）
1. 读 `docs/wiki/index.md`
2. 读 `docs/wiki/current-status.md`
3. 读 `docs/wiki/log.md`

别一上来就靠 session 硬猜。

## 1.5 文档文件自动归档

凡是提到、收到、引用、保存的任何非代码文件 → 第一件事查 `manifests/raw_sources.csv`。
包括但不限于：PDF、Excel、截图、客户发来的附件、聊天图片、CAD图纸、压缩包。
不在里面 → 先登记再用。这步最容易漏。

少量文件可以手填 manifest，大量新文件直接跑：

```bash
python3 scripts/ingest_raw.py
```

定期跑：

```bash
python3 scripts/untracked_raw_check.py
python3 scripts/stale_report.py
python3 scripts/delta_compile.py --write-drafts
```

前者找漏登 raw，第二个找已经过期的 wiki 页面，第三个只起草重编译草稿，不会乱改现有页面。

## 2. 默认范式

- `compile-first`
- `writeback` 必做
- 中等规模先 `wiki`，不先上重 `RAG`
- Obsidian 可替换，范式不可替换
- `Idea / Intent` 优先于 `Code`

## 3. 知识分层

- raw：原始资料
- wiki：编译后的当前共识
- code：执行层

只改代码不回写 wiki，算没做完。

## 4. 一致性规则

- `current-status.md` 和其他 wiki 页面冲突时 → 以更具体的页面为准，然后修正 `current-status.md`
- `log.md` 缺少之前 session 的记录 → 不猜，只追加自己的
- 两个 wiki 页面矛盾 → 标记给用户，解决后再继续
""",
        target / "CLAUDE.md": f"""# {project_name} — Claude Rules

## Knowledge System
This project uses a wiki-first knowledge system. Knowledge lives in `docs/wiki/`, not in chat history.

## Session Protocol (mandatory)

### Session Start
0. Run `python3 scripts/version_check.py` — check for LLM-wiki updates (silent if up to date)
1. Read `docs/wiki/index.md` — get the full page list
2. Read `docs/wiki/current-status.md` — know where things stand
3. Read `docs/wiki/log.md` — understand recent session history
4. Read additional wiki pages as needed for the current task

### During Work
- New decision made → update the relevant wiki page immediately
- **Any non-code file mentioned, received, referenced, or saved → check `manifests/raw_sources.csv` first. If not listed, register it before proceeding.** This includes PDFs, spreadsheets, screenshots, customer attachments, chat images, debug captures, CAD files, archives. This is the most commonly skipped step.
- Task completed → update `docs/wiki/current-status.md`

### Session End
1. Append one line to `docs/wiki/log.md`: date, topic, key outcomes
2. Update `docs/wiki/current-status.md` with latest state
3. If context is running low → generate `CONTINUATION-SUMMARY.md`

### Consistency
- If `current-status.md` conflicts with other wiki pages → trust the more specific page, then fix `current-status.md`
- If `log.md` is missing entries from before your session → don't guess, only append your own
- If two wiki pages contradict each other → flag it to the user, resolve before proceeding

### Token Budget
Normal operations are cheap. Full audit/recompilation are disaster recovery, not regular workflow.
- Session start: read 3 files (index, status, log). ~2K tokens. Never read all pages upfront.
- During work: read specific pages one at a time, only when needed.
- Structural checks: Python scripts (`wiki_check.py`, `raw_manifest_check.py`, `untracked_raw_check.py`, `stale_report.py`, `provenance_check.py`, `delta_compile.py`) — zero LLM tokens unless you choose to feed the draft output back into an LLM.
- If every session does incremental writeback, you never need full audit or recompilation.

### Rules
- compile-first: don't just answer, write conclusions into wiki pages
- writeback is mandatory: if you learned something durable, it goes in the wiki
- all non-code files are raw — PDFs, spreadsheets, images, screenshots, customer files, archives
- raw files stay outside Git, only manifests go in
- every wiki page (except index.md and log.md) must have YAML frontmatter with at least: title, source, created
""",
        target / "docs" / "wiki" / "README.md": f"""# {project_name} Wiki

这套 wiki 解决三个问题：

1. 新 session 老失忆
2. 资料散在各处，没人知道先看哪
3. 新结论只活在聊天里

默认范式：

- `compile-first`
- `writeback` 必做
- 中等规模先 `wiki`
- Obsidian 可替换，范式不可替换
- `Idea / Intent` 优先于 `Code`

自检：

```bash
python3 scripts/wiki_check.py
python3 scripts/raw_manifest_check.py
```
""",
        target / "docs" / "wiki" / "SCHEMA.md": f"""# Wiki Schema

## Frontmatter（每个 wiki 页面必须有）

每个 `.md` 文件的头部用 YAML frontmatter 标注来源和状态：

```yaml
---
title: 页面标题
source: 编译来源（raw 文件路径、URL、或 "session" 表示来自对话）
source_hash: a1b2c3d4e5f67890
compiled_at: 2026-04-07T12:00:00+00:00
compiled_from: [src_a1b2c3d4e5, src_f6g7h8i9j0]
created: 创建日期 (YYYY-MM-DD)
updated: 最后更新日期 (YYYY-MM-DD)
tags: [标签1, 标签2]
status: current / draft / stale
---
```

### 必填字段
- `title` — 页面标题
- `source` — 信息来源。让每个事实可追溯。
- `created` — 创建日期

### 可选字段
- `updated` — 最后更新日期（不填则等于 created）
- `tags` — 分类标签，Obsidian 可直接用
- `status` — `current`（默认）/ `draft`（未确认）/ `stale`（可能过期）
- `source_hash` — 编译时源文件的 SHA-256 前 16 位。文件来源页面要填；`source: session` 的页面可以省略。`provenance_check.py` 用它检测源文件是否已变更。源文件变了 → 页面标记为 stale。
- `compiled_at` — 最近一次把 raw 编译进这页的时间戳（UTC ISO-8601）。不是装饰，是让人一眼知道这页最后一次吃料是什么时候。
- `compiled_from` — 可选多源列表，写成 `[src_a, src_b]`。`source` 仍然是主来源，`compiled_from` 用来记录这页还吃了哪些 source。

### 为什么这样设计
- AI 读一个页面就知道信息从哪来，不用额外查 manifest
- Obsidian 原生支持 frontmatter 属性面板
- 比在正文里写"来源：xxx"更结构化，脚本可以校验
- 零额外 token 开销（frontmatter 是页面自身的一部分）

## 页面

- `index.md`（免 frontmatter，纯索引）
- `log.md`（免 frontmatter，纯日志）
- `project-overview.md`
- `current-status.md`
- `sources-and-data.md`
- `github-and-raw-strategy.md`

## 规则

1. 新 raw 进来，先登记 manifest
2. 新结论，必须回写 wiki（带 frontmatter）
3. 新规则，必须同时补测试
4. 没证据，不要写成结论
5. memory repo 只放编译结果，不放 raw 本体
""",
        target / "docs" / "wiki" / "index.md": """# Wiki Index

- [README.md](./README.md)
- [SCHEMA.md](./SCHEMA.md)
- [project-overview.md](./project-overview.md)
- [current-status.md](./current-status.md)
- [sources-and-data.md](./sources-and-data.md)
- [github-and-raw-strategy.md](./github-and-raw-strategy.md)
- [log.md](./log.md)
""",
        target / "docs" / "wiki" / "log.md": f"""# Wiki Log

## [{today}] bootstrap | 初始化知识系统

- 建立 wiki、manifest、检查脚本和 repo 级默认规则。
""",
        target / "docs" / "wiki" / "project-overview.md": f"""---
title: {project_name} Overview
source: session
created: {today}
tags: [overview]
status: draft
---

# {project_name} Overview

这里写项目的一句话定义、主线目标、交付边界。
""",
        target / "docs" / "wiki" / "current-status.md": f"""---
title: {project_name} Current Status
source: session
created: {today}
tags: [status]
status: current
---

# {project_name} Current Status

这里写当前已支持、未支持、线上状态、最近风险。
""",
        target / "docs" / "wiki" / "sources-and-data.md": f"""---
title: Sources and Data
source: session
created: {today}
tags: [data, raw]
status: current
---

# {project_name} Sources and Data

原始资料默认放在本地 raw 根目录，不直接进 Git。

raw 根目录建议：

```text
../{raw_root_name}/
```

GitHub 里只保留 manifest 和编译结果。

少量 raw 可以手工登记；新文件一多，直接跑：

```bash
python3 scripts/ingest_raw.py
python3 scripts/stale_report.py
python3 scripts/delta_compile.py --write-drafts
```

前者把本地 raw 编成 manifest + lock + intake report，第二个告诉你哪些 wiki 页面已经 stale，第三个只生成手动草稿，不会偷偷覆盖现有 wiki。
""",
        target / "docs" / "wiki" / "github-and-raw-strategy.md": f"""---
title: GitHub and Raw Strategy
source: session
created: {today}
tags: [strategy, git]
status: current
---

# GitHub and Raw Strategy

## 结论

- GitHub private repo 放：`code + wiki + manifests + verified_cases`
- 本地 raw 仓放：`pdf/xlsx/xls/rar/图片/客户原件`
- memory repo 放：编译后的长期记忆，不放 raw 本体

## 为什么

把全量 raw 塞进 Git，只会让仓库越来越肥，diff 也基本没用。

真正该版本化的是：

- 结论
- 规则
- 答案表
- 清晰的索引

不是一堆二进制原件。
""",
        target / "manifests" / "README.md": """# Manifests

这里放 raw 的索引，不放 raw 本体。
""",
        target / "manifests" / "raw_sources.csv": "source_id,company,vendor,kind,filename,raw_rel_path,status,compiled_into,notes\n",
        target / "scripts" / "wiki_check.py": WIKI_CHECK,
        target / "scripts" / "raw_manifest_check.py": RAW_MANIFEST_CHECK,
        target / "scripts" / "ingest_raw.py": INGEST_RAW.replace("__RAW_ROOT_NAME__", raw_root_name),
        target / "scripts" / "untracked_raw_check.py": UNTRACKED_RAW_CHECK,
        target / "scripts" / "provenance_check.py": PROVENANCE_CHECK,
        target / "scripts" / "stale_report.py": STALE_REPORT.replace("__RAW_ROOT_NAME__", raw_root_name),
        target / "scripts" / "delta_compile.py": DELTA_COMPILE.replace("__RAW_ROOT_NAME__", raw_root_name),
        target / "scripts" / "init_raw_root.py": INIT_RAW_ROOT.format(raw_root_name=raw_root_name),
        target / "scripts" / "export_memory_repo.py": EXPORT_MEMORY_REPO,
        target / "scripts" / "version_check.py": VERSION_CHECK,
        target / "scripts" / "upgrade.sh": """#!/usr/bin/env bash
# llm-wiki-version: 1.2.2
# Upgrade LLM-wiki scripts to latest version.
# Updates validation scripts and CI only. Never touches wiki content.
set -euo pipefail
REPO="https://github.com/Ss1024sS/LLM-wiki.git"
TMP=$(mktemp -d)
trap "rm -rf $TMP" EXIT
echo "Fetching latest LLM-wiki..."
git clone --depth 1 "$REPO" "$TMP/repo" 2>/dev/null
UPGRADE="$TMP/repo/scripts/upgrade_knowledge_system.py"
if [ -f "$UPGRADE" ]; then
  python3 "$UPGRADE" "$(pwd)"
else
  echo "Error: upgrade script not found in latest LLM-wiki"
  exit 1
fi
""",
        target / ".claude" / "commands" / "wiki-check.md": """Run all LLM-wiki validation checks on this project.

Execute these commands in order and report results:

```bash
python3 scripts/wiki_check.py
python3 scripts/raw_manifest_check.py
python3 scripts/untracked_raw_check.py
python3 scripts/provenance_check.py
python3 scripts/stale_report.py
```

If any check fails, explain what's wrong and how to fix it.
If all pass, say "Wiki health: OK" with the summary counts.
""",
        target / ".claude" / "commands" / "wiki-upgrade.md": """Check for LLM-wiki updates and upgrade if available.

```bash
python3 scripts/version_check.py
```

If an update is available, ask the user if they want to upgrade, then run:

```bash
bash scripts/upgrade.sh
```

After upgrade, run `/wiki-check` to verify everything still passes.
""",
        target / ".claude" / "commands" / "wiki-status.md": """Show the current wiki status: what pages exist, last log entry, and any issues.

1. Read `docs/wiki/index.md` and list all pages
2. Read the last 3 entries from `docs/wiki/log.md`
3. Read `docs/wiki/current-status.md` and summarize
4. Run `python3 scripts/stale_report.py --dry-run` and report whether anything is stale
5. Run `python3 scripts/version_check.py` to check for updates
6. Report a one-paragraph summary of project state
""",
        target / ".cursorrules": f"""This project ({project_name}) uses a wiki-first knowledge system.

Before starting any non-trivial task:
0. Run: python3 scripts/version_check.py (silent if up to date)
1. Read docs/wiki/index.md for the wiki page list
2. Read docs/wiki/current-status.md for project state
3. Read docs/wiki/log.md for recent session history

During work:
- Any non-code file mentioned, received, or saved (PDF, Excel, screenshots, customer attachments,
  chat images, CAD files, archives) → check manifests/raw_sources.csv first
- Not listed → register it before proceeding. This step is most commonly skipped.

After completing work:
- Update docs/wiki/current-status.md with new state
- Append a log entry to docs/wiki/log.md (date | topic | outcome)
- If a durable decision was made, write it into the relevant wiki page

Consistency:
- If current-status.md conflicts with other wiki pages, trust the specific page and fix current-status.md
- If log.md is missing prior entries, don't guess — only append your own
- If two wiki pages contradict, flag it to the user before proceeding

Rules:
- Compile raw documents into wiki pages, don't just reference them
- Every conclusion goes back into the wiki (writeback is mandatory)
- Raw files (PDF/XLSX) stay outside Git, only manifests/ indexes go in
""",
        target / ".windsurfrules": f"""This project ({project_name}) uses a wiki-first knowledge system.

Before starting any non-trivial task:
0. Run: python3 scripts/version_check.py (silent if up to date)
1. Read docs/wiki/index.md for the wiki page list
2. Read docs/wiki/current-status.md for project state
3. Read docs/wiki/log.md for recent session history

After completing work:
- Update docs/wiki/current-status.md with new state
- Append a log entry to docs/wiki/log.md (date | topic | outcome)
- If a durable decision was made, write it into the relevant wiki page

Consistency:
- If current-status.md conflicts with other wiki pages, trust the specific page and fix current-status.md
- If log.md is missing prior entries, don't guess — only append your own
- If two wiki pages contradict, flag it to the user before proceeding

Rules:
- Compile raw documents into wiki pages, don't just reference them
- Every conclusion goes back into the wiki (writeback is mandatory)
- Raw files (PDF/XLSX) stay outside Git, only manifests/ indexes go in
""",
        target / ".github" / "workflows" / "wiki-lint.yml": """name: Wiki Lint
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check wiki structure
        run: python3 scripts/wiki_check.py
      - name: Check raw manifest
        run: python3 scripts/raw_manifest_check.py
      - name: Check for untracked raw files
        run: python3 scripts/untracked_raw_check.py
""",
        target / ".gitignore": ".obsidian/\\nraw/\\nraw_local/\\nraw_vault/\\n",
    }

    created: list[Path] = []
    skipped: list[Path] = []
    for path, content in files.items():
        if path.exists() and not args.force:
            skipped.append(path)
            continue
        if not args.dry_run:
            write(path, content)
        created.append(path)

    if args.dry_run:
        print(f"[DRY RUN] Would bootstrap: {project_name}")
        print(f"Target repo: {target}")
        print(f"Default raw root name: {raw_root_name}")
        print(f"\\nWould create {len(created)} files:")
        for path in created:
            print(f"  + {path.relative_to(target)}")
        if skipped:
            print(f"\\nWould skip {len(skipped)} existing files (use --force to overwrite):")
            for path in skipped:
                print(f"  ~ {path.relative_to(target)}")
        return 0

    print(f"Bootstrapped knowledge system for: {project_name}")
    print(f"Target repo: {target}")
    print(f"Default raw root name: {raw_root_name}")
    print(f"\\nFiles created: {len(created)}")
    for path in created:
        print(f"  + {path.relative_to(target)}")
    if skipped:
        print(f"\\nSkipped (already exist): {len(skipped)}")
        for path in skipped:
            print(f"  ~ {path.relative_to(target)}")

    print("\\nNext steps:")
    print(f"1. cd {target}")
    print("2. python3 scripts/init_raw_root.py")
    print("3. python3 scripts/wiki_check.py")
    print("4. python3 scripts/raw_manifest_check.py")
    print("5. python3 scripts/export_memory_repo.py /path/to/memory-repo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
