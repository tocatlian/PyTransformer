# PyTransformer

[![CI](https://github.com/tocatlian/PyTransformer/actions/workflows/ci.yml/badge.svg)](https://github.com/tocatlian/PyTransformer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

PyTransformer is a Python package of command-line utilities for transforming PDFs, MP4 files, JPEG metadata, filenames, and plain-text files.

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
- `pyt-jpeg-count-variants`
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
- `.[ocr]` installs `pytesseract`; OCR fallback also requires a system Tesseract installation.
- `.[all]` installs every optional runtime dependency group.
- `.[dev]` installs build, coverage, type-checking, linting, pre-commit, tox, and package-checking tools.

## Validation

After installing the development extra, run:

```bash
make validate
make lint
make coverage
make hooks
make smoke
make smoke-pdf
make smoke-jpeg
make clean
```

`make validate` compiles the package and tests, runs Ruff lint and format checks, runs mypy, validates the pre-commit configuration, verifies generated HTML documentation, verifies module and installed-command help, runs the unit tests, checks coverage, builds source and wheel distributions in a temporary folder, and checks package metadata.

`make coverage` runs the unit tests under coverage.py and enforces the current coverage floor.

`make smoke` runs representative standard-library commands against temporary fixtures. It avoids optional PDF/JPEG/MP4 dependencies.

`make smoke-pdf` and `make smoke-jpeg` run generated-fixture checks for optional PDF and JPEG commands. Install the matching extras first with `python3 -m pip install -e ".[pdf]"` or `python3 -m pip install -e ".[jpeg]"`.

`make hooks` runs the repository's pre-commit hooks across all files from inside a git checkout. It is useful before opening a pull request.

For local CI-style isolation, install the development extra and run:

```bash
python3 -m tox
python3 -m tox -e smoke-pdf,smoke-jpeg
```

The default tox environments run the Python version matrix when those interpreters are available, plus linting, type-checking, package build checks, and the standard-library smoke test. The optional PDF and JPEG smoke environments are opt-in because they install optional runtime dependencies.

## Naming Standard

CLI modules usually use `pyt_domain_verb_object[_batch]` names. The installed command is the same name with underscores changed to hyphens. The inventory command `pyt_help.py` uses the shorter `pyt-help` name.

Python modules:

```text
src/pytransformer/cli/pyt_pdf_extract_text.py
src/pytransformer/cli/pyt_jpeg_strip_metadata.py
src/pytransformer/core/common.py
```

Installed console commands:

```text
pyt-help
pyt-pdf-extract-text
pyt-jpeg-strip-metadata
pyt-mp4-transcribe-batch
```

This gives engineers importable Python modules and gives command-line users idiomatic shell command names.

## Command Reference

| Python module | Console command | Purpose | Example | Writes data? | Setup |
| --- | --- | --- | --- | --- | --- |
| `pyt_help.py` | `pyt-help` | List available PyTransformer commands. | `pyt-help --verbose` | Read-only. | Standard library only. |
| `pyt_pdf_extract_text.py` | `pyt-pdf-extract-text` | Extract PDF text with optional OCR fallback. | `pyt-pdf-extract-text --no-ocr "/path/to/file.pdf"` | Writes a `.txt` file and extraction log. | Requires `.[pdf]`; OCR also needs `.[ocr]` and Tesseract. |
| `pyt_pdf_extract_selectable_text.py` | `pyt-pdf-extract-selectable-text` | Extract selectable PDF text with a lightweight parser. | `pyt-pdf-extract-selectable-text "/path/to/file.pdf"` | Writes a `.txt` file. | Requires `.[pdf]`. |
| `pyt_pdf_extract_selectable_text_batch.py` | `pyt-pdf-extract-selectable-text-batch` | Batch extract selectable text from PDFs in a folder. | `pyt-pdf-extract-selectable-text-batch --output-folder "/path/to/text" "/path/to/pdfs"` | Writes one `.txt` file per PDF. | Requires `.[pdf]`. |
| `pyt_pdf_render_jpeg.py` | `pyt-pdf-render-jpeg` | Render PDF pages as JPEG images. | `pyt-pdf-render-jpeg --dpi 300 --output-folder "/path/to/pages" "/path/to/file.pdf"` | Writes JPEG files to an output folder. | Requires `.[pdf]`. |
| `pyt_mp4_split_chunks.py` | `pyt-mp4-split-chunks` | Split one MP4 into fixed-length chunks. | `pyt-mp4-split-chunks --seconds 30 "/path/to/video.mp4"` | Writes chunked MP4 files to an output folder. | Requires `.[mp4]` and FFmpeg. |
| `pyt_mp4_transcribe.py` | `pyt-mp4-transcribe` | Transcribe one MP4 to text. | `pyt-mp4-transcribe "/path/to/video.mp4"` | Writes a transcript `.txt` file. | Requires `.[mp4]`, FFmpeg, and network access. |
| `pyt_mp4_transcribe_batch.py` | `pyt-mp4-transcribe-batch` | Batch transcribe MP4 files in a folder. | `pyt-mp4-transcribe-batch --output-folder "/path/to/transcripts" "/path/to/videos"` | Writes one transcript per MP4. | Requires `.[mp4]`, FFmpeg, and network access. |
| `pyt_jpeg_show_metadata.py` | `pyt-jpeg-show-metadata` | Show embedded metadata for one JPEG. | `pyt-jpeg-show-metadata --full-values "/path/to/file.jpg"` | Read-only. | Requires `.[jpeg]`. |
| `pyt_jpeg_strip_metadata.py` | `pyt-jpeg-strip-metadata` | Create cleaned JPEG copies without descriptive metadata. | `pyt-jpeg-strip-metadata --dry-run "/path/to/images"` | Writes cleaned copies to a separate folder by default. | Requires `.[jpeg]`. |
| `pyt_jpeg_count_variants.py` | `pyt-jpeg-count-variants` | Count preset variants grouped by JPEG base filename. | `pyt-jpeg-count-variants --list-presets --include-hidden "/path/to/images"` | Read-only. | Standard library only. |
| `pyt_jpeg_sliced_collage.py` | `pyt-jpeg-sliced-collage` | Create a sliced collage from two or more JPEG images. | `pyt-jpeg-sliced-collage --tiff --output collage.tif 10 image-a.jpg image-b.jpg image-c.jpg` | Writes one high-quality JPEG, lossless PNG, or lossless TIFF collage; preserves available color and resolution metadata; refuses to overwrite unless `--overwrite` is passed. | Requires `.[jpeg]`. |
| `pyt_files_append_folder_name.py` | `pyt-files-append-folder-name` | Append the containing folder name to filenames. | `pyt-files-append-folder-name --dry-run "/path/to/Tokyo"` | Renames files; requires confirmation unless `--yes` is passed. | Standard library only. |
| `pyt_text_concatenate.py` | `pyt-text-concatenate` | Concatenate text files in a folder. | `pyt-text-concatenate --output "/path/to/combined.txt" "/path/to/text-files"` | Writes one combined text file. | Standard library only. |

Detailed command notes are available in `docs/commands.md`.

## Documentation

- `docs/commands.md`: command-by-command behavior and dependency notes.
- `docs/privacy.md`: privacy risks for metadata, transcripts, logs, and generated files.
- `docs/architecture.md`: package layout, command structure, and safety model.
- `docs/lessons-learned.md`: reusable project practices, implementation recipes, testing considerations, and things to avoid repeating.

Static HTML documentation is generated from the markdown sources into `docs/html/`:

```bash
make docs
make docs-watch
```

`make docs` rebuilds the HTML once. `make docs-watch` keeps rebuilding when `README.md` or `docs/*.md` changes. Each command section from `docs/commands.md` also gets its own generated page under `docs/html/commands/`.

## Safety Defaults

- Commands validate input paths before doing work.
- Batch commands do not recurse unless explicitly documented.
- Symlinks are skipped by batch file operations.
- Output files are not overwritten unless `--overwrite` is passed.
- Destructive renaming requires an interactive confirmation or `--yes`.
- Dry-run modes are available where a command performs bulk changes.

## Privacy Notes

- MP4 transcription commands use Google Web Speech API through `SpeechRecognition`; do not use them on sensitive audio unless that service is acceptable for your use case.
- JPEG metadata can include GPS coordinates, camera identifiers, timestamps, comments, and editing metadata. Use `pyt-jpeg-show-metadata` before publishing, and use `pyt-jpeg-strip-metadata` to create cleaned copies.
- PDF and media outputs may contain extracted text, rendered pages, or audio-derived transcripts. Treat generated artifacts with the same care as the source files.

See `docs/privacy.md` for more detail.

## Contributing

See `CONTRIBUTING.md` for project standards, validation expectations, and guidance for adding new commands.

The project uses `CODE_OF_CONDUCT.md` for collaboration expectations and `SUPPORT.md` for issue-reporting guidance.

## Security

Please report security concerns privately. See `SECURITY.md`.

## Changelog

Release notes are tracked in `CHANGELOG.md`.

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Paul Tocatlian - <https://www.tocatlian.com>

Project Link: <https://github.com/tocatlian/PyTransformer>
