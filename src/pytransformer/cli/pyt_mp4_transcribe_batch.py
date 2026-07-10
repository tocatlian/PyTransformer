#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_mp4_transcribe_batch.py
Purpose: Transcribe every MP4 file directly inside a folder into text files.
When to use: Use for batch transcription of a flat folder of videos.
Changes: Writes one .txt transcript per MP4 file, either beside each video or in --output-folder.
Inputs: Folder path; optional --output-folder, --overwrite, --include-hidden, and --language.
Environment variables: None.
Dependencies: moviepy, SpeechRecognition, FFmpeg, and network access for Google Web Speech API.
Safety notes: Does not recurse, skips symlinks, and refuses to overwrite transcripts unless --overwrite is passed.
Example: pyt-mp4-transcribe-batch --output-folder "/path/to/transcripts" "/path/to/videos"
Expected result: A transcript file for each MP4 that could be processed.
Related scripts: pyt_mp4_transcribe.py, pyt_mp4_split_chunks.py.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

from pytransformer.core.audio import require_transcription_dependencies, transcribe_mp4_to_text
from pytransformer.core.common import (
    ScriptError,
    build_command_parser,
    configure_logging,
    ensure_output_path,
    fail,
    is_hidden_path,
    require_existing_folder,
    resolve_user_path,
    sorted_directory_items,
    temporary_output_path,
)

MP4_EXTENSIONS = {".mp4"}
DEFAULT_LANGUAGE = "en-US"


@dataclass
class BatchSummary:
    written: int = 0
    skipped: int = 0
    failed: int = 0


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="Transcribe MP4 files directly inside a folder.",
        examples=(
            'pyt-mp4-transcribe-batch --output-folder "/path/to/transcripts" "/path/to/videos"',
            'pyt-mp4-transcribe-batch --language en-US --overwrite "/path/to/videos"',
        ),
    )
    parser.add_argument("folder", type=Path, help="Folder containing MP4 files.")
    parser.add_argument(
        "-o",
        "--output-folder",
        type=Path,
        help="Folder for transcripts. Defaults to writing each transcript beside its MP4 file.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing transcript files.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden MP4 files.")
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Recognition language code (default {DEFAULT_LANGUAGE}).",
    )
    parser.add_argument("--quiet", action="store_true", help="Only print warnings and errors.")
    return parser


def find_mp4_files(folder: Path, *, include_hidden: bool) -> list[Path]:
    mp4_files: list[Path] = []
    for item in sorted_directory_items(folder):
        if not include_hidden and is_hidden_path(item):
            continue
        if item.is_symlink() or not item.is_file():
            continue
        if item.suffix.lower() in MP4_EXTENSIONS:
            mp4_files.append(item)
    return mp4_files


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


def output_path_for(mp4_path: Path, output_folder: Path | None) -> Path:
    if output_folder is None:
        return mp4_path.with_suffix(".txt")
    return output_folder / f"{mp4_path.stem}.txt"


def process_folder(
    folder: Path,
    *,
    output_folder: Path | None,
    overwrite: bool,
    include_hidden: bool,
    language: str,
) -> BatchSummary:
    mp4_files = find_mp4_files(folder, include_hidden=include_hidden)
    summary = BatchSummary()

    if not mp4_files:
        logging.info("No MP4 files found in: %s", folder)
        return summary

    logging.info("Input folder: %s", folder)
    logging.info("MP4 files: %d", len(mp4_files))
    if output_folder is not None:
        logging.info("Transcript folder: %s", output_folder)

    for mp4_path in mp4_files:
        try:
            transcript_path = output_path_for(mp4_path, output_folder)
            if transcript_path.exists() and not overwrite:
                summary.skipped += 1
                logging.warning("Skipped %s: transcript already exists: %s", mp4_path.name, transcript_path)
                continue

            transcript_path = ensure_output_path(
                transcript_path,
                overwrite=overwrite,
                input_paths=[mp4_path],
                label="Transcript file",
            )
            logging.info("Transcribing: %s", mp4_path.name)
            transcript = transcribe_mp4_to_text(mp4_path, language=language)
            with temporary_output_path(transcript_path) as temporary_path:
                temporary_path.write_text(transcript + "\n", encoding="utf-8")
            summary.written += 1
            logging.info("Saved transcript: %s", transcript_path)
        except ScriptError as exc:
            summary.failed += 1
            logging.error("Failed %s: %s", mp4_path.name, exc)
        except OSError as exc:
            summary.failed += 1
            logging.error("Failed %s: %s", mp4_path.name, exc)

    return summary


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(quiet=args.quiet)

    try:
        require_transcription_dependencies()
        folder = require_existing_folder(args.folder, label="Input folder")
        output_folder = resolve_output_folder(args.output_folder)
        summary = process_folder(
            folder,
            output_folder=output_folder,
            overwrite=args.overwrite,
            include_hidden=args.include_hidden,
            language=args.language,
        )
    except ScriptError as exc:
        return fail(str(exc), code=2)

    logging.info("Done. Written: %d | Skipped: %d | Failed: %d", summary.written, summary.skipped, summary.failed)
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
