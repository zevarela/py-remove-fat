"""Summary table formatting and printing."""

from __future__ import annotations

from py_remove_fat.colors import C, ccol, clabel, summary_data_column_colors
from py_remove_fat.config import (
    SUMMARY_COL_WIDTH,
    SUMMARY_REMOVE_STATS_LABEL,
    SUMMARY_REMOVED_LABEL,
    SUMMARY_SCAN_LABEL,
    SUMMARY_TOTAL_LABEL,
)
from py_remove_fat.models import ProjectStats
from py_remove_fat.scan import ScanStats


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size):,} {unit}"
            return f"{size:,.2f} {unit}"
        size /= 1024
    return f"{size:,.2f} TB"


def format_summary_size(num_bytes: int) -> str:
    size_gb = num_bytes / (1024**3)
    if size_gb >= 1:
        return f"{size_gb:,.2f} Gb"
    size_mb = num_bytes / (1024**2)
    if size_mb >= 1:
        return f"{size_mb:,.2f} Mb"
    size_kb = num_bytes / 1024
    if size_kb >= 1:
        return f"{size_kb:,.2f} Kb"
    return f"{num_bytes:,} b"


def _aggregate_target_stats(
    projects: list[ProjectStats],
    target_names: frozenset[str],
) -> tuple[int, int, int, int]:
    """Return (bytes, project_count, files, folders) for the given target names."""
    n_projects = 0
    files = 0
    folders = 0
    num_bytes = 0
    for item in projects:
        hit = False
        for name in target_names:
            if name not in item.sizes:
                continue
            bd = item.sizes[name]
            files += bd.files
            folders += bd.folders
            num_bytes += bd.bytes
            hit = True
        if hit:
            n_projects += 1
    return num_bytes, n_projects, files, folders


def _print_summary_row(
    label: str,
    col1: str,
    col2: str,
    col3: str,
    col4: str,
    *,
    label_width: int,
    label_color: str = "",
    col1_color: str = "",
    col2_color: str = "",
    col3_color: str = "",
    col4_color: str = "",
) -> None:
    w = SUMMARY_COL_WIDTH
    print(
        f"  {clabel(label, label_width, label_color)}"
        f"{ccol(col1, w, col1_color)}"
        f"{ccol(col2, w, col2_color)}"
        f"{ccol(col3, w, col3_color)}"
        f"{ccol(col4, w, col4_color)}"
    )


def _print_summary_data_row(
    label: str,
    num_bytes: int,
    projects: int,
    files: int,
    folders: int,
    *,
    label_width: int,
    label_color: str = "",
    footer_row: bool = False,
) -> None:
    lc = C.BOLD_WHITE if footer_row else label_color
    c1, c2, c3, c4 = summary_data_column_colors(num_bytes, footer_row=footer_row)
    _print_summary_row(
        label,
        format_summary_size(num_bytes),
        f"{projects:,} projects",
        f"{files:,} files",
        f"{folders:,} folders",
        label_width=label_width,
        label_color=lc,
        col1_color=c1,
        col2_color=c2,
        col3_color=c3,
        col4_color=c4,
    )


def _print_summary_stats_row(
    stats: ScanStats,
    *,
    label: str,
    label_width: int,
) -> None:
    _print_summary_row(
        label,
        f"{stats.elapsed_seconds():,} seconds",
        f"{stats.pyprojects_seen:,} projects",
        f"{stats.entries_files:,} files",
        f"{stats.entries_folders:,} folders",
        label_width=label_width,
        label_color=C.BOLD_WHITE,
        col1_color=C.BOLD_CYAN,
        col2_color=C.BOLD_YELLOW,
        col3_color=C.BOLD_BLUE,
        col4_color=C.BOLD_MAGENTA,
    )


def print_summary(
    projects: list[ProjectStats],
    *,
    stats: ScanStats,
    effective_targets: tuple[str, ...],
    summary_label_width: int,
    removed_projects: list[ProjectStats] | None = None,
    delete_names: frozenset[str] | None = None,
) -> None:
    project_count = len(projects)
    deleting = removed_projects is not None and delete_names is not None

    print()
    print(f"{C.BOLD}Summary:{C.RESET}")
    for name in effective_targets:
        n_projects = sum(1 for item in projects if name in item.sizes)
        files = folders = num_bytes = 0
        for item in projects:
            if name in item.sizes:
                b = item.sizes[name]
                files += b.files
                folders += b.folders
                num_bytes += b.bytes
        _print_summary_data_row(
            f"{name}:",
            num_bytes,
            n_projects,
            files,
            folders,
            label_width=summary_label_width,
            label_color=C.CYAN,
        )

    total_files = sum(item.total_files for item in projects)
    total_folders = sum(item.total_folders for item in projects)
    total_bytes = sum(item.total_bytes for item in projects)
    _print_summary_data_row(
        SUMMARY_TOTAL_LABEL,
        total_bytes,
        project_count,
        total_files,
        total_folders,
        label_width=summary_label_width,
        footer_row=True,
    )

    if deleting:
        removed_bytes, removed_count, removed_files, removed_folders = (
            _aggregate_target_stats(removed_projects, delete_names)
        )
        _print_summary_data_row(
            SUMMARY_REMOVED_LABEL,
            removed_bytes,
            removed_count,
            removed_files,
            removed_folders,
            label_width=summary_label_width,
            label_color=C.GREEN,
        )
        stats_label = SUMMARY_REMOVE_STATS_LABEL
    else:
        stats_label = SUMMARY_SCAN_LABEL

    _print_summary_stats_row(stats, label=stats_label, label_width=summary_label_width)
