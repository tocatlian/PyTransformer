#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_jpeg_strip_metadata.py
Purpose: Create cleaned JPEG copies with descriptive metadata removed.
When to use: Use before publishing or sharing JPEG folders that may contain private metadata.
Changes: Writes cleaned JPEG copies to a separate output folder by default.
Inputs: Folder path; optional --output-folder, --overwrite, --dry-run, --include-hidden, and orientation/report flags.
Environment variables: None.
Dependencies: pillow; optional defusedxml for safer XMP parsing.
Safety notes: Refuses to use the input folder as output; existing output files are skipped unless --overwrite is passed.
Example: pyt-jpeg-strip-metadata --dry-run "/path/to/images"
Expected result: Cleaned JPEG copies plus a summary of written, skipped, and failed files.
Related scripts: pyt_jpeg_show_metadata.py.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Any

from pytransformer.core import jpeg_metadata
from pytransformer.core.common import build_command_parser
from pytransformer.core.jpeg_metadata import JPEG_EXTENSIONS, format_display_value, inspect_embedded_metadata


def is_hidden_file(path: Path) -> bool:
    return path.name.startswith(".")


def iter_jpeg_files(input_folder: Path, *, include_hidden: bool) -> list[Path]:
    return sorted(
        (
            path
            for path in input_folder.iterdir()
            if path.is_file()
            and not path.is_symlink()
            and path.suffix.lower() in JPEG_EXTENSIONS
            and (include_hidden or not is_hidden_file(path))
        ),
        key=lambda path: path.name.casefold(),
    )


def resolve_output_folder(input_folder: Path, requested_output_folder: Path | None) -> Path:
    if requested_output_folder is not None:
        output_folder = requested_output_folder.expanduser().resolve()
    else:
        output_folder = input_folder.parent / f"{input_folder.name}_stripped"

    if output_folder == input_folder:
        raise ValueError("Output folder must be different from the input folder.")

    return output_folder


def _to_saveable_image(image: Any) -> Any:
    image.load()
    if image.mode in ("RGB", "L", "CMYK", "YCbCr"):
        return image.copy()
    return image.convert("RGB")


def _get_preservation_save_args(image: Any) -> dict[str, Any]:
    """
    Preserve JPEG encoding characteristics without using Pillow's keep mode
    on a copied or converted image object.
    """
    save_args: dict[str, Any] = {}

    qtables = getattr(image, "quantization", None)
    if qtables:
        save_args["qtables"] = qtables

    jpeg_plugin = jpeg_metadata.JpegImagePlugin
    if jpeg_plugin is None:
        return save_args

    try:
        subsampling = jpeg_plugin.get_sampling(image)
        if subsampling != -1:
            save_args["subsampling"] = subsampling
    except Exception:
        pass

    return save_args


def save_with_color_and_quality_preserved(
    src: Path,
    dst: Path,
    *,
    preserve_visual_orientation: bool,
) -> None:
    jpeg_metadata.require_pillow()
    image_module = jpeg_metadata.Image
    image_ops = jpeg_metadata.ImageOps
    if image_module is None or image_ops is None:
        raise RuntimeError("Pillow is required. Install it with: pip install pillow")

    with image_module.open(src) as image:
        if image.format != "JPEG":
            raise ValueError(f"Input file is not a JPEG according to Pillow: {src.name}")

        info = dict(image.info or {})
        icc_profile = info.get("icc_profile")

        working_image = image_ops.exif_transpose(image) if preserve_visual_orientation else image
        clean = _to_saveable_image(working_image)
        try:
            save_kwargs: dict[str, Any] = {
                "format": "JPEG",
                "exif": b"",
                "optimize": False,
            }

            if icc_profile is not None:
                save_kwargs["icc_profile"] = icc_profile

            save_kwargs.update(_get_preservation_save_args(image))

            if "qtables" not in save_kwargs:
                save_kwargs["quality"] = 95

            clean.save(dst, **save_kwargs)
        finally:
            clean.close()
            if working_image is not image:
                working_image.close()


def format_field_list(
    title: str,
    data: dict[str, str],
    *,
    full_values: bool,
    indent: str = "    ",
) -> str:
    lines = [title]
    if not data:
        lines.append(f"{indent}(none)")
        return "\n".join(lines)
    for key, value in data.items():
        lines.append(f"{indent}{key}: {format_display_value(value, full_values)}")
    return "\n".join(lines)


