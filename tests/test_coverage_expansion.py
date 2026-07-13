# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

from __future__ import annotations

import argparse
import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

from pytransformer.cli import (
    pyt_files_append_folder_name as files_cli,
)
from pytransformer.cli import (
    pyt_image_collage_slice as collage_cli,
)
from pytransformer.cli import (
    pyt_image_split as split_cli,
)
from pytransformer.cli import (
    pyt_image_to_webp as webp_cli,
)
from pytransformer.cli import (
    pyt_jpeg_show_metadata as jpeg_show_cli,
)
from pytransformer.cli import (
    pyt_jpeg_strip_metadata as jpeg_strip_cli,
)
from pytransformer.cli import (
    pyt_mp4_split_chunks as mp4_split_cli,
)
from pytransformer.cli import (
    pyt_mp4_transcribe as mp4_transcribe_cli,
)
from pytransformer.cli import (
    pyt_mp4_transcribe_batch as mp4_batch_cli,
)
from pytransformer.cli import (
    pyt_pdf_extract_selectable_text as selectable_cli,
)
from pytransformer.cli import (
    pyt_pdf_extract_selectable_text_batch as selectable_batch_cli,
)
from pytransformer.cli import (
    pyt_pdf_extract_text as pdf_text_cli,
)
from pytransformer.cli import (
    pyt_pdf_render_jpeg as pdf_render_cli,
)
from pytransformer.cli import (
    pyt_text_concatenate as text_cli,
)
from pytransformer.core import audio, jpeg_metadata
from pytransformer.core.common import ScriptError


class FakeImage:
    def __init__(
        self,
        size: tuple[int, int] = (4, 4),
        *,
        mode: str = "RGB",
        image_format: str = "JPEG",
        info: dict[str, object] | None = None,
    ) -> None:
        self.size = size
        self.width, self.height = size
        self.mode = mode
        self.format = image_format
        self.info = {} if info is None else dict(info)
        self.quantization: dict[str, object] | None = {"q": 1}
        self.closed = False
        self.saved: list[tuple[object, dict[str, object]]] = []
        self.pasted: list[tuple[object, tuple[int, int]]] = []

    def __enter__(self) -> FakeImage:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def load(self) -> None:
        return None

    def verify(self) -> None:
        return None

    def copy(self) -> FakeImage:
        return FakeImage(self.size, mode=self.mode, image_format=self.format, info=self.info)

    def convert(self, mode: str) -> FakeImage:
        return FakeImage(self.size, mode=mode, image_format=self.format, info=self.info)

    def resize(self, size: tuple[int, int], _filter: object) -> FakeImage:
        return FakeImage(size, mode=self.mode, image_format=self.format, info=self.info)

    def crop(self, bounds: tuple[int, int, int, int]) -> FakeImage:
        left, top, right, bottom = bounds
        return FakeImage((right - left, bottom - top), mode=self.mode, image_format=self.format)

    def paste(self, image: FakeImage, position: tuple[int, int]) -> None:
        self.pasted.append((image, position))

    def save(self, path: object, **kwargs: object) -> None:
        self.saved.append((path, kwargs))
        Path(str(path)).write_bytes(b"image")

    def close(self) -> None:
        self.closed = True


class FakeImageModule:
    Resampling = SimpleNamespace(LANCZOS="lanczos")
    LANCZOS = "legacy-lanczos"

    def __init__(self, opened: FakeImage | None = None) -> None:
        self.opened = opened or FakeImage()
        self.frombytes_mode: str | None = None

    def open(self, _path: object) -> FakeImage:
        return self.opened

    def new(self, mode: str, size: tuple[int, int]) -> FakeImage:
        return FakeImage(size, mode=mode, image_format=None)  # type: ignore[arg-type]

    def frombytes(self, mode: str, size: tuple[int, int], _samples: bytes) -> FakeImage:
        self.frombytes_mode = mode
        return FakeImage(size, mode=mode, image_format="PNG")


class FakeReader:
    def __init__(self, pages: list[Any], *, encrypted: bool = False, decrypt_result: int = 1) -> None:
        self.pages = pages
        self.is_encrypted = encrypted
        self.decrypt_result = decrypt_result
        self.closed = False

    def decrypt(self, _password: str) -> int:
        return self.decrypt_result

    def close(self) -> None:
        self.closed = True


class FakePdfPage:
    def __init__(self, text: str = "", *, fail: bool = False) -> None:
        self.text = text
        self.fail = fail

    def extract_text(self) -> str:
        if self.fail:
            raise ValueError("bad page")
        return self.text

    def get_text(self, _kind: str) -> str:
        if self.fail:
            raise ValueError("bad page")
        return self.text


class FakePdfDoc:
    def __init__(self, pages: list[FakePdfPage], *, encrypted: bool = False, auth: bool = True) -> None:
        self.pages = pages
        self.page_count = len(pages)
        self.is_encrypted = encrypted
        self.auth = auth
        self.closed = False

    def authenticate(self, _password: str) -> bool:
        return self.auth

    def load_page(self, index: int) -> FakePdfPage:
        return self.pages[index]

    def close(self) -> None:
        self.closed = True


class FakeFitz:
    def __init__(self, doc: FakePdfDoc) -> None:
        self.doc = doc
        self.matrices: list[tuple[float, float]] = []

    def open(self, _path: str) -> FakePdfDoc:
        return self.doc

    def Matrix(self, x: float, y: float) -> tuple[float, float]:
        self.matrices.append((x, y))
        return x, y


class FakePixmap:
    def __init__(self, *, fail: bool = False) -> None:
        self.n = 3
        self.width = 2
        self.height = 2
        self.samples = b"pixels"
        self.fail = fail
        self.saved_kwargs: dict[str, object] = {}

    def save(self, path: str, **kwargs: object) -> None:
        if self.fail:
            raise OSError("render failed")
        self.saved_kwargs = kwargs
        Path(path).write_bytes(b"jpeg")


class FakeVideoClip:
    def __init__(self, duration: float = 65.0, *, use_subclip: bool = True) -> None:
        self.duration = duration
        self.use_subclip = use_subclip
        self.closed = False
        self.subclips: list[FakeSubclip] = []

    def subclip(self, start: float, end: float) -> FakeSubclip:
        if not self.use_subclip:
            raise AttributeError("subclip unavailable")
        subclip = FakeSubclip(start, end)
        self.subclips.append(subclip)
        return subclip

    def subclipped(self, start: float, end: float) -> FakeSubclip:
        subclip = FakeSubclip(start, end)
        self.subclips.append(subclip)
        return subclip

    def close(self) -> None:
        self.closed = True


