"""Directory scanning, measurement, and progress reporting."""

from __future__ import annotations

import os
import queue
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from py_remove_fat.config import MEASURE_WORKERS, PROGRESS_INTERVAL, WORK_QUEUE_SIZE
from py_remove_fat.models import MeasureJob, ProjectStats, SizeBreakdown


class ScanStats:
    def __init__(self, start_time: float) -> None:
        self._lock = threading.Lock()
        self._start_time = start_time
        self.folders_scanned = 0
        self.pyprojects_seen = 0
        self.projects_found = 0
        self.measured_files = 0
        self.measured_bytes = 0
        self.entries_folders = 0
        self.entries_files = 0

    def add_folder(self) -> None:
        with self._lock:
            self.folders_scanned += 1

    def add_pyproject_seen(self) -> None:
        with self._lock:
            self.pyprojects_seen += 1

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

    def snapshot(self) -> tuple[int, int, int, int, int, int]:
        with self._lock:
            elapsed = int(time.monotonic() - self._start_time)
            return (
                self.folders_scanned,
                self.pyprojects_seen,
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
        folders, pyprojects, projects, files, total_bytes, seconds = (
            self._stats.snapshot()
        )
        megabytes = total_bytes / (1024 * 1024)
        return (
            f"{folders:,} folders scanned in {seconds:,} seconds:    "
            f"{pyprojects:,} pyprojects, {projects:,} with targets    "
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

        if has_pyproject:
            stats.add_pyproject_seen()
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
