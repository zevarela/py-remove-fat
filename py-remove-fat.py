import argparse
import os
import queue
import shutil
import stat
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

MEASURE_WORKERS = 4
DELETE_WORKERS = 4
WORK_QUEUE_SIZE = MEASURE_WORKERS * 2
PROGRESS_INTERVAL = 2.0
SUMMARY_COL_WIDTH = 22

DEFAULT_TARGETS: tuple[str, ...] = (
    ".venv",
    "__pycache__",
    ".ipynb_checkpoints",
    "build",
    "dist",
    "wheels",
)
_DEFAULT_TARGET_SET = frozenset(DEFAULT_TARGETS)


@dataclass(frozen=True)
class SizeBreakdown:
    folders: int
    files: int
    bytes: int

    @property
    def empty(self) -> bool:
        return self.folders == 0 and self.files == 0 and self.bytes == 0


@dataclass
class ProjectStats:
    project_path: Path
    sizes: dict[str, SizeBreakdown]

    @property
    def total_folders(self) -> int:
        return sum(b.folders for b in self.sizes.values())

    @property
    def total_files(self) -> int:
        return sum(b.files for b in self.sizes.values())

    @property
    def total_bytes(self) -> int:
        return sum(b.bytes for b in self.sizes.values())


@dataclass(frozen=True)
class MeasureJob:
    project_path: str
    paths: tuple[tuple[str, str], ...]


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


def compute_summary_label_width(effective_targets: tuple[str, ...]) -> int:
    if not effective_targets:
        return len("scan:")
    return max(len(name) + 1 for name in effective_targets)


def no_projects_message(effective_targets: tuple[str, ...]) -> str:
    names = ", ".join(effective_targets)
    return (
        f"No projects found with pyproject.toml and any of: {names}."
    )


class ScanStats:
    def __init__(self, start_time: float) -> None:
        self._lock = threading.Lock()
        self._start_time = start_time
        self.folders_scanned = 0
        self.projects_found = 0
        self.measured_files = 0
        self.measured_bytes = 0
        self.entries_folders = 0
        self.entries_files = 0

    def add_folder(self) -> None:
        with self._lock:
            self.folders_scanned += 1

    def add_project(self) -> None:
        with self._lock:
            self.projects_found += 1

    def add_entries(self, folders: int, files: int) -> None:
        with self._lock:
            self.entries_folders += folders
            self.entries_files += files

    def add_measured(self, files: int, total_bytes: int) -> None:
        with self._lock:
            self.measured_files += files
            self.measured_bytes += total_bytes

    def elapsed_seconds(self) -> int:
        with self._lock:
            return int(time.monotonic() - self._start_time)

    def snapshot(self) -> tuple[int, int, int, int, int]:
        with self._lock:
            elapsed = int(time.monotonic() - self._start_time)
            return (
                self.folders_scanned,
                self.projects_found,
                self.measured_files,
                self.measured_bytes,
                elapsed,
            )


class ProgressDisplay:
    def __init__(self, stats: ScanStats) -> None:
        self._stats = stats
        self._stream = sys.stderr
        self._enabled = self._stream.isatty()
        self._lock = threading.Lock()
        self._last_update = 0.0

    def _terminal_width(self) -> int:
        try:
            width = shutil.get_terminal_size(fallback=(120, 24)).columns
        except OSError:
            width = 120
        return max(width, 1)

    def _fit_line(self, message: str) -> str:
        width = self._terminal_width()
        if len(message) <= width:
            return message
        if width <= 3:
            return message[:width]
        return "..." + message[-(width - 3) :]

    def _format_message(self) -> str:
        folders, projects, files, total_bytes, seconds = self._stats.snapshot()
        megabytes = total_bytes / (1024 * 1024)
        return (
            f"{folders:,} folders scanned in {seconds:,} seconds:    {projects:,} projects    "
            f"{files:,} files     {megabytes:,.2f} MB "
        )

    def maybe_refresh(self, *, force: bool = False) -> None:
        if not self._enabled:
            return

        now = time.monotonic()
        if not force and now - self._last_update < PROGRESS_INTERVAL:
            return

        with self._lock:
            if not force and now - self._last_update < PROGRESS_INTERVAL:
                return

            self._last_update = now
            width = self._terminal_width()
            text = self._fit_line(self._format_message())
            self._stream.write("\r" + text.ljust(width))
            self._stream.flush()

    def clear(self) -> None:
        if not self._enabled:
            return

        with self._lock:
            self._stream.write("\r" + " " * self._terminal_width() + "\r")
            self._stream.flush()


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