class FakeSubclip:
    def __init__(self, start: float, end: float, *, fail: bool = False) -> None:
        self.start = start
        self.end = end
        self.fail = fail
        self.closed = False

    def write_videofile(self, path: str, **_kwargs: object) -> None:
        if self.fail:
            raise OSError("write failed")
        Path(path).write_bytes(b"video")

    def close(self) -> None:
        self.closed = True


class CoreMetadataTests(unittest.TestCase):
    def test_flatten_and_display_helpers_cover_nested_values(self) -> None:
        flattened = jpeg_metadata.flatten_dict("root", {"a": [1, {"b": b"12"}], "empty": {}})
        self.assertEqual(flattened["root.a[0]"], "1")
        self.assertEqual(flattened["root.a[1].b"], "<bytes length=2>")
        self.assertEqual(flattened["root.empty"], "{}")
        self.assertEqual(jpeg_metadata.flatten_dict("root", []), {"root": "[]"})
        long_value = "x" * 1005
        self.assertIn("truncated 5 chars", jpeg_metadata.format_display_value(long_value, False))
        self.assertEqual(jpeg_metadata.format_display_value(long_value, True), long_value)

    def test_metadata_maps_collect_exif_xmp_iptc_and_info(self) -> None:
        class Exif:
            def items(self) -> list[tuple[int, object]]:
                return [(1, "camera"), (999, 3)]

            def get_ifd(self, key: int) -> dict[int, object]:
                return {2: "value"} if key in {0x8825, 0x8769, 0xA005} else {}

        image = SimpleNamespace(
            info={"exif": b"12", "icc_profile": b"123", "comment": "note", "custom": b"x", "number": 4},
            getexif=lambda: Exif(),
            getxmp=lambda: {"dc": {"title": "sample"}},
        )
        tags = SimpleNamespace(TAGS={1: "Make"}, GPSTAGS={2: "Latitude"})
        iptc = SimpleNamespace(getiptcinfo=lambda _image: {"5": "caption"})
        with (
            patch.object(jpeg_metadata, "ExifTags", tags),
            patch.object(jpeg_metadata, "IptcImagePlugin", iptc),
            patch.object(jpeg_metadata, "HAS_DEFUSEDXML", True),
        ):
            exif = jpeg_metadata.get_exif_map(image)
            metadata = {}
            metadata.update(jpeg_metadata.get_info_map(image))
            metadata.update(exif)
            metadata.update(jpeg_metadata.get_xmp_map(image))
            metadata.update(jpeg_metadata.get_iptc_map(image))
        self.assertEqual(exif["EXIF.Make"], "'camera'")
        self.assertEqual(exif["EXIF.GPS.Latitude"], "'value'")
        self.assertEqual(metadata["INFO.exif_raw"], "<bytes length=2>")
        self.assertIn("XMP.dc.title", metadata)
        self.assertEqual(metadata["IPTC.5"], "'caption'")

    def test_metadata_helpers_tolerate_missing_or_broken_plugins(self) -> None:
        broken = SimpleNamespace(
            getexif=Mock(side_effect=ValueError("bad exif")),
            getxmp=Mock(side_effect=ValueError("bad xmp")),
        )
        with (
            patch.object(jpeg_metadata, "ExifTags", None),
            patch.object(jpeg_metadata, "IptcImagePlugin", None),
            patch.object(jpeg_metadata, "HAS_DEFUSEDXML", True),
        ):
            self.assertEqual(jpeg_metadata.get_exif_map(broken), {})
            self.assertEqual(jpeg_metadata.get_xmp_map(broken), {})
            self.assertEqual(jpeg_metadata.get_iptc_map(broken), {})
        exif = SimpleNamespace(
            items=lambda: [(1, "value")],
            get_ifd=Mock(side_effect=RuntimeError("not available")),
        )
        image = SimpleNamespace(getexif=lambda: exif)
        with patch.object(jpeg_metadata, "ExifTags", SimpleNamespace(TAGS={}, GPSTAGS={})):
            self.assertIn("EXIF.UnknownTag_1", jpeg_metadata.get_exif_map(image))

    def test_lazy_pillow_loading_and_inspection(self) -> None:
        fake_pil = types.ModuleType("PIL")
        fake_image_module = FakeImageModule()
        fake_pil.ExifTags = object()  # type: ignore[attr-defined]
        fake_pil.Image = fake_image_module  # type: ignore[attr-defined]
        fake_pil.ImageOps = object()  # type: ignore[attr-defined]
        fake_pil.IptcImagePlugin = object()  # type: ignore[attr-defined]
        fake_pil.JpegImagePlugin = object()  # type: ignore[attr-defined]
        with (
            patch.dict(sys.modules, {"PIL": fake_pil}),
            patch.object(jpeg_metadata, "PIL_IMPORT_ATTEMPTED", False),
            patch.object(jpeg_metadata, "PIL_IMPORT_ERROR", None),
            patch.object(jpeg_metadata, "Image", None),
        ):
            self.assertTrue(jpeg_metadata.load_pillow())
            self.assertIs(jpeg_metadata.Image, fake_image_module)

        inspected_image = FakeImage(info={"comment": "ok"})
        fake_module = FakeImageModule(inspected_image)
        with (
            patch.object(jpeg_metadata, "Image", fake_module),
            patch.object(jpeg_metadata, "load_pillow", return_value=True),
            patch.object(jpeg_metadata, "get_exif_map", return_value={}),
            patch.object(jpeg_metadata, "get_xmp_map", return_value={}),
            patch.object(jpeg_metadata, "get_iptc_map", return_value={}),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "photo.jpg"
                path.write_bytes(b"jpeg")
                self.assertEqual(jpeg_metadata.inspect_embedded_metadata(path), {"INFO.comment": "'ok'"})


class PdfTests(unittest.TestCase):
    def test_selectable_pdf_helpers_and_main(self) -> None:
        pages = [FakePdfPage("hello"), FakePdfPage("")]
        reader = FakeReader(list(pages))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            pdf = folder / "sample.pdf"
            pdf.write_bytes(b"pdf")
            output = folder / "result.txt"
            with (
                patch.object(selectable_cli, "PdfReader", lambda _path: reader),
                patch.object(selectable_cli, "PDF_IMPORT_ERROR", None),
            ):
                selectable_cli.require_pdf_dependency()
                self.assertEqual(
                    selectable_cli.validate_args(argparse.Namespace(pdf_file=pdf, output=output, overwrite=False)),
                    (pdf.resolve(), output.resolve()),
                )
                self.assertEqual(selectable_cli.extract_text(reader), ("hello\n", 1))
                with patch.object(sys, "argv", ["pyt-pdf-extract-selectable-text", str(pdf), "--output", str(output)]):
                    self.assertEqual(selectable_cli.main(), 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "hello\n")
            self.assertTrue(reader.closed)

    def test_selectable_pdf_encryption_and_failures(self) -> None:
        with self.assertRaises(ScriptError):
            selectable_cli.open_pdf_reader(Path("missing.pdf"), "")
        encrypted = FakeReader([FakePdfPage("ok")], encrypted=True, decrypt_result=0)
        with patch.object(selectable_cli, "PdfReader", lambda _path: encrypted):
            with self.assertRaises(ScriptError):
                selectable_cli.open_pdf_reader(Path("x.pdf"), "secret")
        encrypted.decrypt_result = 1
        with patch.object(selectable_cli, "PdfReader", lambda _path: encrypted):
            self.assertIs(selectable_cli.open_pdf_reader(Path("x.pdf"), "secret"), encrypted)
        with self.assertRaises(ScriptError):
            selectable_cli.extract_text(FakeReader([FakePdfPage(fail=True)]))
        with patch.object(selectable_cli, "PDF_IMPORT_ERROR", ImportError("missing")):
            with self.assertRaises(ScriptError):
                selectable_cli.require_pdf_dependency()

    def test_selectable_batch_processes_writes_skips_and_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "ok.pdf").write_bytes(b"pdf")
            (folder / "bad.pdf").write_bytes(b"pdf")
            (folder / ".hidden.pdf").write_bytes(b"pdf")
            output = folder / "out"
            reader = FakeReader([FakePdfPage("text")])

            def reader_factory(path: str) -> FakeReader:
                if Path(path).name == "bad.pdf":
                    raise ValueError("bad pdf")
                return reader

            with patch.object(selectable_batch_cli, "PdfReader", reader_factory):
                self.assertEqual(
                    [p.name for p in selectable_batch_cli.find_pdf_files(folder, include_hidden=False)],
                    ["bad.pdf", "ok.pdf"],
                )
                summary = selectable_batch_cli.process_folder(
                    folder, output_folder=output, overwrite=False, include_hidden=False, password=""
                )
            self.assertEqual((summary.written, summary.failed), (1, 1))
            (output / "ok.txt").write_text("existing", encoding="utf-8")
            with patch.object(selectable_batch_cli, "PdfReader", reader_factory):
                summary = selectable_batch_cli.process_folder(
                    folder, output_folder=output, overwrite=False, include_hidden=False, password=""
                )
            self.assertGreaterEqual(summary.skipped, 1)
            self.assertEqual(selectable_batch_cli.output_path_for(folder / "ok.pdf", None).name, "ok.txt")
            self.assertIsNone(selectable_batch_cli.resolve_output_folder(None))
            self.assertEqual(selectable_batch_cli.resolve_output_folder(output), output.resolve())

    def test_pdf_text_extraction_with_ocr_and_path_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            pdf = folder / "scan.pdf"
            pdf.write_bytes(b"pdf")
            output = folder / "scan.txt"
            args = argparse.Namespace(pdf_file=pdf, output=output, ocr_dpi=300)
            self.assertEqual(pdf_text_cli.build_paths(args)[0], pdf.resolve())
            with self.assertRaises(pdf_text_cli.TextExtractionError):
                pdf_text_cli.build_paths(argparse.Namespace(pdf_file=pdf, output=pdf, ocr_dpi=300))
            with self.assertRaises(pdf_text_cli.TextExtractionError):
                pdf_text_cli.build_paths(argparse.Namespace(pdf_file=pdf, output=None, ocr_dpi=0))

            doc = FakePdfDoc([FakePdfPage("text"), FakePdfPage(""), FakePdfPage(fail=True)])
            logger = Mock()
            with (
                patch.object(pdf_text_cli, "ocr_available", return_value=True),
                patch.object(pdf_text_cli, "ocr_page", return_value="ocr text"),
            ):
                summary = pdf_text_cli.extract_text_from_pdf(
                    doc, output, overwrite=True, use_ocr=True, ocr_dpi=200, logger=logger
                )
            self.assertEqual((summary.processed_pages, summary.ocr_pages, summary.failed_pages), (2, 1, 1))
            self.assertIn("ocr text", output.read_text(encoding="utf-8"))

    def test_pdf_text_open_and_pixmap_helpers(self) -> None:
        doc = FakePdfDoc([FakePdfPage("x")], encrypted=True, auth=True)
        fake_fitz = FakeFitz(doc)
        with patch.object(pdf_text_cli, "fitz", fake_fitz):
            with self.assertRaises(pdf_text_cli.TextExtractionError):
                pdf_text_cli.open_pdf(Path("x.pdf"), "")
            self.assertIs(pdf_text_cli.open_pdf(Path("x.pdf"), "secret"), doc)
        empty = FakePdfDoc([])
        with patch.object(pdf_text_cli, "fitz", FakeFitz(empty)):
            with self.assertRaises(pdf_text_cli.TextExtractionError):
                pdf_text_cli.open_pdf(Path("x.pdf"), "")

        image_module = FakeImageModule()
        with (
            patch.object(pdf_text_cli, "OCR_IMPORT_ATTEMPTED", True),
            patch.object(pdf_text_cli, "Image", image_module),
            patch.object(pdf_text_cli, "pytesseract", SimpleNamespace(image_to_string=lambda _image: "ocr")),
        ):
            image = pdf_text_cli.pixmap_to_image(SimpleNamespace(n=1, width=2, height=2, samples=b"x"))
            self.assertEqual(image.mode, "RGB")
            page = SimpleNamespace(get_pixmap=lambda **_kwargs: SimpleNamespace(n=3, width=2, height=2, samples=b"x"))
            self.assertEqual(pdf_text_cli.ocr_page(page, 300), "ocr")
            with self.assertRaises(pdf_text_cli.TextExtractionError):
                pdf_text_cli.pixmap_to_image(SimpleNamespace(n=2, width=1, height=1, samples=b"x"))

    def test_pdf_text_main_and_logger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            pdf = folder / "doc.pdf"
            pdf.write_bytes(b"pdf")
            output = folder / "doc.txt"
            doc = FakePdfDoc([FakePdfPage("content")])
            with (
                patch.object(pdf_text_cli, "fitz", FakeFitz(doc)),
                patch.object(pdf_text_cli, "FITZ_IMPORT_ERROR", None),
                patch.object(sys, "argv", ["pyt-pdf-extract-text", "--no-ocr", "--output", str(output), str(pdf)]),
            ):
                self.assertEqual(pdf_text_cli.main(), 0)
            self.assertTrue(doc.closed)
            logger = pdf_text_cli.setup_logger(folder / "extract.log", quiet=True)
            self.assertEqual(logger.name, "pdf_to_text")
            with patch("logging.FileHandler", side_effect=OSError("no log")):
                with self.assertRaises(pdf_text_cli.TextExtractionError):
                    pdf_text_cli.setup_logger(folder / "broken.log", quiet=False)

    def test_pdf_render_conversion_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            pdf = folder / "doc.pdf"
            pdf.write_bytes(b"pdf")
            destination = folder / "images"
            pdf_render_cli.validate_inputs(pdf, destination, 90, 200)
            with self.assertRaises(pdf_render_cli.ConversionError):
                pdf_render_cli.validate_inputs(pdf, destination, 101, 200)
            with self.assertRaises(pdf_render_cli.ConversionError):
                pdf_render_cli.validate_inputs(pdf, destination, 90, 0)
            self.assertTrue(pdf_render_cli.default_output_dir(pdf).name.startswith("doc_images_"))

            pix = FakePixmap()
            failing_pix = FakePixmap(fail=True)
            page1 = SimpleNamespace(get_pixmap=lambda **_kwargs: pix)
            page2 = SimpleNamespace(get_pixmap=lambda **_kwargs: failing_pix)
            doc = SimpleNamespace(page_count=2, load_page=lambda index: [page1, page2][index])
            fake_fitz = FakeFitz(FakePdfDoc([FakePdfPage("x")]))
            with patch.object(pdf_render_cli, "fitz", fake_fitz):
                pdf_render_cli.save_pixmap_jpeg(pix, folder / "fallback.jpg", 80)
                with patch.object(pix, "save", side_effect=[TypeError("old api"), None]):
                    pdf_render_cli.save_pixmap_jpeg(pix, folder / "fallback.jpg", 80)
                summary = pdf_render_cli.convert_pdf_to_images(doc, destination, 72, 80, overwrite=False)
            self.assertEqual((summary.saved, summary.failed), (1, 1))
            existing = destination / "page_1.jpg"
            self.assertTrue(existing.exists())
            with patch.object(pdf_render_cli, "fitz", fake_fitz):
                skipped = pdf_render_cli.convert_pdf_to_images(doc, destination, 72, 80, overwrite=False)
            self.assertGreaterEqual(skipped.skipped, 1)

    def test_pdf_render_open_and_main(self) -> None:
        doc = FakePdfDoc([FakePdfPage("x")], encrypted=True, auth=True)
        with patch.object(pdf_render_cli, "fitz", FakeFitz(doc)):
            with self.assertRaises(pdf_render_cli.ConversionError):
                pdf_render_cli.open_pdf(Path("x.pdf"), "")
            self.assertIs(pdf_render_cli.open_pdf(Path("x.pdf"), "pw"), doc)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            pdf = folder / "doc.pdf"
            pdf.write_bytes(b"pdf")
            render_doc = SimpleNamespace(
                page_count=1,
                load_page=lambda _index: SimpleNamespace(get_pixmap=lambda **_kwargs: FakePixmap()),
                close=lambda: None,
            )
            with (
                patch.object(
                    pdf_render_cli,
                    "fitz",
                    FakeFitz(FakePdfDoc([FakePdfPage("x")])),
                ),
                patch.object(pdf_render_cli, "FITZ_IMPORT_ERROR", None),
                patch.object(pdf_render_cli, "open_pdf", return_value=render_doc),
                patch.object(sys, "argv", ["pyt-pdf-render-jpeg", "--output-folder", str(folder / "out"), str(pdf)]),
            ):
                self.assertEqual(pdf_render_cli.main(), 0)


