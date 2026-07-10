# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

from __future__ import annotations

import unittest

from pytransformer.cli import pyt_jpeg_sliced_collage
from pytransformer.core.common import ScriptError

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency availability varies.
    Image = None  # type: ignore[assignment]


@unittest.skipIf(Image is None, "Pillow is required for sliced collage tests.")
class JpegSlicedCollageTests(unittest.TestCase):
    def test_vertical_collage_alternates_strips_from_each_image(self) -> None:
        first_image = Image.new("RGB", (5, 2), (255, 0, 0))
        second_image = Image.new("RGB", (5, 2), (0, 0, 255))

        output = pyt_jpeg_sliced_collage.create_vertical_sliced_collage(first_image, second_image, 2)

        self.assertEqual(output.size, (5, 2))
        self.assertEqual(output.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(output.getpixel((1, 0)), (255, 0, 0))
        self.assertEqual(output.getpixel((2, 0)), (0, 0, 255))
        self.assertEqual(output.getpixel((3, 0)), (0, 0, 255))
        self.assertEqual(output.getpixel((4, 0)), (255, 0, 0))

    def test_horizontal_collage_alternates_strips_from_each_image(self) -> None:
        first_image = Image.new("RGB", (2, 5), (255, 0, 0))
        second_image = Image.new("RGB", (2, 5), (0, 0, 255))

        output = pyt_jpeg_sliced_collage.create_horizontal_sliced_collage(first_image, second_image, 2)

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
            pyt_jpeg_sliced_collage.validate_same_aspect_ratio(first_image, second_image)
