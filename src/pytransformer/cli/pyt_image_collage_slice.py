#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_image_collage_slice.py
Purpose: Create a high-resolution sliced collage by cycling strips from two or more images.
When to use: Use when same-aspect-ratio images should be interleaved into vertical or horizontal slices.
Changes: Writes one JPEG, PNG, TIFF, or WebP collage to the current working directory.
Inputs: Strip size in pixels and two or more JPEG, PNG, TIFF, or WebP image paths; optional output, format,
quality, and slicing flags.
Environment variables: None.
Dependencies: pillow.
Safety notes: Validates images, applies EXIF orientation, resizes smaller images, preserves available
ICC/resolution metadata, and avoids overwrites by default.
Example: pyt-image-collage-slice --horizontal --webp --output collage.webp 10 image-a.webp image-b.webp image-c.webp
Expected result: An image named image-a+image-b+image-c-10px-strips.jpg in the current working directory.
Related scripts: pyt_image_split.py, pyt_jpeg_show_metadata.py, pyt_jpeg_strip_metadata.py.
"""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from pytransformer.core.common import (
    ScriptError,
    build_command_parser,
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

ASPECT_RATIO_REL_TOLERANCE = 0.001
DEFAULT_JPEG_QUALITY = 100
MAX_OUTPUT_FILENAME_LENGTH = 240
SUPPORTED_INPUT_FORMATS = {"JPEG", "PNG", "TIFF", "WEBP"}
SUPPORTED_INPUT_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
SUPPORTED_OUTPUT_FORMATS = {"jpeg", "png", "tiff", "webp"}
OUTPUT_FORMAT_EXTENSIONS = {"jpeg": "jpg", "png": "png", "tiff": "tif", "webp": "webp"}
OUTPUT_FORMAT_SUFFIXES = {
    "jpeg": {".jpg", ".jpeg"},
    "png": {".png"},
    "tiff": {".tif", ".tiff"},
    "webp": {".webp"},
}


@dataclass(frozen=True)
class ResolutionMetadata:
    """Resolution metadata carried by a JPEG input."""

    dpi: tuple[float, float] | None
    jfif_unit: int | None = None
    jfif_density: tuple[int, int] | None = None


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
        description="Create a high-resolution image collage by cycling strips from two or more images.",
        examples=(
            "pyt-image-collage-slice 10 image-a.jpg image-b.png",
            "pyt-image-collage-slice --vertical 10 image-a.jpg image-b.webp",
            "pyt-image-collage-slice --horizontal 10 image-a.jpg image-b.png image-c.webp",
            "pyt-image-collage-slice --output collage.jpg --quality 90 10 image-a.jpg image-b.png",
            "pyt-image-collage-slice --png --output collage.png 10 image-a.jpg image-b.webp",
            "pyt-image-collage-slice --tiff --output collage.tif 10 image-a.png image-b.webp",
            "pyt-image-collage-slice --webp --output collage.webp 10 image-a.png image-b.webp",
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
    parser.add_argument(
        "images",
        type=Path,
        nargs="+",
        help="Paths to two or more JPEG, PNG, TIFF, or WebP images.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output image path. Defaults to a generated filename in the current working directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output file.",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=DEFAULT_JPEG_QUALITY,
        help=(
            "JPEG and WebP output quality from 1 to 100. "
            f"Ignored for --png and --tiff. Default: {DEFAULT_JPEG_QUALITY}."
        ),
    )
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument(
        "--png",
        action="store_true",
        help="Save a lossless PNG instead of a high-quality JPEG.",
    )
    format_group.add_argument(
        "--tiff",
        action="store_true",
        help="Save a lossless TIFF instead of a high-quality JPEG.",
    )
    format_group.add_argument(
        "--webp",
        action="store_true",
        help="Save a WebP instead of a high-quality JPEG.",
    )

    return parser


def require_pillow() -> None:
    """Require Pillow before using image APIs."""
    if Image is None or ImageOps is None:
        raise ScriptError("Pillow is required. Install it with: python -m pip install Pillow")


def load_image(path: Path, *, label: str) -> Any:
    """Load a supported image, apply EXIF orientation, and return an RGB Pillow image."""
    require_pillow()

    try:
        with Image.open(path) as probe:
            detected_format = probe.format
            if detected_format not in SUPPORTED_INPUT_FORMATS:
                supported = ", ".join(sorted(SUPPORTED_INPUT_FORMATS))
                raise ScriptError(
                    f"The {label} is not a supported image. Detected format: {detected_format or 'unknown'}. "
                    f"Supported formats: {supported}."
                )
            probe.verify()

        with Image.open(path) as image:
            if image.format not in SUPPORTED_INPUT_FORMATS:
                raise ScriptError(f"The {label} is not a supported image after reopening: {path}")

            corrected = ImageOps.exif_transpose(image)
            corrected.load()
            return corrected.convert("RGB")

    except UnidentifiedImageError as exc:
        raise ScriptError(f"The {label} cannot be opened as a valid image: {path}") from exc
    except OSError as exc:
        raise ScriptError(f"The {label} could not be read as a valid image: {path}") from exc


def require_at_least_two_images(image_paths: Sequence[Path]) -> None:
    """Require at least two image paths."""
    if len(image_paths) < 2:
        raise ScriptError("At least two image files are required.")


def validate_same_aspect_ratio(images: Sequence[Any]) -> None:
    """Require all images to have the same aspect ratio within a small tolerance."""
    if not images:
        raise ScriptError("At least one image is required for aspect-ratio validation.")

    base_width, base_height = images[0].size
    base_ratio = base_width / base_height

    for image_index, image in enumerate(images[1:], start=2):
        width, height = image.size
        ratio = width / height

        if not math.isclose(
            base_ratio,
            ratio,
            rel_tol=ASPECT_RATIO_REL_TOLERANCE,
            abs_tol=ASPECT_RATIO_REL_TOLERANCE,
        ):
            raise ScriptError(
                "The input images do not have the same aspect ratio.\n"
                f"First image size: {base_width}x{base_height}, ratio: {base_ratio:.6f}\n"
                f"Image {image_index} size: {width}x{height}, ratio: {ratio:.6f}"
            )


def choose_target_size(images: Sequence[Any]) -> tuple[int, int]:
    """Return the size of the largest image by pixel area."""
    if not images:
        raise ScriptError("At least one image is required to choose a target size.")

    largest_image = max(images, key=lambda image: image.width * image.height)
    return largest_image.size


def get_lanczos_filter() -> Any:
    """Return the Pillow LANCZOS resampling constant across Pillow versions."""
    require_pillow()
    try:
        return Image.Resampling.LANCZOS
    except AttributeError:
        return Image.LANCZOS


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


def get_first_icc_profile(images: Sequence[Any]) -> bytes | None:
    """Return the first embedded ICC profile found in the input images."""
    for image in images:
        icc_profile = image.info.get("icc_profile")
        if isinstance(icc_profile, bytes) and icc_profile:
            return icc_profile
    return None


def _parse_dpi(value: Any) -> tuple[float, float] | None:
    """Return a finite, positive DPI pair or None for malformed metadata."""
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        return None

    x_dpi, y_dpi = value
    if (
        isinstance(x_dpi, (int, float))
        and not isinstance(x_dpi, bool)
        and isinstance(y_dpi, (int, float))
        and not isinstance(y_dpi, bool)
        and math.isfinite(x_dpi)
        and math.isfinite(y_dpi)
        and x_dpi > 0
        and y_dpi > 0
    ):
        return float(x_dpi), float(y_dpi)

    return None


def _parse_jfif_resolution(info: dict[str, Any]) -> tuple[int | None, tuple[int, int] | None]:
    """Return valid JFIF units and density values from Pillow image info."""
    unit = info.get("jfif_unit")
    density = info.get("jfif_density")
    if not isinstance(unit, int) or isinstance(unit, bool) or unit not in {0, 1, 2}:
        return None, None
    if (
        not isinstance(density, (tuple, list))
        or len(density) != 2
        or any(not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 65535 for value in density)
    ):
        return unit, None

    return unit, (density[0], density[1])


def get_first_resolution_metadata(images: Sequence[Any]) -> ResolutionMetadata | None:
    """Return the first usable resolution metadata found in the input images."""
    parsed_resolutions: list[tuple[tuple[float, float] | None, int | None, tuple[int, int] | None]] = []
    for image in images:
        info = image.info
        dpi = _parse_dpi(info.get("dpi"))
        jfif_unit, jfif_density = _parse_jfif_resolution(info)
        parsed_resolutions.append((dpi, jfif_unit, jfif_density))

    for dpi, jfif_unit, jfif_density in parsed_resolutions:
        if dpi is not None:
            return ResolutionMetadata(dpi, jfif_unit, jfif_density)

    for dpi, jfif_unit, jfif_density in parsed_resolutions:
        if dpi is not None or jfif_density is None or jfif_unit is None:
            continue

        if jfif_unit == 0:
            converted_dpi = None
        elif jfif_unit == 1:
            density_x, density_y = jfif_density
            converted_dpi = (float(density_x), float(density_y))
        else:
            density_x, density_y = jfif_density
            converted_dpi = (density_x * 2.54, density_y * 2.54)
        return ResolutionMetadata(converted_dpi, jfif_unit, jfif_density)

    return None


def get_first_dpi(images: Sequence[Any]) -> tuple[float, float] | None:
    """Return the first usable DPI metadata found in the input images."""
    resolution = get_first_resolution_metadata(images)
    return None if resolution is None else resolution.dpi


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


def build_output_filename_parts(image_paths: Sequence[Path]) -> list[str]:
    """Return sanitized filename parts derived from input image stems."""
    return [
        sanitize_filename_part(image_path.stem, fallback=f"image{index}")
        for index, image_path in enumerate(image_paths, start=1)
    ]


def shorten_filename_parts(filename_parts: Sequence[str], suffix: str, separator: str) -> list[str]:
    """Shorten filename parts enough to fit the configured output filename limit."""
    separators_length = len(separator) * (len(filename_parts) - 1)
    available_name_length = MAX_OUTPUT_FILENAME_LENGTH - separators_length - len(suffix)

    if available_name_length < len(filename_parts):
        raise ScriptError("The generated output filename is too long.")

    base_part_length = max(1, available_name_length // len(filename_parts))
    remaining_length = max(0, available_name_length - (base_part_length * len(filename_parts)))

    shortened_parts = []
    for index, filename_part in enumerate(filename_parts, start=1):
        part_length = base_part_length + (1 if remaining_length > 0 else 0)
        remaining_length = max(0, remaining_length - 1)
        shortened_parts.append(filename_part[:part_length].rstrip(" ._") or f"image{index}")

    return shortened_parts


def generate_output_path(image_paths: Sequence[Path], strip_size: int, *, output_format: str = "jpeg") -> Path:
    """Generate a portable output filename in the current working directory."""
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ScriptError(f"Unsupported output format: {output_format}")

    filename_parts = build_output_filename_parts(image_paths)
    extension = OUTPUT_FORMAT_EXTENSIONS[output_format]
    suffix = f"-{strip_size}px-strips.{extension}"
    separator = "+"

    output_filename = f"{separator.join(filename_parts)}{suffix}"

    if len(output_filename) > MAX_OUTPUT_FILENAME_LENGTH:
        filename_parts = shorten_filename_parts(filename_parts, suffix, separator)
        output_filename = f"{separator.join(filename_parts)}{suffix}"

    return Path.cwd() / output_filename


def resolve_output_path(
    requested_output_path: Path | None,
    generated_output_path: Path,
    image_paths: Sequence[Path],
    *,
    overwrite: bool,
    output_format: str = "jpeg",
) -> Path:
    """Resolve and validate the output path."""
    output_path = generated_output_path if requested_output_path is None else requested_output_path
    validate_output_extension(output_path, output_format=output_format)
    if output_path.expanduser().exists() and output_path.expanduser().is_dir():
        raise ScriptError(f"Output path is a directory, not a file: {output_path.expanduser().resolve()}")

    return ensure_output_path(
        output_path,
        overwrite=overwrite,
        input_paths=image_paths,
        label="Output file",
    )


def validate_output_extension(output_path: Path, *, output_format: str) -> None:
    """Reject known image extensions that disagree with the selected output format."""
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ScriptError(f"Unsupported output format: {output_format}")

    suffix = output_path.suffix.lower()
    if not suffix:
        return

    for candidate_format, suffixes in OUTPUT_FORMAT_SUFFIXES.items():
        if suffix in suffixes and candidate_format != output_format:
            expected = ", ".join(sorted(OUTPUT_FORMAT_SUFFIXES[output_format]))
            raise ScriptError(
                f"Output file extension '{suffix}' does not match {output_format} output. Use one of: {expected}."
            )


def validate_same_size(images: Sequence[Any]) -> None:
    """Require all images to have the same pixel size."""
    if not images:
        raise ScriptError("Internal error: at least one image is required before collage generation.")

    expected_size = images[0].size
    if any(image.size != expected_size for image in images[1:]):
        raise ScriptError("Internal error: images must be the same size before collage generation.")


def create_vertical_sliced_collage(images: Sequence[Any], strip_size: int) -> Any:
    """Create a collage by cycling vertical strips from same-size images."""
    require_pillow()
    validate_same_size(images)
    width, height = images[0].size

    if strip_size > width:
        raise ScriptError(
            f"The requested vertical strip size is too large for the image width. "
            f"Image width: {width}px. Strip size: {strip_size}px."
        )

    output = Image.new("RGB", (width, height))

    for x in range(0, width, strip_size):
        right = min(x + strip_size, width)
        strip_index = x // strip_size
        source_image = images[strip_index % len(images)]
        strip = source_image.crop((x, 0, right, height))
        output.paste(strip, (x, 0))

    return output


def create_horizontal_sliced_collage(images: Sequence[Any], strip_size: int) -> Any:
    """Create a collage by cycling horizontal strips from same-size images."""
    require_pillow()
    validate_same_size(images)
    width, height = images[0].size

    if strip_size > height:
        raise ScriptError(
            f"The requested horizontal strip size is too large for the image height. "
            f"Image height: {height}px. Strip size: {strip_size}px."
        )

    output = Image.new("RGB", (width, height))

    for y in range(0, height, strip_size):
        bottom = min(y + strip_size, height)
        strip_index = y // strip_size
        source_image = images[strip_index % len(images)]
        strip = source_image.crop((0, y, width, bottom))
        output.paste(strip, (0, y))

    return output


def create_sliced_collage(images: Sequence[Any], strip_size: int, orientation: str) -> Any:
    """Create a sliced collage in the requested orientation."""
    validate_same_size(images)

    if orientation == "horizontal":
        return create_horizontal_sliced_collage(images, strip_size)
    if orientation == "vertical":
        return create_vertical_sliced_collage(images, strip_size)

    raise ScriptError(f"Unsupported slicing orientation: {orientation}")


def save_jpeg(
    image: Any,
    output_path: Path,
    *,
    quality: int = DEFAULT_JPEG_QUALITY,
    icc_profile: bytes | None = None,
    dpi: tuple[float, float] | None = None,
    resolution: ResolutionMetadata | None = None,
) -> None:
    """Save the output collage as a high-quality progressive JPEG."""
    require_int_range(quality, label="JPEG quality", minimum=1, maximum=100)
    if dpi is None and resolution is not None:
        dpi = resolution.dpi

    save_kwargs: dict[str, Any] = {
        "format": "JPEG",
        "quality": quality,
        "optimize": True,
        "progressive": True,
        "subsampling": 0,
    }

    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile

    if dpi is not None:
        save_kwargs["dpi"] = dpi

    try:
        image.save(output_path, **save_kwargs)
        if resolution is not None and resolution.jfif_unit is not None and resolution.jfif_density is not None:
            preserve_jfif_resolution(output_path, resolution.jfif_unit, resolution.jfif_density)
    except PermissionError as exc:
        raise ScriptError(f"The output file cannot be written because of a permission error: {output_path}") from exc
    except (OSError, ValueError) as exc:
        raise ScriptError(f"The output file could not be saved: {output_path}") from exc


def save_png(
    image: Any,
    output_path: Path,
    *,
    icc_profile: bytes | None = None,
    dpi: tuple[float, float] | None = None,
) -> None:
    """Save the output collage as a lossless PNG."""
    save_kwargs: dict[str, Any] = {
        "format": "PNG",
        "optimize": True,
    }

    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile

    if dpi is not None:
        save_kwargs["dpi"] = dpi

    try:
        image.save(output_path, **save_kwargs)
    except PermissionError as exc:
        raise ScriptError(f"The output file cannot be written because of a permission error: {output_path}") from exc
    except (OSError, ValueError) as exc:
        raise ScriptError(f"The output file could not be saved: {output_path}") from exc


def save_tiff(
    image: Any,
    output_path: Path,
    *,
    icc_profile: bytes | None = None,
    dpi: tuple[float, float] | None = None,
) -> None:
    """Save the output collage as a lossless TIFF."""
    save_kwargs: dict[str, Any] = {
        "format": "TIFF",
        "compression": "tiff_lzw",
    }

    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile

    if dpi is not None:
        save_kwargs["dpi"] = dpi

    try:
        image.save(output_path, **save_kwargs)
    except PermissionError as exc:
        raise ScriptError(f"The output file cannot be written because of a permission error: {output_path}") from exc
    except (OSError, ValueError) as exc:
        raise ScriptError(f"The output file could not be saved: {output_path}") from exc


def save_webp(
    image: Any,
    output_path: Path,
    *,
    quality: int = DEFAULT_JPEG_QUALITY,
    icc_profile: bytes | None = None,
    dpi: tuple[float, float] | None = None,
) -> None:
    """Save the output collage as a WebP image."""
    require_int_range(quality, label="WebP quality", minimum=1, maximum=100)
    save_kwargs: dict[str, Any] = {
        "format": "WEBP",
        "quality": quality,
    }

    if icc_profile is not None:
        save_kwargs["icc_profile"] = icc_profile

    if dpi is not None:
        save_kwargs["dpi"] = dpi

    try:
        image.save(output_path, **save_kwargs)
    except PermissionError as exc:
        raise ScriptError(f"The output file cannot be written because of a permission error: {output_path}") from exc
    except (OSError, ValueError) as exc:
        raise ScriptError(f"The output file could not be saved: {output_path}") from exc


def save_output_image(
    image: Any,
    output_path: Path,
    *,
    output_format: str,
    quality: int,
    icc_profile: bytes | None,
    dpi: tuple[float, float] | None,
    resolution: ResolutionMetadata | None = None,
) -> None:
    """Save the output collage in the requested format."""
    if output_format == "png":
        save_png(image, output_path, icc_profile=icc_profile, dpi=dpi)
        return
    if output_format == "tiff":
        save_tiff(image, output_path, icc_profile=icc_profile, dpi=dpi)
        return
    if output_format == "webp":
        save_webp(image, output_path, quality=quality, icc_profile=icc_profile, dpi=dpi)
        return

    if output_format != "jpeg":
        raise ScriptError(f"Unsupported output format: {output_format}")

    save_jpeg(image, output_path, quality=quality, icc_profile=icc_profile, dpi=dpi, resolution=resolution)


def preserve_jfif_resolution(output_path: Path, unit: int, density: tuple[int, int]) -> None:
    """Restore a source JPEG's JFIF resolution unit and exact density after Pillow saves it."""
    if unit not in {0, 1, 2}:
        raise ScriptError(f"Unsupported JPEG resolution unit: {unit}")
    if any(not isinstance(value, int) or not 0 <= value <= 65535 for value in density):
        raise ScriptError("JPEG resolution density values must be integers from 0 to 65535.")

    raw = bytearray(output_path.read_bytes())
    if raw[:2] != b"\xff\xd8":
        raise ScriptError(f"The saved JPEG has an invalid file header: {output_path}")

    offset = 2
    while offset + 4 <= len(raw):
        if raw[offset] != 0xFF:
            offset += 1
            continue

        marker = raw[offset + 1]
        if marker == 0xDA or marker == 0xD9:
            break
        if marker == 0xFF:
            offset += 1
            continue

        segment_length = int.from_bytes(raw[offset + 2 : offset + 4], "big")
        segment_end = offset + 2 + segment_length
        if segment_length < 2 or segment_end > len(raw):
            break

        payload_start = offset + 4
        if marker == 0xE0 and raw[payload_start : payload_start + 5] == b"JFIF\x00" and segment_length >= 16:
            unit_offset = payload_start + 7
            raw[unit_offset] = unit
            raw[unit_offset + 1 : unit_offset + 3] = density[0].to_bytes(2, "big")
            raw[unit_offset + 3 : unit_offset + 5] = density[1].to_bytes(2, "big")
            try:
                output_path.write_bytes(raw)
            except OSError as exc:
                raise ScriptError(f"The JPEG resolution metadata could not be preserved: {output_path}") from exc
            return

        offset = segment_end

    raise ScriptError(f"The saved JPEG does not contain a JFIF resolution segment: {output_path}")


