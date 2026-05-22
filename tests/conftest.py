"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def no_color(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")


@pytest.fixture
def scan_root(tmp_path: Path) -> Path:
    """Tree with one project that has targets and one bare pyproject.toml."""
    alpha = tmp_path / "alpha"
    alpha.mkdir()
    (alpha / "pyproject.toml").write_text("[project]\nname = 'alpha'\n")
    venv = alpha / ".venv"
    venv.mkdir()
    (venv / "pkg.txt").write_bytes(b"x" * 512)
    cache = alpha / "__pycache__"
    cache.mkdir()
    (cache / "mod.pyc").write_bytes(b"y" * 64)

    beta = tmp_path / "beta"
    beta.mkdir()
    (beta / "pyproject.toml").write_text("[project]\nname = 'beta'\n")

    nested = tmp_path / "outer" / "inner"
    nested.mkdir(parents=True)
    (nested / "pyproject.toml").write_text("[project]\nname = 'inner'\n")
    inner_venv = nested / ".venv"
    inner_venv.mkdir()
    (inner_venv / "data.bin").write_bytes(b"z" * 256)

    return tmp_path


@pytest.fixture
def deletable_project(tmp_path: Path) -> Path:
    """Single project with a small __pycache__ target for deletion tests."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname = 'proj'\n")
    cache = root / "__pycache__"
    cache.mkdir()
    (cache / "a.pyc").write_text("bytecode")
    return tmp_path
