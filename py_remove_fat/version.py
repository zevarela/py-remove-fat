"""Package metadata read from pyproject.toml (single source of truth)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import tomllib

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
_TOOL_TABLE = "py-remove-fat"


@lru_cache(maxsize=1)
def _load_pyproject() -> dict:
    with _PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def read_version() -> str:
    return _load_pyproject()["project"]["version"]


def read_release_label() -> str:
    tool = _load_pyproject().get("tool", {}).get(_TOOL_TABLE, {})
    label = tool.get("release-label")
    if not label or not str(label).strip():
        raise ValueError(
            f"Missing [tool.{_TOOL_TABLE}] release-label in pyproject.toml"
        )
    return str(label).strip()


__version__: str = read_version()
__release_label__: str = read_release_label()
