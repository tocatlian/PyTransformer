# Contributing to PyTransformer

PyTransformer is a Python package with a focused command-line surface. Changes should preserve the package structure, keep command behavior safe by default, and remain easy for another engineer to validate.

## Development Setup

Use Python 3.10 or newer.

From a local checkout:

```bash
python3 -m pip install -e ".[dev]"
```

Install optional runtime dependencies only for the commands you need to exercise manually:

```bash
python3 -m pip install -e ".[all]"
```

Some commands also require system tools:

- MP4 commands require FFmpeg through MoviePy.
- OCR fallback requires a system Tesseract installation in addition to `pytesseract`.

## Project Layout

```text
src/pytransformer/
  cli/      Command entry point modules.
  core/     Shared implementation helpers.
tests/      Standard-library unit tests.
```

## Naming Standards

- Package and module names use lowercase `snake_case`.
- CLI modules live in `src/pytransformer/cli/`.
- CLI module names use `pyt_domain_verb_object[_batch]`; for example, `pyt_jpeg_strip_metadata.py` and `pyt_pdf_extract_selectable_text_batch.py`.
- Shared helpers live in `src/pytransformer/core/`.
- Installed console commands use the hyphenated module name; for example, `pyt-jpeg-strip-metadata`.
- Documentation refers to the project as **PyTransformer**.

## Script Standards

- Every CLI module should expose a `main() -> int` entry point.
- Every CLI module should expose `build_parser() -> argparse.ArgumentParser`.
- Every CLI module should be wired in `[project.scripts]` in `pyproject.toml`.
- Every CLI module should expose `--help`.
- Every command help screen should describe the command, document arguments, and include an `Examples:` section with installed command invocations.
- Every CLI module should include the standard header fields used by the existing modules.
- Prefer `argparse`, `pathlib`, explicit validation, clear exit statuses, and deterministic directory ordering.
- Use `-o`/`--output` for commands that write one file, `-o`/`--output-folder` for commands that write into a folder, and `--quiet` for reduced terminal logging.
- Batch folder commands should skip hidden dotfiles by default and expose `--include-hidden` when hidden files can be included.
- Default behavior should avoid overwriting files or performing destructive actions without clear confirmation.
- Batch commands should skip symlinks unless there is a documented reason not to.
- Shared behavior belongs in `pytransformer.core` when it removes meaningful duplication.

## Validation Expectations

Before sharing changes, run:

```bash
make validate
make lint
make format-check
make type-check
make coverage
make hooks
make smoke
make clean
```

`make validate` also verifies installed console entry points and package build metadata, so run it from an environment where `python3 -m pip install -e ".[dev]"` has already completed.

To install local pre-commit hooks:

```bash
python3 -m pre_commit install
```

If optional dependencies are installed, also run the relevant media/PDF/JPEG command manually against a small fixture and confirm the output is correct.

## Release Checklist

Before uploading the repository publicly, tagging a release, or opening a release pull request, run:

```bash
python3 -m pip install -e ".[dev]"
make validate
make coverage
make hooks
make smoke
make clean
```

`make validate` checks compilation, Ruff linting and formatting, mypy, pre-commit configuration, module-level `--help`, installed console entry points, unit tests, coverage, package build artifacts, and package metadata.

Run `make hooks` from inside a git checkout. If optional dependencies and system tools are available, also test the affected PDF, JPEG, MP4, and OCR commands against small synthetic or sanitized fixtures.

Before publishing, confirm:

- `README.md`, `docs/commands.md`, `docs/privacy.md`, `docs/architecture.md`, `CHANGELOG.md`, `SECURITY.md`, and `SUPPORT.md` match the release.
- `LICENSE` and source SPDX headers use the correct license and copyright range.
- Every command module remains executable.
- `.gitignore` covers generated media, logs, caches, and packaging artifacts.
- Issue templates, the pull request template, Dependabot configuration, and CI workflow are present.
- No private PDFs, media files, transcripts, logs, local paths, or JPEG metadata are included.

## Adding a New Command

1. Add a module under `src/pytransformer/cli/<domain>_<action>.py`.
2. Add a `main() -> int` entry point.
3. Add the command to `[project.scripts]` in `pyproject.toml`.
4. Add argparse options with safe defaults.
5. Add a README row with module name, console command, purpose, example, write behavior, and dependencies.
6. Update README and docs when behavior, privacy, dependencies, or command usage changes.
7. Add tests for logic that can run without optional external services.
8. Run `make validate`.
