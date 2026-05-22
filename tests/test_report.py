"""Tests for report and delete orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from py_remove_fat.models import ProjectStats, SizeBreakdown
from py_remove_fat.report import delete_projects, report_projects
from py_remove_fat.scan import ScanStats
import time


def _sample_project(root: Path) -> ProjectStats:
    return ProjectStats(
        project_path=root / "proj",
        sizes={"__pycache__": SizeBreakdown(1, 1, 10)},
    )


def test_report_projects_empty(capsys, scan_root: Path) -> None:
    stats = ScanStats(time.monotonic())
    report_projects(
        [],
        stats,
        show_list=False,
        effective_targets=(".venv",),
        summary_label_width=10,
    )
    out = capsys.readouterr().out
    assert "No projects found" in out
    assert "Summary:" in out


def test_report_projects_list(capsys, deletable_project: Path) -> None:
    proj = deletable_project / "proj"
    stats = ScanStats(time.monotonic())
    report_projects(
        [_sample_project(deletable_project)],
        stats,
        show_list=True,
        effective_targets=("__pycache__",),
        summary_label_width=14,
    )
    out = capsys.readouterr().out
    assert str(proj) in out
    assert "__pycache__" in out


def test_delete_projects_dry_run(capsys, deletable_project: Path) -> None:
    stats = ScanStats(time.monotonic())
    item = _sample_project(deletable_project)
    delete_projects(
        [item],
        stats,
        delete_names=frozenset({"__pycache__"}),
        dry_run=True,
        skip_confirm=True,
        effective_targets=("__pycache__",),
        summary_label_width=14,
    )
    out = capsys.readouterr().out
    assert "Will remove" in out
    assert "Scan Stats:" in out
    assert "Removed Targets:" not in out
    assert "Remove Stats:" not in out
    assert (deletable_project / "proj" / "__pycache__").is_dir()


def test_delete_projects_skip_confirm(capsys, deletable_project: Path) -> None:
    stats = ScanStats(time.monotonic())
    item = _sample_project(deletable_project)
    delete_projects(
        [item],
        stats,
        delete_names=frozenset({"__pycache__"}),
        dry_run=False,
        skip_confirm=True,
        effective_targets=("__pycache__",),
        summary_label_width=14,
    )
    out = capsys.readouterr().out
    assert "Removed" in out
    assert "Removed Targets:" in out
    assert "Remove Stats:" in out
    assert not (deletable_project / "proj" / "__pycache__").exists()


def test_delete_projects_interactive_yes(capsys, deletable_project: Path) -> None:
    stats = ScanStats(time.monotonic())
    item = _sample_project(deletable_project)
    with patch("py_remove_fat.report.prompt_for_removal", return_value="y"):
        delete_projects(
            [item],
            stats,
            delete_names=frozenset({"__pycache__"}),
            dry_run=False,
            skip_confirm=False,
            effective_targets=("__pycache__",),
            summary_label_width=14,
        )
    assert "Removed" in capsys.readouterr().out


def test_delete_projects_interactive_skip(capsys, deletable_project: Path) -> None:
    stats = ScanStats(time.monotonic())
    item = _sample_project(deletable_project)
    cache = deletable_project / "proj" / "__pycache__"
    with patch("py_remove_fat.report.prompt_for_removal", return_value="n"):
        delete_projects(
            [item],
            stats,
            delete_names=frozenset({"__pycache__"}),
            dry_run=False,
            skip_confirm=False,
            effective_targets=("__pycache__",),
            summary_label_width=14,
        )
    out = capsys.readouterr().out
    assert "Skipped" in out
    assert cache.is_dir()


def test_delete_projects_interactive_all_batch(capsys, deletable_project: Path) -> None:
    stats = ScanStats(time.monotonic())
    item = _sample_project(deletable_project)
    with patch("py_remove_fat.report.prompt_for_removal", return_value="all"):
        delete_projects(
            [item],
            stats,
            delete_names=frozenset({"__pycache__"}),
            dry_run=False,
            skip_confirm=False,
            effective_targets=("__pycache__",),
            summary_label_width=14,
        )
    assert not (deletable_project / "proj" / "__pycache__").exists()
