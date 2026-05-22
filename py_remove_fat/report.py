"""Report and delete orchestration for scan results."""

from __future__ import annotations

from py_remove_fat.colors import C
from py_remove_fat.delete import (
    parallel_delete_projects,
    prompt_for_removal,
    removal_label,
    removal_targets,
    should_remove,
    _delete_single_project,
)
from py_remove_fat.models import ProjectStats
from py_remove_fat.scan import ScanStats
from py_remove_fat.summary import format_size, print_summary
from py_remove_fat.targets import no_projects_message


def _print_delete_summary(
    projects: list[ProjectStats],
    stats: ScanStats,
    *,
    removed_projects: list[ProjectStats],
    delete_names: frozenset[str],
    effective_targets: tuple[str, ...],
    summary_label_width: int,
) -> None:
    print_summary(
        projects,
        stats=stats,
        effective_targets=effective_targets,
        summary_label_width=summary_label_width,
        removed_projects=removed_projects,
        delete_names=delete_names,
    )


def report_projects(
    projects: list[ProjectStats],
    stats: ScanStats,
    *,
    show_list: bool,
    effective_targets: tuple[str, ...],
    summary_label_width: int,
) -> None:
    if not projects:
        print(no_projects_message(effective_targets))
        print_summary(
            projects,
            stats=stats,
            effective_targets=effective_targets,
            summary_label_width=summary_label_width,
        )
        return

    if show_list:
        for item in projects:
            print(
                f"{C.BOLD}{item.project_path}{C.RESET}"
                f"  {C.GREEN}{format_size(item.total_bytes)}{C.RESET}"
            )
            for name in effective_targets:
                if name not in item.sizes:
                    continue
                bd = item.sizes[name]
                print(
                    f"  {C.CYAN}{name}{C.RESET}: {format_size(bd.bytes)}"
                    f" ({bd.files:,} files)"
                )

    print_summary(
        projects,
        stats=stats,
        effective_targets=effective_targets,
        summary_label_width=summary_label_width,
    )


def delete_projects(
    projects: list[ProjectStats],
    stats: ScanStats,
    *,
    delete_names: frozenset[str],
    dry_run: bool,
    skip_confirm: bool,
    effective_targets: tuple[str, ...],
    summary_label_width: int,
) -> None:
    if not projects:
        print(no_projects_message(effective_targets))
        print_summary(
            projects,
            stats=stats,
            effective_targets=effective_targets,
            summary_label_width=summary_label_width,
        )
        return

    processed: list[ProjectStats] = []

    if dry_run:
        for item in projects:
            if not removal_targets(item, delete_names):
                continue
            label = removal_label(item, delete_names)
            print(f"{C.YELLOW}Will remove{C.RESET} {C.BOLD}{label}{C.RESET}")
            processed.append(item)
        print_summary(
            projects,
            stats=stats,
            effective_targets=effective_targets,
            summary_label_width=summary_label_width,
        )
        return

    remove_all = skip_confirm
    batch: list[ProjectStats] = []

    for item in projects:
        targets = removal_targets(item, delete_names)
        if not targets:
            continue

        label = removal_label(item, delete_names)
        if not remove_all:
            response = prompt_for_removal(label)
            if response in {"a", "all"}:
                remove_all = True
                batch.append(item)
                continue
            if not should_remove(response):
                print(f"{C.DIM}Skipped {item.project_path}{C.RESET}")
                continue

            _delete_single_project(item, delete_names=delete_names)
            processed.append(item)
            print(f"{C.GREEN}Removed{C.RESET} {label}")
            continue

        batch.append(item)

    if batch:
        processed.extend(
            parallel_delete_projects(
                batch,
                delete_names=delete_names,
            )
        )

    _print_delete_summary(
        projects,
        stats,
        removed_projects=processed,
        delete_names=delete_names,
        effective_targets=effective_targets,
        summary_label_width=summary_label_width,
    )
