"""Tests for CLI argument handling and main()."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from py_remove_fat.cli import main, parse_args, print_banner


def test_parse_args_defaults() -> None:
    args = parse_args([])
    assert args.path == "."
    assert args.list is False
    assert args.del_names is None


def test_print_banner(capsys) -> None:
    print_banner()
    assert "Py Remove Fat" in capsys.readouterr().out


def test_main_scan_ok(capsys, scan_root: Path) -> None:
    code = main([str(scan_root)])
    assert code == 0
    assert "Summary:" in capsys.readouterr().out


def test_main_list(capsys, scan_root: Path) -> None:
    code = main([str(scan_root), "--list"])
    assert code == 0
    assert "alpha" in capsys.readouterr().out


def test_main_dry_run_delete(capsys, deletable_project: Path) -> None:
    code = main(
        [
            str(deletable_project),
            "--del",
            "__pycache__",
            "--print-only",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "Will remove" in out
    assert "Scan Stats:" in out
    assert "Removed Targets:" not in out
    assert "Remove Stats:" not in out


def test_main_del_all_yes(capsys, scan_root: Path) -> None:
    code = main([str(scan_root), "--del-all", "--yes", "--exclude", "build,dist,wheels,.ipynb_checkpoints"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Removed Targets:" in out
    assert "Remove Stats:" in out


def test_main_unknown_exclude(capsys, scan_root: Path) -> None:
    code = main([str(scan_root), "--exclude", "not-a-target"])
    assert code == 1
    assert "Unknown --exclude" in capsys.readouterr().err


def test_main_path_not_found(capsys) -> None:
    code = main(["/nonexistent/path/xyz"])
    assert code == 1
    assert "does not exist" in capsys.readouterr().err


def test_main_del_and_del_all_mutual(capsys, scan_root: Path) -> None:
    code = main([str(scan_root), "--del", ".venv", "--del-all"])
    assert code == 1


def test_main_print_only_requires_del(capsys, scan_root: Path) -> None:
    code = main([str(scan_root), "--print-only"])
    assert code == 1


def test_main_empty_del(capsys, scan_root: Path) -> None:
    code = main([str(scan_root), "--del", ""])
    assert code == 1


def test_main_unknown_del_name(capsys, scan_root: Path) -> None:
    code = main([str(scan_root), "--del", "not-in-targets"])
    assert code == 1
    assert "Unknown name(s)" in capsys.readouterr().err


def test_main_exclude_all_targets(capsys, scan_root: Path) -> None:
    code = main(
        [
            str(scan_root),
            "--exclude",
            ".venv,__pycache__,.ipynb_checkpoints,build,dist,wheels",
        ]
    )
    assert code == 1
    assert "No effective targets" in capsys.readouterr().err


def test_main_path_is_file(capsys, tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("x")
    code = main([str(f)])
    assert code == 1
    assert "not a directory" in capsys.readouterr().err


def test_main_include_extra(capsys, scan_root: Path) -> None:
    code = main([str(scan_root), "--include", "data"])
    assert code == 0


def test_prompt_for_removal_invalid_then_valid(capsys) -> None:
    from py_remove_fat.delete import prompt_for_removal

    with patch("builtins.input", side_effect=["maybe", "yes"]):
        assert prompt_for_removal("proj (.venv)") == "yes"
    assert "Please enter" in capsys.readouterr().out