def close_images(images: Sequence[Any]) -> None:
    """Close Pillow images while tolerating already-closed or test-double objects."""
    for image in images:
        close = getattr(image, "close", None)
        if close is not None:
            close()


def resolve_requested_output_format(*, png: bool, tiff: bool, webp: bool) -> str:
    """Return the selected output format from the mutually exclusive CLI flags."""
    if png:
        return "png"
    if tiff:
        return "tiff"
    if webp:
        return "webp"
    return "jpeg"


def main() -> int:
    """Main script entry point."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        output_format = resolve_requested_output_format(png=args.png, tiff=args.tiff, webp=args.webp)
        if output_format in {"jpeg", "webp"}:
            require_int_range(args.quality, label="JPEG/WebP quality", minimum=1, maximum=100)
        require_at_least_two_images(args.images)
        image_paths = [
            require_existing_file(image_path, label=f"Image {index}", suffixes=SUPPORTED_INPUT_SUFFIXES)
            for index, image_path in enumerate(args.images, start=1)
        ]

        images: list[Any] = []
        output_image: Any | None = None
        try:
            for index, image_path in enumerate(image_paths, start=1):
                images.append(load_image(image_path, label=f"image {index}"))

            validate_same_aspect_ratio(images)
            target_size = choose_target_size(images)
            icc_profile = get_first_icc_profile(images)
            resolution = get_first_resolution_metadata(images)
            dpi = None if resolution is None else resolution.dpi

            resized_images = [
                resize_to_target(image, target_size, label=f"image {index}")
                for index, image in enumerate(images, start=1)
            ]
            for original, resized in zip(images, resized_images, strict=True):
                if resized is not original:
                    original.close()
            images = resized_images

            output_image = create_sliced_collage(images, args.strip_size, args.orientation)
            output_path = resolve_output_path(
                args.output,
                generate_output_path(image_paths, args.strip_size, output_format=output_format),
                image_paths,
                overwrite=args.overwrite,
                output_format=output_format,
            )

            with temporary_output_path(output_path) as temporary_path:
                save_output_image(
                    output_image,
                    temporary_path,
                    output_format=output_format,
                    quality=args.quality,
                    icc_profile=icc_profile,
                    dpi=dpi,
                    resolution=resolution,
                )
        finally:
            if output_image is not None:
                output_image.close()
            close_images(images)
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
