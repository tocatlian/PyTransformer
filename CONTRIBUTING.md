# Contributing to PyTransformer

PyTransformer is a Python package with a focused command-line surface. Changes should preserve the package structure, keep command behavior safe by default, and remain easy for another engineer to validate.

Use the [README](README.md) for the first-time-user path, the [command guide](docs/commands.md) for current command behavior, the [privacy guide](docs/privacy.md) for data handling, and the [architecture guide](docs/architecture.md) for implementation structure.

## GitHub Workflow

The `main` branch is protected. For every change:

1. Create a focused `codex/<description>` branch from `main`.
2. Commit only the intended source, test, and documentation changes.
3. Push the branch and open a pull request targeting `main`.
4. Wait for all required Python CI checks to pass.
5. Squash-merge the pull request. Merged branches are deleted automatically.

Do not push directly to `main`. Keep generated files, local fixtures, and unrelated working-tree changes out of pull requests.

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

Before sharing changes, install the development extra and run the CI-equivalent gate:

```bash
python3 -m pip install -e ".[dev]"
make validate
```

`make validate` covers compilation, linting, formatting, type checks, hook configuration, generated documentation and links, command help, installed entry points, unit tests, repository-wide coverage, and package metadata.

Run `make smoke-pdf`, `make smoke-jpeg`, or `make smoke-m4a` when the change affects that optional domain. They require the matching extras or system tools; use generated fixtures rather than private files.

To install local pre-commit hooks:

```bash
python3 -m pre_commit install
```

If optional dependencies are installed, also run the relevant media/PDF/JPEG command manually against a small fixture and confirm the output is correct.

For isolated local checks that mirror CI-style environments, run:

```bash
python3 -m tox
python3 -m tox -e smoke-pdf,smoke-jpeg
```

The optional smoke environments install the matching package extras and use generated fixtures, so they are useful before changing PDF or JPEG command behavior.

## Release Checklist

Start with the [validation expectations](#validation-expectations) and complete the optional smoke checks for the affected domains. Before tagging or publishing, confirm:

- The [README](README.md), [command guide](docs/commands.md), [privacy guide](docs/privacy.md), [architecture guide](docs/architecture.md), [CHANGELOG.md](CHANGELOG.md), [SECURITY.md](SECURITY.md), and [SUPPORT.md](SUPPORT.md) match the release.
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
5. Add the command's behavior, examples, outputs, dependencies, and privacy implications to the [command guide](docs/commands.md) and the relevant supporting docs.
6. Update the README only when the user-facing overview or command category links need to change.
7. Add tests for logic that can run without optional external services.
8. Run `make docs`, then `make validate`.