def print_metadata_report(
    *,
    before: dict[str, str],
    after: dict[str, str],
    full_values: bool,
) -> None:
    removed = {key: value for key, value in before.items() if key not in after}
    kept = {key: value for key, value in after.items() if key in before and before[key] == value}
    added = {key: value for key, value in after.items() if key not in before}

    print(format_field_list("Removed embedded metadata fields:", removed, full_values=full_values))
    print()
    print(format_field_list("Kept embedded metadata fields:", kept, full_values=full_values))
    print()
    print(format_field_list("Embedded metadata present before processing:", before, full_values=full_values))
    print()
    print(format_field_list("Embedded metadata present after processing:", after, full_values=full_values))
    if added:
        print()
        print(format_field_list("Fields newly present after save:", added, full_values=full_values))


def process_folder(
    input_folder: Path,
    *,
    output_folder_arg: Path | None,
    overwrite: bool,
    dry_run: bool,
    include_hidden: bool,
    preserve_visual_orientation: bool,
    quiet: bool,
    debug: bool,
    full_values: bool,
) -> int:
    if not input_folder.exists():
        print(f"Error: folder does not exist: {input_folder}", file=sys.stderr)
        return 2

    if not input_folder.is_dir():
        print(f"Error: path is not a folder: {input_folder}", file=sys.stderr)
        return 2

    if not jpeg_metadata.load_pillow():
        print("Error: Pillow is required. Install it with: pip install pillow", file=sys.stderr)
        return 2

    try:
        output_folder = resolve_output_folder(input_folder, output_folder_arg)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    try:
        jpeg_files = iter_jpeg_files(input_folder, include_hidden=include_hidden)
    except PermissionError:
        print(f"Error: permission denied while reading folder: {input_folder}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Error: could not read folder '{input_folder}': {exc}", file=sys.stderr)
        return 2

    if not jpeg_files:
        print(f"No JPEG files found in: {input_folder}")
        return 0

    if not dry_run:
        try:
            output_folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"Error: could not create output folder '{output_folder}': {exc}", file=sys.stderr)
            return 2

    if not quiet:
        print(f"Input folder : {input_folder}")
        print(f"Output folder: {output_folder}")
        print(f"JPEG files   : {len(jpeg_files)}")
        if dry_run:
            print("Mode         : dry run")
        print()

    written = 0
    planned = 0
    skipped = 0
    failures = 0

    for src in jpeg_files:
        dst = output_folder / src.name

        if dst.exists() and not overwrite:
            skipped += 1
            if not quiet:
                print(f"Skipped existing output: {dst.name}")
            continue

        if dry_run:
            planned += 1
            if not quiet:
                print(f"Would process: {src.name} -> {dst}")
            continue

        if not quiet:
            print("=" * 100)
            print(f"File: {src.name}")

        try:
            before = inspect_embedded_metadata(src, input_label="Input file")
            save_with_color_and_quality_preserved(
                src,
                dst,
                preserve_visual_orientation=preserve_visual_orientation,
            )
            after = inspect_embedded_metadata(dst, input_label="Output file")
            written += 1

            if not quiet:
                print_metadata_report(before=before, after=after, full_values=full_values)
        except Exception as exc:
            failures += 1
            print(f"Error processing {src.name}: {exc}", file=sys.stderr)
            if debug:
                traceback.print_exc()

        if not quiet:
            print()

    if not quiet:
        print("=" * 100)

    if dry_run:
        print(f"Dry run complete. Planned: {planned} | Skipped: {skipped} | Failed: {failures}")
    else:
        print(f"Completed. Written: {written} | Skipped: {skipped} | Failed: {failures}")

    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description=(
            "Strip descriptive metadata from JPEG images while preserving ICC profile, "
            "JPEG encoding characteristics, and visual orientation when possible."
        ),
        examples=(
            'pyt-jpeg-strip-metadata --dry-run "/path/to/images"',
            'pyt-jpeg-strip-metadata --output-folder "/path/to/clean" "/path/to/images"',
        ),
    )
    parser.add_argument(
        "folder",
        type=Path,
        help="Path to the folder containing JPEG images.",
    )
    parser.add_argument(
        "-o",
        "--output-folder",
        type=Path,
        help="Destination folder. Defaults to a sibling folder named <folder>_stripped.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without writing files.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden dotfiles.")
    parser.add_argument(
        "--keep-pixel-orientation",
        action="store_true",
        help="Do not bake EXIF orientation into pixels before removing EXIF metadata.",
    )
    parser.add_argument("--quiet", action="store_true", help="Only print errors and the final summary.")
    parser.add_argument("--debug", action="store_true", help="Print tracebacks for files that fail.")
    parser.add_argument(
        "--full-values",
        action="store_true",
        help="Print complete metadata values instead of truncating very long values.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return process_folder(
        args.folder.expanduser().resolve(),
        output_folder_arg=args.output_folder,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        include_hidden=args.include_hidden,
        preserve_visual_orientation=not args.keep_pixel_orientation,
        quiet=args.quiet,
        debug=args.debug,
        full_values=args.full_values,
    )


if __name__ == "__main__":
    raise SystemExit(main())
