#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_mp4_transcribe.py
Purpose: Transcribe speech from one MP4 file into a UTF-8 text file.
When to use: Use for a single video when Google Web Speech API transcription is acceptable.
Changes: Writes one .txt transcript file and uses a temporary WAV file during processing.
Inputs: MP4 file path; optional --output, --overwrite, and --language.
Environment variables: None.
Dependencies: moviepy, SpeechRecognition, FFmpeg, and network access for Google Web Speech API.
Safety notes: Refuses to overwrite an existing transcript unless --overwrite is passed.
Example: pyt-mp4-transcribe --language en-US "/path/to/video.mp4"
Expected result: A text transcript next to the MP4 or at --output.
Related scripts: pyt_mp4_transcribe_batch.py, pyt_mp4_split_chunks.py.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pytransformer.core.audio import require_transcription_dependencies, transcribe_mp4_to_text
from pytransformer.core.common import (
    ScriptError,
    build_command_parser,
    configure_logging,
    ensure_output_path,
    fail,
    require_existing_file,
    temporary_output_path,
)

MP4_EXTENSIONS = {".mp4"}
DEFAULT_LANGUAGE = "en-US"


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="Transcribe one MP4 file to a text file.",
        examples=(
            'pyt-mp4-transcribe "/path/to/video.mp4"',
            'pyt-mp4-transcribe --language en-US --output "/path/to/transcript.txt" "/path/to/video.mp4"',
        ),
    )
    parser.add_argument("mp4_file", type=Path, help="Path to the MP4 file to transcribe.")
    parser.add_argument("-o", "--output", type=Path, help="Transcript path. Defaults to <mp4>.txt.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing transcript file.")
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Recognition language code (default {DEFAULT_LANGUAGE}).",
    )
    parser.add_argument("--quiet", action="store_true", help="Only print warnings and errors.")
    return parser


def validate_args(args: argparse.Namespace) -> tuple[Path, Path]:
    mp4_path = require_existing_file(args.mp4_file, label="MP4 file", suffixes=MP4_EXTENSIONS)
    output_path = args.output if args.output else mp4_path.with_suffix(".txt")
    output_path = ensure_output_path(
        output_path,
        overwrite=args.overwrite,
        input_paths=[mp4_path],
        label="Transcript file",
    )
    return mp4_path, output_path


def transcribe_mp4(mp4_path: Path, output_path: Path, *, language: str) -> None:
    logging.info("Extracting and transcribing audio: %s", mp4_path)
    transcript = transcribe_mp4_to_text(mp4_path, language=language)
    with temporary_output_path(output_path) as temporary_path:
        temporary_path.write_text(transcript + "\n", encoding="utf-8")
    logging.info("Transcript saved: %s", output_path)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(quiet=args.quiet)

    try:
        require_transcription_dependencies()
        mp4_path, output_path = validate_args(args)
        transcribe_mp4(mp4_path, output_path, language=args.language)
    except ScriptError as exc:
        return fail(str(exc), code=2)
    except OSError as exc:
        return fail(str(exc), code=1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
