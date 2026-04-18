from __future__ import annotations
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
