#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_jpeg_sliced_collage.py
Purpose: Create a high-resolution JPEG collage by alternating strips from two JPEG images.
When to use: Use when two same-aspect-ratio JPEG images should be interleaved into vertical or horizontal slices.
Changes: Writes one JPEG collage to the current working directory.
Inputs: Strip size in pixels and two JPEG image paths; optional --vertical or --horizontal slicing.
Environment variables: None.
Dependencies: pillow.
Safety notes: Validates both input images, applies EXIF orientation, and resizes the smaller image to match the larger.
Example: pyt-jpeg-sliced-collage --horizontal 10 image-a.jpg image-b.jpg
Expected result: A JPEG named image-a+image-b-10px-strips.jpg in the current working directory.
Related scripts: pyt_jpeg_show_metadata.py, pyt_jpeg_strip_metadata.py.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

from pytransformer.core.common import ScriptError, build_command_parser, fail, require_existing_file

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:  # pragma: no cover - exercised only when optional dependency is missing.
    Image = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]
    UnidentifiedImageError = OSError  # type: ignore[misc,assignment]

ASPECT_RATIO_REL_TOLERANCE = 0.001
JPEG_QUALITY = 95
MAX_OUTPUT_FILENAME_LENGTH = 240

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED_NAMES = {
    "AUX",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "CON",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
    "NUL",
    "PRN",
}


def parse_positive_integer(value: str) -> int:
    """Parse a strictly positive base-10 integer."""
    if not re.fullmatch(r"[0-9]+", value):
        raise argparse.ArgumentTypeError(f"The strip size must be a positive integer. Received: {value!r}")

    strip_size = int(value)
    if strip_size <= 0:
        raise argparse.ArgumentTypeError(f"The strip size must be greater than zero. Received: {strip_size}")

    return strip_size


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = build_command_parser(
        description="Create a high-resolution JPEG collage by alternating strips from two JPEG images.",
        examples=(
            "pyt-jpeg-sliced-collage 10 image-a.jpg image-b.jpg",
            "pyt-jpeg-sliced-collage --vertical 10 image-a.jpg image-b.jpg",
            "pyt-jpeg-sliced-collage --horizontal 10 image-a.jpg image-b.jpg",
        ),
    )

    direction_group = parser.add_mutually_exclusive_group()
    direction_group.add_argument(
        "--horizontal",
        action="store_const",
        const="horizontal",
        dest="orientation",
        help="Slice the images into horizontal strips.",
    )
    direction_group.add_argument(
        "--vertical",
        action="store_const",
        const="vertical",
        dest="orientation",
        help="Slice the images into vertical strips. This is the default.",
    )
    parser.set_defaults(orientation="vertical")

    parser.add_argument(
        "strip_size",
        type=parse_positive_integer,
        help=(
            "Positive integer strip size in pixels. For vertical slicing, this is strip width. "
            "For horizontal slicing, this is strip height."
        ),
    )
    parser.add_argument("image_1", type=Path, help="Path to the first JPEG image.")
    parser.add_argument("image_2", type=Path, help="Path to the second JPEG image.")

    return parser


def require_pillow() -> None:
    """Require Pillow before using image APIs."""
    if Image is None or ImageOps is None:
        raise ScriptError("Pillow is required. Install it with: python -m pip install Pillow")


def load_jpeg_image(path: Path, *, label: str) -> Any:
    """Load a JPEG image, apply EXIF orientation, and return an RGB Pillow image."""
    require_pillow()

    try:
        with Image.open(path) as probe:
            detected_format = probe.format
            if detected_format != "JPEG":
                raise ScriptError(f"The {label} is not a JPEG image. Detected format: {detected_format or 'unknown'}")
            probe.verify()

        with Image.open(path) as image:
            if image.format != "JPEG":
                raise ScriptError(f"The {label} is not a JPEG image after reopening: {path}")

            corrected = ImageOps.exif_transpose(image)
            corrected.load()
            return corrected.convert("RGB")

    except UnidentifiedImageError as exc:
        raise ScriptError(f"The {label} cannot be opened as a valid image: {path}") from exc
    except OSError as exc:
        raise ScriptError(f"The {label} could not be read as a valid JPEG: {path}") from exc


def validate_same_aspect_ratio(image_1: Any, image_2: Any) -> None:
    """Require two images to have the same aspect ratio within a small tolerance."""
    width_1, height_1 = image_1.size
    width_2, height_2 = image_2.size

    ratio_1 = width_1 / height_1
    ratio_2 = width_2 / height_2

    if not math.isclose(
        ratio_1,
        ratio_2,
        rel_tol=ASPECT_RATIO_REL_TOLERANCE,
        abs_tol=ASPECT_RATIO_REL_TOLERANCE,
    ):
        raise ScriptError(
            "The two images do not have the same aspect ratio.\n"
            f"First image size: {width_1}x{height_1}, ratio: {ratio_1:.6f}\n"
            f"Second image size: {width_2}x{height_2}, ratio: {ratio_2:.6f}"
        )


def choose_target_size(image_1: Any, image_2: Any) -> tuple[int, int]:
    """Return the size of the larger image by pixel area."""
    area_1 = image_1.width * image_1.height
    area_2 = image_2.width * image_2.height

    if area_1 >= area_2:
        return image_1.size
    return image_2.size


def get_lanczos_filter() -> Any:
    """Return the Pillow LANCZOS resampling constant across Pillow versions."""
    require_pillow()
    try:
        return Image.Resampling.LANCZOS
    except AttributeError:
        return Image.LANCZOS  # type: ignore[attr-defined]


