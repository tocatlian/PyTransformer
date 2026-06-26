#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_pdf_render_jpeg.py
Purpose: Convert every page of one PDF into high-resolution JPEG images.
When to use: Use when PDF pages need image files for review, OCR, or image workflows.
Changes: Creates or updates an output folder containing page_*.jpg files.
Inputs: PDF file path; optional --output-folder, --dpi, --quality, --overwrite, and --password.
Environment variables: None.
Dependencies: PyMuPDF.
Safety notes: Existing JPEG files are skipped unless --overwrite is passed.
Example: pyt-pdf-render-jpeg --dpi 300 --quality 95 --output-folder "/path/to/output" "/path/to/file.pdf"
Expected result: Numbered JPEG files rendered from the PDF pages.
Related scripts: pyt_pdf_extract_text.py, pyt_pdf_extract_selectable_text.py, pyt_pdf_extract_selectable_text_batch.py.
"""

from __future__ import annotations

import argparse
import importlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pytransformer.core.common import build_command_parser

fitz: Any | None
FITZ_IMPORT_ERROR: ImportError | None

try:
    fitz = importlib.import_module("fitz")  # PyMuPDF
except ImportError as exc:
    fitz = None
    FITZ_IMPORT_ERROR = exc
else:
    FITZ_IMPORT_ERROR = None


VALID_EXT = {".pdf"}
DEFAULT_DPI = 300
DEFAULT_QUALITY = 95


class ConversionError(RuntimeError):
    """Raised for user-fixable conversion failures."""


@dataclass
class ConversionSummary:
    saved: int = 0
    skipped: int = 0
    failed: int = 0


def setup_logger(quiet: bool) -> None:
    logging.basicConfig(
        level=logging.ERROR if quiet else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="Convert a PDF into high resolution JPEG images.",
        examples=(
            'pyt-pdf-render-jpeg --dpi 300 "/path/to/file.pdf"',
            'pyt-pdf-render-jpeg --quality 95 --output-folder "/path/to/pages" "/path/to/file.pdf"',
        ),
    )
    parser.add_argument("pdf_file", type=Path, help="Path to the input PDF.")
    parser.add_argument(
        "-o",
        "--output-folder",
        type=Path,
        help="Destination folder. Defaults to a timestamped sibling folder.",
    )
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help=f"Desired output DPI (default {DEFAULT_DPI}).")
    parser.add_argument(
        "--quality",
        type=int,
        default=DEFAULT_QUALITY,
        help=f"JPEG quality 1-100 (default {DEFAULT_QUALITY}).",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing images if present.")
    parser.add_argument("--quiet", action="store_true", help="Only print errors.")
    parser.add_argument("--password", default="", help="Password for encrypted PDFs.")
    return parser


def validate_inputs(pdf_path: Path, dest_dir: Path, quality: int, dpi: int) -> None:
    if not pdf_path.exists():
        raise ConversionError(f"PDF not found: {pdf_path}")

    if not pdf_path.is_file():
        raise ConversionError(f"PDF path is not a file: {pdf_path}")

    if pdf_path.suffix.lower() not in VALID_EXT:
        raise ConversionError(f"File is not a PDF: {pdf_path}")

    if dpi <= 0:
        raise ConversionError(f"DPI must be positive. Got {dpi}")

    if not (1 <= quality <= 100):
        raise ConversionError(f"JPEG quality must be between 1 and 100. Got {quality}")

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConversionError(f"Could not create destination directory: {dest_dir} ({exc})") from exc

    if not dest_dir.is_dir():
        raise ConversionError(f"Destination path is not a directory: {dest_dir}")


def open_pdf(pdf_path: Path, password: str) -> Any:
    fitz_module = fitz
    if fitz_module is None:
        raise ConversionError("PyMuPDF is required. Install it with: pip install pymupdf")

    try:
        doc = fitz_module.open(str(pdf_path))
    except Exception as exc:
        raise ConversionError(f"Failed to open PDF: {exc}") from exc

    try:
        if doc.is_encrypted:
            if not password:
                raise ConversionError("PDF is encrypted; pass --password to unlock it.")
            if not doc.authenticate(password):
                raise ConversionError("PDF is encrypted and the provided password did not work.")

        if doc.page_count <= 0:
            raise ConversionError("PDF has no pages to convert.")
    except Exception:
        doc.close()
        raise

    return doc


def save_pixmap_jpeg(pix: Any, out_path: Path, quality: int) -> None:
    """
    Handle PyMuPDF version differences:
    - Newer versions use jpg_quality.
    - Older versions use quality.
    """
    try:
        pix.save(str(out_path), jpg_quality=quality)
    except TypeError:
        pix.save(str(out_path), quality=quality)


def convert_pdf_to_images(
    doc: Any,
    dest_dir: Path,
    dpi: int,
    quality: int,
    overwrite: bool,
) -> ConversionSummary:
    fitz_module = fitz
    if fitz_module is None:
        raise ConversionError("PyMuPDF is required. Install it with: pip install pymupdf")

    zoom = dpi / 72.0
    matrix = fitz_module.Matrix(zoom, zoom)

    total_pages = doc.page_count
    digits = len(str(total_pages))
    summary = ConversionSummary()

    logging.info("Pages to process: %d", total_pages)
    logging.info("Rendering at ~%d DPI, JPEG quality %d", dpi, quality)

    for idx in range(total_pages):
        page_num = idx + 1
        out_path = dest_dir / f"page_{page_num:0{digits}d}.jpg"

        if out_path.exists() and not overwrite:
            logging.warning("Skipping existing file: %s", out_path.name)
            summary.skipped += 1
            continue

        try:
            page = doc.load_page(idx)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            save_pixmap_jpeg(pix, out_path, quality)
        except Exception as exc:
            logging.error("Failed to convert page %d: %s", page_num, exc)
            summary.failed += 1
            continue

        summary.saved += 1
        logging.info("Saved %s (%d of %d)", out_path.name, page_num, total_pages)

    return summary


def default_output_dir(pdf_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return pdf_path.parent / f"{pdf_path.stem}_images_{stamp}"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    setup_logger(quiet=args.quiet)

    if FITZ_IMPORT_ERROR is not None:
        logging.error("PyMuPDF is required. Install it with: pip install pymupdf")
        return 2

    pdf_path = args.pdf_file.expanduser().resolve()

    doc = None
    try:
        if args.output_folder is None:
            dest_dir = default_output_dir(pdf_path)
        else:
            dest_dir = args.output_folder.expanduser().resolve()
        validate_inputs(pdf_path, dest_dir, args.quality, args.dpi)

        logging.info("PDF: %s", pdf_path)
        logging.info("Output directory: %s", dest_dir)

        doc = open_pdf(pdf_path, args.password)
        summary = convert_pdf_to_images(doc, dest_dir, args.dpi, args.quality, args.overwrite)
    except ConversionError as exc:
        logging.error("%s", exc)
        return 1
    finally:
        if doc is not None:
            doc.close()

    logging.info(
        "Done. Saved: %d | Skipped: %d | Failed: %d",
        summary.saved,
        summary.skipped,
        summary.failed,
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
