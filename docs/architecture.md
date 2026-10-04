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

Use `make docs` for a one-time rebuild, `make docs-check` to verify generated HTML and documentation links, and `make docs-watch` while editing Markdown. Watch mode tracks root Markdown files and Markdown under `docs/`, including additions and removals. Generated HTML is excluded from watch inputs.

Register each new documentation page in `MARKDOWN_PAGES` in `scripts/build_docs.py`, including its source path, output filename, title, and navigation label. The same registry controls rendering, Markdown-to-HTML links, and navigation. Watching an unregistered source does not add a rendered page. [The ownership map](knowledge.md) identifies the authoritative topic owners. [Operations](operations.md) owns deployment and cleanup.

Keep the docs workflow single-source. If the generator changes, update the Makefile, CI, GitHub Pages workflow, project instructions, README guidance, and generated HTML together so future contributors are not left choosing between competing builders.

## Safety Model

The [product requirements](requirements.md#file-safety) own shared safety behavior. The [command guide](commands.md) owns command-specific exceptions and output behavior. [CONTRIBUTING.md](../CONTRIBUTING.md) owns the validation expectations for safeguard changes.

## Output Finalization

`pytransformer.core.common.temporary_output_path` owns shared staged output handling. On macOS, or when the destination is a detected Apple File Provider path, it stages outside the destination and copies the completed data into the visible final filename, flushes it, and calls `fsync`. On other paths it uses temporary sibling output and final replacement.

The copy helper backs up an existing output before copying and attempts restoration on failure. Newly created partial output is removed on failure. This copy path does not provide atomic replacement to concurrent readers. Use the helper rather than reimplementing filesystem finalization in each command. The [decision log](lessons-learned.md#finder-visible-output) owns the reason for the macOS behavior and its tradeoff.