def resize_to_target(image: Any, target_size: tuple[int, int], *, label: str) -> Any:
    """Resize an image to the target size when needed."""
    if image.size == target_size:
        return image

    try:
        return image.resize(target_size, get_lanczos_filter())
    except OSError as exc:
        raise ScriptError(
            f"The {label} has the same aspect ratio but could not be resized to {target_size[0]}x{target_size[1]}."
        ) from exc


def sanitize_filename_part(value: str, *, fallback: str) -> str:
    """Make one generated filename segment portable across common filesystems."""
    sanitized = INVALID_FILENAME_CHARS.sub("_", value)
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.strip(" .")

    if not sanitized:
        sanitized = fallback

    if sanitized.upper() in WINDOWS_RESERVED_NAMES:
        sanitized = f"{sanitized}_file"

    return sanitized


def generate_output_path(image_path_1: Path, image_path_2: Path, strip_size: int) -> Path:
    """Generate the historical output filename in the current working directory."""
    filename_1 = sanitize_filename_part(image_path_1.stem, fallback="image1")
    filename_2 = sanitize_filename_part(image_path_2.stem, fallback="image2")

    suffix = f"-{strip_size}px-strips.jpg"
    separator = "+"

    output_filename = f"{filename_1}{separator}{filename_2}{suffix}"

    if len(output_filename) > MAX_OUTPUT_FILENAME_LENGTH:
        available_length = MAX_OUTPUT_FILENAME_LENGTH - len(separator) - len(suffix)

        if available_length < 2:
            raise ScriptError("The generated output filename is too long.")

        filename_1_length = max(1, available_length // 2)
        filename_2_length = max(1, available_length - filename_1_length)

        filename_1 = filename_1[:filename_1_length].rstrip(" ._") or "image1"
        filename_2 = filename_2[:filename_2_length].rstrip(" ._") or "image2"

        output_filename = f"{filename_1}{separator}{filename_2}{suffix}"

    return Path.cwd() / output_filename


def create_vertical_sliced_collage(image_1: Any, image_2: Any, strip_size: int) -> Any:
    """Create a collage by alternating vertical strips from two same-size images."""
    require_pillow()
    width, height = image_1.size

    if strip_size > width:
        raise ScriptError(
            f"The requested vertical strip size is too large for the image width. "
            f"Image width: {width}px. Strip size: {strip_size}px."
        )

    output = Image.new("RGB", (width, height))

    for x in range(0, width, strip_size):
        right = min(x + strip_size, width)
        strip_index = x // strip_size
        source_image = image_1 if strip_index % 2 == 0 else image_2
        strip = source_image.crop((x, 0, right, height))
        output.paste(strip, (x, 0))

    return output


def create_horizontal_sliced_collage(image_1: Any, image_2: Any, strip_size: int) -> Any:
    """Create a collage by alternating horizontal strips from two same-size images."""
    require_pillow()
    width, height = image_1.size

    if strip_size > height:
        raise ScriptError(
            f"The requested horizontal strip size is too large for the image height. "
            f"Image height: {height}px. Strip size: {strip_size}px."
        )

    output = Image.new("RGB", (width, height))

    for y in range(0, height, strip_size):
        bottom = min(y + strip_size, height)
        strip_index = y // strip_size
        source_image = image_1 if strip_index % 2 == 0 else image_2
        strip = source_image.crop((0, y, width, bottom))
        output.paste(strip, (0, y))

    return output


def create_sliced_collage(image_1: Any, image_2: Any, strip_size: int, orientation: str) -> Any:
    """Create a sliced collage in the requested orientation."""
    if image_1.size != image_2.size:
        raise ScriptError("Internal error: images must be the same size before collage generation.")

    if orientation == "horizontal":
        return create_horizontal_sliced_collage(image_1, image_2, strip_size)
    if orientation == "vertical":
        return create_vertical_sliced_collage(image_1, image_2, strip_size)

    raise ScriptError(f"Unsupported slicing orientation: {orientation}")


def save_jpeg(image: Any, output_path: Path) -> None:
    """Save the output collage as a high-quality progressive JPEG."""
    try:
        image.save(
            output_path,
            format="JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
            progressive=True,
        )
    except PermissionError as exc:
        raise ScriptError(f"The output file cannot be written because of a permission error: {output_path}") from exc
    except OSError as exc:
        raise ScriptError(f"The output file could not be saved: {output_path}") from exc


def main() -> int:
    """Main script entry point."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        image_path_1 = require_existing_file(args.image_1, label="First image")
        image_path_2 = require_existing_file(args.image_2, label="Second image")

        image_1 = load_jpeg_image(image_path_1, label="first image")
        image_2 = load_jpeg_image(image_path_2, label="second image")

        validate_same_aspect_ratio(image_1, image_2)
        target_size = choose_target_size(image_1, image_2)

        image_1 = resize_to_target(image_1, target_size, label="first image")
        image_2 = resize_to_target(image_2, target_size, label="second image")

        output_image = create_sliced_collage(
            image_1,
            image_2,
            args.strip_size,
            args.orientation,
        )
        output_path = generate_output_path(image_path_1, image_path_2, args.strip_size)

        save_jpeg(output_image, output_path)
    except ScriptError as error:
        return fail(str(error), code=1)
    except KeyboardInterrupt:
        return fail("Interrupted by user.", code=130)
    except MemoryError:
        return fail("Not enough memory to process these images at full resolution.", code=1)
    except Exception as error:
        return fail(f"Unexpected failure: {error}", code=1)

    print(f"Success: created {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
