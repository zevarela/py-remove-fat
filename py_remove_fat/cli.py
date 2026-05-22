"""Command-line interface and main entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from py_remove_fat.colors import C
from py_remove_fat.config import BANNER, DEFAULT_TARGETS, DEFAULT_TARGET_SET
from py_remove_fat.report import delete_projects, report_projects
from py_remove_fat.scan import find_projects
from py_remove_fat.targets import (
    compute_summary_label_width,
    flatten_append_args,
    parse_name_list,
    resolve_effective_targets,
)


def print_banner() -> None:
    print(f"{C.BOLD_CYAN}{BANNER}{C.RESET}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan for Python projects (pyproject.toml) with configurable "
            "sibling folders, report disk usage, and optionally remove them."
        )
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Root path to scan recursively (default: .\\)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List each project path and size before the summary",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip individual removal confirmations when used with --del or --del-all",
    )
    parser.add_argument(
        "--include",
        metavar="names",
        action="append",
        help=(
            "Comma-separated extra target folder names for this run "
            "(repeatable)"
        ),
    )
    parser.add_argument(
        "--exclude",
        metavar="names",
        action="append",
        help=(
            "Comma-separated names removed from default targets "
            "(repeatable; default targets only)"
        ),
    )
    parser.add_argument(
        "--del",
        dest="del_names",
        metavar="names",
        default=None,
        help=(
            "Comma-separated folder names to remove "
            "(must match summary labels without the trailing colon)"
        ),
    )
    parser.add_argument(
        "--del-all",
        action="store_true",
        help="Remove all effective targets that exist under each project",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help=(
            "With --del or --del-all: print removals only, do not delete or prompt"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    print_banner()
    args = parse_args(argv)
    root = Path(args.path).resolve()

    include = flatten_append_args(args.include)
    exclude = flatten_append_args(args.exclude)

    for name in exclude:
        if name not in DEFAULT_TARGET_SET:
            print(
                f"Unknown --exclude name {name!r}; "
                f"allowed: {', '.join(DEFAULT_TARGETS)}",
                file=sys.stderr,
            )
            return 1

    effective_targets = resolve_effective_targets(include, exclude)
    if not effective_targets:
        print(
            "No effective targets after --include/--exclude.",
            file=sys.stderr,
        )
        return 1

    deleting = (args.del_all or args.del_names is not None) and not args.print_only
    summary_label_width = compute_summary_label_width(
        effective_targets,
        deleting=deleting,
    )
    measure_targets = frozenset(effective_targets)
    never_descend = DEFAULT_TARGET_SET | frozenset(include)

    if args.del_all and args.del_names is not None:
        print("Use either --del or --del-all, not both.", file=sys.stderr)
        return 1

    if args.print_only and not args.del_all and args.del_names is None:
        print(
            "--print-only requires --del or --del-all.",
            file=sys.stderr,
        )
        return 1

    delete_names: frozenset[str] | None
    if args.del_all:
        delete_names = frozenset(effective_targets)
    elif args.del_names is not None:
        del_list = parse_name_list(args.del_names)
        if not del_list:
            print(
                "--del requires at least one non-empty folder name.",
                file=sys.stderr,
            )
            return 1
        unknown = [n for n in del_list if n not in effective_targets]
        if unknown:
            print(
                "Unknown name(s) in --del "
                f"(not in effective targets): {', '.join(unknown)}",
                file=sys.stderr,
            )
            print(
                f"Effective targets this run: {', '.join(effective_targets)}",
                file=sys.stderr,
            )
            return 1
        delete_names = frozenset(del_list)
    else:
        delete_names = None

    if not root.exists():
        print(f"Path does not exist: {root}", file=sys.stderr)
        return 1
    if not root.is_dir():
        print(f"Path is not a directory: {root}", file=sys.stderr)
        return 1

    projects, stats = find_projects(
        root,
        measure_targets=measure_targets,
        never_descend=never_descend,
    )

    if delete_names is not None:
        delete_projects(
            projects,
            stats,
            delete_names=delete_names,
            dry_run=args.print_only,
            skip_confirm=args.yes,
            effective_targets=effective_targets,
            summary_label_width=summary_label_width,
        )
    else:
        report_projects(
            projects,
            stats,
            show_list=args.list,
            effective_targets=effective_targets,
            summary_label_width=summary_label_width,
        )

    return 0
