#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_m4a_to_mp3.py
Purpose: Convert one or more M4A audio files into sibling MP3 files.
When to use: Use when M4A recordings need to be shared or processed as MP3 files.
Changes: Writes one MP3 file beside each original M4A through temporary output files.
Inputs: One or more non-empty M4A file paths; optional --overwrite, --quality, --bitrate, --quiet, and --debug.
Environment variables: None.
Dependencies: FFmpeg available on PATH.
Safety notes: Refuses to overwrite existing MP3 files unless --overwrite is passed; failed files do not stop
other inputs.
Example: pyt-m4a-to-mp3 "/path/to/recording.m4a"
Expected result: One MP3 file beside each source M4A.
Related scripts: pyt_mp4_split_chunks.py, pyt_mp4_transcribe.py.
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from pytransformer.core.common import (
    ScriptError,
    build_command_parser,
    configure_logging,
    ensure_output_path,
    fail,
    require_existing_file,
    require_int_range,
    temporary_output_path,
)

M4A_EXTENSIONS = {".m4a"}
FFMPEG_COMMAND = "ffmpeg"
DEFAULT_QUALITY = 2
MIN_QUALITY = 0
MAX_QUALITY = 9
MIN_BITRATE_KBPS = 8
MAX_BITRATE_KBPS = 320
SUPPORTED_BITRATES_KBPS = (8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
MAX_FFMPEG_ERROR_LENGTH = 2000


@dataclass
class ConversionSummary:
    """Track successful and failed input conversions."""

    converted: int = 0
    failed: int = 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = build_command_parser(
        description="Convert one or more M4A audio files into sibling MP3 files.",
        examples=(
            'pyt-m4a-to-mp3 "/path/to/recording.m4a"',
            "pyt-m4a-to-mp3 first.m4a second.m4a",
            'pyt-m4a-to-mp3 --bitrate 192k --overwrite "/path/to/recording.m4a"',
        ),
    )
    quality_group = parser.add_mutually_exclusive_group()
    quality_group.add_argument(
        "-q",
        "--quality",
        type=int,
        default=DEFAULT_QUALITY,
        help=(
            f"Variable-bitrate LAME quality from {MIN_QUALITY} (best) to {MAX_QUALITY} (smallest). "
            f"Default: {DEFAULT_QUALITY}."
        ),
    )
    quality_group.add_argument(
        "-b",
        "--bitrate",
        type=parse_bitrate,
        help="Constant MP3 bitrate using standard values from 8k through 320k.",
    )
    parser.add_argument(
        "m4a_files",
        type=Path,
        nargs="+",
        help="One or more M4A files to convert.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing sibling MP3 file.")
    parser.add_argument("--quiet", action="store_true", help="Only show warnings and errors.")
    parser.add_argument("--debug", action="store_true", help="Show debug logging.")
    return parser


def build_output_path(m4a_path: Path) -> Path:
    """Return the sibling MP3 path for an input M4A file."""
    return m4a_path.with_suffix(".mp3")


def parse_bitrate(value: str) -> str:
    """Normalize and validate a constant MP3 bitrate argument."""
    try:
        return normalize_bitrate(value)
    except ScriptError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def normalize_bitrate(value: str) -> str:
    """Normalize a bitrate value for FFmpeg and reject unsupported MP3 rates."""
    match = re.fullmatch(r"(\d+)[kK]?", value.strip())
    if match is None:
        raise ScriptError("MP3 bitrate must be an integer with an optional 'k' suffix.")

    bitrate_kbps = int(match.group(1))
    if bitrate_kbps not in SUPPORTED_BITRATES_KBPS:
        supported = ", ".join(f"{rate}k" for rate in SUPPORTED_BITRATES_KBPS)
        raise ScriptError(
            f"MP3 bitrate must use a standard value between {MIN_BITRATE_KBPS}k and {MAX_BITRATE_KBPS}k: {supported}."
        )
    return f"{bitrate_kbps}k"


def require_ffmpeg() -> str:
    """Return the FFmpeg executable path or raise a clear setup error."""
    ffmpeg_path = shutil.which(FFMPEG_COMMAND)
    if ffmpeg_path is None:
        raise ScriptError("FFmpeg is required and must be available on PATH.")
    return ffmpeg_path


def validate_args(args: argparse.Namespace) -> list[tuple[Path, Path]]:
    """Validate all source files and resolve their sibling output paths."""
    m4a_paths = []
    for path in args.m4a_files:
        m4a_path = require_existing_file(path, label="M4A file", suffixes=M4A_EXTENSIONS)
        try:
            input_size = m4a_path.stat().st_size
        except OSError as exc:
            raise ScriptError(f"Could not inspect M4A file '{m4a_path}': {exc}") from exc
        if input_size == 0:
            raise ScriptError(f"M4A file is empty: {m4a_path}")
        m4a_paths.append(m4a_path)

    if len(set(m4a_paths)) != len(m4a_paths):
        raise ScriptError("Each M4A input must be provided only once.")

    return [
        (
            m4a_path,
            ensure_output_path(
                build_output_path(m4a_path),
                overwrite=args.overwrite,
                input_paths=[m4a_path],
                label="MP3 file",
            ),
        )
        for m4a_path in m4a_paths
    ]


def build_ffmpeg_command(
    ffmpeg_path: str,
    m4a_path: Path,
    output_path: Path,
    *,
    quality: int,
    bitrate: str | None,
) -> list[str]:
    """Build the FFmpeg command for one M4A-to-MP3 conversion."""
    require_int_range(quality, label="MP3 quality", minimum=MIN_QUALITY, maximum=MAX_QUALITY)
    normalized_bitrate = normalize_bitrate(bitrate) if bitrate is not None else None
    audio_quality_args = ["-b:a", normalized_bitrate] if normalized_bitrate is not None else ["-q:a", str(quality)]
    return [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(m4a_path),
        "-map",
        "0:a:0",
        "-map",
        "0:v:0?",
        "-c:a",
        "libmp3lame",
        *audio_quality_args,
        "-c:v",
        "mjpeg",
        "-disposition:v",
        "attached_pic",
        "-map_metadata",
        "0",
        "-id3v2_version",
        "3",
        str(output_path),
    ]


def convert_m4a_to_mp3(
    m4a_path: Path,
    output_path: Path,
    *,
    quality: int = DEFAULT_QUALITY,
    bitrate: str | None = None,
    ffmpeg_path: str | None = None,
) -> None:
    """Convert one M4A file to MP3 with FFmpeg and finalize it atomically."""
    resolved_ffmpeg_path = ffmpeg_path or require_ffmpeg()
    try:
        with temporary_output_path(output_path) as temporary_path:
            command = build_ffmpeg_command(
                resolved_ffmpeg_path,
                m4a_path,
                temporary_path,
                quality=quality,
                bitrate=bitrate,
            )
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                details = (result.stderr or "").strip()[-MAX_FFMPEG_ERROR_LENGTH:]
                if not details:
                    details = f"FFmpeg exited with status {result.returncode}."
                raise ScriptError(f"Could not convert '{m4a_path}' to MP3: {details}")
            try:
                output_size = temporary_path.stat().st_size
            except OSError as exc:
                raise ScriptError(f"FFmpeg did not create an MP3 file for '{m4a_path}': {exc}") from exc
            if output_size == 0:
                raise ScriptError(f"FFmpeg created an empty MP3 file for '{m4a_path}'.")
    except OSError as exc:
        raise ScriptError(f"Could not run FFmpeg: {exc}") from exc


def run(args: argparse.Namespace) -> int:
    """Run the command."""
    configure_logging(quiet=args.quiet, debug=args.debug)
    require_int_range(args.quality, label="MP3 quality", minimum=MIN_QUALITY, maximum=MAX_QUALITY)
    args.bitrate = normalize_bitrate(args.bitrate) if args.bitrate is not None else None
    conversion_paths = validate_args(args)
    ffmpeg_path = require_ffmpeg()
    summary = ConversionSummary()

    for m4a_path, output_path in conversion_paths:
        logging.info("Converting %s to %s.", m4a_path, output_path)
        try:
            convert_m4a_to_mp3(
                m4a_path,
                output_path,
                quality=args.quality,
                bitrate=args.bitrate,
                ffmpeg_path=ffmpeg_path,
            )
        except ScriptError as exc:
            summary.failed += 1
            logging.error("Failed to convert %s: %s", m4a_path, exc)
            continue

        summary.converted += 1
        logging.info("MP3 saved: %s", output_path)
        print(output_path)

    logging.info("Done. Converted: %d | Failed: %d", summary.converted, summary.failed)
    return 1 if summary.failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except ScriptError as exc:
        return fail(str(exc), code=2)


if __name__ == "__main__":
    raise SystemExit(main())
