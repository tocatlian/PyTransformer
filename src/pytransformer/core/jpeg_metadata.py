# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""Shared JPEG metadata helpers for PyTransformer commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import defusedxml  # noqa: F401

    HAS_DEFUSEDXML = True
except Exception:
    HAS_DEFUSEDXML = False


JPEG_EXTENSIONS = {".jpg", ".jpeg", ".jpe", ".jfif"}
MAX_DISPLAY_VALUE_LENGTH = 1000

Image: Any | None = None
ImageOps: Any | None = None
ExifTags: Any | None = None
IptcImagePlugin: Any | None = None
JpegImagePlugin: Any | None = None
PIL_IMPORT_ERROR: ImportError | None = None
PIL_IMPORT_ATTEMPTED = False


def load_pillow() -> bool:
    """Load Pillow lazily so standard-library commands still import without optional extras."""
    global ExifTags
    global Image
    global ImageOps
    global IptcImagePlugin
    global JpegImagePlugin
    global PIL_IMPORT_ATTEMPTED
    global PIL_IMPORT_ERROR

    if PIL_IMPORT_ATTEMPTED:
        return Image is not None

    PIL_IMPORT_ATTEMPTED = True
    try:
        from PIL import ExifTags as pillow_exif_tags
        from PIL import Image as pillow_image
        from PIL import ImageOps as pillow_image_ops
        from PIL import IptcImagePlugin as pillow_iptc_image_plugin
        from PIL import JpegImagePlugin as pillow_jpeg_image_plugin
    except ImportError as exc:
        PIL_IMPORT_ERROR = exc
        return False

    ExifTags = pillow_exif_tags
    Image = pillow_image
    ImageOps = pillow_image_ops
    IptcImagePlugin = pillow_iptc_image_plugin
    JpegImagePlugin = pillow_jpeg_image_plugin
    return True


def require_pillow() -> None:
    """Raise a consistent error when JPEG commands run without Pillow installed."""
    if not load_pillow():
        raise RuntimeError("Pillow is required. Install it with: pip install pillow") from PIL_IMPORT_ERROR


def flatten_dict(prefix: str, value: Any) -> dict[str, str]:
    """Flatten nested metadata mappings into dot-delimited display keys."""
    output: dict[str, str] = {}

    def _walk(current_prefix: str, item: Any) -> None:
        if isinstance(item, dict):
            if not item:
                output[current_prefix] = "{}"
                return
            for key, sub_value in item.items():
                key_str = str(key)
                next_prefix = f"{current_prefix}.{key_str}" if current_prefix else key_str
                _walk(next_prefix, sub_value)
        elif isinstance(item, (list, tuple)):
            if not item:
                output[current_prefix] = "[]"
                return
            for index, sub_value in enumerate(item):
                next_prefix = f"{current_prefix}[{index}]"
                _walk(next_prefix, sub_value)
        elif isinstance(item, bytes):
            output[current_prefix] = f"<bytes length={len(item)}>"
        else:
            output[current_prefix] = repr(item)

    _walk(prefix, value)
    return output


def get_exif_map(image: Any) -> dict[str, str]:
    """Collect standard, GPS, EXIF sub-IFD, and interoperability EXIF fields."""
    result: dict[str, str] = {}
    exif_tags = ExifTags
    if exif_tags is None:
        return result

    try:
        exif = image.getexif()
    except Exception:
        return result

    if not exif:
        return result

    for tag_id, value in exif.items():
        tag_name = exif_tags.TAGS.get(tag_id, f"UnknownTag_{tag_id}")
        result[f"EXIF.{tag_name}"] = repr(value)

    try:
        gps_ifd = exif.get_ifd(0x8825)
        if gps_ifd:
            for tag_id, value in gps_ifd.items():
                tag_name = exif_tags.GPSTAGS.get(tag_id, f"UnknownGPSTag_{tag_id}")
                result[f"EXIF.GPS.{tag_name}"] = repr(value)
    except Exception:
        pass

    try:
        exif_ifd = exif.get_ifd(0x8769)
        if exif_ifd:
            for tag_id, value in exif_ifd.items():
                tag_name = exif_tags.TAGS.get(tag_id, f"UnknownExifIFDTag_{tag_id}")
                result[f"EXIF.SubIFD.{tag_name}"] = repr(value)
    except Exception:
        pass

    try:
        interop_ifd = exif.get_ifd(0xA005)
        if interop_ifd:
            for tag_id, value in interop_ifd.items():
                tag_name = exif_tags.TAGS.get(tag_id, f"UnknownInteropTag_{tag_id}")
                result[f"EXIF.Interop.{tag_name}"] = repr(value)
    except Exception:
        pass

    return result


def get_xmp_map(image: Any) -> dict[str, str]:
    """Collect XMP fields when defusedxml is available for Pillow's XMP parser."""
    if not HAS_DEFUSEDXML:
        return {}

    try:
        xmp = image.getxmp()
    except Exception:
        return {}

    if not xmp:
        return {}

    return flatten_dict("XMP", xmp)


def get_iptc_map(image: Any) -> dict[str, str]:
    """Collect IPTC metadata fields."""
    result: dict[str, str] = {}
    iptc_plugin = IptcImagePlugin
    if iptc_plugin is None:
        return result

    try:
        iptc = iptc_plugin.getiptcinfo(image)
    except Exception:
        return result

    if not iptc:
        return result

    for key, value in iptc.items():
        result[f"IPTC.{key}"] = repr(value)

    return result


def get_info_map(image: Any) -> dict[str, str]:
    """Collect Pillow image info fields without printing raw binary values."""
    result: dict[str, str] = {}
    info = dict(image.info or {})

    for key, value in info.items():
        if key == "exif" and isinstance(value, bytes):
            result["INFO.exif_raw"] = f"<bytes length={len(value)}>"
        elif key == "icc_profile" and isinstance(value, bytes):
            result["INFO.icc_profile"] = f"<bytes length={len(value)}>"
        elif key == "comment":
            result["INFO.comment"] = repr(value)
        elif isinstance(value, bytes):
            result[f"INFO.{key}"] = f"<bytes length={len(value)}>"
        else:
            result[f"INFO.{key}"] = repr(value)

    return result


def inspect_embedded_metadata(path: Path, *, input_label: str = "File") -> dict[str, str]:
    """Return sorted embedded JPEG metadata for a file."""
    require_pillow()
    image_module = Image
    if image_module is None:
        raise RuntimeError("Pillow is required. Install it with: pip install pillow")

    with image_module.open(path) as image:
        if image.format != "JPEG":
            raise ValueError(f"{input_label} is not a JPEG according to Pillow: {path.name}")

        metadata: dict[str, str] = {}
        metadata.update(get_info_map(image))
        metadata.update(get_exif_map(image))
        metadata.update(get_xmp_map(image))
        metadata.update(get_iptc_map(image))
        return dict(sorted(metadata.items(), key=lambda kv: kv[0]))


def format_display_value(value: str, full_values: bool) -> str:
    """Truncate long metadata values for terminal display unless full output is requested."""
    if full_values or len(value) <= MAX_DISPLAY_VALUE_LENGTH:
        return value
    hidden_chars = len(value) - MAX_DISPLAY_VALUE_LENGTH
    return f"{value[:MAX_DISPLAY_VALUE_LENGTH]}... <truncated {hidden_chars} chars>"
