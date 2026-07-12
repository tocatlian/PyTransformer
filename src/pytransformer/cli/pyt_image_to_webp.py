#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_image_to_webp.py
Purpose: Convert one or more JPEG, PNG, or TIFF images to sibling WebP files.
When to use: Use when source images should be prepared as WebP files for web publishing.
Changes: Writes WebP files next to each original image using the same filename stem.
Inputs: One or more JPEG, PNG, or TIFF image paths; optional WebP quality.
Environment variables: None.
Dependencies: pillow.
Safety notes: Validates images, applies EXIF orientation, preserves available ICC/resolution metadata,
and avoids overwrites by default.
Example: pyt-image-to-webp --quality 98 image.jpg image.tif
Expected result: Files named image.webp next to each source image.
Related scripts: pyt_image_split.py, pyt_image_collage_slice.py, pyt_jpeg_strip_metadata.py.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Sequence

from pytransformer.core.common import (
    ScriptError,
    build_command_parser,
    configure_logging,
    ensure_output_path,
    fail,
    require_existing_file,
    require_int_range,
    temporary_output_path,
)

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:  # pragma: no cover - exercised only when optional dependency is missing.
    Image = None
    ImageOps = None
    UnidentifiedImageError = OSError

DEFAULT_WEBP_QUALITY = 98
SUPPORTED_FORMATS = {"JPEG", "PNG", "TIFF"}
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = build_command_parser(
        description="Convert one or more JPEG, PNG, or TIFF images to sibling WebP files.",
        examples=(
            "pyt-image-to-webp image.jpg",
            "pyt-image-to-webp --quality 90 first.jpg second.png third.tif",
            "pyt-image-to-webp -q 98 --overwrite image.tiff",
        ),
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=DEFAULT_WEBP_QUALITY,
        help=f"WebP output quality from 1 to 100. Default: {DEFAULT_WEBP_QUALITY}.",
    )
    parser.add_argument(
        "images",
        type=Path,
        nargs="+",
        help="One or more JPEG, PNG, or TIFF images to convert.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing WebP files.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show warnings and errors.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug logging.",
    )
    return parser


def require_pillow() -> None:
    """Require Pillow before using image APIs."""
    if Image is None or ImageOps is None:
        raise ScriptError("Pillow is required. Install it with: python -m pip install Pillow")


def build_output_path(image_path: Path) -> Path:
    """Return the sibling WebP path for an input image."""
    return image_path.with_suffix(".webp")


def resolve_output_path(image_path: Path, *, overwrite: bool) -> Path:
    """Resolve and validate the WebP output path for one image."""
    return ensure_output_path(
        build_output_path(image_path),
        overwrite=overwrite,
        input_paths=[image_path],
        label="WebP image",
    )


def load_image(path: Path) -> Any:
    """Load a supported source image and apply EXIF orientation."""
    require_pillow()

    try:
        with Image.open(path) as probe:
            detected_format = probe.format
            if detected_format not in SUPPORTED_FORMATS:
                supported = ", ".join(sorted(SUPPORTED_FORMATS))
                raise ScriptError(
                    f"Unsupported image format for '{path}'. Detected: {detected_format or 'unknown'}. "
                    f"Supported formats: {supported}."
                )
            probe.verify()

        with Image.open(path) as image:
            corrected = ImageOps.exif_transpose(image)
            corrected.load()
            return corrected.copy()

    except UnidentifiedImageError as exc:
        raise ScriptError(f"The image cannot be opened as a valid image: {path}") from exc
    except OSError as exc:
        raise ScriptError(f"The image could not be read: {path}") from exc


def get_save_kwargs(image: Any, *, quality: int) -> dict[str, Any]:
    """Build Pillow save options for WebP output."""
    require_int_range(quality, label="WebP quality", minimum=1, maximum=100)
    kwargs: dict[str, Any] = {
        "format": "WEBP",
        "quality": quality,
        "method": 6,
    }

    icc_profile = image.info.get("icc_profile")
    if isinstance(icc_profile, bytes) and icc_profile:
        kwargs["icc_profile"] = icc_profile

    dpi = image.info.get("dpi")
    if isinstance(dpi, (tuple, list)) and len(dpi) == 2:
        kwargs["dpi"] = tuple(dpi)

    return kwargs


def save_webp(image: Any, output_path: Path, *, quality: int) -> None:
    """Save an image as WebP through a temporary sibling file."""
    save_kwargs = get_save_kwargs(image, quality=quality)
    with temporary_output_path(output_path) as temporary_path:
        image.save(temporary_path, **save_kwargs)


def process_image(image_path: Path, *, overwrite: bool, quality: int) -> Path:
    """Convert one image and return the written output path."""
    resolved_image_path = require_existing_file(image_path, label="Image", suffixes=SUPPORTED_SUFFIXES)
    output_path = resolve_output_path(resolved_image_path, overwrite=overwrite)
    image = load_image(resolved_image_path)
    try:
        save_webp(image, output_path, quality=quality)
    finally:
        image.close()
    return output_path


def run(args: argparse.Namespace) -> int:
    """Run the command."""
    configure_logging(quiet=args.quiet, debug=args.debug)
    require_int_range(args.quality, label="WebP quality", minimum=1, maximum=100)

    written_paths: list[Path] = []
    for image_path in args.images:
        output_path = process_image(image_path, overwrite=args.overwrite, quality=args.quality)
        written_paths.append(output_path)
        logging.info("Converted %s to %s.", image_path, output_path)

    for output_path in written_paths:
        print(output_path)

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except ScriptError as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
