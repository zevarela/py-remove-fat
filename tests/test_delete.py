"""Tests for deletion helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from py_remove_fat.delete import (
    parallel_delete_projects,
    removal_label,
    removal_targets,
    remove_tree,
    should_remove,
)
from py_remove_fat.models import ProjectStats, SizeBreakdown


def test_should_remove() -> None:
    assert should_remove("y") is True
    assert should_remove("yes") is True
    assert should_remove("a") is True
    assert should_remove("n") is False


def test_removal_targets_and_label() -> None:
    item = ProjectStats(
        project_path=Path("/proj"),
        sizes={".venv": SizeBreakdown(1, 1, 10)},
    )
    names = frozenset({".venv", "dist"})
    targets = removal_targets(item, names)
    assert targets == [Path("/proj") / ".venv"]
    assert removal_label(item, names).endswith("(.venv)")
    assert "proj" in removal_label(item, names)


def test_remove_tree_and_parallel_delete(deletable_project: Path) -> None:
    proj = deletable_project / "proj"
    cache = proj / "__pycache__"
    assert cache.is_dir()

    item = ProjectStats(
        project_path=proj,
        sizes={"__pycache__": SizeBreakdown(1, 1, 8)},
    )
    removed = parallel_delete_projects([item], delete_names=frozenset({"__pycache__"}))
    assert len(removed) == 1
    assert not cache.exists()


def test_remove_tree_direct(tmp_path: Path) -> None:
    target = tmp_path / "gone"
    target.mkdir()
    (target / "f.txt").write_text("x")
    remove_tree(target)
    assert not target.exists()


def test_parallel_delete_reports_failure(
    capsys: pytest.CaptureFixture[str],
    deletable_project: Path,
) -> None:
    proj = deletable_project / "proj"
    item = ProjectStats(
        project_path=proj,
        sizes={"__pycache__": SizeBreakdown(1, 1, 8)},
    )

    def boom(_item: ProjectStats, *, delete_names: frozenset[str]) -> None:
        raise OSError("permission denied")

    with patch(
        "py_remove_fat.delete._delete_single_project",
        side_effect=boom,
    ):
        removed = parallel_delete_projects(
            [item],
            delete_names=frozenset({"__pycache__"}),
        )

    assert removed == []
    err = capsys.readouterr().err
    assert "Failed" in err
    assert str(proj) in err
