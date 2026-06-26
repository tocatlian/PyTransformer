#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_pdf_extract_selectable_text.py
Purpose: Extract selectable text from one PDF using a lightweight PDF parser.
When to use: Use for text-layer PDFs when OCR is not needed.
Changes: Writes one UTF-8 .txt file next to the PDF or to --output.
Inputs: PDF file path; optional --output and --overwrite.
Environment variables: None.
Dependencies: pypdf or PyPDF2.
Safety notes: Refuses to overwrite existing output unless --overwrite is passed.
Example: pyt-pdf-extract-selectable-text "/path/to/file.pdf"
Expected result: A .txt file containing page text separated by blank lines.
Related scripts: pyt_pdf_extract_selectable_text_batch.py, pyt_pdf_extract_text.py, pyt_pdf_render_jpeg.py.
"""

from __future__ import annotations

import argparse
import importlib
import logging
from pathlib import Path
from typing import Any

from pytransformer.core.common import (
    ScriptError,
    build_command_parser,
    configure_logging,
    ensure_output_path,
    fail,
    require_existing_file,
)

PdfReader: Any | None
PDF_IMPORT_ERROR: ImportError | None

try:
    pypdf_module = importlib.import_module("pypdf")
except ImportError as first_import_error:
    try:
        pypdf2_module = importlib.import_module("PyPDF2")
    except ImportError:
        PdfReader = None
        PDF_IMPORT_ERROR = first_import_error
    else:
        PdfReader = pypdf2_module.PdfReader
        PDF_IMPORT_ERROR = None
else:
    PdfReader = pypdf_module.PdfReader
    PDF_IMPORT_ERROR = None


PDF_EXTENSIONS = {".pdf"}


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="Extract selectable text from one PDF.",
        examples=(
            'pyt-pdf-extract-selectable-text "/path/to/file.pdf"',
            'pyt-pdf-extract-selectable-text --output "/path/to/output.txt" --overwrite "/path/to/file.pdf"',
        ),
    )
    parser.add_argument("pdf_file", type=Path, help="Path to the input PDF.")
    parser.add_argument("-o", "--output", type=Path, help="Output .txt path. Defaults to <pdf>.txt.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the output file if it exists.")
    parser.add_argument("--password", default="", help="Password for encrypted PDFs.")
    parser.add_argument("--quiet", action="store_true", help="Only print warnings and errors.")
    return parser


def require_pdf_dependency() -> None:
    if PDF_IMPORT_ERROR is not None:
        raise ScriptError("pypdf or PyPDF2 is required. Install one with: pip install pypdf")


def validate_args(args: argparse.Namespace) -> tuple[Path, Path]:
    pdf_path = require_existing_file(args.pdf_file, label="PDF file", suffixes=PDF_EXTENSIONS)
    output_path = args.output if args.output else pdf_path.with_suffix(".txt")
    output_path = ensure_output_path(output_path, overwrite=args.overwrite, input_paths=[pdf_path], label="Output file")
    return pdf_path, output_path


def open_pdf_reader(pdf_path: Path, password: str) -> Any:
    pdf_reader_cls = PdfReader
    if pdf_reader_cls is None:
        raise ScriptError("pypdf or PyPDF2 is required. Install one with: pip install pypdf")

    try:
        reader = pdf_reader_cls(str(pdf_path))
    except Exception as exc:
        raise ScriptError(f"Could not open PDF '{pdf_path}': {exc}") from exc

    if getattr(reader, "is_encrypted", False):
        if not password:
            raise ScriptError("PDF is encrypted; pass --password to unlock it.")
        try:
            result = reader.decrypt(password)
        except Exception as exc:
            raise ScriptError(f"Could not decrypt PDF: {exc}") from exc
        if result == 0:
            raise ScriptError("PDF is encrypted and the provided password did not work.")

    if not reader.pages:
        raise ScriptError("PDF has no pages to extract.")

    return reader


def extract_text(reader: Any) -> tuple[str, int]:
    page_text: list[str] = []
    empty_pages = 0

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            raise ScriptError(f"Could not extract text from page {page_number}: {exc}") from exc
        if not text.strip():
            empty_pages += 1
        page_text.append(text.rstrip())

    return "\n\n".join(page_text).rstrip() + "\n", empty_pages


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(quiet=args.quiet)

    try:
        require_pdf_dependency()
        pdf_path, output_path = validate_args(args)
        reader = open_pdf_reader(pdf_path, args.password)
        text, empty_pages = extract_text(reader)
        output_path.write_text(text, encoding="utf-8")
    except ScriptError as exc:
        return fail(str(exc), code=2)
    except OSError as exc:
        return fail(str(exc), code=1)

    logging.info("Text saved: %s", output_path)
    if empty_pages:
        logging.warning("Pages with no extractable text: %d", empty_pages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