class AudioAndVideoTests(unittest.TestCase):
    def test_audio_helpers_cover_dependencies_extraction_and_transcription(self) -> None:
        with patch.object(audio, "MOVIEPY_IMPORT_ERROR", ImportError("moviepy")):
            with self.assertRaises(ScriptError):
                audio.require_transcription_dependencies()
        with (
            patch.object(audio, "MOVIEPY_IMPORT_ERROR", None),
            patch.object(audio, "SPEECH_RECOGNITION_IMPORT_ERROR", ImportError("speech")),
        ):
            with self.assertRaises(ScriptError):
                audio.require_transcription_dependencies()

        clip = Mock()
        clip_cls = Mock(return_value=clip)
        with patch.object(audio, "AudioFileClip", clip_cls):
            audio.extract_wav(Path("video.mp4"), Path("audio.wav"))
        clip.write_audiofile.assert_called_once()
        clip.close.assert_called_once()
        clip_cls.side_effect = OSError("extract")
        with patch.object(audio, "AudioFileClip", clip_cls):
            with self.assertRaises(ScriptError):
                audio.extract_wav(Path("video.mp4"), Path("audio.wav"))

        class UnknownValueError(Exception):
            pass

        class RequestError(Exception):
            pass

        class AudioFile:
            def __init__(self, path: str) -> None:
                self.path = path

            def __enter__(self) -> AudioFile:
                return self

            def __exit__(self, *_args: object) -> None:
                return None

        recognizer = Mock()
        recognizer.record.return_value = "audio-data"
        recognition = SimpleNamespace(
            Recognizer=lambda: recognizer,
            AudioFile=AudioFile,
            UnknownValueError=UnknownValueError,
            RequestError=RequestError,
        )
        with patch.object(audio, "sr", recognition):
            recognizer.recognize_google.return_value = "hello"
            self.assertEqual(audio.transcribe_wav(Path("audio.wav"), language="en-US"), "hello")
            recognizer.recognize_google.side_effect = UnknownValueError()
            self.assertIn("could not understand", audio.transcribe_wav(Path("audio.wav"), language="en-US"))
            recognizer.recognize_google.side_effect = RequestError("offline")
            with self.assertRaises(ScriptError):
                audio.transcribe_wav(Path("audio.wav"), language="en-US")
            recognizer.recognize_google.side_effect = RuntimeError("bad")
            with self.assertRaises(ScriptError):
                audio.transcribe_wav(Path("audio.wav"), language="en-US")

        with patch.object(audio, "sr", None):
            with self.assertRaises(ScriptError):
                audio.transcribe_wav(Path("audio.wav"), language="en-US")
        with (
            patch.object(audio, "require_transcription_dependencies"),
            patch.object(audio, "extract_wav") as extract,
            patch.object(audio, "transcribe_wav", return_value="text") as transcribe,
        ):
            self.assertEqual(audio.transcribe_mp4_to_text(Path("video.mp4"), language="en-US"), "text")
            extract.assert_called_once()
            transcribe.assert_called_once()

    def test_mp4_split_and_transcription_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            video = folder / "video.mp4"
            video.write_bytes(b"mp4")
            args = argparse.Namespace(mp4_file=video, output_folder=None, seconds=30)
            self.assertEqual(mp4_split_cli.validate_args(args)[0], video.resolve())
            with self.assertRaises(ScriptError):
                mp4_split_cli.validate_args(argparse.Namespace(mp4_file=video, output_folder=video, seconds=30))
            clip = FakeVideoClip()
            (folder / "chunks").mkdir()
            with patch.object(mp4_split_cli, "VideoFileClip", lambda _path: clip):
                summary = mp4_split_cli.split_video(video, folder / "chunks", chunk_seconds=30, overwrite=False)
            self.assertEqual((summary.saved, summary.failed), (3, 0))
            self.assertTrue(clip.closed)

            class FallbackClip:
                duration = 1.0

                def subclipped(self, start: float, end: float) -> FakeSubclip:
                    return FakeSubclip(start, end)

                def close(self) -> None:
                    return None

            (folder / "fallback").mkdir()
            with patch.object(mp4_split_cli, "VideoFileClip", lambda _path: FallbackClip()):
                fallback_summary = mp4_split_cli.split_video(
                    video, folder / "fallback", chunk_seconds=30, overwrite=True
                )
            self.assertEqual(fallback_summary.saved, 1)

            output = folder / "transcript.txt"
            self.assertEqual(
                mp4_transcribe_cli.validate_args(argparse.Namespace(mp4_file=video, output=output, overwrite=False))[0],
                video.resolve(),
            )
            with patch.object(mp4_transcribe_cli, "transcribe_mp4_to_text", return_value="hello"):
                mp4_transcribe_cli.transcribe_mp4(video, output, language="en-US")
            self.assertEqual(output.read_text(encoding="utf-8"), "hello\n")
            with (
                patch.object(mp4_transcribe_cli, "require_transcription_dependencies"),
                patch.object(mp4_transcribe_cli, "transcribe_mp4_to_text", return_value="ok"),
                patch.object(sys, "argv", ["pyt-mp4-transcribe", str(video), "--output", str(folder / "main.txt")]),
            ):
                self.assertEqual(mp4_transcribe_cli.main(), 0)

    def test_mp4_batch_finds_files_and_handles_all_summary_states(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            good = folder / "good.mp4"
            bad = folder / "bad.mp4"
            hidden = folder / ".hidden.mp4"
            for path in (good, bad, hidden):
                path.write_bytes(b"mp4")
            output = folder / "txt"
            self.assertEqual(
                [p.name for p in mp4_batch_cli.find_mp4_files(folder, include_hidden=False)],
                ["bad.mp4", "good.mp4"],
            )

            def transcribe(path: Path, *, language: str) -> str:
                if path.name == "bad.mp4":
                    raise ScriptError("bad audio")
                return language

            with patch.object(mp4_batch_cli, "transcribe_mp4_to_text", side_effect=transcribe):
                summary = mp4_batch_cli.process_folder(
                    folder, output_folder=output, overwrite=False, include_hidden=False, language="en-US"
                )
            self.assertEqual((summary.written, summary.failed), (1, 1))
            self.assertIsNone(mp4_batch_cli.resolve_output_folder(None))
            self.assertEqual(mp4_batch_cli.output_path_for(good, output), output / "good.txt")
            (output / "good.txt").write_text("old", encoding="utf-8")
            with patch.object(mp4_batch_cli, "transcribe_mp4_to_text", side_effect=ScriptError("bad audio")):
                summary = mp4_batch_cli.process_folder(
                    folder, output_folder=output, overwrite=False, include_hidden=False, language="en-US"
                )
            self.assertGreaterEqual(summary.skipped, 1)


class ImageCommandTests(unittest.TestCase):
    def test_webp_helpers_and_run(self) -> None:
        image = FakeImage(info={"icc_profile": b"icc", "dpi": [72, 72]})
        self.assertEqual(webp_cli.get_save_kwargs(image, quality=80)["dpi"], (72, 72))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.webp"
            webp_cli.save_webp(image, output, quality=80)
            self.assertTrue(output.exists())
            source = Path(tmp) / "input.jpg"
            source.write_bytes(b"jpg")
            with patch.object(webp_cli, "load_image", return_value=image), patch.object(webp_cli, "save_webp"):
                self.assertEqual(
                    webp_cli.process_image(source, overwrite=True, quality=80), source.with_suffix(".webp").resolve()
                )
            args = argparse.Namespace(images=[source], quality=80, overwrite=True, quiet=True, debug=False)
            with patch.object(webp_cli, "process_image", return_value=output):
                self.assertEqual(webp_cli.run(args), 0)
        with patch.object(webp_cli, "Image", None), patch.object(webp_cli, "ImageOps", None):
            with self.assertRaises(ScriptError):
                webp_cli.require_pillow()
        with self.assertRaises(ScriptError):
            webp_cli.get_save_kwargs(image, quality=0)

    def test_webp_load_error_paths_and_main_error(self) -> None:
        unsupported = FakeImage(image_format="GIF")
        fake_module = FakeImageModule(unsupported)
        with (
            patch.object(webp_cli, "Image", fake_module),
            patch.object(webp_cli, "ImageOps", SimpleNamespace(exif_transpose=lambda image: image)),
        ):
            with self.assertRaises(ScriptError):
                webp_cli.load_image(Path("unsupported.gif"))
        with (
            patch.object(webp_cli, "Image", fake_module),
            patch.object(webp_cli, "ImageOps", SimpleNamespace(exif_transpose=lambda image: image)),
            patch.object(webp_cli, "UnidentifiedImageError", ValueError),
            patch.object(fake_module, "open", side_effect=ValueError("invalid")),
        ):
            with self.assertRaises(ScriptError):
                webp_cli.load_image(Path("broken.jpg"))
        with patch.object(webp_cli, "run", side_effect=ScriptError("bad command")):
            self.assertEqual(webp_cli.main(["photo.jpg"]), 1)

    def test_image_split_helpers_save_and_main(self) -> None:
        image = FakeImage((10, 6), info={"icc_profile": b"icc", "dpi": (72, 72)})
        self.assertEqual(split_cli.calculate_vertical_bounds(10, 3), [(0, 3), (3, 6), (6, 10)])
        self.assertEqual(split_cli.calculate_horizontal_bounds(6, 2), [(0, 3), (3, 6)])
        with self.assertRaises(ScriptError):
            split_cli.calculate_vertical_bounds(2, 3)
        with self.assertRaises(ScriptError):
            split_cli.split_image(image, 2, "diagonal")
        self.assertEqual(len(split_cli.split_image_vertically(image, 2)), 2)
        self.assertEqual(len(split_cli.split_image_horizontally(image, 2)), 2)
        self.assertEqual(split_cli.get_save_kwargs(image, "JPEG", quality=90)["subsampling"], 0)
        self.assertEqual(split_cli.get_save_kwargs(image, "TIFF", quality=90)["compression"], "tiff_lzw")
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / "one.jpg", Path(tmp) / "two.jpg"]
            split_cli.save_split_images(image, "JPEG", paths, orientation="vertical", quality=90)
            self.assertTrue(all(path.exists() for path in paths))
            source = Path(tmp) / "source.jpg"
            source.write_bytes(b"jpg")
            with patch.object(split_cli, "load_image", return_value=(image, "JPEG")):
                with patch.object(split_cli, "save_split_images"):
                    self.assertEqual(
                        len(split_cli.process_image(source, 2, orientation="vertical", overwrite=True, quality=90)),
                        2,
                    )
            args = argparse.Namespace(
                images=[source], count=2, orientation="vertical", overwrite=True, quality=90, quiet=True, debug=False
            )
            with patch.object(split_cli, "process_image", return_value=paths):
                self.assertEqual(split_cli.run(args), 0)

    def test_collage_helpers_and_save_formats(self) -> None:
        images = [FakeImage((6, 4)), FakeImage((6, 4))]
        fake_module = FakeImageModule()
        with patch.object(collage_cli, "Image", fake_module), patch.object(collage_cli, "ImageOps", object()):
            self.assertEqual(collage_cli.get_lanczos_filter(), "lanczos")
            output = collage_cli.create_sliced_collage(images, 2, "vertical")
            self.assertEqual(output.size, (6, 4))
            output = collage_cli.create_sliced_collage(images, 2, "horizontal")
            self.assertEqual(output.size, (6, 4))
            resized = collage_cli.resize_to_target(images[0], (8, 4), label="image")
            self.assertEqual(resized.size, (8, 4))
            with self.assertRaises(ScriptError):
                collage_cli.create_vertical_sliced_collage(images, 7)
            with self.assertRaises(ScriptError):
                collage_cli.create_sliced_collage(images, 2, "diagonal")
        self.assertEqual(collage_cli.sanitize_filename_part("CON", fallback="image"), "CON_file")
        self.assertEqual(collage_cli.sanitize_filename_part("<>", fallback="image"), "_")
        self.assertEqual(collage_cli.get_first_dpi([FakeImage(info={"dpi": (300, 300)})]), (300.0, 300.0))
        self.assertIsNone(collage_cli.get_first_dpi([FakeImage(info={"dpi": (0, 1)})]))
        with self.assertRaises(ScriptError):
            collage_cli.shorten_filename_parts(["a"], "x" * 300, "+")

        image = FakeImage()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out.jpg"
            resolution = collage_cli.ResolutionMetadata((72.0, 72.0), 1, (72, 72))
            with patch.object(collage_cli, "preserve_jfif_resolution") as preserve:
                collage_cli.save_jpeg(image, output, resolution=resolution)
                preserve.assert_called_once()
            collage_cli.save_png(image, Path(tmp) / "out.png", icc_profile=b"icc", dpi=(72, 72))
            collage_cli.save_tiff(image, Path(tmp) / "out.tif")
            collage_cli.save_webp(image, Path(tmp) / "out.webp", quality=90)
            with self.assertRaises(ScriptError):
                collage_cli.save_output_image(
                    image,
                    Path(tmp) / "bad",
                    output_format="gif",
                    quality=90,
                    icc_profile=None,
                    dpi=None,
                )

    def test_collage_resolution_and_main(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            output = folder / "collage.jpg"
            raw = bytearray(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00\xff\xda")
            path = folder / "image.jpg"
            path.write_bytes(raw)
            collage_cli.preserve_jfif_resolution(path, 2, (300, 240))
            self.assertEqual(path.read_bytes()[13], 2)
            with self.assertRaises(ScriptError):
                collage_cli.preserve_jfif_resolution(path, 3, (1, 1))
            input_paths = [folder / "a.jpg", folder / "b.jpg"]
            for item in input_paths:
                item.write_bytes(b"jpg")
            fake = FakeImage((4, 4))

            def fake_save(_image: object, output_path: Path, **_kwargs: object) -> None:
                output_path.write_bytes(b"output")

            with (
                patch.object(collage_cli, "load_image", return_value=fake),
                patch.object(collage_cli, "create_sliced_collage", return_value=fake),
                patch.object(collage_cli, "save_output_image", side_effect=fake_save),
                patch.object(
                    sys,
                    "argv",
                    [
                        "pyt-image-collage-slice",
                        "2",
                        str(input_paths[0]),
                        str(input_paths[1]),
                        "--output",
                        str(output),
                    ],
                ),
            ):
                self.assertEqual(collage_cli.main(), 0)
            with (
                patch.object(collage_cli, "require_at_least_two_images", side_effect=ScriptError("too few")),
                patch.object(sys, "argv", ["pyt-image-collage-slice", "2", str(input_paths[0])]),
            ):
                self.assertEqual(collage_cli.main(), 1)

    def test_collage_validation_and_save_error_paths(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            collage_cli.parse_positive_integer("zero")
        with self.assertRaises(argparse.ArgumentTypeError):
            collage_cli.parse_positive_integer("0")
        with patch.object(collage_cli, "Image", None), patch.object(collage_cli, "ImageOps", None):
            with self.assertRaises(ScriptError):
                collage_cli.require_pillow()
        with self.assertRaises(ScriptError):
            collage_cli.validate_same_aspect_ratio([])
        with self.assertRaises(ScriptError):
            collage_cli.choose_target_size([])
        with self.assertRaises(ScriptError):
            collage_cli.validate_same_size([])
        with self.assertRaises(ScriptError):
            collage_cli.validate_same_size([FakeImage((1, 1)), FakeImage((2, 2))])
        bad_resize = FakeImage((1, 1))
        bad_resize.resize = Mock(side_effect=OSError("resize failed"))  # type: ignore[method-assign]
        with self.assertRaises(ScriptError):
            collage_cli.resize_to_target(bad_resize, (2, 2), label="bad")

        fallback_module = SimpleNamespace(Resampling=SimpleNamespace(), LANCZOS="legacy")
        with patch.object(collage_cli, "Image", fallback_module), patch.object(collage_cli, "ImageOps", object()):
            self.assertEqual(collage_cli.get_lanczos_filter(), "legacy")
        resolution = collage_cli.get_first_resolution_metadata(
            [FakeImage(info={"jfif_unit": 1, "jfif_density": (72, 72)})]
        )
        if resolution is None:
            self.fail("expected JFIF resolution")
        self.assertEqual(resolution.dpi, (72.0, 72.0))
        resolution = collage_cli.get_first_resolution_metadata(
            [FakeImage(info={"jfif_unit": 2, "jfif_density": (100, 200)})]
        )
        if resolution is None:
            self.fail("expected metric JFIF resolution")
        self.assertEqual(resolution.dpi, (254.0, 508.0))
        resolution = collage_cli.get_first_resolution_metadata(
            [FakeImage(info={"jfif_unit": 0, "jfif_density": (1, 2)})]
        )
        if resolution is None:
            self.fail("expected unitless JFIF resolution")
        self.assertIsNone(resolution.dpi)
        self.assertEqual(collage_cli._parse_jfif_resolution({"jfif_unit": 1, "jfif_density": (1, "bad")}), (1, None))
        self.assertEqual(collage_cli.build_output_filename_parts([Path("<>"), Path("CON")]), ["_", "CON_file"])
        short = collage_cli.shorten_filename_parts(["first", "second"], "-x.jpg", "+")
        self.assertEqual(len(short), 2)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with self.assertRaises(ScriptError):
                collage_cli.resolve_output_path(folder, folder / "generated.jpg", [], overwrite=False)
            with self.assertRaises(ScriptError):
                collage_cli.validate_output_extension(Path("x.jpg"), output_format="png")
            with self.assertRaises(ScriptError):
                collage_cli.validate_output_extension(Path("x.jpg"), output_format="gif")
            malformed = folder / "bad.jpg"
            malformed.write_bytes(b"not-jpeg")
            with self.assertRaises(ScriptError):
                collage_cli.preserve_jfif_resolution(malformed, 1, (1, 1))
            no_jfif = folder / "no-jfif.jpg"
            no_jfif.write_bytes(b"\xff\xd8\xff\xd9")
            with self.assertRaises(ScriptError):
                collage_cli.preserve_jfif_resolution(no_jfif, 1, (1, 1))

            class FailingImage(FakeImage):
                def __init__(self, error: Exception) -> None:
                    super().__init__()
                    self.error = error

                def save(self, path: object, **kwargs: object) -> None:
                    raise self.error

            for saver, extension in (
                (collage_cli.save_jpeg, ".jpg"),
                (collage_cli.save_png, ".png"),
                (collage_cli.save_tiff, ".tif"),
                (collage_cli.save_webp, ".webp"),
            ):
                with self.subTest(saver=saver.__name__):
                    with self.assertRaises(ScriptError):
                        saver(FailingImage(PermissionError("no")), folder / f"permission{extension}")
                    with self.assertRaises(ScriptError):
                        saver(FailingImage(OSError("bad")), folder / f"error{extension}")

    def test_collage_load_and_main_exception_paths(self) -> None:
        image_module = FakeImageModule(FakeImage(image_format="GIF"))
        with patch.object(collage_cli, "Image", image_module), patch.object(collage_cli, "ImageOps", object()):
            with self.assertRaises(ScriptError):
                collage_cli.load_image(Path("bad.gif"), label="image")
        with (
            patch.object(collage_cli, "Image", image_module),
            patch.object(collage_cli, "ImageOps", SimpleNamespace(exif_transpose=lambda _image: _image)),
            patch.object(collage_cli, "UnidentifiedImageError", ValueError),
            patch.object(image_module, "open", side_effect=ValueError("bad image")),
        ):
            with self.assertRaises(ScriptError):
                collage_cli.load_image(Path("bad.jpg"), label="image")

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            first, second = folder / "first.jpg", folder / "second.jpg"
            first.write_bytes(b"x")
            second.write_bytes(b"x")

            def fake_save(_image: object, output_path: Path, **_kwargs: object) -> None:
                output_path.write_bytes(b"output")

            with (
                patch.object(collage_cli, "load_image", side_effect=[FakeImage((4, 4)), FakeImage((8, 8))]),
                patch.object(collage_cli, "Image", FakeImageModule()),
                patch.object(collage_cli, "ImageOps", object()),
                patch.object(collage_cli, "save_output_image", side_effect=fake_save),
                patch.object(
                    sys,
                    "argv",
                    ["pyt-image-collage-slice", "2", str(first), str(second), "--output", str(folder / "collage.jpg")],
                ),
            ):
                self.assertEqual(collage_cli.main(), 0)
            for error, expected in ((KeyboardInterrupt(), 130), (MemoryError(), 1), (RuntimeError("boom"), 1)):
                with (
                    patch.object(collage_cli, "load_image", side_effect=error),
                    patch.object(sys, "argv", ["pyt-image-collage-slice", "2", str(first), str(second)]),
                ):
                    self.assertEqual(collage_cli.main(), expected)


class JpegAndStandardLibraryTests(unittest.TestCase):
    def test_standard_library_command_mains_cover_confirmation_and_failure_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "Paris"
            folder.mkdir()
            (folder / "photo.jpg").write_bytes(b"x")
            with patch.object(sys, "argv", ["pyt-files-append-folder-name", "--dry-run", str(folder)]):
                self.assertEqual(files_cli.main(), 0)
            with patch.object(sys, "argv", ["pyt-files-append-folder-name", "--yes", str(folder)]):
                self.assertEqual(files_cli.main(), 0)
            self.assertTrue((folder / "photo-Paris.jpg").exists())
            with (
                patch.object(files_cli, "confirm_action", side_effect=ScriptError("cancelled")),
                patch.object(sys, "argv", ["pyt-files-append-folder-name", str(folder)]),
            ):
                (folder / "another.jpg").write_bytes(b"x")
                self.assertEqual(files_cli.main(), 2)

            empty = root / "empty"
            empty.mkdir()
            with patch.object(sys, "argv", ["pyt-files-append-folder-name", str(empty)]):
                self.assertEqual(files_cli.main(), 0)
            with patch.object(files_cli, "sorted_directory_items", return_value=[]):
                with self.assertRaises(ScriptError):
                    files_cli.build_rename_plan(Path("/"), include_hidden=False)

            text_folder = root / "texts"
            text_folder.mkdir()
            (text_folder / "a.txt").write_text("a", encoding="utf-8")
            with patch.object(sys, "argv", ["pyt-text-concatenate", str(text_folder)]):
                self.assertEqual(text_cli.main(), 0)
            with (
                patch.object(text_cli, "require_existing_folder", side_effect=ScriptError("bad folder")),
                patch.object(sys, "argv", ["pyt-text-concatenate", str(text_folder)]),
            ):
                self.assertEqual(text_cli.main(), 2)

    def test_standard_helpers_cover_skips_and_rename_race(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Folder"
            folder.mkdir()
            source = folder / "file.txt"
            source.write_text("x", encoding="utf-8")
            target = folder / "file-Folder.txt"
            target.write_text("existing", encoding="utf-8")
            self.assertEqual(files_cli.build_rename_plan(folder, include_hidden=False), ([], 2))
            plan = files_cli.RenamePlan(source=source, target=target)
            summary = files_cli.apply_rename_plan([plan], dry_run=False)
            self.assertEqual(summary.skipped, 1)
            target.unlink()
            with patch("pathlib.Path.rename", side_effect=OSError("read-only")):
                summary = files_cli.apply_rename_plan([plan], dry_run=False)
            self.assertEqual(summary.failed, 1)
            self.assertEqual(files_cli.build_target_path(source, "Folder").name, "file-Folder.txt")
            self.assertTrue(files_cli.already_has_folder_name(target, "folder"))

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            output = folder / "combined.txt"
            hidden = folder / ".hidden.txt"
            hidden.write_text("hidden", encoding="utf-8")
            output.write_text("old", encoding="utf-8")
            self.assertEqual(text_cli.find_text_files(folder, output.resolve(), include_hidden=False), [])
            self.assertEqual(text_cli.resolve_output_path(folder, output, overwrite=True), output.resolve())

    def test_jpeg_strip_helpers_and_processing(self) -> None:
        self.assertTrue(jpeg_strip_cli.is_hidden_file(Path(".hidden.jpg")))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            visible = folder / "photo.jpg"
            hidden = folder / ".hidden.jpg"
            png = folder / "skip.png"
            for path in (visible, hidden, png):
                path.write_bytes(b"x")
            self.assertEqual(
                [p.name for p in jpeg_strip_cli.iter_jpeg_files(folder, include_hidden=False)], ["photo.jpg"]
            )
            self.assertEqual(len(jpeg_strip_cli.iter_jpeg_files(folder, include_hidden=True)), 2)
            with self.assertRaises(ValueError):
                jpeg_strip_cli.resolve_output_folder(folder.resolve(), folder)
            clean = FakeImage(info={"icc_profile": b"icc"})
            plugin = SimpleNamespace(get_sampling=lambda _image: 0)
            fake_module = FakeImageModule(clean)
            with (
                patch.object(jpeg_metadata, "load_pillow", return_value=True),
                patch.object(jpeg_metadata, "Image", fake_module),
                patch.object(jpeg_metadata, "ImageOps", SimpleNamespace(exif_transpose=lambda image: image)),
                patch.object(jpeg_metadata, "JpegImagePlugin", plugin),
                patch.object(jpeg_strip_cli, "inspect_embedded_metadata", side_effect=[{"EXIF.Make": "x"}, {}]),
            ):
                destination = folder / "clean"
                destination.mkdir()
                jpeg_strip_cli.save_with_color_and_quality_preserved(
                    visible, destination / visible.name, preserve_visual_orientation=True
                )
                self.assertEqual(
                    jpeg_strip_cli.process_folder(
                        folder,
                        output_folder_arg=destination,
                        overwrite=True,
                        dry_run=False,
                        include_hidden=False,
                        preserve_visual_orientation=True,
                        quiet=False,
                        debug=True,
                        full_values=False,
                    ),
                    0,
                )
            self.assertTrue((destination / visible.name).exists())
            with patch.object(jpeg_metadata, "load_pillow", return_value=True):
                self.assertEqual(
                    jpeg_strip_cli.process_folder(
                        folder,
                        output_folder_arg=folder / "dry",
                        overwrite=False,
                        dry_run=True,
                        include_hidden=True,
                        preserve_visual_orientation=False,
                        quiet=False,
                        debug=False,
                        full_values=True,
                    ),
                    0,
                )
        report = io.StringIO()
        with contextlib.redirect_stdout(report):
            jpeg_strip_cli.print_metadata_report(before={"a": "1"}, after={"b": "2"}, full_values=False)
        self.assertIn("Removed", report.getvalue())
        self.assertEqual(jpeg_strip_cli.format_field_list("Fields", {}, full_values=False), "Fields\n    (none)")

    def test_jpeg_show_and_text_commands(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as output:
            jpeg_show_cli.print_metadata({}, full_values=False)
            jpeg_show_cli.print_metadata({"A": "value", "Long": "x" * 1002}, full_values=False)
        self.assertIn("No embedded", output.getvalue())
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "a.txt").write_text("a", encoding="utf-8")
            (folder / "b.txt").write_text("b", encoding="utf-8")
            hidden = folder / ".hidden.txt"
            hidden.write_text("hidden", encoding="utf-8")
            output_path = folder / "combined.txt"
            self.assertEqual(
                text_cli.find_text_files(folder, output_path, include_hidden=False),
                [folder / "a.txt", folder / "b.txt"],
            )
            text_cli.concatenate_text_files([folder / "a.txt", folder / "b.txt"], output_path, separator="---")
            self.assertEqual(output_path.read_text(encoding="utf-8"), "a\n---\nb\n")
            with self.assertRaises(ScriptError):
                text_cli.concatenate_text_files([], output_path, separator="\n")
            bad = folder / "bad.txt"
            bad.write_bytes(b"\xff")
            with self.assertRaises(ScriptError):
                text_cli.concatenate_text_files([bad], output_path, separator="\n")

    def test_file_rename_and_jpeg_show_main_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Tokyo"
            folder.mkdir()
            source = folder / "one.jpg"
            source.write_bytes(b"x")
            plans, skipped = files_cli.build_rename_plan(folder, include_hidden=False)
            self.assertEqual((len(plans), skipped), (1, 0))
            dry = files_cli.apply_rename_plan(plans, dry_run=True)
            self.assertEqual(dry.planned, 1)
            self.assertEqual(files_cli.apply_rename_plan(plans, dry_run=False).renamed, 1)
            self.assertTrue((folder / "one-Tokyo.jpg").exists())
        with (
            patch.object(jpeg_show_cli, "inspect_embedded_metadata", side_effect=ValueError("bad")),
            patch.object(jpeg_show_cli, "require_existing_file", return_value=Path("photo.jpg")),
            patch.object(sys, "argv", ["pyt-jpeg-show-metadata", "photo.jpg"]),
        ):
            self.assertEqual(jpeg_show_cli.main(), 1)


if __name__ == "__main__":
    unittest.main()
