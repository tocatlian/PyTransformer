# Command Guide

PyTransformer exposes installed console commands through `pyproject.toml`. Each command also has an importable Python module under `pytransformer.cli`.

Every command supports `-h`/`--help`. Help output describes the command, lists positional and optional arguments, and ends with an `Examples:` section showing installed command invocations.

Command names follow their module names: `pyt_domain_verb_object[_batch].py` becomes `pyt-domain-verb-object[-batch]`. The command inventory module `pyt_help.py` is exposed as `pyt-help`.

## Discovery Command

### `pyt-help`

Lists available PyTransformer console commands.

Display modes:

- Default: command names with short descriptions.
- `--terse`: command names only, one per line.
- `--verbose`: command names, descriptions, and Python module filenames.

Use when:

- You want to see every installed `pyt-*` command.
- You want command names only for shell scripting.
- You want to map console commands back to Python module files.

Writes:

- Nothing. This command is read-only.

Dependencies:

- Python standard library only.

## PDF Commands

Single-file commands use `-o`/`--output` when they write one file. Commands that write a folder of generated files use `-o`/`--output-folder`.

### `pyt-pdf-extract-text`

Extracts text from one PDF with optional OCR fallback for image-only pages.

Use when:

- A PDF may contain scanned pages.
- You want a log of extraction progress.
- OCR fallback is acceptable for pages without a text layer.

Writes:

- A UTF-8 `.txt` file.
- An extraction log next to the input PDF.

Dependencies:

- `.[pdf]`
- `.[ocr]`, Pillow, pytesseract, and system Tesseract for OCR fallback.

### `pyt-pdf-extract-selectable-text`

Extracts selectable text from one PDF using a lightweight parser.

Use when:

- The PDF already has a text layer.
- OCR is not needed.

Writes:

- One UTF-8 `.txt` file.

Dependencies:

- `.[pdf]`

### `pyt-pdf-extract-selectable-text-batch`

Extracts selectable text from every PDF directly inside a folder.

Use when:

- You have a flat folder of text-layer PDFs.
- You want one transcript per PDF.

Writes:

- One UTF-8 `.txt` file per PDF.

Dependencies:

- `.[pdf]`

### `pyt-pdf-render-jpeg`

Renders every page of one PDF as JPEG images.

Use when:

- PDF pages need to be reviewed or processed as images.
- A downstream workflow expects JPEG files.

Writes:

- Numbered `page_*.jpg` files.
- A timestamped sibling folder by default, or the folder passed with `--output-folder`.

Dependencies:

- `.[pdf]`

## MP4 Commands

### `pyt-mp4-split-chunks`

Splits one MP4 into fixed-length chunks.

Writes:

- Numbered MP4 chunk files in a sibling or requested output folder.

Dependencies:

- `.[mp4]`
- FFmpeg.

### `pyt-mp4-transcribe`

Transcribes one MP4 file to text through Google Web Speech API.

Writes:

- One transcript `.txt` file.

Dependencies:

- `.[mp4]`
- FFmpeg.
- Network access.

### `pyt-mp4-transcribe-batch`

Transcribes MP4 files directly inside a folder.

Writes:

- One transcript `.txt` file per MP4.

Dependencies:

- `.[mp4]`
- FFmpeg.
- Network access.

## JPEG Commands

### `pyt-jpeg-show-metadata`

Displays metadata embedded in one JPEG.

Writes:

- Nothing. This command is read-only.

Dependencies:

- `.[jpeg]`

### `pyt-jpeg-strip-metadata`

Creates cleaned JPEG copies with descriptive metadata removed.

Writes:

- Cleaned JPEG copies in a separate output folder by default.

Dependencies:

- `.[jpeg]`

### `pyt-jpeg-count-variants`

Counts JPEG preset variants grouped by base filename.

Hidden files are skipped by default. Pass `--include-hidden` to include dotfiles.

Writes:

- Nothing. This command is read-only.

Dependencies:

- Python standard library only.

### `pyt-jpeg-sliced-collage`

Creates a high-resolution JPEG collage from two or more JPEG images by cycling strips from each image.

Use when:

- Same-aspect-ratio JPEG images should be interleaved into a sliced collage.
- You want vertical strips by default, or horizontal strips with `--horizontal`.
- You want to choose the destination with `--output` or JPEG quality with `--quality`.
- You want a lossless PNG output with `--png`, or a lossless TIFF output with `--tiff`.

Writes:

- One JPEG, PNG, or TIFF collage in the current working directory, or at `--output`.
- Existing output files are refused unless `--overwrite` is passed.
- JPEG output defaults to quality 100, full chroma detail, and the first available input ICC color profile and resolution metadata.
- JPEG output preserves the first available input JFIF resolution unit and exact density when present, along with its DPI representation.
- PNG output is lossless and also preserves the first available input ICC color profile and DPI.
- TIFF output is lossless LZW-compressed TIFF and also preserves the first available input ICC color profile and DPI.

Dependencies:

- `.[jpeg]`

## File And Text Commands

Folder commands that skip hidden dotfiles by default expose `--include-hidden`.

### `pyt-files-append-folder-name`

Renames files by appending the containing folder name before the file extension.

Writes:

- Renames existing files in place.

Safety:

- Supports `--dry-run`.
- Requires interactive confirmation unless `--yes` is passed.

Dependencies:

- Python standard library only.

### `pyt-text-concatenate`

Concatenates text files directly inside a folder into one UTF-8 text file.

Writes:

- One combined text file.

Dependencies:

- Python standard library only.
