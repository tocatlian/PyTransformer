#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_pdf_extract_text.py
Purpose: Extract text from one PDF, with optional OCR fallback for image-only pages.
When to use: Use when a PDF may contain scanned pages or when stronger extraction is needed than the lightweight parser.
Changes: Writes one UTF-8 .txt file and one extraction log file next to the PDF.
Inputs: PDF file path; optional --output, --overwrite, --password, --no-ocr, and --ocr-dpi.
Environment variables: None.
Dependencies: PyMuPDF; optional pillow, pytesseract, and a system Tesseract install for OCR fallback.
Safety notes: Refuses to overwrite existing output unless --overwrite is passed.
Example: pyt-pdf-extract-text --no-ocr -o "/path/to/output.txt" "/path/to/file.pdf"
Expected result: A text file containing extracted page text, with OCR used when enabled and available.
Related scripts: pyt_pdf_extract_selectable_text.py, pyt_pdf_extract_selectable_text_batch.py, pyt_pdf_render_jpeg.py.
"""

from __future__ import annotations

import argparse
import importlib
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pytransformer.core.common import ScriptError, build_command_parser, temporary_output_path

fitz: Any | None
FITZ_IMPORT_ERROR: ImportError | None

try:
    fitz = importlib.import_module("fitz")  # PyMuPDF
except ImportError as exc:
    fitz = None
    FITZ_IMPORT_ERROR = exc
else:
    FITZ_IMPORT_ERROR = None

Image: Any | None = None
pytesseract: Any | None = None
PIL_IMPORT_ERROR: ImportError | None = None
PYTESSERACT_IMPORT_ERROR: ImportError | None = None
OCR_IMPORT_ATTEMPTED = False


DEFAULT_OCR_DPI = 300


class TextExtractionError(RuntimeError):
    """Raised for user-fixable extraction failures."""


@dataclass
class ExtractionSummary:
    total_pages: int
    processed_pages: int = 0
    ocr_pages: int = 0
    empty_pages: int = 0
    failed_pages: int = 0


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="Extract or OCR text from a PDF and save it to a .txt file.",
        examples=(
            'pyt-pdf-extract-text "/path/to/file.pdf"',
            'pyt-pdf-extract-text --no-ocr --output "/path/to/output.txt" "/path/to/file.pdf"',
        ),
    )
    parser.add_argument("pdf_file", type=Path, help="Input PDF file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output text file. Defaults to a .txt file next to the PDF.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the output text file if it exists.")
    parser.add_argument("--password", default="", help="Password for encrypted PDFs.")
    parser.add_argument("--no-ocr", action="store_true", help="Do not use OCR fallback on image-only pages.")
    parser.add_argument(
        "--ocr-dpi",
        type=int,
        default=DEFAULT_OCR_DPI,
        help=f"OCR render DPI for image-only pages (default {DEFAULT_OCR_DPI}).",
    )
    parser.add_argument("--quiet", action="store_true", help="Only print warnings and errors to the console.")
    return parser


def setup_logger(log_path: Path, quiet: bool) -> logging.Logger:
    logger = logging.getLogger("pdf_to_text")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING if quiet else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
    except OSError as exc:
        raise TextExtractionError(f"Could not open log file '{log_path}': {exc}") from exc

    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def build_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    pdf_path = args.pdf_file.expanduser().resolve()
    output_path = args.output.expanduser().resolve() if args.output else pdf_path.with_suffix(".txt")
    log_path = pdf_path.with_name(f"{pdf_path.stem}_extract.log")

    if not pdf_path.exists():
        raise TextExtractionError(f"PDF not found: {pdf_path}")

    if not pdf_path.is_file():
        raise TextExtractionError(f"PDF path is not a file: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise TextExtractionError(f"File is not a PDF: {pdf_path}")

    if args.ocr_dpi <= 0:
        raise TextExtractionError(f"OCR DPI must be positive. Got {args.ocr_dpi}")

    if output_path == pdf_path:
        raise TextExtractionError("Output path must be different from the input PDF path.")

    if output_path.exists() and not args.overwrite:
        raise TextExtractionError(f"Output already exists: {output_path}. Pass --overwrite to replace it.")

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise TextExtractionError(f"Could not create output directory '{output_path.parent}': {exc}") from exc

    return pdf_path, output_path, log_path


def load_ocr_dependencies() -> None:
    global Image
    global PIL_IMPORT_ERROR
    global PYTESSERACT_IMPORT_ERROR
    global OCR_IMPORT_ATTEMPTED
    global pytesseract

    if OCR_IMPORT_ATTEMPTED:
        return

    OCR_IMPORT_ATTEMPTED = True

    try:
        from PIL import Image as pillow_image
    except ImportError as exc:
        PIL_IMPORT_ERROR = exc
    else:
        Image = pillow_image

    try:
        import pytesseract as pytesseract_module
    except ImportError as exc:
        PYTESSERACT_IMPORT_ERROR = exc
    else:
        pytesseract = pytesseract_module


def ocr_available() -> bool:
    load_ocr_dependencies()
    return Image is not None and pytesseract is not None


def ocr_dependency_message() -> str:
    missing = []
    if PIL_IMPORT_ERROR is not None:
        missing.append("pillow")
    if PYTESSERACT_IMPORT_ERROR is not None:
        missing.append("pytesseract")
    if not missing:
        return "Tesseract OCR may not be installed or reachable"
    return "missing " + " and ".join(missing)


def open_pdf(pdf_path: Path, password: str) -> Any:
    fitz_module = fitz
    if fitz_module is None:
        raise TextExtractionError("PyMuPDF is required. Install it with: pip install pymupdf")

    try:
        doc = fitz_module.open(str(pdf_path))
    except Exception as exc:
        raise TextExtractionError(f"Cannot open PDF '{pdf_path}': {exc}") from exc

    try:
        if doc.is_encrypted:
            if not password:
                raise TextExtractionError("PDF is encrypted; pass --password to unlock it.")
            if not doc.authenticate(password):
                raise TextExtractionError("PDF is encrypted and the provided password did not work.")

        if doc.page_count <= 0:
            raise TextExtractionError("PDF has no pages to extract.")
    except Exception:
        doc.close()
        raise

    return doc


def pixmap_to_image(pix: Any) -> Any:
    load_ocr_dependencies()
    image_module = Image
    if image_module is None:
        raise TextExtractionError("OCR image conversion is unavailable because pillow is not installed.")

    if pix.n == 1:
        mode = "L"
    elif pix.n == 3:
        mode = "RGB"
    elif pix.n == 4:
        mode = "RGBA"
    else:
        raise TextExtractionError(f"Unsupported OCR image channel count: {pix.n}")

    image = image_module.frombytes(mode, (pix.width, pix.height), pix.samples)
    if image.mode == "RGB":
        return image

    converted = image.convert("RGB")
    image.close()
    return converted


def ocr_page(page: Any, dpi: int) -> str:
    load_ocr_dependencies()
    if not ocr_available():
        raise TextExtractionError(f"OCR fallback is unavailable: {ocr_dependency_message()}.")
    ocr_engine = pytesseract
    if ocr_engine is None:
        raise TextExtractionError(f"OCR fallback is unavailable: {ocr_dependency_message()}.")

    pix = page.get_pixmap(dpi=dpi, alpha=False)
    image = pixmap_to_image(pix)
    try:
        return ocr_engine.image_to_string(image)
    finally:
        image.close()


def extract_text_from_pdf(
    doc: Any,
    output_path: Path,
    *,
    overwrite: bool,
    use_ocr: bool,
    ocr_dpi: int,
    logger: logging.Logger,
) -> ExtractionSummary:
    summary = ExtractionSummary(total_pages=doc.page_count)
    if output_path.exists() and not overwrite:
        raise TextExtractionError(f"Output already exists: {output_path}. Pass --overwrite to replace it.")

    try:
        with temporary_output_path(output_path) as temporary_path:
            with temporary_path.open("w", encoding="utf-8") as out_file:
                for page_index in range(doc.page_count):
                    page_number = page_index + 1
                    logger.info("Processing page %d/%d", page_number, doc.page_count)

                    try:
                        page = doc.load_page(page_index)
                        text = page.get_text("text") or ""

                        if not text.strip():
                            if use_ocr and ocr_available():
                                logger.info("Page %d has no text layer; running OCR fallback.", page_number)
                                text = ocr_page(page, ocr_dpi)
                                summary.ocr_pages += 1
                            elif use_ocr:
                                logger.warning(
                                    "Page %d has no text layer; OCR fallback unavailable: %s.",
                                    page_number,
                                    ocr_dependency_message(),
                                )
                                summary.empty_pages += 1
                            else:
                                logger.info("Page %d has no text layer; OCR fallback disabled.", page_number)
                                summary.empty_pages += 1

                        out_file.write(text)
                        if not text.endswith("\n"):
                            out_file.write("\n")
                        summary.processed_pages += 1
                    except Exception as exc:
                        logger.error("Error on page %d: %s", page_number, exc)
                        summary.failed_pages += 1
    except ScriptError as exc:
        raise TextExtractionError(str(exc)) from exc
    except OSError as exc:
        raise TextExtractionError(f"Failed writing '{output_path}': {exc}") from exc

    return summary


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if FITZ_IMPORT_ERROR is not None:
        print("Error: PyMuPDF is required. Install it with: pip install pymupdf", file=sys.stderr)
        return 2

    logger = None
    doc = None

    try:
        pdf_path, output_path, log_path = build_paths(args)
        logger = setup_logger(log_path, args.quiet)
        use_ocr = not args.no_ocr

        logger.info("Starting extraction for '%s'", pdf_path)
        logger.info("Output text file: '%s'", output_path)
        logger.info("Log file: '%s'", log_path)

        doc = open_pdf(pdf_path, args.password)
        logger.info("Opened PDF '%s' (%d pages)", pdf_path, doc.page_count)
        summary = extract_text_from_pdf(
            doc,
            output_path,
            overwrite=args.overwrite,
            use_ocr=use_ocr,
            ocr_dpi=args.ocr_dpi,
            logger=logger,
        )
    except TextExtractionError as exc:
        if logger is None:
            print(f"Error: {exc}", file=sys.stderr)
        else:
            logger.error("%s", exc)
        return 1
    finally:
        if doc is not None:
            doc.close()

    logger.info(
        "Extraction complete. Processed: %d/%d | OCR pages: %d | Empty pages: %d | Failed pages: %d",
        summary.processed_pages,
        summary.total_pages,
        summary.ocr_pages,
        summary.empty_pages,
        summary.failed_pages,
    )
    logger.info("Output: '%s'", output_path)
    return 1 if summary.failed_pages else 0


if __name__ == "__main__":
    raise SystemExit(main())
