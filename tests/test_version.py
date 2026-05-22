"""Tests for version loading from pyproject.toml."""

from __future__ import annotations

import re
from pathlib import Path

import tomllib

from py_remove_fat import __version__
from py_remove_fat.config import BANNER
from py_remove_fat.version import read_release_label, read_version


def test_version_matches_pyproject() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    expected_version = data["project"]["version"]
    expected_label = data["tool"]["py-remove-fat"]["release-label"]

    assert __version__ == expected_version
    assert read_version() == expected_version
    assert read_release_label() == expected_label
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
    assert BANNER == f"Py Remove Fat, v{expected_version}, {expected_label}"
