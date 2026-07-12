#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_files_append_folder_name.py
Purpose: Rename files by appending the containing folder name before each file extension.
When to use: Use when exported files should carry their folder or shoot name in the filename.
Changes: Renames regular files directly inside the selected folder.
Inputs: Folder path; optional --dry-run, --yes, and --include-hidden.
Environment variables: None.
Dependencies: Python standard library only.
Safety notes: Requires confirmation unless --yes is passed; skips symlinks and existing targets.
Example: pyt-files-append-folder-name --dry-run "/path/to/Tokyo"
Expected result: Files such as photo.jpg become photo-Tokyo.jpg.
Related scripts: pyt_image_variants_count.py.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

from pytransformer.core.common import (
    ScriptError,
    build_command_parser,
    configure_logging,
    confirm_action,
    fail,
    is_hidden_path,
    require_existing_folder,
    sorted_directory_items,
)


@dataclass
class RenamePlan:
    source: Path
    target: Path


@dataclass
class RenameSummary:
    renamed: int = 0
    planned: int = 0
    skipped: int = 0
    failed: int = 0


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="Append the folder name to regular files directly inside a folder.",
        examples=(
            'pyt-files-append-folder-name --dry-run "/path/to/Tokyo"',
            'pyt-files-append-folder-name --yes "/path/to/Tokyo"',
        ),
    )
    parser.add_argument("folder", type=Path, help="Folder containing files to rename.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned renames without changing files.")
    parser.add_argument("--yes", action="store_true", help="Skip the interactive confirmation prompt.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden dotfiles.")
    parser.add_argument("--quiet", action="store_true", help="Only print warnings and errors.")
    return parser


def build_target_path(source: Path, folder_name: str) -> Path:
    return source.with_name(f"{source.stem}-{folder_name}{source.suffix}")


def already_has_folder_name(path: Path, folder_name: str) -> bool:
    return path.stem.casefold().endswith(f"-{folder_name}".casefold())


def build_rename_plan(folder: Path, *, include_hidden: bool) -> tuple[list[RenamePlan], int]:
    plans: list[RenamePlan] = []
    skipped = 0
    folder_name = folder.name

    if not folder_name:
        raise ScriptError(f"Could not derive a folder name from: {folder}")

    for item in sorted_directory_items(folder):
        if not include_hidden and is_hidden_path(item):
            skipped += 1
            continue
        if item.is_symlink() or not item.is_file():
            skipped += 1
            continue
        if already_has_folder_name(item, folder_name):
            skipped += 1
            continue

        target = build_target_path(item, folder_name)
        if target.exists():
            logging.warning("Skipping %s because target already exists: %s", item.name, target.name)
            skipped += 1
            continue
        plans.append(RenamePlan(source=item, target=target))

    return plans, skipped


def apply_rename_plan(plans: list[RenamePlan], *, dry_run: bool) -> RenameSummary:
    summary = RenameSummary(planned=len(plans))
    for plan in plans:
        if dry_run:
            logging.info("Would rename: %s -> %s", plan.source.name, plan.target.name)
            continue

        try:
            if plan.target.exists():
                summary.skipped += 1
                logging.warning("Skipping %s because target now exists: %s", plan.source.name, plan.target.name)
                continue
            plan.source.rename(plan.target)
            summary.renamed += 1
            logging.info("Renamed: %s -> %s", plan.source.name, plan.target.name)
        except OSError as exc:
            summary.failed += 1
            logging.error("Failed to rename %s: %s", plan.source.name, exc)
    return summary


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(quiet=args.quiet)

    try:
        folder = require_existing_folder(args.folder, label="Input folder")
        plans, skipped = build_rename_plan(folder, include_hidden=args.include_hidden)

        if not plans:
            logging.info("No files need renaming. Skipped: %d", skipped)
            return 0

        for plan in plans:
            logging.info("Plan: %s -> %s", plan.source.name, plan.target.name)

        if not args.dry_run:
            confirm_action(
                f"This will rename {len(plans)} file(s) in '{folder}'.",
                yes=args.yes,
            )

        summary = apply_rename_plan(plans, dry_run=args.dry_run)
        summary.skipped = skipped
    except ScriptError as exc:
        return fail(str(exc), code=2)

    if args.dry_run:
        logging.info("Dry run complete. Planned: %d | Skipped: %d", summary.planned, summary.skipped)
    else:
        logging.info(
            "Done. Renamed: %d | Skipped: %d | Failed: %d",
            summary.renamed,
            summary.skipped,
            summary.failed,
        )
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