def _print_summary_row(
    label: str,
    col1: str,
    col2: str,
    col3: str,
    col4: str,
    *,
    label_width: int,
) -> None:
    w = SUMMARY_COL_WIDTH
    print(
        f"  {label:<{label_width}}"
        f"{col1:>{w}}{col2:>{w}}{col3:>{w}}{col4:>{w}}"
    )


def _print_summary_data_row(
    label: str,
    num_bytes: int,
    projects: int,
    files: int,
    folders: int,
    *,
    label_width: int,
) -> None:
    _print_summary_row(
        label,
        format_summary_size(num_bytes),
        f"{projects:,} projects",
        f"{files:,} files",
        f"{folders:,} folders",
        label_width=label_width,
    )


def _print_summary_scan_row(stats: ScanStats, *, label_width: int) -> None:
    entries = stats.entries_folders + stats.entries_files
    _print_summary_row(
        "scan:",
        f"{entries:,} entries",
        f"{stats.elapsed_seconds():,} seconds",
        f"{stats.entries_files:,} files",
        f"{stats.entries_folders:,} folders",
        label_width=label_width,
    )


def measure_directory(path: str, stats: ScanStats | None = None) -> SizeBreakdown:
    folders = 0
    files = 0
    total_bytes = 0
    stack = [path]

    while stack:
        dirpath = stack.pop()
        try:
            with os.scandir(dirpath) as entries:
                dir_entries = 0
                file_entries = 0
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            dir_entries += 1
                            folders += 1
                            stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            file_entries += 1
                            files += 1
                            total_bytes += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
                if stats is not None:
                    stats.add_entries(dir_entries, file_entries)
        except OSError:
            pass

    return SizeBreakdown(folders=folders, files=files, bytes=total_bytes)


def _scan_tree(
    root: str,
    work_queue: queue.Queue[MeasureJob | None],
    stats: ScanStats,
    progress: ProgressDisplay,
    *,
    measure_targets: frozenset[str],
    never_descend: frozenset[str],
) -> None:
    stack = [root]

    while stack:
        current = stack.pop()
        stats.add_folder()
        progress.maybe_refresh()

        has_pyproject = False
        found: dict[str, str] = {}
        subdirs: list[str] = []

        try:
            with os.scandir(current) as entries:
                dir_entries = 0
                file_entries = 0
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            dir_entries += 1
                            if entry.name in never_descend:
                                if entry.name in measure_targets:
                                    found[entry.name] = entry.path
                            else:
                                subdirs.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            file_entries += 1
                            if entry.name == "pyproject.toml":
                                has_pyproject = True
                    except OSError:
                        pass
                stats.add_entries(dir_entries, file_entries)
        except OSError:
            continue

        stack.extend(reversed(subdirs))

        if has_pyproject and found:
            stats.add_project()
            work_queue.put(
                MeasureJob(
                    project_path=current,
                    paths=tuple(found.items()),
                )
            )
            progress.maybe_refresh()


def _measure_worker(
    work_queue: queue.Queue[MeasureJob | None],
    result_queue: queue.Queue[ProjectStats],
    stats: ScanStats,
    progress: ProgressDisplay,
) -> None:
    while True:
        job = work_queue.get()
        try:
            if job is None:
                break

            sizes: dict[str, SizeBreakdown] = {}
            measured_files = 0
            measured_bytes = 0

            for name, path in job.paths:
                bd = measure_directory(path, stats)
                sizes[name] = bd
                measured_files += bd.files
                measured_bytes += bd.bytes

            stats.add_measured(measured_files, measured_bytes)
            progress.maybe_refresh()
            result_queue.put(
                ProjectStats(
                    project_path=Path(job.project_path),
                    sizes=sizes,
                )
            )
        finally:
            if job is not None:
                work_queue.task_done()


def find_projects(
    root: Path,
    *,
    measure_targets: frozenset[str],
    never_descend: frozenset[str],
) -> tuple[list[ProjectStats], ScanStats]:
    start_time = time.monotonic()
    stats = ScanStats(start_time)
    progress = ProgressDisplay(stats)
    work_queue: queue.Queue[MeasureJob | None] = queue.Queue(maxsize=WORK_QUEUE_SIZE)
    result_queue: queue.Queue[ProjectStats] = queue.Queue()

    try:
        with ThreadPoolExecutor(max_workers=MEASURE_WORKERS) as executor:
            for _ in range(MEASURE_WORKERS):
                executor.submit(
                    _measure_worker,
                    work_queue,
                    result_queue,
                    stats,
                    progress,
                )

            _scan_tree(
                str(root),
                work_queue,
                stats,
                progress,
                measure_targets=measure_targets,
                never_descend=never_descend,
            )

            work_queue.join()

            for _ in range(MEASURE_WORKERS):
                work_queue.put(None)

        results: list[ProjectStats] = []
        while True:
            try:
                results.append(result_queue.get_nowait())
            except queue.Empty:
                break
    finally:
        progress.maybe_refresh(force=True)
        progress.clear()

    return sorted(results, key=lambda item: str(item.project_path)), stats


