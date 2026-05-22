"""CLI target name parsing and effective target resolution."""

from __future__ import annotations

from py_remove_fat.config import (
    DEFAULT_TARGETS,
    SUMMARY_REMOVE_STATS_LABEL,
    SUMMARY_REMOVED_LABEL,
    SUMMARY_SCAN_LABEL,
    SUMMARY_TOTAL_LABEL,
)


def parse_name_list(value: str | None) -> tuple[str, ...]:
    if value is None or not value.strip():
        return ()
    parts: list[str] = []
    for segment in value.split(","):
        name = segment.strip()
        if name:
            parts.append(name)
    return tuple(parts)


def flatten_append_args(fragments: list[str] | None) -> tuple[str, ...]:
    if not fragments:
        return ()
    out: list[str] = []
    for part in fragments:
        out.extend(parse_name_list(part))
    return tuple(out)


def resolve_effective_targets(
    include: tuple[str, ...],
    exclude: tuple[str, ...],
) -> tuple[str, ...]:
    exclude_set = frozenset(exclude)
    ordered: list[str] = []
    seen: set[str] = set()
    for name in DEFAULT_TARGETS:
        if name in exclude_set:
            continue
        ordered.append(name)
        seen.add(name)
    for name in include:
        if name not in seen:
            ordered.append(name)
            seen.add(name)
    return tuple(ordered)


def compute_summary_label_width(
    effective_targets: tuple[str, ...],
    *,
    deleting: bool = False,
) -> int:
    widths = [len(name) + 1 for name in effective_targets]
    widths.extend((len(SUMMARY_TOTAL_LABEL), len(SUMMARY_SCAN_LABEL)))
    if deleting:
        widths.extend(
            (len(SUMMARY_REMOVED_LABEL), len(SUMMARY_REMOVE_STATS_LABEL))
        )
    return max(widths)


def no_projects_message(effective_targets: tuple[str, ...]) -> str:
    names = ", ".join(effective_targets)
    return (
        f"No projects found with pyproject.toml and any of: {names}."
    )
