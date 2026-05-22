"""Tests for summary formatting and printing."""

from __future__ import annotations

from pathlib import Path

from py_remove_fat.models import ProjectStats, SizeBreakdown
from py_remove_fat.scan import ScanStats
from py_remove_fat.summary import (
    _aggregate_target_stats,
    format_size,
    format_summary_size,
    print_summary,
)
import time


def test_format_size_units() -> None:
    assert format_size(500) == "500 B"
    assert "KB" in format_size(2048)
    assert "MB" in format_size(2 * 1024**2)
    assert "GB" in format_size(2 * 1024**3)


def test_format_summary_size_units() -> None:
    assert format_summary_size(0) == "0 b"
    assert "Kb" in format_summary_size(2048)
    assert "Mb" in format_summary_size(2 * 1024**2)
    assert "Gb" in format_summary_size(2 * 1024**3)


def test_print_summary(capsys, scan_root: Path) -> None:
    stats = ScanStats(time.monotonic())
    stats.pyprojects_seen = 3
    stats.entries_files = 10
    stats.entries_folders = 5
    projects = [
        ProjectStats(
            project_path=scan_root / "alpha",
            sizes={
                ".venv": SizeBreakdown(folders=1, files=1, bytes=512),
                "__pycache__": SizeBreakdown(folders=1, files=1, bytes=64),
            },
        ),
    ]
    print_summary(
        projects,
        stats=stats,
        effective_targets=(".venv", "__pycache__"),
        summary_label_width=12,
    )
    out = capsys.readouterr().out
    assert "Summary:" in out
    assert "All Targets:" in out
    assert "Scan Stats:" in out
    assert "Removed Targets:" not in out
    assert "3 projects" in out or "3 seconds" in out


def test_aggregate_target_stats() -> None:
    projects = [
        ProjectStats(
            project_path=Path("/a"),
            sizes={
                ".venv": SizeBreakdown(1, 2, 100),
                "__pycache__": SizeBreakdown(0, 1, 10),
            },
        ),
        ProjectStats(
            project_path=Path("/b"),
            sizes={".venv": SizeBreakdown(2, 1, 50)},
        ),
    ]
    num_bytes, n_proj, files, folders = _aggregate_target_stats(
        projects,
        frozenset({".venv"}),
    )
    assert num_bytes == 150
    assert n_proj == 2
    assert files == 3
    assert folders == 3


def test_print_summary_delete_mode(capsys, scan_root: Path) -> None:
    stats = ScanStats(time.monotonic())
    all_projects = [
        ProjectStats(
            project_path=scan_root / "alpha",
            sizes={
                ".venv": SizeBreakdown(folders=1, files=1, bytes=512),
                "__pycache__": SizeBreakdown(folders=1, files=1, bytes=64),
            },
        ),
        ProjectStats(
            project_path=scan_root / "outer" / "inner",
            sizes={".venv": SizeBreakdown(folders=1, files=1, bytes=256)},
        ),
    ]
    removed = [all_projects[0]]
    print_summary(
        all_projects,
        stats=stats,
        effective_targets=(".venv", "__pycache__"),
        summary_label_width=18,
        removed_projects=removed,
        delete_names=frozenset({"__pycache__"}),
    )
    out = capsys.readouterr().out
    assert "All Targets:" in out
    assert "Removed Targets:" in out
    assert "Remove Stats:" in out
    assert "Scan Stats:" not in out
