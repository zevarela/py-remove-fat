"""Tests for filesystem scanning and measurement."""

from __future__ import annotations

from pathlib import Path

from py_remove_fat.scan import ScanStats, find_projects, measure_directory
import time


def test_measure_directory(tmp_path: Path) -> None:
    d = tmp_path / "data"
    d.mkdir()
    (d / "a.txt").write_bytes(b"12345")
    sub = d / "sub"
    sub.mkdir()
    (sub / "b.txt").write_bytes(b"67")

    stats = ScanStats(time.monotonic())
    bd = measure_directory(str(d), stats)
    assert bd.files == 2
    assert bd.folders == 1
    assert bd.bytes == 7
    assert stats.entries_files >= 2


def test_find_projects_discovers_targets(scan_root: Path) -> None:
    projects, stats = find_projects(
        scan_root,
        measure_targets=frozenset({".venv", "__pycache__"}),
        never_descend=frozenset({".venv", "__pycache__"}),
    )
    paths = {str(p.project_path.name) for p in projects}
    assert "alpha" in paths
    assert "inner" in paths
    assert stats.pyprojects_seen >= 3
    assert stats.projects_found == len(projects)


def test_find_projects_pyproject_without_targets(scan_root: Path) -> None:
    projects, stats = find_projects(
        scan_root,
        measure_targets=frozenset({".venv"}),
        never_descend=frozenset({".venv"}),
    )
    assert stats.pyprojects_seen >= stats.projects_found
    assert stats.pyprojects_seen > len(projects)


def test_scan_stats_elapsed() -> None:
    stats = ScanStats(time.monotonic() - 2)
    assert stats.elapsed_seconds() >= 0
