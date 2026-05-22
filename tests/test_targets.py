"""Tests for target parsing and resolution."""

from __future__ import annotations

from py_remove_fat.targets import (
    compute_summary_label_width,
    flatten_append_args,
    no_projects_message,
    parse_name_list,
    resolve_effective_targets,
)


def test_parse_name_list_empty() -> None:
    assert parse_name_list(None) == ()
    assert parse_name_list("") == ()
    assert parse_name_list("  ,  ") == ()


def test_parse_name_list_splits_and_strips() -> None:
    assert parse_name_list(" .venv , build ") == (".venv", "build")


def test_flatten_append_args() -> None:
    assert flatten_append_args(None) == ()
    assert flatten_append_args(["a,b", "c"]) == ("a", "b", "c")


def test_resolve_effective_targets_exclude() -> None:
    result = resolve_effective_targets((), (".venv", "build"))
    assert ".venv" not in result
    assert "build" not in result
    assert "__pycache__" in result


def test_resolve_effective_targets_include() -> None:
    result = resolve_effective_targets((".git", "data"), ())
    assert ".git" in result
    assert result.index(".git") > result.index("wheels")


def test_compute_summary_label_width() -> None:
    width = compute_summary_label_width((".venv", "node_modules"))
    assert width >= len("node_modules:")


def test_compute_summary_label_width_deleting() -> None:
    width = compute_summary_label_width((".venv",), deleting=True)
    assert width >= len("Removed Targets:")
    assert width >= len("Remove Stats:")


def test_no_projects_message() -> None:
    msg = no_projects_message((".venv",))
    assert "pyproject.toml" in msg
    assert ".venv" in msg
