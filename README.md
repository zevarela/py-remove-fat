# py-remove-fat

**py-remove-fat** helps you save precious disk space on Python projects you are not currently using. It scans a directory tree for folders that contain `pyproject.toml`, identifies **rebuildable** sibling directories next to that file, reports how much space they use, and lets you remove them safely—interactively or in bulk.

The main idea is simple: many Python projects carry large folders that are expensive to keep on disk but cheap to recreate when you need the project again. Virtual environments are the usual offender—**`.venv` folders can grow to hundreds of megabytes or even gigabytes each**, and they add up fast when you have dozens of repos checked out. Those environments are fully rebuildable. Tools like [uv](https://docs.astral.sh/uv/) can recreate a `.venv` in seconds from the dependency information in `pyproject.toml` (and lockfiles when present):

```powershell
cd path\to\project
uv sync
```

The tool also measures other regenerable artifacts—`__pycache__`, build output, wheels, Jupyter checkpoints, and more—so you can see where space is going before deleting anything.

## Features

- **Recursive scan** — Walks a directory tree without descending into default-named heavy directories listed under [Default targets](#default-targets) (plus `--include` names); those directories are skipped for traversal whether or not they are measured this run
- **Project discovery** — Treats a directory as a **project root** when it contains `pyproject.toml` and **any** sibling directory whose name is in this run's **effective targets**
- **Configurable targets** — Default list plus repeatable `--include` / `--exclude` (comma-separated or repeated flags)
- **Congruent names** — Summary column labels match folder names on disk (`name:`); `--del` takes the exact same strings (without the trailing colon)
- **Dynamic summary layout** — The first summary column expands to fit the longest target label
- **Live progress** — Updates running totals every 2 seconds while scanning and measuring
- **Parallel measurement** — Bounded thread pool so scanning and sizing run concurrently
- **Parallel batch deletion** — With `--yes` or `a`/`all`, removes multiple projects concurrently (4 workers)
- **Interactive cleanup** — Confirm removal per project, or skip prompts with `--yes`
- **Dry run** — `--print-only` with `--del` or `--del-all` lists `Will remove ...` lines without deleting or prompting

## Default targets

These directory names are measured next to `pyproject.toml` by default (unless `--exclude` drops them):

| Folder name | Notes |
|-------------|--------|
| `.venv` | Virtual environment (often very large; rebuild with `uv sync` or your usual workflow) |
| `__pycache__` | Python bytecode cache |
| `.ipynb_checkpoints` | Jupyter checkpoints |
| `build` | Typical build output |
| `dist` | Typical distribution output |
| `wheels` | Wheel output directory when used at project root |

Use `--include` to measure additional sibling folders (for example `.git`, `data`, `node_modules`). Default-named directories are **never entered** during the scan (for performance), even if you `--exclude` them from measurement for this run.

## Requirements

- Python 3.14 or later
- No third-party dependencies

## Installation

Clone or copy this repository, then run the script directly:

```powershell
git clone https://github.com/zevarela/py-remove-fat.git
cd py-remove-fat
python py-remove-fat.py
```

Or run it with [uv](https://docs.astral.sh/uv/):

```powershell
uv run py-remove-fat.py
```

## Usage

```text
python py-remove-fat.py [path]
  [--list] [--yes]
  [--include names] [--exclude names]
  [--del names | --del-all] [--print-only]
```

Without `--del` or `--del-all`, the tool scans and reports only.

### Arguments

| Argument | Description |
|----------|-------------|
| `path` | Root directory to scan recursively. Defaults to the current directory (`.`) |

### Options

| Option | Description |
|--------|-------------|
| `--list` | List each project path and per-target sizes before the summary |
| `--include names` | Comma-separated extra target folder names; flag may be repeated |
| `--exclude names` | Comma-separated names removed from defaults only (`--exclude` must name default targets); flag may be repeated |
| `--del names` | Comma-separated folder names to remove (must exactly match disk names / summary labels minus `:`) |
| `--del-all` | Remove every effective target that exists under each project |
| `--print-only` | With `--del` or `--del-all`: print planned removals only (`Will remove …`); does not prompt or delete |
| `--yes` | Skip interactive removal confirmations when deleting (not used with `--print-only`) |
| `-h`, `--help` | Show help and exit |

`--del` and `--del-all` are mutually exclusive. `--print-only` requires `--del` or `--del-all`.

### Target resolution

Effective targets this run:

1. All default targets not listed in `--exclude` (combined from all `--exclude` usages), preserving default order
2. Then each `--include` entry (combined from all `--include` usages) that was not already present

## Examples

### Scan the current directory

```powershell
python py-remove-fat.py
```

With `--list`, each project is shown before the summary:

```powershell
python py-remove-fat.py --list
```

### Scan a tree and include extra folders

Recursively scan `C:\Src` for Python projects (directories containing `pyproject.toml`). Default targets are included, plus these additional sibling folders when present: `data`, `.git`, `notebooks`, `assets`, and `docs`.

```powershell
uv run py-remove-fat.py C:\Src --include data,.git,notebooks,assets,docs
```

Results:

```text
Py Remove Fat, v1.0.0, May 2026

Summary:
  .venv:                            9.51 Gb           27 projects         312,451 files        35,384 folders
  __pycache__:                    577.30 Kb           15 projects              38 files             0 folders
  .ipynb_checkpoints:             103.21 Kb            3 projects               6 files             0 folders
  build:                                0 b            0 projects               0 files             0 folders
  dist:                             8.58 Mb            8 projects              17 files             0 folders
  wheels:                               0 b            0 projects               0 files             0 folders
  data:                           539.31 Mb           21 projects             191 files            50 folders
  .git:                           342.08 Mb           40 projects           4,197 files         1,891 folders
  notebooks:                        9.96 Mb            5 projects             130 files            18 folders
  assets:                           5.22 Mb            6 projects              13 files             7 folders
  docs:                            26.63 Mb           13 projects             150 files            16 folders
  total:                           10.42 Gb           74 projects         317,193 files        37,366 folders
  scan:                     445,333 entries             5 seconds         392,234 files        53,099 folders
```

### Omit measuring defaults

```powershell
python py-remove-fat.py --exclude .venv,build,dist,wheels C:\Src
```

### Dry run: show what would be removed

```powershell
python py-remove-fat.py --del .venv --print-only C:\Src
python py-remove-fat.py --exclude build,dist,wheels --del-all --print-only C:\Src
```

Results:

```text
Will remove C:\Src\proj (.venv)
...
```

### Remove specific targets

```powershell
python py-remove-fat.py --del .venv,__pycache__ C:\Src
```

### Remove everything found (effective targets) without prompts

```powershell
python py-remove-fat.py --del-all --yes C:\Src
```

### Interactive removal prompt

When not using `--yes` or `--print-only`, confirm each path:

```text
Remove D:\Src\my-project (.venv, dist)? [y/n/a]:
```

| Response | Action |
|----------|--------|
| `y`, `yes` | Remove the listed targets for this project |
| `n`, `no` | Skip this project |
| `a`, `all` | Remove this project and all remaining ones in parallel without further prompts |

## How it works

1. The tool recursively walks the given root using `os.scandir`.
2. If a directory entry has a name in the **default target set** or in `--include`, the walker records it as a measurement candidate when it is a direct child of a directory that also contains `pyproject.toml`, and it **does not descend** into that directory.
3. A **project root** is a directory with `pyproject.toml` and at least one present effective target directory as a sibling.
4. Each target tree is measured with the same iterative directory walk; measurement can run in parallel across projects.

Deletion uses `shutil.rmtree` with a Windows-friendly handler for read-only files.

## Notes

- Use only on paths you own and understand.
- **Permanent deletion** — Recreate environments and build outputs with your usual tools when needed. For `.venv`, run `uv sync` (or equivalent) in the project directory.
- Use **`--print-only`** and carefully **review all output** before deleting anything. Folders added with `--include` (such as `.git` or `data`) are not rebuildable the same way a virtual environment is.

## License

You are free to use, modify, and distribute this tool as you see fit.
Attribution is appreciated but not required.
This tool is provided "as is" without any warranty.
