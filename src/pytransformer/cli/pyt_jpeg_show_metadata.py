#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_jpeg_show_metadata.py
Purpose: Display embedded metadata from one JPEG image.
When to use: Use before cleanup or publishing to inspect EXIF, GPS EXIF, XMP, IPTC, comments, and ICC metadata.
Changes: Read-only; prints metadata to standard output.
Inputs: JPEG file path; optional --full-values.
Environment variables: None.
Dependencies: pillow; optional defusedxml for safer XMP parsing.
Safety notes: Does not modify the image file.
Example: pyt-jpeg-show-metadata --full-values "/path/to/file.jpg"
Expected result: A sorted metadata report or a message that no embedded metadata was found.
Related scripts: pyt_jpeg_strip_metadata.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pytransformer.core.common import ScriptError, build_command_parser, fail, require_existing_file
from pytransformer.core.jpeg_metadata import JPEG_EXTENSIONS, format_display_value, inspect_embedded_metadata


def print_metadata(metadata: dict[str, str], *, full_values: bool = False) -> None:
    if not metadata:
        print("No embedded metadata found.")
        return

    max_key_len = max(len(key) for key in metadata)
    for key, value in metadata.items():
        print(f"{key.ljust(max_key_len)} : {format_display_value(value, full_values)}")


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="Display only metadata embedded inside a JPEG file.",
        examples=(
            'pyt-jpeg-show-metadata "/path/to/file.jpg"',
            'pyt-jpeg-show-metadata --full-values "/path/to/file.jpg"',
        ),
    )
    parser.add_argument(
        "jpeg_file",
        type=Path,
        help="Path to the JPEG file to inspect.",
    )
    parser.add_argument(
        "--full-values",
        action="store_true",
        help="Print complete metadata values instead of truncating very long values.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        path = require_existing_file(args.jpeg_file, label="JPEG file", suffixes=JPEG_EXTENSIONS)
        metadata = inspect_embedded_metadata(path)
    except ScriptError as exc:
        return fail(str(exc), code=2)
    except Exception as exc:
        print(f"Error: could not read JPEG metadata: {exc}", file=sys.stderr)
        return 1

    print_metadata(metadata, full_values=args.full_values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
