#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_mp4_split_chunks.py
Purpose: Split one MP4 file into fixed-length MP4 chunks.
When to use: Use when a long video needs smaller files for upload, review, or downstream processing.
Changes: Creates a sibling output folder and writes chunk files into it.
Inputs: MP4 file path; optional --seconds, --output-folder, and --overwrite.
Environment variables: None.
Dependencies: moviepy and its FFmpeg runtime.
Safety notes: Existing chunk files are skipped unless --overwrite is passed.
Example: pyt-mp4-split-chunks --seconds 30 "/path/to/video.mp4"
Expected result: Numbered MP4 chunk files in <video>_chunks or the requested output folder.
Related scripts: pyt_mp4_transcribe.py, pyt_mp4_transcribe_batch.py.
"""

from __future__ import annotations

import argparse
import importlib
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pytransformer.core.common import (
    ScriptError,
    build_command_parser,
    configure_logging,
    fail,
    require_existing_file,
    require_positive_int,
    resolve_user_path,
    temporary_output_path,
)

VideoFileClip: Any | None
MOVIEPY_IMPORT_ERROR: ImportError | None

try:
    moviepy_editor = importlib.import_module("moviepy.editor")
except ImportError as first_import_error:
    try:
        moviepy_module = importlib.import_module("moviepy")
    except ImportError:
        VideoFileClip = None
        MOVIEPY_IMPORT_ERROR = first_import_error
    else:
        VideoFileClip = moviepy_module.VideoFileClip
        MOVIEPY_IMPORT_ERROR = None
else:
    VideoFileClip = moviepy_editor.VideoFileClip
    MOVIEPY_IMPORT_ERROR = None


MP4_EXTENSIONS = {".mp4"}
DEFAULT_CHUNK_SECONDS = 30


@dataclass
class ChunkSummary:
    saved: int = 0
    skipped: int = 0
    failed: int = 0


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="Split one MP4 file into fixed-length chunks.",
        examples=(
            'pyt-mp4-split-chunks --seconds 30 "/path/to/video.mp4"',
            'pyt-mp4-split-chunks --seconds 120 --output-folder "/path/to/chunks" "/path/to/video.mp4"',
        ),
    )
    parser.add_argument("mp4_file", type=Path, help="Path to the MP4 file to split.")
    parser.add_argument(
        "-s",
        "--seconds",
        type=int,
        default=DEFAULT_CHUNK_SECONDS,
        help=f"Chunk length in seconds (default {DEFAULT_CHUNK_SECONDS}).",
    )
    parser.add_argument(
        "-o",
        "--output-folder",
        type=Path,
        help="Destination folder. Defaults to a sibling folder named <video>_chunks.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing chunk files.")
    parser.add_argument("--quiet", action="store_true", help="Only print warnings and errors.")
    return parser


def resolve_output_folder(video_path: Path, requested_folder: Path | None) -> Path:
    if requested_folder is None:
        return video_path.with_name(f"{video_path.stem}_chunks")
    return resolve_user_path(requested_folder)


def validate_args(args: argparse.Namespace) -> tuple[Path, Path]:
    require_positive_int(args.seconds, label="Chunk length")
    video_path = require_existing_file(args.mp4_file, label="MP4 file", suffixes=MP4_EXTENSIONS)
    output_folder = resolve_output_folder(video_path, args.output_folder)

    if output_folder == video_path:
        raise ScriptError("Output folder must be different from the input MP4 file.")

    try:
        output_folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ScriptError(f"Could not create output folder '{output_folder}': {exc}") from exc

    if not output_folder.is_dir():
        raise ScriptError(f"Output path is not a folder: {output_folder}")

    return video_path, output_folder


def split_video(video_path: Path, output_folder: Path, *, chunk_seconds: int, overwrite: bool) -> ChunkSummary:
    video_clip_cls = VideoFileClip
    if video_clip_cls is None:
        raise ScriptError("moviepy is required. Install it with: pip install moviepy")

    summary = ChunkSummary()
    clip: Any | None = None

    try:
        clip = video_clip_cls(str(video_path))
        duration = float(clip.duration or 0)
        if not math.isfinite(duration) or duration <= 0:
            raise ScriptError(f"Could not determine a positive duration for: {video_path}")

        total_chunks = int(duration // chunk_seconds) + int(duration % chunk_seconds > 0)
        digits = len(str(total_chunks))
        logging.info("Video: %s", video_path)
        logging.info("Output folder: %s", output_folder)
        logging.info(
            "Duration: %.2f seconds | Chunk length: %d seconds | Chunks: %d",
            duration,
            chunk_seconds,
            total_chunks,
        )

        for index in range(total_chunks):
            chunk_number = index + 1
            start_time = index * chunk_seconds
            end_time = min((index + 1) * chunk_seconds, duration)
            chunk_path = output_folder / f"{video_path.stem}_chunk_{chunk_number:0{digits}d}.mp4"

            if chunk_path.exists() and not overwrite:
                logging.warning("Skipping existing chunk: %s", chunk_path.name)
                summary.skipped += 1
                continue

            subclip = None
            try:
                if hasattr(clip, "subclip"):
                    subclip = clip.subclip(start_time, end_time)
                else:
                    subclip = clip.subclipped(start_time, end_time)
                with temporary_output_path(chunk_path) as temporary_path:
                    subclip.write_videofile(
                        str(temporary_path),
                        codec="libx264",
                        audio_codec="aac",
                        logger=None,
                    )
                summary.saved += 1
                logging.info("Saved chunk %d/%d: %s", chunk_number, total_chunks, chunk_path.name)
            except Exception as exc:
                summary.failed += 1
                logging.error("Failed to save chunk %d/%d: %s", chunk_number, total_chunks, exc)
            finally:
                if subclip is not None:
                    subclip.close()
    finally:
        if clip is not None:
            clip.close()

    return summary


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(quiet=args.quiet)

    if MOVIEPY_IMPORT_ERROR is not None:
        return fail("moviepy is required. Install it with: pip install moviepy", code=2)

    try:
        video_path, output_folder = validate_args(args)
        summary = split_video(video_path, output_folder, chunk_seconds=args.seconds, overwrite=args.overwrite)
    except ScriptError as exc:
        return fail(str(exc), code=2)

    logging.info("Done. Saved: %d | Skipped: %d | Failed: %d", summary.saved, summary.skipped, summary.failed)
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
