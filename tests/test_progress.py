"""Tests for progress display and color initialization edge cases."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from py_remove_fat.colors import C, init_colors
from py_remove_fat.delete import parallel_delete_projects
from py_remove_fat.scan import ProgressDisplay, ScanStats
import time


def test_parallel_delete_empty() -> None:
    assert parallel_delete_projects([], delete_names=frozenset({".venv"})) == []


def test_progress_display_not_tty() -> None:
    stats = ScanStats(time.monotonic())
    progress = ProgressDisplay(stats)
    progress._enabled = False
    progress.maybe_refresh(force=True)
    progress.clear()


def test_progress_display_tty_refresh(capsys) -> None:
    stats = ScanStats(time.monotonic())
    progress = ProgressDisplay(stats)
    progress._enabled = True
    progress._stream = sys.stderr
    with patch.object(progress, "_terminal_width", return_value=80):
        progress.maybe_refresh(force=True)
        progress.clear()


def test_progress_fit_line_truncation() -> None:
    stats = ScanStats(time.monotonic())
    progress = ProgressDisplay(stats)
    with patch.object(progress, "_terminal_width", return_value=5):
        assert progress._fit_line("hello world") == "...ld"


def test_init_colors_no_color_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    saved = C.GREEN
    C.GREEN = ""
    init_colors()
    assert C.GREEN == ""
    C.GREEN = saved


def test_init_colors_with_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    saved_green = C.GREEN
    C.GREEN = ""
    with patch.object(sys.stdout, "isatty", return_value=True):
        with patch.object(sys, "platform", "linux"):
            init_colors()
    assert C.GREEN == "\033[32m"
    C.GREEN = saved_green
