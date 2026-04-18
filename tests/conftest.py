"""Shared pytest fixtures.

Each test gets a freshly bootstrapped project in a tmp_path. The bootstrap
script and its templates are loaded from the repo we're sitting in.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO_ROOT / "scripts" / "bootstrap_knowledge_system.py"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        **kwargs,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    target = tmp_path / "proj"
    result = run([sys.executable, str(BOOTSTRAP), str(target), "Test Project", "--raw-root-name", "test_raw"])
    assert result.returncode == 0, f"bootstrap failed: {result.stdout}\n{result.stderr}"
    return target
