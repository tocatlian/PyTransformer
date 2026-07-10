#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_pdf_extract_selectable_text_batch.py
Purpose: Extract selectable text from every PDF directly inside a folder.
When to use: Use for batch conversion of text-layer PDFs when OCR is not needed.
Changes: Writes one UTF-8 .txt file per PDF beside each PDF or in --output-folder.
Inputs: Folder path; optional --output-folder, --overwrite, --include-hidden, and --password.
Environment variables: None.
Dependencies: pypdf or PyPDF2.
Safety notes: Does not recurse, skips symlinks, and refuses to overwrite output unless --overwrite is passed.
Example: pyt-pdf-extract-selectable-text-batch --output-folder "/path/to/text" "/path/to/pdfs"
Expected result: One .txt file for each PDF that could be processed.
Related scripts: pyt_pdf_extract_selectable_text.py, pyt_pdf_extract_text.py, pyt_pdf_render_jpeg.py.
"""

from __future__ import annotations

import argparse
import importlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pytransformer.core.common import (
    ScriptError,
    build_command_parser,
    close_resource,
    configure_logging,
    ensure_output_path,
    fail,
    is_hidden_path,
    require_existing_folder,
    resolve_user_path,
    sorted_directory_items,
    temporary_output_path,
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


@dataclass
class BatchSummary:
    written: int = 0
    skipped: int = 0
    failed: int = 0
    empty_pages: int = 0


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="Extract selectable text from PDFs directly inside a folder.",
        examples=(
            'pyt-pdf-extract-selectable-text-batch --output-folder "/path/to/text" "/path/to/pdfs"',
            'pyt-pdf-extract-selectable-text-batch --overwrite --password "secret" "/path/to/pdfs"',
        ),
    )
    parser.add_argument("folder", type=Path, help="Folder containing PDF files.")
    parser.add_argument(
        "-o",
        "--output-folder",
        type=Path,
        help="Folder for text output. Defaults to writing each .txt beside its PDF.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden PDF files.")
    parser.add_argument("--password", default="", help="Password to try for encrypted PDFs.")
    parser.add_argument("--quiet", action="store_true", help="Only print warnings and errors.")
    return parser


def require_pdf_dependency() -> None:
    if PDF_IMPORT_ERROR is not None:
        raise ScriptError("pypdf or PyPDF2 is required. Install one with: pip install pypdf")


def find_pdf_files(folder: Path, *, include_hidden: bool) -> list[Path]:
    pdf_files: list[Path] = []
    for item in sorted_directory_items(folder):
        if not include_hidden and is_hidden_path(item):
            continue
        if item.is_symlink() or not item.is_file():
            continue
        if item.suffix.lower() in PDF_EXTENSIONS:
            pdf_files.append(item)
    return pdf_files


def resolve_output_folder(path: Path | None) -> Path | None:
    if path is None:
        return None
    output_folder = resolve_user_path(path)
    try:
        output_folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ScriptError(f"Could not create output folder '{output_folder}': {exc}") from exc
    if not output_folder.is_dir():
        raise ScriptError(f"Output path is not a folder: {output_folder}")
    return output_folder


def output_path_for(pdf_path: Path, output_folder: Path | None) -> Path:
    if output_folder is None:
        return pdf_path.with_suffix(".txt")
    return output_folder / f"{pdf_path.stem}.txt"


def open_pdf_reader(pdf_path: Path, password: str) -> Any:
    pdf_reader_cls = PdfReader
    if pdf_reader_cls is None:
        raise ScriptError("pypdf or PyPDF2 is required. Install one with: pip install pypdf")

    try:
        reader = pdf_reader_cls(str(pdf_path))
    except Exception as exc:
        raise ScriptError(f"Could not open PDF: {exc}") from exc

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


def process_folder(
    folder: Path,
    *,
    output_folder: Path | None,
    overwrite: bool,
    include_hidden: bool,
    password: str,
) -> BatchSummary:
    pdf_files = find_pdf_files(folder, include_hidden=include_hidden)
    summary = BatchSummary()

    if not pdf_files:
        logging.info("No PDF files found in: %s", folder)
        return summary

    logging.info("Input folder: %s", folder)
    logging.info("PDF files: %d", len(pdf_files))
    if output_folder is not None:
        logging.info("Output folder: %s", output_folder)

    for pdf_path in pdf_files:
        try:
            planned_output_path = output_path_for(pdf_path, output_folder)
            if planned_output_path.exists() and not overwrite:
                summary.skipped += 1
                logging.warning("Skipped %s: output already exists: %s", pdf_path.name, planned_output_path)
                continue

            output_path = ensure_output_path(
                planned_output_path,
                overwrite=overwrite,
                input_paths=[pdf_path],
                label="Output file",
            )
            reader = open_pdf_reader(pdf_path, password)
            try:
                text, empty_pages = extract_text(reader)
            finally:
                close_resource(reader)
            with temporary_output_path(output_path) as temporary_path:
                temporary_path.write_text(text, encoding="utf-8")
            summary.empty_pages += empty_pages
            summary.written += 1
            logging.info("Saved text: %s", output_path.name)
        except ScriptError as exc:
            summary.failed += 1
            logging.error("Failed %s: %s", pdf_path.name, exc)
        except OSError as exc:
            summary.failed += 1
            logging.error("Failed %s: %s", pdf_path.name, exc)

    return summary


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(quiet=args.quiet)

    try:
        require_pdf_dependency()
        folder = require_existing_folder(args.folder, label="Input folder")
        output_folder = resolve_output_folder(args.output_folder)
        summary = process_folder(
            folder,
            output_folder=output_folder,
            overwrite=args.overwrite,
            include_hidden=args.include_hidden,
            password=args.password,
        )
    except ScriptError as exc:
        return fail(str(exc), code=2)

    logging.info(
        "Done. Written: %d | Skipped: %d | Failed: %d | Empty pages: %d",
        summary.written,
        summary.skipped,
        summary.failed,
        summary.empty_pages,
    )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
