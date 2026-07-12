# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from pytransformer.cli import pyt_image_to_webp
from pytransformer.core.common import ScriptError

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency availability varies.
    Image = None


class ImageToWebpUnitTests(unittest.TestCase):
    def test_build_parser_defaults_to_quality_98(self) -> None:
        args = pyt_image_to_webp.build_parser().parse_args(["image.jpg"])

        self.assertEqual(args.quality, 98)
        self.assertEqual(args.images, [Path("image.jpg")])

    def test_build_parser_accepts_quality_before_images(self) -> None:
        args = pyt_image_to_webp.build_parser().parse_args(["--quality", "90", "first.jpg", "second.png"])

        self.assertEqual(args.quality, 90)
        self.assertEqual(args.images, [Path("first.jpg"), Path("second.png")])

    def test_build_output_path_replaces_source_suffix_with_webp(self) -> None:
        self.assertEqual(pyt_image_to_webp.build_output_path(Path("/tmp/image.jpg")), Path("/tmp/image.webp"))
        self.assertEqual(pyt_image_to_webp.build_output_path(Path("/tmp/image.tif")), Path("/tmp/image.webp"))

    def test_resolve_output_path_rejects_existing_file_without_overwrite(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.png"
            output_path = temp_path / "image.webp"
            input_path.write_bytes(b"input")
            output_path.write_bytes(b"existing")

            with self.assertRaises(ScriptError):
                pyt_image_to_webp.resolve_output_path(input_path, overwrite=False)

    def test_resolve_output_path_allows_existing_file_with_overwrite(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.png"
            output_path = temp_path / "image.webp"
            input_path.write_bytes(b"input")
            output_path.write_bytes(b"existing")

            self.assertEqual(pyt_image_to_webp.resolve_output_path(input_path, overwrite=True), output_path.resolve())

    def test_save_kwargs_use_webp_quality_and_method(self) -> None:
        image = Mock()
        image.info = {}

        save_kwargs = pyt_image_to_webp.get_save_kwargs(image, quality=90)

        self.assertEqual(save_kwargs["format"], "WEBP")
        self.assertEqual(save_kwargs["quality"], 90)
        self.assertEqual(save_kwargs["method"], 6)

    def test_save_kwargs_rejects_quality_outside_supported_range(self) -> None:
        image = Mock()
        image.info = {}

        with self.assertRaises(ScriptError):
            pyt_image_to_webp.get_save_kwargs(image, quality=101)

    def test_save_kwargs_preserves_metadata_when_supplied(self) -> None:
        image = Mock()
        image.info = {"icc_profile": b"profile", "dpi": (300, 300)}

        save_kwargs = pyt_image_to_webp.get_save_kwargs(image, quality=98)

        self.assertEqual(save_kwargs["icc_profile"], b"profile")
        self.assertEqual(save_kwargs["dpi"], (300, 300))


@unittest.skipIf(Image is None, "Pillow is required for image to WebP tests.")
class ImageToWebpPillowTests(unittest.TestCase):
    def test_process_image_writes_sibling_webp_file(self) -> None:
        assert Image is not None
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.png"
            Image.new("RGB", (3, 4), (255, 0, 0)).save(input_path)

            output_path = pyt_image_to_webp.process_image(input_path, overwrite=False, quality=98)

            self.assertEqual(output_path, (temp_path / "image.webp").resolve())
            with Image.open(output_path) as output_image:
                self.assertEqual(output_image.format, "WEBP")
                self.assertEqual(output_image.size, (3, 4))

    def test_process_image_accepts_tiff_input(self) -> None:
        assert Image is not None
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.tif"
            Image.new("RGB", (2, 2), (0, 0, 255)).save(input_path)

            output_path = pyt_image_to_webp.process_image(input_path, overwrite=False, quality=90)

            with Image.open(output_path) as output_image:
                self.assertEqual(output_image.format, "WEBP")

    def test_process_image_rejects_existing_output_without_overwrite(self) -> None:
        assert Image is not None
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.jpg"
            output_path = temp_path / "image.webp"
            Image.new("RGB", (2, 2), (255, 0, 0)).save(input_path)
            output_path.write_bytes(b"existing")

            with self.assertRaises(ScriptError):
                pyt_image_to_webp.process_image(input_path, overwrite=False, quality=98)
