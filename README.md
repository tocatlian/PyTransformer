# PyTransformer

[![CI](https://github.com/tocatlian/PyTransformer/actions/workflows/ci.yml/badge.svg)](https://github.com/tocatlian/PyTransformer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/tocatlian/PyTransformer/blob/main/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://github.com/tocatlian/PyTransformer/blob/main/pyproject.toml)

PyTransformer is a Python package of command-line utilities for transforming PDFs, M4A and MP4 media, JPEG metadata, filenames, and plain-text files.

The project follows a standard Python `src/` layout. Internal modules use lowercase `snake_case` names so they are importable, and installed terminal commands use short hyphenated `pyt-*` names.

## Installation

From a local checkout:

```bash
python3 -m pip install -e .
```

For development:

```bash
python3 -m pip install -e ".[dev]"
```

## Quick Start

After installing from a checkout, confirm the command inventory:

```bash
pyt-help --verbose
```

Try a command that uses only the Python standard library:

```bash
mkdir -p /tmp/pytransformer-demo/texts
printf 'alpha\n' > /tmp/pytransformer-demo/texts/a.txt
printf 'beta\n' > /tmp/pytransformer-demo/texts/b.txt
pyt-text-concatenate --output /tmp/pytransformer-demo/combined.txt /tmp/pytransformer-demo/texts
cat /tmp/pytransformer-demo/combined.txt
```

## Dependency Groups

The base install has no runtime dependencies and supports these standard-library commands:

- `pyt-files-append-folder-name`
- `pyt-image-variants-count`
- `pyt-text-concatenate`

Install optional dependency groups only for the commands you need:

```bash
python3 -m pip install -e ".[pdf]"
python3 -m pip install -e ".[jpeg]"
python3 -m pip install -e ".[mp4]"
python3 -m pip install -e ".[ocr]"
python3 -m pip install -e ".[all]"
```

- `.[pdf]` installs `pymupdf` and `pypdf` for PDF extraction and rendering commands.
- `.[jpeg]` installs `pillow` and `defusedxml` for JPEG metadata commands.
- `.[mp4]` installs `moviepy` and `SpeechRecognition`; MP4 commands also require FFmpeg, and transcription uses network access.
- `pyt-m4a-to-mp3` uses a system FFmpeg installation to convert M4A audio to sibling MP3 files; it does not require an additional Python dependency group.
- `.[ocr]` installs `pytesseract`; OCR fallback also requires a system Tesseract installation.
- `.[all]` installs every optional runtime dependency group.
- `.[dev]` installs build, coverage, type-checking, linting, pre-commit, tox, and package-checking tools.

## Validation

After installing the development extra, run the CI-equivalent validation gate:

```bash
make validate
```

`make validate` compiles the package and tests, checks formatting and types, verifies generated documentation and installed commands, runs the unit tests and repository-wide coverage gate, and checks package build metadata.

The optional PDF, JPEG, and M4A smoke checks require their matching extras or system tools. See the [validation expectations](CONTRIBUTING.md#validation-expectations) for the complete local and release checklist.

For local CI-style isolation, use `python3 -m tox` after installing the development extra.

## Naming Standard

CLI modules usually use `pyt_<family>_<object>_<action>[_mode]` names. The installed command is the same name with underscores changed to hyphens. The inventory command `pyt_help.py` uses the shorter `pyt-help` name.

Python modules:

```text
src/pytransformer/cli/pyt_pdf_extract_text.py
src/pytransformer/cli/pyt_jpeg_strip_metadata.py
src/pytransformer/cli/pyt_image_split.py
src/pytransformer/core/common.py
```

Installed console commands:

```text
pyt-help
pyt-pdf-extract-text
pyt-jpeg-strip-metadata
pyt-image-split
pyt-mp4-transcribe-batch
```

This gives engineers importable Python modules and gives command-line users idiomatic shell command names.

## Command Reference

The [command guide](docs/commands.md) is the authoritative reference for arguments, examples, outputs, dependencies, and safety behavior.

- [Discovery commands](docs/commands.md#discovery-command)
- [Image commands](docs/commands.md#image-commands)
- [PDF commands](docs/commands.md#pdf-commands)
- [MP4 commands](docs/commands.md#mp4-commands)
- [M4A audio commands](docs/commands.md#audio-commands)
- [JPEG and metadata commands](docs/commands.md#jpeg-commands)
- [File and text commands](docs/commands.md#file-and-text-commands)

## Documentation

- [Command guide](docs/commands.md): command-by-command behavior and dependency notes.
- [Privacy guide](docs/privacy.md): privacy risks for metadata, transcripts, logs, and generated files.
- [Architecture](docs/architecture.md): package layout, command structure, and documentation build.
- [Lessons learned](docs/lessons-learned.md): rationale and project-specific lessons that supplement the normative contributor guidance.

Static HTML documentation is generated from the markdown sources into `docs/html/`:

```bash
make docs
make docs-watch
```

`make docs` rebuilds the HTML once. `make docs-watch` keeps rebuilding when `README.md` or `docs/*.md` changes. Each command section from `docs/commands.md` also gets its own generated page under `docs/html/commands/`.

## Safety Defaults

Commands validate paths, avoid unexpected overwrites, skip symlinks in batch operations, and provide confirmation or dry-run controls for destructive work. See the [command guide](docs/commands.md) for command-specific behavior.

## Privacy Notes

MP4 transcription sends audio to Google Web Speech API, and JPEG, PDF, and media outputs may contain sensitive source data. Read the [privacy guide](docs/privacy.md) before processing or publishing private files.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for project standards, validation expectations, release preparation, and guidance for adding new commands. The `main` branch is protected: use a focused `codex/<description>` branch, open a pull request, wait for all required CI checks, and squash-merge instead of pushing directly to `main`.

The project uses the [Code of Conduct](CODE_OF_CONDUCT.md) for collaboration expectations and [SUPPORT.md](SUPPORT.md) for issue-reporting guidance.

## Security

Please report security concerns privately. See the [Security Policy](SECURITY.md).

## Changelog

Release notes are tracked in the [CHANGELOG.md](CHANGELOG.md).

## License

Distributed under the [MIT License](https://github.com/tocatlian/PyTransformer/blob/main/LICENSE).

## Contact

Paul Tocatlian - <https://www.tocatlian.com>

Project Link: <https://github.com/tocatlian/PyTransformer>
