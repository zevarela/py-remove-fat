"""Tests for terminal color helpers."""

from __future__ import annotations

from py_remove_fat.colors import C, ccol, clabel, summary_data_column_colors


def test_clabel_without_color() -> None:
    assert clabel("hi", 5, "") == "hi   "


def test_ccol_without_color() -> None:
    assert ccol("9", 4, "") == "   9"


def test_summary_data_column_colors_normal() -> None:
    c1, c2, c3, c4 = summary_data_column_colors(100, footer_row=False)
    assert c1 == C.GREEN
    assert c2 == C.YELLOW
    assert c3 == C.BLUE
    assert c4 == C.MAGENTA


def test_summary_data_column_colors_zero_bytes() -> None:
    c1, _, _, _ = summary_data_column_colors(0, footer_row=False)
    assert c1 == C.DIM


def test_summary_data_column_colors_footer() -> None:
    c1, c2, c3, c4 = summary_data_column_colors(100, footer_row=True)
    assert c1 == C.BOLD_GREEN
    assert c2 == C.BOLD_YELLOW
    assert c3 == C.BOLD_BLUE
    assert c4 == C.BOLD_MAGENTA
