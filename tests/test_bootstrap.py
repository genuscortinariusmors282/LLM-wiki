"""End-to-end: bootstrap a project, run its checks, then poison the
fixtures and confirm the checks catch the breakage.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .conftest import BOOTSTRAP, run


def test_bootstrap_creates_expected_files(project: Path) -> None:
    expected = [
        "AGENTS.md",
        "CLAUDE.md",
        ".cursorrules",
        ".windsurfrules",
        ".gitignore",
        "docs/wiki/README.md",
        "docs/wiki/SCHEMA.md",
        "docs/wiki/index.md",
        "docs/wiki/log.md",
        "docs/wiki/project-overview.md",
        "docs/wiki/current-status.md",
        "docs/wiki/sources-and-data.md",
        "docs/wiki/github-and-raw-strategy.md",
        "manifests/README.md",
        "manifests/raw_sources.csv",
        "scripts/wiki_check.py",
        "scripts/raw_manifest_check.py",
        "scripts/ingest_raw.py",
        "scripts/untracked_raw_check.py",
        "scripts/provenance_check.py",
        "scripts/stale_report.py",
        "scripts/delta_compile.py",
        "scripts/version_check.py",
        "scripts/init_raw_root.py",
        "scripts/export_memory_repo.py",
        "scripts/upgrade.sh",
        ".claude/commands/wiki-check.md",
        ".claude/commands/wiki-upgrade.md",
        ".claude/commands/wiki-status.md",
        ".github/workflows/wiki-lint.yml",
    ]
    for rel in expected:
        assert (project / rel).exists(), f"missing: {rel}"


def test_no_unresolved_sentinels(project: Path) -> None:
    """Every generated file should have all __FOO__ placeholders substituted."""
    import re
    sentinel_re = re.compile(r"__[A-Z][A-Z0-9_]*__")
    allowed = {"__main__", "__init__", "__name__", "__file__"}
    for path in project.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        bad = [m for m in sentinel_re.findall(text) if m not in allowed]
        assert not bad, f"unresolved sentinels in {path.relative_to(project)}: {bad}"


def test_project_name_substituted(project: Path) -> None:
    claude_md = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Test Project" in claude_md


def test_gitignore_has_real_newlines(project: Path) -> None:
    """Regression: pre-extraction produced a one-line .gitignore with literal \\n."""
    gi = (project / ".gitignore").read_text(encoding="utf-8")
    assert "raw/" in gi.splitlines()
    assert "\\n" not in gi


def test_wiki_check_passes_on_fresh_bootstrap(project: Path) -> None:
    result = run([sys.executable, str(project / "scripts" / "wiki_check.py")])
    assert result.returncode == 0, f"wiki_check failed:\n{result.stdout}"
    assert "wiki_check: OK" in result.stdout


def test_raw_manifest_check_passes_on_fresh_bootstrap(project: Path) -> None:
    result = run([sys.executable, str(project / "scripts" / "raw_manifest_check.py")])
    assert result.returncode == 0, f"raw_manifest_check failed:\n{result.stdout}"


def test_wiki_check_catches_missing_required_file(project: Path) -> None:
    (project / "docs" / "wiki" / "current-status.md").unlink()
    result = run([sys.executable, str(project / "scripts" / "wiki_check.py")])
    assert result.returncode == 1
    assert "current-status.md" in result.stdout


def test_wiki_check_catches_broken_link(project: Path) -> None:
    sources = project / "docs" / "wiki" / "sources-and-data.md"
    sources.write_text(sources.read_text(encoding="utf-8") + "\n[broken](./does-not-exist.md)\n", encoding="utf-8")
    result = run([sys.executable, str(project / "scripts" / "wiki_check.py")])
    assert result.returncode == 1
    assert "broken link" in result.stdout


def test_wiki_check_catches_missing_frontmatter(project: Path) -> None:
    page = project / "docs" / "wiki" / "current-status.md"
    page.write_text("# No frontmatter here\n", encoding="utf-8")
    result = run([sys.executable, str(project / "scripts" / "wiki_check.py")])
    assert result.returncode == 1
    assert "frontmatter" in result.stdout


def test_wiki_check_catches_bad_log_header(project: Path) -> None:
    log = project / "docs" / "wiki" / "log.md"
    log.write_text(log.read_text(encoding="utf-8") + "\n## bad header\n", encoding="utf-8")
    result = run([sys.executable, str(project / "scripts" / "wiki_check.py")])
    assert result.returncode == 1
    assert "log header" in result.stdout


def test_wiki_check_substring_false_positive_caught(project: Path) -> None:
    """Regression: pre-1.3.0 used substring match, so a page named `policy.md`
    falsely passed the index check whenever `pricing-policy.md` was indexed.
    """
    wiki = project / "docs" / "wiki"
    fm = "---\ntitle: X\nsource: session\ncreated: 2026-01-01\n---\n# X\n"
    (wiki / "pricing-policy.md").write_text(fm, encoding="utf-8")
    (wiki / "policy.md").write_text(fm, encoding="utf-8")
    index = wiki / "index.md"
    text = index.read_text(encoding="utf-8")
    index.write_text(text + "\n- [Pricing](./pricing-policy.md)\n", encoding="utf-8")
    result = run([sys.executable, str(project / "scripts" / "wiki_check.py")])
    assert result.returncode == 1
    assert "policy.md" in result.stdout


def test_wiki_check_ignores_links_inside_code_fences(project: Path) -> None:
    """Links inside ``` ... ``` blocks are illustrative, not real refs."""
    page = project / "docs" / "wiki" / "current-status.md"
    body = page.read_text(encoding="utf-8")
    body += "\n```markdown\n[fake](./does-not-exist.md)\n```\n"
    page.write_text(body, encoding="utf-8")
    result = run([sys.executable, str(project / "scripts" / "wiki_check.py")])
    assert result.returncode == 0, result.stdout


def test_wiki_check_ignores_links_inside_inline_code(project: Path) -> None:
    page = project / "docs" / "wiki" / "current-status.md"
    body = page.read_text(encoding="utf-8")
    body += "\nUse `[label](./bad.md)` to format inline code.\n"
    page.write_text(body, encoding="utf-8")
    result = run([sys.executable, str(project / "scripts" / "wiki_check.py")])
    assert result.returncode == 0, result.stdout


def test_raw_manifest_check_catches_duplicate_id(project: Path) -> None:
    manifest = project / "manifests" / "raw_sources.csv"
    manifest.write_text(
        "source_id,company,vendor,kind,filename,raw_rel_path,status,compiled_into,notes\n"
        "src_a,X,Y,document,a.pdf,a.pdf,new,,\n"
        "src_a,X,Y,document,b.pdf,b.pdf,new,,\n",
        encoding="utf-8",
    )
    result = run([sys.executable, str(project / "scripts" / "raw_manifest_check.py")])
    assert result.returncode == 1
    assert "duplicate" in result.stdout


def test_raw_manifest_check_catches_bad_status(project: Path) -> None:
    manifest = project / "manifests" / "raw_sources.csv"
    manifest.write_text(
        "source_id,company,vendor,kind,filename,raw_rel_path,status,compiled_into,notes\n"
        "src_a,X,Y,document,a.pdf,a.pdf,bogus_status,,\n",
        encoding="utf-8",
    )
    result = run([sys.executable, str(project / "scripts" / "raw_manifest_check.py")])
    assert result.returncode == 1
    assert "bad status" in result.stdout


def test_raw_manifest_check_catches_compiled_without_target(project: Path) -> None:
    manifest = project / "manifests" / "raw_sources.csv"
    manifest.write_text(
        "source_id,company,vendor,kind,filename,raw_rel_path,status,compiled_into,notes\n"
        "src_a,X,Y,document,a.pdf,a.pdf,compiled,,\n",
        encoding="utf-8",
    )
    result = run([sys.executable, str(project / "scripts" / "raw_manifest_check.py")])
    assert result.returncode == 1
    assert "compiled_into" in result.stdout


def test_manifest_meta_json_created(project: Path) -> None:
    import json
    meta_path = project / "manifests" / "raw_sources.meta.json"
    assert meta_path.exists()
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert "source_id" in data["columns"]


def test_raw_manifest_check_legacy_compat(project: Path) -> None:
    """Projects bootstrapped before meta.json existed should still pass."""
    (project / "manifests" / "raw_sources.meta.json").unlink()
    result = run([sys.executable, str(project / "scripts" / "raw_manifest_check.py")])
    assert result.returncode == 0, result.stdout
    assert "loaded from legacy" in result.stdout


def test_raw_manifest_check_future_schema_skipped(project: Path) -> None:
    """A future schema_version should not break old CI — script returns 0 with notice."""
    import json
    meta = project / "manifests" / "raw_sources.meta.json"
    data = json.loads(meta.read_text(encoding="utf-8"))
    data["schema_version"] = 99
    meta.write_text(json.dumps(data), encoding="utf-8")
    result = run([sys.executable, str(project / "scripts" / "raw_manifest_check.py")])
    assert result.returncode == 0
    assert "SKIPPED" in result.stdout


def test_raw_manifest_check_malformed_meta(project: Path) -> None:
    meta = project / "manifests" / "raw_sources.meta.json"
    meta.write_text("not json {{{", encoding="utf-8")
    result = run([sys.executable, str(project / "scripts" / "raw_manifest_check.py")])
    assert result.returncode != 0
    assert "malformed" in (result.stdout + result.stderr)


def test_wiki_size_report_runs_on_fresh_bootstrap(project: Path) -> None:
    result = run([sys.executable, str(project / "scripts" / "wiki_size_report.py")])
    assert result.returncode == 0, result.stdout
    assert "GREEN" in result.stdout
    assert "estimated tokens" in result.stdout


def test_wiki_size_report_json_output(project: Path) -> None:
    import json
    result = run([sys.executable, str(project / "scripts" / "wiki_size_report.py"), "--json"])
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["bucket"] == "GREEN"
    assert data["page_count"] >= 5
    assert "thresholds" in data


def test_wiki_size_report_thresholds_promote(project: Path) -> None:
    """Stuff a page until it crosses YELLOW, confirm bucket changes."""
    bloat = project / "docs" / "wiki" / "current-status.md"
    body = bloat.read_text(encoding="utf-8")
    body += "\n" + ("padding line. " * 12_000)
    bloat.write_text(body, encoding="utf-8")
    result = run([sys.executable, str(project / "scripts" / "wiki_size_report.py")])
    assert result.returncode == 0
    assert "YELLOW" in result.stdout or "RED" in result.stdout


def test_provenance_check_ci_mode_passes_without_raw(project: Path) -> None:
    page = project / "docs" / "wiki" / "current-status.md"
    page.write_text(
        "---\n"
        "title: Current Status\n"
        "source: raw/example.pdf\n"
        "source_hash: 0123456789abcdef\n"
        "created: 2026-01-01\n"
        "---\n"
        "# X\n",
        encoding="utf-8",
    )
    result = run([sys.executable, str(project / "scripts" / "provenance_check.py"), "--ci"])
    assert result.returncode == 0, result.stdout
    assert "ci-mode" in result.stdout


def test_provenance_check_ci_mode_catches_missing_hash(project: Path) -> None:
    page = project / "docs" / "wiki" / "current-status.md"
    page.write_text(
        "---\n"
        "title: Current Status\n"
        "source: raw/example.pdf\n"
        "created: 2026-01-01\n"
        "---\n"
        "# X\n",
        encoding="utf-8",
    )
    result = run([sys.executable, str(project / "scripts" / "provenance_check.py"), "--ci"])
    assert result.returncode == 1
    assert "without source_hash" in result.stdout


def test_runtime_headers_present_on_all_scripts(project: Path) -> None:
    scripts_dir = project / "scripts"
    for script in scripts_dir.glob("*.py"):
        head = "\n".join(script.read_text(encoding="utf-8").splitlines()[:30])
        assert "# runtime:" in head, f"{script.name} missing # runtime: header in first 30 lines"


def test_runtime_profile_wiki_page_exists(project: Path) -> None:
    page = project / "docs" / "wiki" / "runtime-profile.md"
    assert page.exists()
    text = page.read_text(encoding="utf-8")
    assert "ci-safe" in text
    assert "dev-only" in text
    index = (project / "docs" / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "runtime-profile.md" in index


def test_ci_workflow_only_runs_ci_safe_scripts(project: Path) -> None:
    workflow = (project / ".github" / "workflows" / "wiki-lint.yml").read_text(encoding="utf-8")
    if "provenance_check.py" in workflow:
        assert "--ci" in workflow, "provenance_check in CI must use --ci"
    forbidden_in_ci = ["stale_report.py", "delta_compile.py", "ingest_raw.py"]
    for fname in forbidden_in_ci:
        assert fname not in workflow, f"dev-only script {fname} found in CI workflow"


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "neverwritten"
    result = run([sys.executable, str(BOOTSTRAP), str(target), "X", "--dry-run"])
    assert result.returncode == 0
    assert "[DRY RUN]" in result.stdout
    assert not target.exists()


def test_force_creates_bak(project: Path) -> None:
    (project / "CLAUDE.md").write_text("# manual edit\n", encoding="utf-8")
    result = run([
        sys.executable,
        str(BOOTSTRAP),
        str(project),
        "Test Project",
        "--raw-root-name", "test_raw",
        "--force",
    ])
    assert result.returncode == 0
    bak_files = list(project.glob("CLAUDE.md.bak.*"))
    assert len(bak_files) == 1
    assert bak_files[0].read_text(encoding="utf-8") == "# manual edit\n"


def test_force_no_backup_skips_bak(project: Path) -> None:
    (project / "CLAUDE.md").write_text("# manual edit\n", encoding="utf-8")
    result = run([
        sys.executable,
        str(BOOTSTRAP),
        str(project),
        "Test Project",
        "--raw-root-name", "test_raw",
        "--force",
        "--no-backup",
    ])
    assert result.returncode == 0
    assert not list(project.glob("CLAUDE.md.bak.*"))


def test_no_force_skips_existing(project: Path) -> None:
    (project / "CLAUDE.md").write_text("# manual edit\n", encoding="utf-8")
    result = run([
        sys.executable,
        str(BOOTSTRAP),
        str(project),
        "Test Project",
        "--raw-root-name", "test_raw",
    ])
    assert result.returncode == 0
    assert (project / "CLAUDE.md").read_text(encoding="utf-8") == "# manual edit\n"
    assert "Skipped" in result.stdout
