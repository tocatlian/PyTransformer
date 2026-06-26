#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_text_concatenate.py
Purpose: Concatenate text files directly inside a folder into one UTF-8 text file.
When to use: Use when a folder of .txt files should become a single combined text document.
Changes: Writes one output .txt file in the input folder or at --output.
Inputs: Folder path; optional --output, --overwrite, --include-hidden, and --separator.
Environment variables: None.
Dependencies: Python standard library only.
Safety notes: Does not recurse, skips symlinks, and refuses to overwrite output unless --overwrite is passed.
Example: pyt-text-concatenate --output "/path/to/combined.txt" "/path/to/text-files"
Expected result: One combined UTF-8 text file with deterministic input ordering.
Related scripts: pyt_pdf_extract_selectable_text.py, pyt_pdf_extract_selectable_text_batch.py, pyt_pdf_extract_text.py.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pytransformer.core.common import (
    ScriptError,
    build_command_parser,
    configure_logging,
    ensure_output_path,
    fail,
    is_hidden_path,
    require_existing_folder,
    sorted_directory_items,
)

TXT_EXTENSIONS = {".txt"}
DEFAULT_SEPARATOR = "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="Concatenate text files directly inside a folder.",
        examples=(
            'pyt-text-concatenate --output "/path/to/combined.txt" "/path/to/text-files"',
            'pyt-text-concatenate --overwrite "/path/to/text-files"',
        ),
    )
    parser.add_argument("folder", type=Path, help="Folder containing .txt files to concatenate.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file. Defaults to <folder>/<folder-name>.txt.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the output file if it exists.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden .txt files.")
    parser.add_argument(
        "--separator",
        default=DEFAULT_SEPARATOR,
        help="Text inserted between files. Defaults to one newline.",
    )
    parser.add_argument("--quiet", action="store_true", help="Only print warnings and errors.")
    return parser


def resolve_output_path(folder: Path, requested_output: Path | None, *, overwrite: bool) -> Path:
    output_path = requested_output if requested_output else folder / f"{folder.name}.txt"
    return ensure_output_path(output_path, overwrite=overwrite, label="Output file")


def find_text_files(folder: Path, output_path: Path, *, include_hidden: bool) -> list[Path]:
    text_files: list[Path] = []
    for item in sorted_directory_items(folder):
        if not include_hidden and is_hidden_path(item):
            continue
        if item.is_symlink() or not item.is_file():
            continue
        if item.resolve() == output_path:
            continue
        if item.suffix.lower() in TXT_EXTENSIONS:
            text_files.append(item)
    return text_files


def concatenate_text_files(text_files: list[Path], output_path: Path, *, separator: str) -> None:
    if not text_files:
        raise ScriptError("No .txt files found to concatenate.")

    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        for index, text_path in enumerate(text_files):
            if index:
                output_file.write(separator)
                if separator and not separator.endswith("\n"):
                    output_file.write("\n")

            try:
                content = text_path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise ScriptError(f"Could not read '{text_path.name}' as UTF-8 text: {exc}") from exc
            output_file.write(content)
            if content and not content.endswith("\n"):
                output_file.write("\n")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(quiet=args.quiet)

    try:
        folder = require_existing_folder(args.folder, label="Input folder")
        output_path = resolve_output_path(folder, args.output, overwrite=args.overwrite)
        text_files = find_text_files(folder, output_path, include_hidden=args.include_hidden)
        concatenate_text_files(text_files, output_path, separator=args.separator)
    except ScriptError as exc:
        return fail(str(exc), code=2)
    except OSError as exc:
        return fail(str(exc), code=1)

    logging.info("Concatenated %d files into: %s", len(text_files), output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
