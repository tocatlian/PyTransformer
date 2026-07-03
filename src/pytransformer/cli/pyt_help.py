#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_help.py
Purpose: List installed PyTransformer console commands.
When to use: Use when you want to discover available PyTransformer terminal commands.
Changes: Read-only; prints command names and descriptions to standard output.
Inputs: Optional --terse and --verbose display mode flags.
Environment variables: None.
Dependencies: Python standard library only.
Safety notes: Does not inspect user files or modify the filesystem.
Example: pyt-help --verbose
Expected result: A list of available pyt-* commands with module filenames.
Related scripts: All pytransformer.cli command modules.
"""

from __future__ import annotations

import argparse
import importlib
import pkgutil
from dataclasses import dataclass
from typing import Sequence

from pytransformer.core.common import build_command_parser

COMMAND_MODULE_PREFIX = "pyt_"


@dataclass(frozen=True)
class CommandInfo:
    command: str
    module_name: str
    description: str


def module_name_to_command(module_name: str) -> str:
    return module_name.replace("_", "-")


def iter_command_module_names() -> list[str]:
    cli_package = importlib.import_module("pytransformer.cli")
    package_paths = getattr(cli_package, "__path__", [])
    return sorted(
        module_info.name
        for module_info in pkgutil.iter_modules(package_paths)
        if module_info.name.startswith(COMMAND_MODULE_PREFIX)
    )


def load_command_description(module_name: str) -> str:
    module = importlib.import_module(f"pytransformer.cli.{module_name}")
    parser_builder = getattr(module, "build_parser", None)
    if not callable(parser_builder):
        return ""

    parser = parser_builder()
    if not isinstance(parser, argparse.ArgumentParser):
        return ""
    return parser.description or ""


def discover_commands() -> list[CommandInfo]:
    commands = [
        CommandInfo(
            command=module_name_to_command(module_name),
            module_name=module_name,
            description=load_command_description(module_name),
        )
        for module_name in iter_command_module_names()
    ]
    return sorted(commands, key=lambda command_info: command_info.command)


def print_commands(commands: Sequence[CommandInfo], *, terse: bool, verbose: bool) -> None:
    if terse:
        for command in commands:
            print(command.command)
        return

    if not commands:
        print("No PyTransformer commands found.")
        return

    print("PyTransformer commands:")
    command_width = max(len(command.command) for command in commands)
    for command in commands:
        detail = command.description
        if verbose:
            detail = f"{detail} ({command.module_name}.py)" if detail else f"{command.module_name}.py"
        print(f"  {command.command.ljust(command_width)}  {detail}")


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="List available PyTransformer console commands.",
        examples=(
            "pyt-help",
            "pyt-help --terse",
            "pyt-help --verbose",
        ),
    )
    display_group = parser.add_mutually_exclusive_group()
    display_group.add_argument(
        "--terse",
        "--names-only",
        dest="terse",
        action="store_true",
        help="Print only command names, one per line. --names-only is a backward-compatible alias.",
    )
    display_group.add_argument(
        "--verbose",
        "--with-modules",
        dest="verbose",
        action="store_true",
        help="Include the Python module filename for each command. --with-modules is a backward-compatible alias.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    print_commands(discover_commands(), terse=args.terse, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
