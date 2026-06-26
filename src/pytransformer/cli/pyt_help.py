#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""
Script: pyt_help.py
Purpose: List installed PyTransformer console commands.
When to use: Use when you want to discover available PyTransformer terminal commands.
Changes: Read-only; prints command names and descriptions to standard output.
Inputs: Optional --names-only and --with-modules flags.
Environment variables: None.
Dependencies: Python standard library only.
Safety notes: Does not inspect user files or modify the filesystem.
Example: pyt-help
Expected result: A list of available pyt-* commands.
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


def print_commands(commands: Sequence[CommandInfo], *, names_only: bool, with_modules: bool) -> None:
    if names_only:
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
        if with_modules:
            detail = f"{detail} ({command.module_name}.py)" if detail else f"{command.module_name}.py"
        print(f"  {command.command.ljust(command_width)}  {detail}")


def build_parser() -> argparse.ArgumentParser:
    parser = build_command_parser(
        description="List available PyTransformer console commands.",
        examples=(
            "pyt-help",
            "pyt-help --names-only",
            "pyt-help --with-modules",
        ),
    )
    parser.add_argument(
        "--names-only",
        action="store_true",
        help="Print only command names, one per line.",
    )
    parser.add_argument(
        "--with-modules",
        action="store_true",
        help="Include the Python module filename for each command.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    print_commands(discover_commands(), names_only=args.names_only, with_modules=args.with_modules)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
