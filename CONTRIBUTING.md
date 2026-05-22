# Contributing

Thank you for your interest in **py-remove-fat**. This project is intentionally small and uses [uv](https://docs.astral.sh/uv/) for development and running.

## Getting started

```powershell
git clone https://github.com/zevarela/py-remove-fat.git
cd py-remove-fat
uv sync --dev
uv run pytest
```

Requires **Python 3.12+** (see `.python-version` for the pinned version used locally).

## Versioning

Release metadata lives in [`pyproject.toml`](pyproject.toml) only:

- `[project].version` — semver for the release
- `[tool.py-remove-fat].release-label` — month/year shown in the CLI banner (e.g. `May 2026`)

Update **both** when cutting a release. At runtime, `py_remove_fat.version` reads them via `tomllib`.

## Pull requests

1. Open an issue for larger changes (optional for tiny fixes).
2. Branch from `main`, keep diffs focused.
3. Run `uv run pytest` (coverage must stay ≥ 80%).
4. Update [`CHANGELOG.md`](CHANGELOG.md) for user-visible changes.

## CI

GitHub Actions runs `uv run pytest` on **Ubuntu and Windows** with Python **3.12.12**. Linux catches most logic regressions; Windows exercises platform-specific delete and terminal-color paths. macOS is not in CI but the tool is stdlib-only and expected to work there.

## Contact

| Purpose | Channel |
| -------- | -------- |
| Bugs, ideas, feature requests | [GitHub Issues](https://github.com/zevarela/py-remove-fat/issues) |
| Direct contact | [LinkedIn — zevere](https://www.linkedin.com/in/zevarela/) |

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
