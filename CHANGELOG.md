# Changelog

All notable changes to this project are documented in this file.

## v1.1.0 — May 2026

- 8x increase in perceived speed of the scan (due to increased output frequency of live progress counts). Now it feels even faster.
- Improved summary information with colored terminal output and project counts
- Delete/dry-run summary: full-scan rows retained, plus **Removed Targets** and **Remove Stats**
- Code refactoring into the `py_remove_fat/` package with ≥80% pytest coverage enforced
- Version and banner release label read from `pyproject.toml` only
- Python 3.12+ support; CI on Ubuntu and Windows
- Tidy up of README.md project landing page, including a banner image, CHANGELOG.md and LICENSE files
- Contributing guide, issue templates, and security policy

## v1.0.0 — May 2026

- Initial release: scan, report, and remove rebuildable folders next to `pyproject.toml`
