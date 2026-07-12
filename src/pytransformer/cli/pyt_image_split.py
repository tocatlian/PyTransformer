#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_image_split.py
Purpose: Split one or more images horizontally or vertically into numbered output images.
When to use: Use when images should be cut into a fixed number of rows or columns.
Changes: Writes numbered image slices next to each original image.
Inputs: One or more JPEG, PNG, TIFF, or WebP image paths; optional slice count and orientation.
Environment variables: None.
Dependencies: pillow.
Safety notes: Validates images, applies EXIF orientation, preserves format and available ICC/resolution metadata,
and avoids overwrites by default.
Example: pyt-image-split --count 2 --horizontal image.webp
Expected result: Images named image-1.webp and image-2.webp next to image.webp.
Related scripts: pyt_image_collage_slice.py, pyt_jpeg_show_metadata.py, pyt_jpeg_strip_metadata.py.
"""

from __future__ import annotations

import argparse
import logging
import math
import re
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

DEFAULT_JPEG_QUALITY = 100
DEFAULT_SLICE_COUNT = 2
SUPPORTED_FORMATS = {"JPEG", "PNG", "TIFF", "WEBP"}
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
SUPPORTED_ORIENTATIONS = {"horizontal", "vertical"}


def parse_slice_count(value: str) -> int:
    """Parse the requested output image count."""
    if not re.fullmatch(r"[0-9]+", value):
        raise argparse.ArgumentTypeError(f"The slice count must be a positive integer. Received: {value!r}")

    slice_count = int(value)
    if slice_count < 2:
        raise argparse.ArgumentTypeError(f"The slice count must be at least 2. Received: {slice_count}")

    return slice_count


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = build_command_parser(
        description="Split one or more images horizontally or vertically into numbered output images.",
        examples=(
            "pyt-image-split image.jpg",
            "pyt-image-split --count 3 first.jpg second.png",
            "pyt-image-split --horizontal --count 2 wide-image.webp",
            "pyt-image-split --orientation vertical --quality 95 image.jpg",
        ),
    )
    orientation_group = parser.add_mutually_exclusive_group()
    orientation_group.add_argument(
        "--horizontal",
        action="store_const",
        const="horizontal",
        dest="orientation",
        help="Split each image into left-to-right columns.",
    )
    orientation_group.add_argument(
        "--vertical",
        action="store_const",
        const="vertical",
        dest="orientation",
        help="Split each image into top-to-bottom rows. This is the default.",
    )
    orientation_group.add_argument(
        "--orientation",
        choices=sorted(SUPPORTED_ORIENTATIONS),
        help="Split orientation. Use 'vertical' for top-to-bottom rows or 'horizontal' for left-to-right columns.",
    )
    parser.set_defaults(orientation="vertical")
    parser.add_argument(
        "-c",
        "--count",
        type=parse_slice_count,
        default=DEFAULT_SLICE_COUNT,
        help=f"Number of output images to create for each input image. Default: {DEFAULT_SLICE_COUNT}.",
    )
    parser.add_argument(
        "images",
        type=Path,
        nargs="+",
        help="One or more JPEG, PNG, TIFF, or WebP images to split.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing split images.",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=DEFAULT_JPEG_QUALITY,
        help=f"JPEG and WebP output quality from 1 to 100. Ignored for PNG and TIFF. Default: {DEFAULT_JPEG_QUALITY}.",
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


def load_image(path: Path) -> tuple[Any, str]:
    """Load a supported image, apply EXIF orientation, and return the image plus its original format."""
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
            original_format = image.format
            if original_format not in SUPPORTED_FORMATS:
                raise ScriptError(f"Unsupported image format after reopening '{path}': {original_format or 'unknown'}")

            corrected = ImageOps.exif_transpose(image)
            corrected.load()
            return corrected.copy(), original_format

    except UnidentifiedImageError as exc:
        raise ScriptError(f"The image cannot be opened as a valid image: {path}") from exc
    except OSError as exc:
        raise ScriptError(f"The image could not be read: {path}") from exc


def calculate_vertical_bounds(height: int, slice_count: int) -> list[tuple[int, int]]:
    """Return stacked crop bounds that cover the full image height."""
    if slice_count > height:
        raise ScriptError(
            f"The slice count is larger than the image height. Image height: {height}px. Slice count: {slice_count}."
        )

    bounds = []
    for index in range(slice_count):
        top = math.floor(index * height / slice_count)
        bottom = math.floor((index + 1) * height / slice_count)
        if bottom <= top:
            raise ScriptError("The requested split would create an empty image slice.")
        bounds.append((top, bottom))

    return bounds


def calculate_horizontal_bounds(width: int, slice_count: int) -> list[tuple[int, int]]:
    """Return side-by-side crop bounds that cover the full image width."""
    if slice_count > width:
        raise ScriptError(
            f"The slice count is larger than the image width. Image width: {width}px. Slice count: {slice_count}."
        )

    bounds = []
    for index in range(slice_count):
        left = math.floor(index * width / slice_count)
        right = math.floor((index + 1) * width / slice_count)
        if right <= left:
            raise ScriptError("The requested split would create an empty image slice.")
        bounds.append((left, right))

    return bounds


def build_split_output_paths(image_path: Path, slice_count: int) -> list[Path]:
    """Return sibling output paths with -1, -2, ... suffixes."""
    return [
        image_path.with_name(f"{image_path.stem}-{index}{image_path.suffix}") for index in range(1, slice_count + 1)
    ]


def resolve_output_paths(image_path: Path, slice_count: int, *, overwrite: bool) -> list[Path]:
    """Resolve and validate all split output paths for one image."""
    output_paths = build_split_output_paths(image_path, slice_count)
    return [
        ensure_output_path(output_path, overwrite=overwrite, input_paths=[image_path], label="Split image")
        for output_path in output_paths
    ]


def get_save_kwargs(image: Any, image_format: str, *, quality: int) -> dict[str, Any]:
    """Build Pillow save options for the original image format."""
    kwargs: dict[str, Any] = {"format": image_format}

    icc_profile = image.info.get("icc_profile")
    if isinstance(icc_profile, bytes) and icc_profile:
        kwargs["icc_profile"] = icc_profile

    dpi = image.info.get("dpi")
    if isinstance(dpi, (tuple, list)) and len(dpi) == 2:
        kwargs["dpi"] = tuple(dpi)

    if image_format in {"JPEG", "WEBP"}:
        require_int_range(quality, label=f"{image_format} quality", minimum=1, maximum=100)
        kwargs["quality"] = quality
        if image_format == "JPEG":
            kwargs["subsampling"] = 0
    elif image_format == "TIFF":
        kwargs["compression"] = "tiff_lzw"

    return kwargs


def split_image_vertically(image: Any, slice_count: int) -> list[Any]:
    """Split an image into equal-height vertical slices."""
    bounds = calculate_vertical_bounds(image.height, slice_count)
    return [image.crop((0, top, image.width, bottom)) for top, bottom in bounds]


def split_image_horizontally(image: Any, slice_count: int) -> list[Any]:
    """Split an image into equal-width horizontal slices."""
    bounds = calculate_horizontal_bounds(image.width, slice_count)
    return [image.crop((left, 0, right, image.height)) for left, right in bounds]


def split_image(image: Any, slice_count: int, orientation: str) -> list[Any]:
    """Split an image in the requested orientation."""
    if orientation == "horizontal":
        return split_image_horizontally(image, slice_count)
    if orientation == "vertical":
        return split_image_vertically(image, slice_count)
    raise ScriptError(f"Unsupported split orientation: {orientation}")


def save_split_images(
    image: Any,
    image_format: str,
    output_paths: Sequence[Path],
    *,
    orientation: str = "vertical",
    quality: int = DEFAULT_JPEG_QUALITY,
) -> None:
    """Save split image slices to their final output paths."""
    slices = split_image(image, len(output_paths), orientation)
    save_kwargs = get_save_kwargs(image, image_format, quality=quality)

    for output_path, image_slice in zip(output_paths, slices, strict=True):
        with temporary_output_path(output_path) as temporary_path:
            image_slice.save(temporary_path, **save_kwargs)


def process_image(image_path: Path, slice_count: int, *, orientation: str, overwrite: bool, quality: int) -> list[Path]:
    """Split one image and return the written output paths."""
    resolved_image_path = require_existing_file(image_path, label="Image", suffixes=SUPPORTED_SUFFIXES)
    image, image_format = load_image(resolved_image_path)
    output_paths = resolve_output_paths(resolved_image_path, slice_count, overwrite=overwrite)
    save_split_images(image, image_format, output_paths, orientation=orientation, quality=quality)
    return output_paths


def run(args: argparse.Namespace) -> int:
    """Run the command."""
    configure_logging(quiet=args.quiet, debug=args.debug)
    require_int_range(args.quality, label="JPEG/WebP quality", minimum=1, maximum=100)

    written_paths: list[Path] = []
    for image_path in args.images:
        output_paths = process_image(
            image_path,
            args.count,
            orientation=args.orientation,
            overwrite=args.overwrite,
            quality=args.quality,
        )
        written_paths.extend(output_paths)
        logging.info("Split %s into %d images.", image_path, len(output_paths))

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
