#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_image_variants_count.py
Purpose: Count image preset variants grouped by base filename.
When to use: Use for folders where files are named <base>-<preset>.<ext> and variant coverage should be checked.
Changes: Read-only; prints a grouped summary to standard output.
Inputs: Folder path; optional --list-presets and --include-hidden.
Environment variables: None.
Dependencies: Python standard library only.
Safety notes: Does not recurse, skips hidden files unless requested, skips symlinks, and does not modify files.
Example: pyt-image-variants-count --list-presets "/path/to/images"
Expected result: Counts for each base filename plus duplicate-preset warnings.
Related scripts: pyt_files_append_folder_name.py.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from pytransformer.core.common import (
    ScriptError,
    build_command_parser,
    fail,
    require_existing_folder,
    sorted_directory_items,
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".jpe", ".jfif", ".png", ".tif", ".tiff", ".webp"}


@dataclass
class VariantAnalysis:
    """Grouped image variant analysis for one folder."""

    presets_by_base_name: dict[str, set[str]] = field(default_factory=dict)
    duplicates_by_base_name: dict[str, list[str]] = field(default_factory=dict)
    total_files_scanned: int = 0
    total_matching_jpg_files_processed: int = 0
    total_files_skipped: int = 0
    total_duplicate_preset_entries: int = 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = build_command_parser(
        description="Analyze image files in a folder and count preset variations for each base file name.",
        examples=(
            'pyt-image-variants-count "/path/to/images"',
            'pyt-image-variants-count --list-presets --include-hidden "/path/to/images"',
        ),
    )

    parser.add_argument(
        "folder",
        type=Path,
        help="Path to the folder containing image files to analyze.",
    )

    parser.add_argument(
        "--list-presets", action="store_true", help="List the preset names found for each base file name."
    )
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden image files.")

    return parser


def is_hidden_file(path: Path) -> bool:
    """
    Return True if the file is hidden.

    On macOS, hidden files commonly begin with a dot.
    Example: .DS_Store
    """
    return path.name.startswith(".")


def is_image_file(path: Path) -> bool:
    """
    Return True if the file has a supported image extension.

    The comparison is case insensitive, so .jpg, .JPG, and .Jpg match.
    """
    return path.suffix.lower() in IMAGE_EXTENSIONS


def parse_file_name(path: Path) -> tuple[str, str] | None:
    """
    Parse a file name that follows this pattern:

        [file]-[preset].jpg

    The function splits the stem at the final dash.

    Returns:
        tuple[str, str] if the file matches the convention.
        None if the file does not match the convention.

    Examples:
        IMG001-Warm.jpg returns ("IMG001", "Warm")
        Tokyo-Shoot-001-Warm.jpg returns ("Tokyo-Shoot-001", "Warm")
        IMG001.jpg returns None
        IMG001-.jpg returns None
        -Warm.jpg returns None
    """
    stem = path.stem

    if "-" not in stem:
        return None

    base_name, preset_name = stem.rsplit("-", 1)

    base_name = base_name.strip()
    preset_name = preset_name.strip()

    if not base_name or not preset_name:
        return None

    return base_name, preset_name


def analyze_folder(folder_path: Path, *, include_hidden: bool = False) -> VariantAnalysis:
    """
    Analyze JPEG files directly inside the given folder.

    Returns:
        A typed VariantAnalysis summary.
    """
    presets_by_base_name: defaultdict[str, set[str]] = defaultdict(set)
    duplicates_by_base_name: defaultdict[str, list[str]] = defaultdict(list)
    seen_presets_by_base_name: defaultdict[str, set[str]] = defaultdict(set)

    total_files_scanned = 0
    total_matching_jpg_files_processed = 0
    total_files_skipped = 0
    total_duplicate_preset_entries = 0

    folder_items = sorted_directory_items(folder_path)

    for item in folder_items:
        total_files_scanned += 1

        try:
            if not include_hidden and is_hidden_file(item):
                total_files_skipped += 1
                continue

            if item.is_symlink():
                total_files_skipped += 1
                continue

            if not item.is_file():
                total_files_skipped += 1
                continue

            if not is_image_file(item):
                total_files_skipped += 1
                continue

            parsed_name = parse_file_name(item)

            if parsed_name is None:
                total_files_skipped += 1
                continue

            base_name, preset_name = parsed_name
            total_matching_jpg_files_processed += 1

            normalized_preset_name = preset_name.casefold()

            if normalized_preset_name in seen_presets_by_base_name[base_name]:
                duplicates_by_base_name[base_name].append(preset_name)
                total_duplicate_preset_entries += 1
            else:
                seen_presets_by_base_name[base_name].add(normalized_preset_name)
                presets_by_base_name[base_name].add(preset_name)

        except PermissionError:
            print(
                f"Warning: Permission denied while inspecting: {item.name}",
                file=sys.stderr,
            )
            total_files_skipped += 1
        except OSError as error:
            print(
                f"Warning: Could not inspect '{item.name}': {error}",
                file=sys.stderr,
            )
            total_files_skipped += 1

    return VariantAnalysis(
        presets_by_base_name=dict(presets_by_base_name),
        duplicates_by_base_name=dict(duplicates_by_base_name),
        total_files_scanned=total_files_scanned,
        total_matching_jpg_files_processed=total_matching_jpg_files_processed,
        total_files_skipped=total_files_skipped,
        total_duplicate_preset_entries=total_duplicate_preset_entries,
    )


def pluralize_variation(count: int) -> str:
    """Return the correct singular or plural label for preset variation."""
    if count == 1:
        return "preset variation"
    return "preset variations"


def print_results(results: VariantAnalysis, list_presets: bool) -> None:
    """
    Print the grouped preset summary and final totals.
    """
    print()
    print("Preset variation summary")
    print()

    if not results.presets_by_base_name:
        print("No matching image files found.")
    else:
        for base_name in sorted(results.presets_by_base_name):
            presets = sorted(results.presets_by_base_name[base_name], key=str.casefold)
            preset_count = len(presets)

            print(f"{base_name}: {preset_count} {pluralize_variation(preset_count)}")

            if list_presets:
                for preset in presets:
                    print(f"    {preset}")

            if base_name in results.duplicates_by_base_name:
                duplicate_presets = sorted(
                    results.duplicates_by_base_name[base_name],
                    key=str.casefold,
                )
                print("    Duplicate preset entries:")
                for duplicate_preset in duplicate_presets:
                    print(f"        {duplicate_preset}")

    print()
    print("Final summary")
    print(f"Total files scanned: {results.total_files_scanned}")
    print(f"Total matching JPEG files processed: {results.total_matching_jpg_files_processed}")
    print(f"Total files skipped: {results.total_files_skipped}")
    print(f"Total unique base file names found: {len(results.presets_by_base_name)}")
    print(f"Total duplicate preset entries found: {results.total_duplicate_preset_entries}")


def main() -> int:
    """
    Main script entry point.
    """
    parser = build_parser()
    args = parser.parse_args()

    try:
        folder_path = require_existing_folder(args.folder, label="Input folder")
        results = analyze_folder(folder_path, include_hidden=args.include_hidden)
    except ScriptError as error:
        return fail(str(error), code=2)

    print_results(results, args.list_presets)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
