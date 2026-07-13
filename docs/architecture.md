# Architecture

PyTransformer is intentionally small: each command is a thin command-line wrapper around focused implementation functions, with shared behavior kept in `pytransformer.core`.

## Package Layout

```text
src/pytransformer/
  __init__.py
  py.typed
  cli/
    *_*.py
  core/
    audio.py
    common.py
    jpeg_metadata.py
```

## Command Modules

Each file in `pytransformer.cli` is importable as a normal Python module and executable as an installed console script.

The command modules own:

- Argument parsing.
- User-facing summaries.
- Exit codes.
- Command-specific orchestration.

They should avoid doing substantial work at import time so `--help`, tests, and packaging checks keep working without optional runtime dependencies installed. The [command guide](commands.md) is the source of truth for user-facing command behavior; [CONTRIBUTING.md](../CONTRIBUTING.md) owns contributor-facing naming, parser, and validation standards.

## Core Modules

Shared helpers live in `pytransformer.core`.

- `common.py` handles path validation, output guards, deterministic directory ordering, logging, and confirmation prompts.
- `audio.py` handles MP4 audio extraction and speech recognition helpers.
- `jpeg_metadata.py` handles JPEG metadata inspection shared by the show and strip commands.

Core modules should stay small and boring. Add shared code there when it prevents command behavior from drifting or removes real duplication.

## Optional Dependencies

The base package has no runtime dependencies. PDF, JPEG, MP4, and OCR support are exposed as optional extras in `pyproject.toml`.

Optional imports should be lazy or guarded so:

- Standard-library commands work after a base install.
- Every command can display `--help`.
- Missing optional packages produce direct installation guidance.
- `make type-check` can validate the package without installing every optional runtime dependency.

## Documentation Build

Markdown files remain the documentation source of truth. `scripts/build_docs.py` converts `README.md` and project documentation into static HTML under `docs/html/`, and it splits the command sections in `docs/commands.md` into one generated page per console command.

Use `make docs` for a one-time rebuild, `make docs-check` to verify generated HTML and documentation links, and `make docs-watch` while editing markdown. The [README](../README.md) is the first-time-user entry point; [CONTRIBUTING.md](../CONTRIBUTING.md), [privacy.md](privacy.md), and this page cover project operations, data handling, and implementation structure.

Keep the docs workflow single-source. If the generator changes, update the Makefile, CI, GitHub Pages workflow, project instructions, README guidance, and generated HTML together so future contributors are not left choosing between competing builders.

## Safety Model

Commands should default to conservative file behavior:

- Validate input paths before processing.
- Skip symlinks in batch operations.
- Avoid recursion unless documented.
- Avoid overwriting outputs unless `--overwrite` is passed.
- Require confirmation or `--dry-run` for bulk renaming.
- Keep generated artifacts separate from source files when practical.

The [command guide](commands.md) documents command-specific exceptions and output behavior. Contributor rules for introducing or changing these safeguards belong in [CONTRIBUTING.md](../CONTRIBUTING.md).
