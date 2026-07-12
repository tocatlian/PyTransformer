# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

from __future__ import annotations

import argparse
import contextlib
import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from pytransformer.cli import pyt_image_split
from pytransformer.core.common import ScriptError

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency availability varies.
    Image = None


class ImgSplitImageUnitTests(unittest.TestCase):
    def test_parse_slice_count_rejects_non_numeric_values(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            pyt_image_split.parse_slice_count("two")

    def test_parse_slice_count_rejects_values_below_two(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            pyt_image_split.parse_slice_count("1")

    def test_build_parser_defaults_to_two_vertical_slices(self) -> None:
        args = pyt_image_split.build_parser().parse_args(["image.jpg"])

        self.assertEqual(args.count, 2)
        self.assertEqual(args.orientation, "vertical")
        self.assertEqual(args.images, [Path("image.jpg")])

    def test_build_parser_accepts_horizontal_orientation_option(self) -> None:
        args = pyt_image_split.build_parser().parse_args(["--horizontal", "--count", "3", "image.jpg"])

        self.assertEqual(args.count, 3)
        self.assertEqual(args.orientation, "horizontal")

    def test_build_parser_accepts_orientation_choice_option(self) -> None:
        args = pyt_image_split.build_parser().parse_args(["--orientation", "horizontal", "image.webp"])

        self.assertEqual(args.orientation, "horizontal")
        self.assertEqual(args.images, [Path("image.webp")])

    def test_build_parser_rejects_conflicting_orientation_options(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            pyt_image_split.build_parser().parse_args(["--horizontal", "--vertical", "image.jpg"])

    def test_calculate_vertical_bounds_covers_entire_width(self) -> None:
        bounds = pyt_image_split.calculate_vertical_bounds(10, 3)

        self.assertEqual(bounds, [(0, 3), (3, 6), (6, 10)])

    def test_calculate_horizontal_bounds_covers_entire_height(self) -> None:
        bounds = pyt_image_split.calculate_horizontal_bounds(10, 3)

        self.assertEqual(bounds, [(0, 3), (3, 6), (6, 10)])

    def test_calculate_vertical_bounds_rejects_more_slices_than_columns(self) -> None:
        with self.assertRaises(ScriptError):
            pyt_image_split.calculate_vertical_bounds(2, 3)

    def test_calculate_horizontal_bounds_rejects_more_slices_than_rows(self) -> None:
        with self.assertRaises(ScriptError):
            pyt_image_split.calculate_horizontal_bounds(2, 3)

    def test_build_split_output_paths_appends_numbered_suffixes(self) -> None:
        output_paths = pyt_image_split.build_split_output_paths(Path("/tmp/image.jpg"), 3)

        self.assertEqual(
            output_paths,
            [
                Path("/tmp/image-1.jpg"),
                Path("/tmp/image-2.jpg"),
                Path("/tmp/image-3.jpg"),
            ],
        )

    def test_build_split_output_paths_preserves_webp_suffix(self) -> None:
        output_paths = pyt_image_split.build_split_output_paths(Path("/tmp/image.webp"), 2)

        self.assertEqual(output_paths, [Path("/tmp/image-1.webp"), Path("/tmp/image-2.webp")])

    def test_resolve_output_paths_rejects_existing_file_without_overwrite(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.png"
            output_path = temp_path / "image-1.png"
            input_path.write_bytes(b"input")
            output_path.write_bytes(b"existing")

            with self.assertRaises(ScriptError):
                pyt_image_split.resolve_output_paths(input_path, 2, overwrite=False)

    def test_resolve_output_paths_allows_existing_file_with_overwrite(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.png"
            output_path = temp_path / "image-1.png"
            input_path.write_bytes(b"input")
            output_path.write_bytes(b"existing")

            output_paths = pyt_image_split.resolve_output_paths(input_path, 2, overwrite=True)

            self.assertEqual(output_paths[0], output_path.resolve())

    def test_save_jpeg_uses_high_quality_settings(self) -> None:
        image = Mock()
        image.info = {}

        save_kwargs = pyt_image_split.get_save_kwargs(image, "JPEG", quality=100)

        self.assertEqual(save_kwargs["format"], "JPEG")
        self.assertEqual(save_kwargs["quality"], 100)
        self.assertEqual(save_kwargs["subsampling"], 0)

    def test_save_webp_uses_quality_setting(self) -> None:
        image = Mock()
        image.info = {}

        save_kwargs = pyt_image_split.get_save_kwargs(image, "WEBP", quality=90)

        self.assertEqual(save_kwargs["format"], "WEBP")
        self.assertEqual(save_kwargs["quality"], 90)
        self.assertNotIn("subsampling", save_kwargs)

    def test_save_jpeg_rejects_quality_outside_supported_range(self) -> None:
        image = Mock()
        image.info = {}

        with self.assertRaises(ScriptError):
            pyt_image_split.get_save_kwargs(image, "JPEG", quality=101)

    def test_save_webp_rejects_quality_outside_supported_range(self) -> None:
        image = Mock()
        image.info = {}

        with self.assertRaises(ScriptError):
            pyt_image_split.get_save_kwargs(image, "WEBP", quality=0)

    def test_save_tiff_uses_lzw_compression(self) -> None:
        image = Mock()
        image.info = {}

        save_kwargs = pyt_image_split.get_save_kwargs(image, "TIFF", quality=100)

        self.assertEqual(save_kwargs["format"], "TIFF")
        self.assertEqual(save_kwargs["compression"], "tiff_lzw")

    def test_save_kwargs_preserves_metadata_when_supplied(self) -> None:
        image = Mock()
        image.info = {"icc_profile": b"profile", "dpi": (300, 300)}

        save_kwargs = pyt_image_split.get_save_kwargs(image, "PNG", quality=100)

        self.assertEqual(save_kwargs["icc_profile"], b"profile")
        self.assertEqual(save_kwargs["dpi"], (300, 300))

    def test_split_image_rejects_unknown_orientation(self) -> None:
        image = Mock()

        with self.assertRaises(ScriptError):
            pyt_image_split.split_image(image, 2, "diagonal")


@unittest.skipIf(Image is None, "Pillow is required for image split tests.")
class ImgSplitImagePillowTests(unittest.TestCase):
    def test_split_image_vertically_preserves_height_and_all_columns(self) -> None:
        assert Image is not None
        image = Image.new("RGB", (6, 4), (255, 0, 0))

        slices = pyt_image_split.split_image_vertically(image, 2)

        self.assertEqual([image_slice.size for image_slice in slices], [(3, 4), (3, 4)])

    def test_split_image_horizontally_preserves_width_and_all_rows(self) -> None:
        assert Image is not None
        image = Image.new("RGB", (3, 5), (255, 0, 0))

        slices = pyt_image_split.split_image_horizontally(image, 2)

        self.assertEqual([image_slice.size for image_slice in slices], [(3, 2), (3, 3)])

    def test_split_image_dispatches_vertical_and_horizontal_orientations(self) -> None:
        assert Image is not None
        image = Image.new("RGB", (5, 5), (255, 0, 0))

        vertical_slices = pyt_image_split.split_image(image, 2, "vertical")
        horizontal_slices = pyt_image_split.split_image(image, 2, "horizontal")

        self.assertEqual([image_slice.size for image_slice in vertical_slices], [(2, 5), (3, 5)])
        self.assertEqual([image_slice.size for image_slice in horizontal_slices], [(5, 2), (5, 3)])

    def test_process_image_writes_vertical_sibling_split_images_by_default(self) -> None:
        assert Image is not None
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.png"
            Image.new("RGB", (3, 4), (255, 0, 0)).save(input_path)

            output_paths = pyt_image_split.process_image(
                input_path,
                2,
                orientation="vertical",
                overwrite=False,
                quality=100,
            )

            self.assertEqual(
                output_paths,
                [(temp_path / "image-1.png").resolve(), (temp_path / "image-2.png").resolve()],
            )
            with Image.open(output_paths[0]) as first_output:
                self.assertEqual(first_output.size, (1, 4))
            with Image.open(output_paths[1]) as second_output:
                self.assertEqual(second_output.size, (2, 4))

    def test_process_image_writes_horizontal_sibling_split_images(self) -> None:
        assert Image is not None
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.png"
            Image.new("RGB", (4, 3), (0, 0, 255)).save(input_path)

            output_paths = pyt_image_split.process_image(
                input_path,
                2,
                orientation="horizontal",
                overwrite=False,
                quality=100,
            )

            self.assertEqual(
                output_paths,
                [(temp_path / "image-1.png").resolve(), (temp_path / "image-2.png").resolve()],
            )
            with Image.open(output_paths[0]) as first_output:
                self.assertEqual(first_output.size, (4, 1))
            with Image.open(output_paths[1]) as second_output:
                self.assertEqual(second_output.size, (4, 2))

    def test_process_image_rejects_existing_outputs_without_overwrite(self) -> None:
        assert Image is not None
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.png"
            output_path = temp_path / "image-1.png"
            Image.new("RGB", (3, 4), (255, 0, 0)).save(input_path)
            output_path.write_bytes(b"existing")

            with self.assertRaises(ScriptError):
                pyt_image_split.process_image(
                    input_path,
                    2,
                    orientation="vertical",
                    overwrite=False,
                    quality=100,
                )

    def test_process_image_rejects_unsupported_suffix_before_loading(self) -> None:
        with TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "image.gif"
            input_path.write_bytes(b"not loaded")

            with self.assertRaises(ScriptError):
                pyt_image_split.process_image(
                    input_path,
                    2,
                    orientation="vertical",
                    overwrite=False,
                    quality=100,
                )

    def test_load_image_rejects_corrupt_supported_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "image.png"
            input_path.write_bytes(b"not an image")

            with self.assertRaises(ScriptError):
                pyt_image_split.load_image(input_path)

    def test_process_image_writes_webp_split_images(self) -> None:
        assert Image is not None
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.webp"
            Image.new("RGB", (4, 4), (0, 255, 0)).save(input_path, format="WEBP")

            output_paths = pyt_image_split.process_image(
                input_path,
                2,
                orientation="horizontal",
                overwrite=False,
                quality=90,
            )

            self.assertEqual(
                output_paths,
                [(temp_path / "image-1.webp").resolve(), (temp_path / "image-2.webp").resolve()],
            )
            with Image.open(output_paths[0]) as first_output:
                self.assertEqual(first_output.format, "WEBP")
                self.assertEqual(first_output.size, (4, 2))
            with Image.open(output_paths[1]) as second_output:
                self.assertEqual(second_output.format, "WEBP")
                self.assertEqual(second_output.size, (4, 2))

    def test_main_prints_written_paths(self) -> None:
        assert Image is not None
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "image.png"
            Image.new("RGB", (2, 4), (255, 0, 0)).save(input_path)
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = pyt_image_split.main(["--quiet", str(input_path)])

            self.assertEqual(exit_code, 0)
            self.assertIn(str((temp_path / "image-1.png").resolve()), stdout.getvalue())
            self.assertIn(str((temp_path / "image-2.png").resolve()), stdout.getvalue())

    def test_main_returns_error_for_invalid_quality(self) -> None:
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            exit_code = pyt_image_split.main(["--quality", "101", "image.png"])

        self.assertEqual(exit_code, 1)
        self.assertIn("JPEG/WebP quality", stderr.getvalue())