def print_summary(
    projects: list[ProjectStats],
    *,
    stats: ScanStats,
    effective_targets: tuple[str, ...],
    summary_label_width: int,
) -> None:
    project_count = len(projects)

    print()
    print("Summary:")
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
        )

    total_files = sum(item.total_files for item in projects)
    total_folders = sum(item.total_folders for item in projects)
    total_bytes = sum(item.total_bytes for item in projects)
    _print_summary_data_row(
        "total:",
        total_bytes,
        project_count,
        total_files,
        total_folders,
        label_width=summary_label_width,
    )
    _print_summary_scan_row(stats, label_width=summary_label_width)


def _handle_remove_error(func, path, _exc_info) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_tree(path: Path) -> None:
    shutil.rmtree(path, onerror=_handle_remove_error)


def _delete_single_project(
    item: ProjectStats,
    *,
    delete_names: frozenset[str],
) -> None:
    for target in _removal_targets(item, delete_names):
        remove_tree(target)


def _parallel_delete_projects(
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
        label = _removal_label(item, delete_names)
        print(f"Removed {label}")

    return removed


def _removal_targets(
    item: ProjectStats,
    delete_names: frozenset[str],
) -> list[Path]:
    return [
        item.project_path / n
        for n in sorted(delete_names)
        if n in item.sizes
    ]


def _removal_label(item: ProjectStats, delete_names: frozenset[str]) -> str:
    names = sorted(n for n in delete_names if n in item.sizes)
    return f"{item.project_path} ({', '.join(names)})"


def prompt_for_removal(label: str) -> str:
    while True:
        response = input(f"Remove {label}? [y/n/a]: ").strip().lower()
        if response in {"y", "yes", "n", "no", "a", "all"}:
            return response
        print("Please enter y/yes, n/no, or a/all.")


def should_remove(response: str) -> bool:
    return response in {"y", "yes", "a", "all"}


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
            print(f"{item.project_path}  {format_size(item.total_bytes)}")
            for name in effective_targets:
                if name not in item.sizes:
                    continue
                bd = item.sizes[name]
                print(
                    f"  {name}: {format_size(bd.bytes)} "
                    f"({bd.files:,} files)"
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
            if not _removal_targets(item, delete_names):
                continue
            label = _removal_label(item, delete_names)
            print(f"Will remove {label}")
            processed.append(item)
        print_summary(
            processed,
            stats=stats,
            effective_targets=effective_targets,
            summary_label_width=summary_label_width,
        )
        return

    remove_all = skip_confirm
    batch: list[ProjectStats] = []

    for item in projects:
        targets = _removal_targets(item, delete_names)
        if not targets:
            continue

        label = _removal_label(item, delete_names)
        if not remove_all:
            response = prompt_for_removal(label)
            if response in {"a", "all"}:
                remove_all = True
                batch.append(item)
                continue
            if not should_remove(response):
                print(f"Skipped {item.project_path}")
                continue

            _delete_single_project(item, delete_names=delete_names)
            processed.append(item)
            print(f"Removed {label}")
            continue

        batch.append(item)

    if batch:
        processed.extend(
            _parallel_delete_projects(
                batch,
                delete_names=delete_names,
            )
        )

    print_summary(
        processed,
        stats=stats,
        effective_targets=effective_targets,
        summary_label_width=summary_label_width,
    )


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
    args = parse_args(argv)
    root = Path(args.path).resolve()

    include = flatten_append_args(args.include)
    exclude = flatten_append_args(args.exclude)

    for name in exclude:
        if name not in _DEFAULT_TARGET_SET:
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

    summary_label_width = compute_summary_label_width(effective_targets)
    measure_targets = frozenset(effective_targets)
    never_descend = _DEFAULT_TARGET_SET | frozenset(include)

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


if __name__ == "__main__":
    print("Py Remove Fat, v1.0.0, May 2026")
    raise SystemExit(main())
