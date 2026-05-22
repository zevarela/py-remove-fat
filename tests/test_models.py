"""Tests for data model helpers."""

from __future__ import annotations

from pathlib import Path

from py_remove_fat.models import ProjectStats, SizeBreakdown


def test_size_breakdown_empty() -> None:
    assert SizeBreakdown(0, 0, 0).empty is True
    assert SizeBreakdown(1, 0, 0).empty is False


def test_project_stats_totals() -> None:
    item = ProjectStats(
        project_path=Path("/p"),
        sizes={
            "a": SizeBreakdown(folders=2, files=3, bytes=100),
            "b": SizeBreakdown(folders=1, files=1, bytes=50),
        },
    )
    assert item.total_folders == 3
    assert item.total_files == 4
    assert item.total_bytes == 150
