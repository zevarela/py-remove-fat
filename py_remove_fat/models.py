"""Data classes for scan measurements and project aggregates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
