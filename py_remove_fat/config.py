"""Shared constants and default target configuration."""

from __future__ import annotations

MEASURE_WORKERS = 4
DELETE_WORKERS = 4
WORK_QUEUE_SIZE = MEASURE_WORKERS * 2
PROGRESS_INTERVAL = 0.25
SUMMARY_COL_WIDTH = 22
SUMMARY_TOTAL_LABEL = "All Targets:"
SUMMARY_REMOVED_LABEL = "Removed Targets:"
SUMMARY_SCAN_LABEL = "Scan Stats:"
SUMMARY_REMOVE_STATS_LABEL = "Remove Stats:"

DEFAULT_TARGETS: tuple[str, ...] = (
    ".venv",
    "__pycache__",
    ".ipynb_checkpoints",
    "build",
    "dist",
    "wheels",
)
DEFAULT_TARGET_SET: frozenset[str] = frozenset(DEFAULT_TARGETS)

from py_remove_fat.version import __release_label__, __version__

BANNER = f"Py Remove Fat, v{__version__}, {__release_label__}"
