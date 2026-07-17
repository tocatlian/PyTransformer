# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""Shared command-line helpers for the PyTransformer utility scripts."""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Collection, Iterable, Iterator


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
    if resolved.exists():
        if resolved.is_dir():
            raise ScriptError(f"{label} is a directory, not a file: {resolved}")
        if not overwrite:
            raise ScriptError(f"{label} already exists: {resolved}. Pass --overwrite to replace it.")
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ScriptError(f"Could not create output folder '{resolved.parent}': {exc}") from exc
    return resolved


def copy_temporary_output(temporary_path: Path, output_path: Path) -> None:
    """Copy a completed temporary file into its final path and flush it to disk."""
    resolved = resolve_user_path(output_path)
    output_existed = resolved.exists()
    created_output = False
    backup_path: Path | None = None
    try:
        if output_existed:
            backup_descriptor, backup_name = tempfile.mkstemp(
                prefix=".pytransformer-backup-",
                suffix=resolved.suffix,
            )
            os.close(backup_descriptor)
            backup_path = Path(backup_name)
            shutil.copyfile(resolved, backup_path)

        destination_mode = "wb" if output_existed else "xb"
        destination = resolved.open(destination_mode)
        created_output = not output_existed
        try:
            with temporary_path.open("rb") as source:
                with destination:
                    shutil.copyfileobj(source, destination)
                    destination.flush()
                    os.fsync(destination.fileno())
        finally:
            if not destination.closed:
                destination.close()
    except OSError:
        if output_existed and backup_path is not None:
            with contextlib.suppress(OSError):
                shutil.copyfile(backup_path, resolved)
        elif created_output:
            with contextlib.suppress(OSError):
                resolved.unlink()
        raise
    finally:
        if backup_path is not None:
            with contextlib.suppress(OSError):
                backup_path.unlink()


def is_file_provider_path(path: Path) -> bool:
    """Return whether the output folder or an ancestor is managed by File Provider."""
    if sys.platform != "darwin":
        return False

    getxattr = getattr(os, "getxattr", None)
    attributes = (
        "com.apple.file-provider-domain-id",
        "com.apple.icloud.desktop",
        "com.apple.fileprovider.detached#B",
    )
    if getxattr is None:
        xattr_command = shutil.which("xattr")
        if xattr_command is None:
            return False
    else:
        xattr_command = None

    # Provider metadata is usually attached to the provider root, rather than
    # every child folder. Checking only path.parent misses normal-looking
    # folders nested in iCloud Drive, Desktop, Dropbox, and OneDrive.
    for folder in (path.parent, *path.parent.parents):
        folder_name = os.fspath(folder)
        for attribute in attributes:
            if getxattr is not None:
                try:
                    getxattr(folder_name, attribute)
                except OSError:
                    continue
                return True

            if xattr_command is None:
                return False
            try:
                result = subprocess.run(
                    [xattr_command, "-p", attribute, folder_name],
                    capture_output=True,
                    check=False,
                )
            except OSError:
                return False
            if result.returncode == 0:
                return True
    return False


@contextlib.contextmanager
def temporary_output_path(path: Path) -> Iterator[Path]:
    """Yield a temporary path and finalize it safely for the destination filesystem.

    macOS output is always staged outside the destination and copied into its
    final name. Finder can miss a hidden temporary file being renamed into a
    watched folder, including ordinary folders whose provider metadata is not
    exposed to applications. Other platforms retain the atomic same-folder
    replacement behavior unless the output is a detected Apple File Provider
    path.
    """
    resolved = resolve_user_path(path)
    provider_output = is_file_provider_path(resolved)
    copy_finalize = sys.platform == "darwin" or provider_output
    temporary_parent = Path(tempfile.gettempdir()).resolve() if copy_finalize else resolved.parent
    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=temporary_parent,
            prefix=f".{resolved.stem}-",
            suffix=resolved.suffix,
        )
        os.close(file_descriptor)
    except OSError as exc:
        raise ScriptError(f"Could not prepare temporary output for '{resolved}': {exc}") from exc

    temporary_path = Path(temporary_name)
    try:
        temporary_path.unlink()
        yield temporary_path
        try:
            if copy_finalize:
                copy_temporary_output(temporary_path, resolved)
            else:
                temporary_path.replace(resolved)
        except OSError as exc:
            raise ScriptError(f"Could not finalize output file '{resolved}': {exc}") from exc
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary_path.unlink()


def close_resource(resource: object) -> None:
    """Close a resource or its file-like stream without masking the main result."""
    close = getattr(resource, "close", None)
    if callable(close):
        with contextlib.suppress(Exception):
            close()
        return

    stream = getattr(resource, "stream", None)
    stream_close = getattr(stream, "close", None)
    if callable(stream_close):
        with contextlib.suppress(Exception):
            stream_close()


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
