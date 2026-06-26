# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""Shared command-line helpers for the PyTransformer utility scripts."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Collection, Iterable


class ScriptError(RuntimeError):
    """Raised for user-fixable command-line or filesystem errors."""


class CommandHelpFormatter(argparse.HelpFormatter):
    """Wrap normal help text while preserving command examples."""

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        if text.startswith("Examples:\n"):
            return "\n".join(f"{indent}{line}" if line else line for line in text.splitlines())
        return super()._fill_text(text, width, indent)


def build_command_parser(*, description: str, examples: Iterable[str]) -> argparse.ArgumentParser:
    """Build a parser with consistent description, argument help, and examples."""
    epilog = "Examples:\n" + "\n".join(f"  {example}" for example in examples)
    return argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=CommandHelpFormatter,
    )


def configure_logging(*, quiet: bool = False, debug: bool = False) -> None:
    """Configure consistent terminal logging for command scripts."""
    if debug:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        force=True,
    )


def fail(message: str, *, code: int = 1) -> int:
    """Print a standard error message and return an exit status."""
    print(f"Error: {message}", file=sys.stderr)
    return code


def resolve_user_path(path: Path) -> Path:
    """Expand '~' and resolve a path without requiring it to exist first."""
    return path.expanduser().resolve()


def require_existing_file(path: Path, *, label: str = "File", suffixes: Collection[str] = ()) -> Path:
    """Validate that path is an existing file, optionally with an allowed suffix."""
    resolved = resolve_user_path(path)
    if not resolved.exists():
        raise ScriptError(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise ScriptError(f"{label} is not a file: {resolved}")
    if suffixes and resolved.suffix.lower() not in {suffix.lower() for suffix in suffixes}:
        expected = ", ".join(sorted(suffixes))
        raise ScriptError(f"{label} must use one of these extensions ({expected}): {resolved}")
    return resolved


def require_existing_folder(path: Path, *, label: str = "Folder") -> Path:
    """Validate that path is an existing folder."""
    resolved = resolve_user_path(path)
    if not resolved.exists():
        raise ScriptError(f"{label} does not exist: {resolved}")
    if not resolved.is_dir():
        raise ScriptError(f"{label} is not a folder: {resolved}")
    return resolved


def ensure_output_path(
    path: Path,
    *,
    overwrite: bool = False,
    input_paths: Iterable[Path] = (),
    label: str = "Output file",
) -> Path:
    """Prepare an output path while preventing accidental clobbering."""
    resolved = resolve_user_path(path)
    protected_inputs = {resolve_user_path(input_path) for input_path in input_paths}
    if resolved in protected_inputs:
        raise ScriptError(f"{label} must be different from the input path: {resolved}")
    if resolved.exists() and not overwrite:
        raise ScriptError(f"{label} already exists: {resolved}. Pass --overwrite to replace it.")
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ScriptError(f"Could not create output folder '{resolved.parent}': {exc}") from exc
    return resolved


def require_positive_int(value: int, *, label: str) -> None:
    """Require a positive integer option value."""
    if value <= 0:
        raise ScriptError(f"{label} must be positive. Got {value}.")


def require_int_range(value: int, *, label: str, minimum: int, maximum: int) -> None:
    """Require an integer option value inside an inclusive range."""
    if not (minimum <= value <= maximum):
        raise ScriptError(f"{label} must be between {minimum} and {maximum}. Got {value}.")


def is_hidden_path(path: Path) -> bool:
    """Return True for dotfiles and folders."""
    return path.name.startswith(".")


def sorted_directory_items(folder: Path) -> list[Path]:
    """Return directory items in deterministic, case-insensitive order."""
    try:
        return sorted(folder.iterdir(), key=lambda path: path.name.casefold())
    except PermissionError as exc:
        raise ScriptError(f"Permission denied while reading folder: {folder}") from exc
    except OSError as exc:
        raise ScriptError(f"Could not read folder '{folder}': {exc}") from exc


def confirm_action(message: str, *, yes: bool = False) -> None:
    """Require explicit confirmation for destructive or hard-to-reverse actions."""
    if yes:
        return
    if not sys.stdin.isatty():
        raise ScriptError(f"{message} Pass --yes to confirm in non-interactive runs.")

    answer = input(f"{message} Type 'yes' to continue: ").strip().casefold()
    if answer != "yes":
        raise ScriptError("Operation cancelled.")
