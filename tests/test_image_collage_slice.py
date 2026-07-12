# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

from __future__ import annotations

import contextlib
import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from pytransformer.cli import pyt_image_collage_slice
from pytransformer.core.common import ScriptError

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency availability varies.
    Image = None


@unittest.skipIf(Image is None, "Pillow is required for sliced collage tests.")
class JpegSlicedCollageTests(unittest.TestCase):
    def test_vertical_collage_alternates_strips_from_each_image(self) -> None:
        first_image = Image.new("RGB", (5, 2), (255, 0, 0))
        second_image = Image.new("RGB", (5, 2), (0, 0, 255))

        output = pyt_image_collage_slice.create_vertical_sliced_collage([first_image, second_image], 2)

        self.assertEqual(output.size, (5, 2))
        self.assertEqual(output.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(output.getpixel((1, 0)), (255, 0, 0))
        self.assertEqual(output.getpixel((2, 0)), (0, 0, 255))
        self.assertEqual(output.getpixel((3, 0)), (0, 0, 255))
        self.assertEqual(output.getpixel((4, 0)), (255, 0, 0))

    def test_horizontal_collage_alternates_strips_from_each_image(self) -> None:
        first_image = Image.new("RGB", (2, 5), (255, 0, 0))
        second_image = Image.new("RGB", (2, 5), (0, 0, 255))

        output = pyt_image_collage_slice.create_horizontal_sliced_collage([first_image, second_image], 2)

        self.assertEqual(output.size, (2, 5))
        self.assertEqual(output.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(output.getpixel((0, 1)), (255, 0, 0))
        self.assertEqual(output.getpixel((0, 2)), (0, 0, 255))
        self.assertEqual(output.getpixel((0, 3)), (0, 0, 255))
        self.assertEqual(output.getpixel((0, 4)), (255, 0, 0))

    def test_aspect_ratio_mismatch_is_rejected(self) -> None:
        first_image = Image.new("RGB", (4, 4), (255, 0, 0))
        second_image = Image.new("RGB", (8, 4), (0, 0, 255))

        with self.assertRaises(ScriptError):
            pyt_image_collage_slice.validate_same_aspect_ratio([first_image, second_image])

    def test_vertical_collage_cycles_through_three_images(self) -> None:
        first_image = Image.new("RGB", (7, 2), (255, 0, 0))
        second_image = Image.new("RGB", (7, 2), (0, 255, 0))
        third_image = Image.new("RGB", (7, 2), (0, 0, 255))

        output = pyt_image_collage_slice.create_vertical_sliced_collage(
            [first_image, second_image, third_image],
            2,
        )

        self.assertEqual(output.size, (7, 2))
        self.assertEqual(output.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(output.getpixel((2, 0)), (0, 255, 0))
        self.assertEqual(output.getpixel((4, 0)), (0, 0, 255))
        self.assertEqual(output.getpixel((6, 0)), (255, 0, 0))

    def test_horizontal_collage_cycles_through_three_images(self) -> None:
        first_image = Image.new("RGB", (2, 7), (255, 0, 0))
        second_image = Image.new("RGB", (2, 7), (0, 255, 0))
        third_image = Image.new("RGB", (2, 7), (0, 0, 255))

        output = pyt_image_collage_slice.create_horizontal_sliced_collage(
            [first_image, second_image, third_image],
            2,
        )

        self.assertEqual(output.size, (2, 7))
        self.assertEqual(output.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(output.getpixel((0, 2)), (0, 255, 0))
        self.assertEqual(output.getpixel((0, 4)), (0, 0, 255))
        self.assertEqual(output.getpixel((0, 6)), (255, 0, 0))

    def test_requires_at_least_two_image_paths(self) -> None:
        with self.assertRaises(ScriptError):
            pyt_image_collage_slice.require_at_least_two_images([])

    def test_resolve_output_path_rejects_existing_file_without_overwrite(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.jpg"
            output_path = temp_path / "output.jpg"
            input_path.write_bytes(b"input")
            output_path.write_bytes(b"existing")

            with self.assertRaises(ScriptError):
                pyt_image_collage_slice.resolve_output_path(
                    output_path,
                    temp_path / "generated.jpg",
                    [input_path],
                    overwrite=False,
                )

    def test_resolve_output_path_allows_existing_file_with_overwrite(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.jpg"
            output_path = temp_path / "output.jpg"
            input_path.write_bytes(b"input")
            output_path.write_bytes(b"existing")

            resolved = pyt_image_collage_slice.resolve_output_path(
                output_path,
                temp_path / "generated.jpg",
                [input_path],
                overwrite=True,
            )

            self.assertEqual(resolved, output_path.resolve())

    def test_quality_argument_is_range_checked(self) -> None:
        with self.assertRaises(ScriptError):
            pyt_image_collage_slice.require_int_range(101, label="JPEG quality", minimum=1, maximum=100)

    def test_default_jpeg_quality_is_100(self) -> None:
        self.assertEqual(pyt_image_collage_slice.DEFAULT_JPEG_QUALITY, 100)

    def test_save_jpeg_disables_chroma_subsampling(self) -> None:
        image = Mock()

        pyt_image_collage_slice.save_jpeg(image, Path("output.jpg"))

        image.save.assert_called_once()
        _, save_kwargs = image.save.call_args
        self.assertEqual(save_kwargs["subsampling"], 0)
        self.assertEqual(save_kwargs["quality"], 100)

    def test_save_jpeg_preserves_icc_profile_when_supplied(self) -> None:
        image = Mock()
        icc_profile = b"test-profile"

        pyt_image_collage_slice.save_jpeg(image, Path("output.jpg"), icc_profile=icc_profile)

        _, save_kwargs = image.save.call_args
        self.assertEqual(save_kwargs["icc_profile"], icc_profile)

    def test_save_jpeg_preserves_dpi_when_supplied(self) -> None:
        image = Mock()

        pyt_image_collage_slice.save_jpeg(image, Path("output.jpg"), dpi=(300, 300))

        _, save_kwargs = image.save.call_args
        self.assertEqual(save_kwargs["dpi"], (300, 300))

    def test_save_jpeg_rejects_quality_outside_supported_range(self) -> None:
        image = Mock()

        with self.assertRaises(ScriptError):
            pyt_image_collage_slice.save_jpeg(image, Path("output.jpg"), quality=101)

        image.save.assert_not_called()

    def test_save_png_uses_lossless_png_format_and_preserves_metadata(self) -> None:
        image = Mock()
        icc_profile = b"test-profile"

        pyt_image_collage_slice.save_png(
            image,
            Path("output.png"),
            icc_profile=icc_profile,
            dpi=(300, 300),
        )

        image.save.assert_called_once()
        _, save_kwargs = image.save.call_args
        self.assertEqual(save_kwargs["format"], "PNG")
        self.assertEqual(save_kwargs["icc_profile"], icc_profile)
        self.assertEqual(save_kwargs["dpi"], (300, 300))

    def test_save_output_image_dispatches_to_png(self) -> None:
        image = Mock()

        pyt_image_collage_slice.save_output_image(
            image,
            Path("output.png"),
            output_format="png",
            quality=100,
            icc_profile=None,
            dpi=None,
        )

        _, save_kwargs = image.save.call_args
        self.assertEqual(save_kwargs["format"], "PNG")

    def test_save_tiff_uses_lossless_tiff_format_and_preserves_metadata(self) -> None:
        image = Mock()
        icc_profile = b"test-profile"

        pyt_image_collage_slice.save_tiff(
            image,
            Path("output.tif"),
            icc_profile=icc_profile,
            dpi=(300, 300),
        )

        image.save.assert_called_once()
        _, save_kwargs = image.save.call_args
        self.assertEqual(save_kwargs["format"], "TIFF")
        self.assertEqual(save_kwargs["compression"], "tiff_lzw")
        self.assertEqual(save_kwargs["icc_profile"], icc_profile)
        self.assertEqual(save_kwargs["dpi"], (300, 300))

    def test_save_output_image_dispatches_to_tiff(self) -> None:
        image = Mock()

        pyt_image_collage_slice.save_output_image(
            image,
            Path("output.tif"),
            output_format="tiff",
            quality=100,
            icc_profile=None,
            dpi=None,
        )

        _, save_kwargs = image.save.call_args
        self.assertEqual(save_kwargs["format"], "TIFF")

    def test_get_first_icc_profile_returns_first_available_profile(self) -> None:
        first_image = Image.new("RGB", (2, 2), (255, 0, 0))
        second_image = Image.new("RGB", (2, 2), (0, 0, 255))
        second_image.info["icc_profile"] = b"test-profile"

        self.assertEqual(
            pyt_image_collage_slice.get_first_icc_profile([first_image, second_image]),
            b"test-profile",
        )

    def test_get_first_dpi_returns_first_available_dpi(self) -> None:
        first_image = Image.new("RGB", (2, 2), (255, 0, 0))
        second_image = Image.new("RGB", (2, 2), (0, 0, 255))
        second_image.info["dpi"] = (300, 240)

        self.assertEqual(
            pyt_image_collage_slice.get_first_dpi([first_image, second_image]),
            (300.0, 240.0),
        )

    def test_get_first_resolution_metadata_preserves_jfif_unit_and_density(self) -> None:
        image = Image.new("RGB", (2, 2), (255, 0, 0))
        image.info["dpi"] = (299.72, 238.76)
        image.info["jfif_unit"] = 2
        image.info["jfif_density"] = (118, 94)

        resolution = pyt_image_collage_slice.get_first_resolution_metadata([image])

        assert resolution is not None
        self.assertEqual(resolution.dpi, (299.72, 238.76))
        self.assertEqual(resolution.jfif_unit, 2)
        self.assertEqual(resolution.jfif_density, (118, 94))

    def test_get_first_resolution_metadata_skips_malformed_dpi(self) -> None:
        first_image = Image.new("RGB", (2, 2), (255, 0, 0))
        first_image.info["dpi"] = (float("nan"), 300)
        second_image = Image.new("RGB", (2, 2), (0, 0, 255))
        second_image.info["dpi"] = (300, 240)

        self.assertEqual(
            pyt_image_collage_slice.get_first_dpi([first_image, second_image]),
            (300.0, 240.0),
        )

    def test_get_first_resolution_metadata_prefers_later_dpi_over_unitless_density(self) -> None:
        first_image = Image.new("RGB", (2, 2), (255, 0, 0))
        first_image.info["jfif_unit"] = 0
        first_image.info["jfif_density"] = (17, 23)
        second_image = Image.new("RGB", (2, 2), (0, 0, 255))
        second_image.info["dpi"] = (300, 240)

        resolution = pyt_image_collage_slice.get_first_resolution_metadata([first_image, second_image])

        assert resolution is not None
        self.assertEqual(resolution.dpi, (300.0, 240.0))

    def test_save_jpeg_preserves_jfif_unit_and_exact_density(self) -> None:
        image = Image.new("RGB", (8, 8), (100, 120, 140))
        resolution = pyt_image_collage_slice.ResolutionMetadata(
            dpi=(299.72, 238.76),
            jfif_unit=2,
            jfif_density=(118, 94),
        )

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.jpg"
            pyt_image_collage_slice.save_jpeg(image, output_path, resolution=resolution)

            with Image.open(output_path) as saved_image:
                self.assertEqual(saved_image.info["jfif_unit"], 2)
                self.assertEqual(saved_image.info["jfif_density"], (118, 94))

    def test_save_jpeg_preserves_unitless_jfif_density(self) -> None:
        image = Image.new("RGB", (8, 8), (100, 120, 140))
        resolution = pyt_image_collage_slice.ResolutionMetadata(
            dpi=None,
            jfif_unit=0,
            jfif_density=(17, 23),
        )

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.jpg"
            pyt_image_collage_slice.save_jpeg(image, output_path, resolution=resolution)

            with Image.open(output_path) as saved_image:
                self.assertEqual(saved_image.info["jfif_unit"], 0)
                self.assertEqual(saved_image.info["jfif_density"], (17, 23))

    def test_generate_output_path_uses_png_extension_for_png_output(self) -> None:
        output_path = pyt_image_collage_slice.generate_output_path(
            [Path("first.jpg"), Path("second.jpg")],
            10,
            output_format="png",
        )

        self.assertEqual(output_path.name, "first+second-10px-strips.png")

    def test_generate_output_path_uses_tif_extension_for_tiff_output(self) -> None:
        output_path = pyt_image_collage_slice.generate_output_path(
            [Path("first.jpg"), Path("second.jpg")],
            10,
            output_format="tiff",
        )

        self.assertEqual(output_path.name, "first+second-10px-strips.tif")

    def test_generate_output_path_uses_webp_extension_for_webp_output(self) -> None:
        output_path = pyt_image_collage_slice.generate_output_path(
            [Path("first.jpg"), Path("second.webp")],
            10,
            output_format="webp",
        )

        self.assertEqual(output_path.name, "first+second-10px-strips.webp")

    def test_generate_output_path_rejects_unknown_format(self) -> None:
        with self.assertRaises(ScriptError):
            pyt_image_collage_slice.generate_output_path(
                [Path("first.jpg"), Path("second.jpg")],
                10,
                output_format="gif",
            )

    def test_validate_output_extension_rejects_mismatched_known_extension(self) -> None:
        with self.assertRaises(ScriptError):
            pyt_image_collage_slice.validate_output_extension(Path("collage.png"), output_format="jpeg")

    def test_validate_output_extension_allows_matching_and_unknown_extensions(self) -> None:
        pyt_image_collage_slice.validate_output_extension(Path("collage.jpeg"), output_format="jpeg")
        pyt_image_collage_slice.validate_output_extension(Path("collage.custom"), output_format="png")
        pyt_image_collage_slice.validate_output_extension(Path("collage.webp"), output_format="webp")

    def test_save_output_image_dispatches_to_webp(self) -> None:
        image = Mock()

        pyt_image_collage_slice.save_output_image(
            image,
            Path("output.webp"),
            output_format="webp",
            quality=90,
            icc_profile=None,
            dpi=None,
        )

        _, save_kwargs = image.save.call_args
        self.assertEqual(save_kwargs["format"], "WEBP")
        self.assertEqual(save_kwargs["quality"], 90)

    def test_lossless_output_ignores_jpeg_quality_range(self) -> None:
        parser = pyt_image_collage_slice.build_parser()
        args = parser.parse_args(["--png", "--quality", "0", "10", "first.jpg", "second.jpg"])

        self.assertEqual(
            pyt_image_collage_slice.resolve_requested_output_format(png=args.png, tiff=args.tiff, webp=args.webp),
            "png",
        )

    def test_close_images_closes_each_image(self) -> None:
        first_image = Mock()
        second_image = Mock()

        pyt_image_collage_slice.close_images([first_image, second_image])

        first_image.close.assert_called_once_with()
        second_image.close.assert_called_once_with()

    def test_png_and_tiff_options_are_mutually_exclusive(self) -> None:
        parser = pyt_image_collage_slice.build_parser()

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["--png", "--tiff", "10", "first.jpg", "second.jpg"])
