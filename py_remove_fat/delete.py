"""Filesystem removal and interactive delete helpers."""

from __future__ import annotations

import os
import shutil
import stat
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from py_remove_fat.colors import C
from py_remove_fat.config import DELETE_WORKERS
from py_remove_fat.models import ProjectStats


def _handle_remove_error(func, path, _exc_info) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_tree(path: Path) -> None:
    shutil.rmtree(path, onerror=_handle_remove_error)


def removal_targets(
    item: ProjectStats,
    delete_names: frozenset[str],
) -> list[Path]:
    return [
        item.project_path / n
        for n in sorted(delete_names)
        if n in item.sizes
    ]


def removal_label(item: ProjectStats, delete_names: frozenset[str]) -> str:
    names = sorted(n for n in delete_names if n in item.sizes)
    return f"{item.project_path} ({', '.join(names)})"


def _delete_single_project(
    item: ProjectStats,
    *,
    delete_names: frozenset[str],
) -> None:
    for target in removal_targets(item, delete_names):
        remove_tree(target)


def parallel_delete_projects(
    projects: list[ProjectStats],
    *,
    delete_names: frozenset[str],
) -> list[ProjectStats]:
    if not projects:
        return []

    removed: list[ProjectStats] = []
    errors: list[tuple[ProjectStats, BaseException]] = []

    with ThreadPoolExecutor(max_workers=DELETE_WORKERS) as executor:
        future_to_item = {
            executor.submit(
                _delete_single_project,
                item,
                delete_names=delete_names,
            ): item
            for item in projects
        }
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                future.result()
                removed.append(item)
            except Exception as exc:
                errors.append((item, exc))

    for item, exc in errors:
        print(f"Failed {item.project_path}: {exc}", file=sys.stderr)

    for item in sorted(removed, key=lambda p: str(p.project_path)):
        label = removal_label(item, delete_names)
        print(f"{C.GREEN}Removed{C.RESET} {label}")

    return removed


def prompt_for_removal(label: str) -> str:
    while True:
        response = input(
            f"Remove {C.BOLD}{label}{C.RESET}? {C.YELLOW}[y/n/a]{C.RESET}: "
        ).strip().lower()
        if response in {"y", "yes", "n", "no", "a", "all"}:
            return response
        print("Please enter y/yes, n/no, or a/all.")


def should_remove(response: str) -> bool:
    return response in {"y", "yes", "a", "all"}
