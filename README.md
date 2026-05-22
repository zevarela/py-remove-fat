# py-remove-fat

[![py-remove-fat hero image](https://raw.githubusercontent.com/zevarela/py-remove-fat/refs/heads/main/py-remove-fat.png)](https://github.com/zevarela/py-remove-fat/blob/main/py-remove-fat.png)

**py-remove-fat** helps you save disk space on Python projects you are not actively using. It quickly scans for `pyproject.toml`, measures **rebuildable** sibling folders (`.venv`, caches, build output, …), and lets you remove them safely—interactively or in bulk.

**Quick start**

```powershell
uv run py-remove-fat.py C:\Src                          # scan and summarize
uv run py-remove-fat.py C:\Src --del .venv --print-only # no deletes, print what would be deleted
uv run py-remove-fat.py C:\Src --del .venv              # delete with confirmation (--yes to skip)
```

Works on Windows, Linux, and macOS. Requires **Python 3.12+** (stdlib only). This repo uses **[uv](https://docs.astral.sh/uv/)** to install and run—no `pip install` path is documented on purpose.

Virtual environments are the usual offender—`**.venv` folders can grow to hundreds of megabytes or gigabytes** across many repos. They are fully rebuildable; [uv](https://docs.astral.sh/uv/) can recreate one in seconds:

```powershell
cd path\to\project
uv sync
```

The tool also measures `__pycache__`, build output, wheels, Jupyter checkpoints, and more—so you can see where space goes before deleting anything.

## Features

- **Fast recursive scan** — Skips heavy default target dirs during traversal (see [Default targets](#default-targets))
- **Project discovery** — Finds dirs with `pyproject.toml` plus at least one effective target sibling
- **Configurable targets** — `--include` / `--exclude` (comma-separated, repeatable)
- **Colored summary** — Per-column highlights when the terminal supports it (`NO_COLOR` respected)
- **Live progress** — Running totals on stderr while scanning
- **Parallel measure & delete** — Thread pools for sizing and batch removal
- **Dry run** — `--print-only` lists `Will remove …` without deleting
- **Interactive or batch delete** — Per-project prompts, `--yes`, or `a`/`all`

## Default targets

Measured next to `pyproject.toml` by default (unless `--exclude` drops them):


| Folder name          | Notes                                                               |
| -------------------- | ------------------------------------------------------------------- |
| `.venv`              | Virtual environment (rebuild with `uv sync` or your usual workflow) |
| `__pycache__`        | Python bytecode cache                                               |
| `.ipynb_checkpoints` | Jupyter checkpoints                                                 |
| `build`              | Typical build output                                                |
| `dist`               | Typical distribution output                                         |
| `wheels`             | Wheel output when used at project root                              |


Use `--include` for extra siblings (e.g. `.git`, `data`, `node_modules`). Default-named dirs are **never descended into** during the scan (performance), even if excluded from measurement.

## Installation

```powershell
git clone https://github.com/zevarela/py-remove-fat.git
cd py-remove-fat
uv sync
uv run py-remove-fat.py
```

After `uv sync`, you can also run the installed entry point:

```powershell
uv run py-remove-fat --help
```

## Usage

```text
uv run py-remove-fat.py [path]
  [--list] [--yes]
  [--include names] [--exclude names]
  [--del names | --del-all] [--print-only]
```

Without `--del` or `--del-all`, the tool scans and reports only.


| Argument / option | Description                                              |
| ----------------- | -------------------------------------------------------- |
| `path`            | Root to scan (default: `.`)                              |
| `--list`          | List each project before the summary                     |
| `--include names` | Extra target folder names (repeatable); see note below   |
| `--exclude names` | Remove names from defaults only (repeatable)             |
| `--del names`     | Remove listed folders (match summary labels without `:`) |
| `--del-all`       | Remove all effective targets found per project           |
| `--print-only`    | With `--del` / `--del-all`: show plan only               |
| `--yes`           | Skip removal prompts                                     |
| `-h`, `--help`    | Help                                                     |


`--del` and `--del-all` are mutually exclusive. `--print-only` requires `--del` or `--del-all`.

**Effective targets:** defaults minus `--exclude`, then plus `--include` (deduplicated, order preserved).

> **Warning:** Deletion is permanent. Always run with `--print-only` first. `--include` targets like `.git` or `data` are not rebuildable like `.venv`.

> **`--include` and discovery:** Names you `--include` are treated like default targets for traversal—they are **not descended into** during the scan. That keeps large trees fast, but it also means any `pyproject.toml` **inside** those folders (e.g. under `data/` or `node_modules/`) will **not** be discovered. This is intentional.

## Examples

### Scan

```powershell
uv run py-remove-fat.py
uv run py-remove-fat.py --list C:\Src
```

### Include extra folders

```powershell
uv run py-remove-fat.py C:\Src --include data,.git,notebooks,assets,docs
```

Sample output:

```text
Py Remove Fat, v1.1.0, May 2026

Summary:
  .venv:                            9.52 Gb           27 projects         313,202 files        35,441 folders
  __pycache__:                    577.30 Kb           15 projects              38 files             0 folders
  .ipynb_checkpoints:             103.21 Kb            3 projects               6 files             0 folders
  build:                                0 b            0 projects               0 files             0 folders
  dist:                             8.58 Mb            8 projects              17 files             0 folders
  wheels:                               0 b            0 projects               0 files             0 folders
  All Targets:                      9.53 Gb           41 projects         313,263 files        35,441 folders
  Scan Stats:                     3 seconds          101 projects         420,200 files        64,626 folders
```

### Dry run and delete

```powershell
uv run py-remove-fat.py --del .venv --print-only C:\Src
uv run py-remove-fat.py --del .venv,__pycache__ --yes C:\Src
uv run py-remove-fat.py --del-all --yes C:\Src
```

After a real delete, the summary keeps **full-scan** per-target and **All Targets** rows, adds **Removed Targets** for what was removed, and uses **Remove Stats** instead of **Scan Stats**. With `--print-only`, the summary matches a normal scan (no **Removed Targets** row).

```text
Summary:
  .venv:                            9.52 Gb           27 projects         …
  …
  All Targets:                      9.53 Gb           41 projects         …
  Removed Targets:                  1.20 Gb            5 projects         …
  Remove Stats:                     3 seconds          101 projects         …
```

Interactive prompt (without `--yes`):

```text
Remove D:\Src\my-project (.venv, dist)? [y/n/a]:
```


| Response   | Action                                                |
| ---------- | ----------------------------------------------------- |
| `y`, `yes` | Remove targets for this project                       |
| `n`, `no`  | Skip                                                  |
| `a`, `all` | Remove this and all remaining without further prompts |


## Development

Source: `py_remove_fat/` package; `py-remove-fat.py` is a thin launcher.

```powershell
uv sync --dev
uv run pytest
```

CI runs `uv run pytest` on Ubuntu and Windows (Python 3.12.12) for every push/PR to `main`.

## Community

| | |
| --- | --- |
| Bugs, ideas, enhancements | [GitHub Issues](https://github.com/zevarela/py-remove-fat/issues) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Maintainer | [LinkedIn](https://www.linkedin.com/in/zevarela/) |

## How it works

1. Recursively walks the root with `os.scandir`.
2. Records target siblings next to `pyproject.toml` and does not descend into them.
3. A **project** has `pyproject.toml` and at least one present effective target.
4. Target trees are measured in parallel; deletion uses `shutil.rmtree` (Windows read-only friendly).

## License

MIT — see [LICENSE](LICENSE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).