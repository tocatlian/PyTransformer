# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, NoReturn
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CLI_DIR = SRC / "pytransformer" / "cli"

sys.path.insert(0, str(SRC))

from pytransformer.core import common, jpeg_metadata

COMMAND_MODULES = sorted(path.stem for path in CLI_DIR.glob("*.py") if path.name != "__init__.py")
CONSOLE_COMMANDS = [module_name.replace("_", "-") for module_name in COMMAND_MODULES]
PUBLIC_REPOSITORY_FILES = [
    ".editorconfig",
    ".gitattributes",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/dependabot.yml",
    ".github/pull_request_template.md",
    ".github/workflows/ci.yml",
    ".github/workflows/pages.yml",
    ".gitignore",
    ".pre-commit-config.yaml",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "Makefile",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
    "docs/architecture.md",
    "docs/commands.md",
    "docs/html/architecture.html",
    "docs/html/commands.html",
    "docs/html/index.html",
    "docs/html/lessons-learned.html",
    "docs/html/privacy.html",
    "docs/html/contributing.html",
    "docs/html/security.html",
    "docs/html/support.html",
    "docs/html/code-of-conduct.html",
    "docs/html/changelog.html",
    "docs/html/styles.css",
    "docs/privacy.md",
    "docs/lessons-learned.md",
    "pyproject.toml",
    "scripts/build_docs.py",
    "scripts/check_docs_links.py",
    "tox.ini",
]


def load_cli_module(module_name: str) -> Any:
    return importlib.import_module(f"pytransformer.cli.{module_name}")


class ProjectQualityTests(unittest.TestCase):
    def test_python_files_have_spdx_license_headers(self) -> None:
        for path in sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "tests").rglob("*.py")):
            with self.subTest(path=path.relative_to(ROOT)):
                lines = path.read_text(encoding="utf-8").splitlines()
                header = "\n".join(lines[:5])
                self.assertIn("SPDX-License-Identifier: MIT", header)
                self.assertIn("Copyright (c) 2023-2026 Paul Tocatlian", header)

    def test_command_modules_are_importable_python_modules(self) -> None:
        self.assertTrue(COMMAND_MODULES, "No command modules were discovered.")
        allowed_domains = {"files", "help", "image", "jpeg", "m4a", "mp4", "pdf", "text"}
        retired_module_names = {
            "files_append_folder_name",
            "jpeg_metadata_show",
            "jpeg_metadata_strip",
            "jpeg_variant_count",
            "jpeg_show_metadata",
            "jpeg_strip_metadata",
            "jpeg_count_variants",
            "jpeg_sliced_collage",
            "img_split_image",
            "image_split_image",
            "mp4_chunk",
            "mp4_dir_to_txt",
            "mp4_file_to_txt",
            "mp4_split_chunks",
            "mp4_transcribe",
            "mp4_transcribe_batch",
            "pdf_dir_to_txt",
            "pdf_file_to_txt",
            "pdf_to_jpg",
            "pdf_to_txt",
            "pdf_extract_text",
            "pdf_extract_selectable_text",
            "pdf_extract_selectable_text_batch",
            "pdf_render_jpeg",
            "txt_concat",
            "text_concatenate",
        }
        for module_name in COMMAND_MODULES:
            with self.subTest(module=module_name):
                self.assertEqual(module_name, module_name.lower())
                self.assertNotIn("-", module_name)
                self.assertTrue(module_name.startswith("pyt_"))
                self.assertNotIn(module_name, retired_module_names)
                self.assertIn(module_name.split("_", maxsplit=2)[1], allowed_domains)
                self.assertTrue(
                    module_name.isidentifier(),
                    f"{module_name}.py is not importable as a Python module name.",
                )
                load_cli_module(module_name)

    def test_all_command_modules_have_standard_header_fields(self) -> None:
        required_fields = [
            "Script:",
            "Purpose:",
            "When to use:",
            "Changes:",
            "Inputs:",
            "Environment variables:",
            "Dependencies:",
            "Safety notes:",
            "Example:",
            "Expected result:",
            "Related scripts:",
        ]

        for module_name in COMMAND_MODULES:
            path = CLI_DIR / f"{module_name}.py"
            with self.subTest(module=module_name):
                content = path.read_text(encoding="utf-8")
                self.assertTrue(content.startswith("#!/usr/bin/env python3\n"))
                for field in required_fields:
                    self.assertIn(field, content)

    def test_all_command_modules_are_executable_scripts(self) -> None:
        for module_name in COMMAND_MODULES:
            path = CLI_DIR / f"{module_name}.py"
            with self.subTest(module=module_name):
                self.assertTrue(
                    path.stat().st_mode & stat.S_IXUSR,
                    f"{path.relative_to(ROOT)} should be executable by the file owner.",
                )

    def test_all_command_modules_expose_help(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC)

        for module_name in COMMAND_MODULES:
            with self.subTest(module=module_name):
                result = subprocess.run(
                    [sys.executable, "-m", f"pytransformer.cli.{module_name}", "--help"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                    env=env,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())

    def test_all_command_modules_expose_build_parser(self) -> None:
        for module_name, console_command in zip(COMMAND_MODULES, CONSOLE_COMMANDS, strict=True):
            module = load_cli_module(module_name)
            with self.subTest(module=module_name):
                self.assertTrue(hasattr(module, "build_parser"), f"{module_name} should expose build_parser().")
                parser = module.build_parser()
                help_text = parser.format_help()
                self.assertIsInstance(parser, argparse.ArgumentParser)
                self.assertIn("usage:", help_text.lower())
                self.assertIn("Examples:", help_text)
                self.assertIn(console_command, help_text)

    def test_batch_folder_commands_offer_include_hidden(self) -> None:
        for module_name in [
            "pyt_files_append_folder_name",
            "pyt_jpeg_strip_metadata",
            "pyt_image_variants_count",
            "pyt_mp4_transcribe_batch",
            "pyt_pdf_extract_selectable_text_batch",
            "pyt_text_concatenate",
        ]:
            module = load_cli_module(module_name)
            with self.subTest(module=module_name):
                help_text = module.build_parser().format_help()
                self.assertIn("--include-hidden", help_text)

    def test_commands_use_visible_quiet_option_name(self) -> None:
        for module_name in COMMAND_MODULES:
            module = load_cli_module(module_name)
            with self.subTest(module=module_name):
                help_text = module.build_parser().format_help()
                self.assertNotIn("--silent", help_text)

    def test_readme_points_to_authoritative_command_guide(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("[command guide](docs/commands.md)", readme)
        self.assertIn("[M4A audio commands](docs/commands.md#audio-commands)", readme)

    def test_readme_includes_standard_library_quick_start(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("## Quick Start", readme)
        self.assertIn("pyt-help --verbose", readme)
        self.assertIn("pyt-text-concatenate", readme)

    def test_command_docs_mention_every_console_command(self) -> None:
        command_docs = (ROOT / "docs" / "commands.md").read_text(encoding="utf-8")
        for console_command in CONSOLE_COMMANDS:
            with self.subTest(command=console_command):
                self.assertIn(console_command, command_docs)

    def test_documentation_links_are_valid(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_docs_links.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_html_docs_include_every_console_command_page(self) -> None:
        html_docs = ROOT / "docs" / "html"
        self.assertTrue((html_docs / "commands.html").is_file())
        for console_command in CONSOLE_COMMANDS:
            with self.subTest(command=console_command):
                page_path = html_docs / "commands" / f"{console_command}.html"
                self.assertTrue(page_path.is_file())
                self.assertIn(console_command, page_path.read_text(encoding="utf-8"))

    def test_pyproject_exposes_every_command_module_as_console_script(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        for module_name, console_command in zip(COMMAND_MODULES, CONSOLE_COMMANDS, strict=True):
            entry_point = f'{console_command} = "pytransformer.cli.{module_name}:main"'
            with self.subTest(module=module_name):
                self.assertIn(entry_point, pyproject)

    def test_public_repository_files_are_present(self) -> None:
        for relative_path in PUBLIC_REPOSITORY_FILES:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).exists())

    def test_package_metadata_has_public_release_hygiene(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        expected_fragments = [
            'license = "MIT"',
            'license-files = ["LICENSE"]',
            "Typing :: Typed",
            "[tool.setuptools.package-data]",
            'pytransformer = ["py.typed"]',
            "coverage>=7.6",
            "mypy>=1.13",
            "pre-commit>=4.0",
            "twine>=5.1",
            "tox>=4.19",
            "[tool.coverage.run]",
            "fail_under = 80",
            "[tool.mypy]",
        ]
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, pyproject)
        self.assertTrue((SRC / "pytransformer" / "py.typed").exists())
        self.assertNotIn("Development Status :: 3 - Alpha", pyproject)

    def test_makefile_includes_public_validation_targets(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        for target in [
            "format-check",
            "type-check",
            "coverage",
            "hook-config-check",
            "hooks",
            "entrypoint-check",
            "docs",
            "docs-check",
            "docs-watch",
            "build-check",
            "tox",
            "smoke-optional",
            "smoke-pdf",
            "smoke-jpeg",
            "smoke-m4a",
            "validate-all",
        ]:
            with self.subTest(target=target):
                self.assertIn(f"{target}:", makefile)
        for console_command in CONSOLE_COMMANDS:
            with self.subTest(command=console_command):
                self.assertIn(console_command, makefile)

    def test_public_text_files_do_not_reference_local_paths(self) -> None:
        public_files = PUBLIC_REPOSITORY_FILES
        forbidden_fragments = [
            "/" + "Users/",
            "/" + "var/folders/",
            "\\" + "Users\\",
        ]

        for relative_path in public_files:
            path = ROOT / relative_path
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                with self.subTest(path=relative_path, fragment=fragment):
                    self.assertNotIn(fragment, content)

    def test_current_public_docs_use_current_command_prefix(self) -> None:
        public_files = [
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            ".github/ISSUE_TEMPLATE/feature_request.yml",
            ".github/pull_request_template.md",
            "CONTRIBUTING.md",
            "README.md",
            "SECURITY.md",
            "SUPPORT.md",
            "docs/architecture.md",
            "docs/commands.md",
            "docs/privacy.md",
        ]
        forbidden_fragments = [
            "pre-1.0",
            "pytransformer-*",
            "pytransformer-pdf-to-txt",
        ]

        for relative_path in public_files:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                with self.subTest(path=relative_path, fragment=fragment):
                    self.assertNotIn(fragment, content)


class CommonHelperTests(unittest.TestCase):
    def test_require_existing_file_and_folder_return_resolved_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            file_path = folder / "sample.txt"
            file_path.write_text("hello", encoding="utf-8")

            self.assertEqual(common.require_existing_folder(folder), folder.resolve())
            self.assertEqual(common.require_existing_file(file_path, suffixes={".txt"}), file_path.resolve())

    def test_ensure_output_path_rejects_existing_output_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.txt"
            output_path.write_text("existing", encoding="utf-8")

            with self.assertRaises(common.ScriptError):
                common.ensure_output_path(output_path)

    def test_ensure_output_path_rejects_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.txt"
            input_path.write_text("existing", encoding="utf-8")

            with self.assertRaises(common.ScriptError):
                common.ensure_output_path(input_path, overwrite=True, input_paths=[input_path])

    def test_ensure_output_path_rejects_directory_even_with_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_folder = Path(tmp) / "output"
            output_folder.mkdir()

            with self.assertRaises(common.ScriptError):
                common.ensure_output_path(output_folder, overwrite=True)

    def test_file_provider_path_detects_icloud_metadata(self) -> None:
        def fake_getxattr(_path: str, attribute: str) -> bytes:
            if attribute == "com.apple.icloud.desktop":
                return b"1"
            raise OSError("attribute not found")

        with (
            patch.object(common.sys, "platform", "darwin"),
            patch.object(common.os, "getxattr", create=True, side_effect=fake_getxattr),
        ):
            self.assertTrue(common.is_file_provider_path(Path("/Users/example/Desktop/recording.mp3")))

    def test_file_provider_path_returns_false_without_provider_metadata(self) -> None:
        with (
            patch.object(common.sys, "platform", "darwin"),
            patch.object(common.os, "getxattr", create=True, side_effect=OSError("attribute not found")),
        ):
            self.assertFalse(common.is_file_provider_path(Path("/tmp/recording.mp3")))

    def test_file_provider_path_uses_macos_xattr_command_when_needed(self) -> None:
        result = subprocess.CompletedProcess([], 0, stdout=b"1", stderr=b"")
        with (
            patch.object(common.sys, "platform", "darwin"),
            patch.object(common.os, "getxattr", None, create=True),
            patch.object(common.shutil, "which", return_value="/usr/bin/xattr"),
            patch.object(common.subprocess, "run", return_value=result) as run_mock,
        ):
            self.assertTrue(common.is_file_provider_path(Path("/Users/example/Desktop/recording.mp3")))

        self.assertEqual(run_mock.call_args.args[0][:3], ["/usr/bin/xattr", "-p", "com.apple.file-provider-domain-id"])

    def test_temporary_output_path_commits_and_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.txt"
            with common.temporary_output_path(output_path) as temporary_path:
                temporary_path.write_text("complete", encoding="utf-8")

            self.assertEqual(output_path.read_text(encoding="utf-8"), "complete")
            self.assertEqual(list(output_path.parent.glob(".output-*.txt")), [])

    def test_temporary_output_path_preserves_existing_output_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.txt"
            output_path.write_text("original", encoding="utf-8")

            with self.assertRaises(RuntimeError):
                with common.temporary_output_path(output_path) as temporary_path:
                    temporary_path.write_text("partial", encoding="utf-8")
                    raise RuntimeError("write failed")

            self.assertEqual(output_path.read_text(encoding="utf-8"), "original")

    def test_temporary_output_path_uses_external_staging_for_file_provider_output(self) -> None:
        with tempfile.TemporaryDirectory() as output_tmp, tempfile.TemporaryDirectory() as staging_tmp:
            output_path = Path(output_tmp) / "output.txt"
            staging_path = Path(staging_tmp)
            with (
                patch.object(common, "is_file_provider_path", return_value=True),
                patch.object(common.tempfile, "gettempdir", return_value=staging_tmp),
            ):
                with common.temporary_output_path(output_path) as temporary_path:
                    self.assertEqual(temporary_path.parent, staging_path.resolve())
                    temporary_path.write_text("complete", encoding="utf-8")

            self.assertEqual(output_path.read_text(encoding="utf-8"), "complete")
            self.assertEqual(list(staging_path.iterdir()), [])

    def test_temporary_output_path_uses_destination_folder_for_normal_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.txt"
            with patch.object(common, "is_file_provider_path", return_value=False):
                with common.temporary_output_path(output_path) as temporary_path:
                    self.assertEqual(temporary_path.parent, output_path.parent.resolve())
                    temporary_path.write_text("complete", encoding="utf-8")

            self.assertEqual(output_path.read_text(encoding="utf-8"), "complete")

    def test_copy_temporary_output_replaces_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            temporary_path = folder / "temporary.txt"
            output_path = folder / "output.txt"
            temporary_path.write_text("new", encoding="utf-8")
            output_path.write_text("original", encoding="utf-8")

            common.copy_temporary_output(temporary_path, output_path)

            self.assertEqual(output_path.read_text(encoding="utf-8"), "new")
            self.assertEqual(temporary_path.read_text(encoding="utf-8"), "new")

    def test_path_and_value_validation_failures_are_user_facing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            file_path = folder / "sample.dat"
            file_path.write_text("hello", encoding="utf-8")

            with self.assertRaises(common.ScriptError):
                common.require_existing_file(folder)
            with self.assertRaises(common.ScriptError):
                common.require_existing_file(file_path, suffixes={".txt"})
            with self.assertRaises(common.ScriptError):
                common.require_existing_folder(file_path)
            with self.assertRaises(common.ScriptError):
                common.require_positive_int(0, label="Count")
            with self.assertRaises(common.ScriptError):
                common.require_int_range(11, label="Quality", minimum=1, maximum=10)

    def test_sorted_directory_items_and_confirmation_guards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "b.txt").touch()
            (folder / "A.txt").touch()

            self.assertEqual([path.name for path in common.sorted_directory_items(folder)], ["A.txt", "b.txt"])
            common.confirm_action("Already confirmed.", yes=True)
            with self.assertRaises(common.ScriptError):
                common.confirm_action("Dangerous action.")

    def test_jpeg_metadata_pure_formatting_helpers(self) -> None:
        flattened = jpeg_metadata.flatten_dict(
            "root",
            {
                "empty_dict": {},
                "empty_list": [],
                "items": [b"abc", "value"],
            },
        )
        self.assertEqual(flattened["root.empty_dict"], "{}")
        self.assertEqual(flattened["root.empty_list"], "[]")
        self.assertEqual(flattened["root.items[0]"], "<bytes length=3>")
        self.assertEqual(flattened["root.items[1]"], "'value'")

        long_value = "x" * (jpeg_metadata.MAX_DISPLAY_VALUE_LENGTH + 3)
        self.assertIn("<truncated 3 chars>", jpeg_metadata.format_display_value(long_value, full_values=False))
        self.assertEqual(jpeg_metadata.format_display_value(long_value, full_values=True), long_value)


class StandardLibraryScriptTests(unittest.TestCase):
    def test_pyt_help_lists_discovered_commands(self) -> None:
        script = load_cli_module("pyt_help")

        commands = script.discover_commands()
        command_names = [command.command for command in commands]

        self.assertIn("pyt-help", command_names)
        self.assertIn("pyt-pdf-extract-text", command_names)
        self.assertEqual(command_names, sorted(command_names))

        help_text = script.build_parser().format_help()
        self.assertIn("--terse", help_text)
        self.assertIn("--verbose", help_text)
        self.assertIn("--names-only", help_text)
        self.assertIn("--with-modules", help_text)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            script.print_commands(commands, terse=True, verbose=False)
        self.assertIn("pyt-help\n", output.getvalue())

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            script.print_commands(commands, terse=False, verbose=True)
        self.assertIn("pyt_help.py", output.getvalue())

    def test_text_concat_skips_output_file_and_uses_deterministic_order(self) -> None:
        script = load_cli_module("pyt_text_concatenate")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "b.txt").write_text("bravo\n", encoding="utf-8")
            (folder / "a.txt").write_text("alpha\n", encoding="utf-8")
            output_path = folder / "combined.txt"

            text_files = script.find_text_files(folder, output_path.resolve(), include_hidden=False)
            self.assertEqual([path.name for path in text_files], ["a.txt", "b.txt"])

            script.concatenate_text_files(text_files, output_path, separator="\n")
            self.assertEqual(output_path.read_text(encoding="utf-8"), "alpha\n\nbravo\n")

    def test_text_concat_rejects_empty_and_invalid_utf8_inputs(self) -> None:
        script = load_cli_module("pyt_text_concatenate")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            output_path = folder / "combined.txt"

            with self.assertRaises(common.ScriptError):
                script.concatenate_text_files([], output_path, separator="\n")

            invalid_path = folder / "invalid.txt"
            invalid_path.write_bytes(b"\xff")
            output_path.write_text("original", encoding="utf-8")
            with self.assertRaises(common.ScriptError):
                script.concatenate_text_files([invalid_path], output_path, separator="\n")
            self.assertEqual(output_path.read_text(encoding="utf-8"), "original")

    def test_rename_plan_skips_hidden_files_and_existing_targets(self) -> None:
        script = load_cli_module("pyt_files_append_folder_name")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Tokyo"
            folder.mkdir()
            (folder / "one.jpg").write_text("one", encoding="utf-8")
            (folder / ".hidden.jpg").write_text("hidden", encoding="utf-8")
            (folder / "existing.txt").write_text("existing", encoding="utf-8")
            (folder / "existing-Tokyo.txt").write_text("target", encoding="utf-8")

            plans, skipped = script.build_rename_plan(folder, include_hidden=False)
            self.assertEqual([plan.source.name for plan in plans], ["one.jpg"])
            self.assertEqual(skipped, 3)

            summary = script.apply_rename_plan(plans, dry_run=False)
            self.assertEqual(summary.renamed, 1)
            self.assertTrue((folder / "one-Tokyo.jpg").exists())

    def test_rename_plan_does_not_replace_target_created_after_planning(self) -> None:
        script = load_cli_module("pyt_files_append_folder_name")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Tokyo"
            folder.mkdir()
            source = folder / "one.jpg"
            target = folder / "one-Tokyo.jpg"
            source.write_text("source", encoding="utf-8")
            plan = script.RenamePlan(source=source, target=target)
            target.write_text("target", encoding="utf-8")

            summary = script.apply_rename_plan([plan], dry_run=False)

            self.assertEqual(summary.renamed, 0)
            self.assertEqual(summary.skipped, 1)
            self.assertEqual(source.read_text(encoding="utf-8"), "source")
            self.assertEqual(target.read_text(encoding="utf-8"), "target")

    def test_rename_plan_dry_run_leaves_files_unchanged(self) -> None:
        script = load_cli_module("pyt_files_append_folder_name")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Paris"
            folder.mkdir()
            source = folder / "one.jpg"
            source.write_text("one", encoding="utf-8")

            plans, skipped = script.build_rename_plan(folder, include_hidden=False)
            summary = script.apply_rename_plan(plans, dry_run=True)
            self.assertEqual(skipped, 0)
            self.assertEqual(summary.planned, 1)
            self.assertEqual(summary.renamed, 0)
            self.assertTrue(source.exists())
            self.assertFalse((folder / "one-Paris.jpg").exists())

    def test_pyt_image_variants_count_groups_case_insensitive_extensions(self) -> None:
        script = load_cli_module("pyt_image_variants_count")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "photo-warm.jpg").touch()
            (folder / "photo-cool.PNG").touch()
            (folder / "photo-neutral.webp").touch()
            (folder / "photo.jpg").touch()
            (folder / ".hidden-warm.jpg").touch()

            results = script.analyze_folder(folder)
            self.assertEqual(results.total_matching_jpg_files_processed, 3)
            self.assertEqual(results.total_files_skipped, 2)
            self.assertEqual(results.presets_by_base_name["photo"], {"warm", "cool", "neutral"})

    def test_pyt_image_variants_count_tracks_duplicates_and_prints_summary(self) -> None:
        script = load_cli_module("pyt_image_variants_count")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "photo-warm.jpg").touch()
            (folder / "photo-WARM.jpeg").touch()

            results = script.analyze_folder(folder)
            self.assertEqual(results.total_duplicate_preset_entries, 1)
            self.assertEqual([name.casefold() for name in results.duplicates_by_base_name["photo"]], ["warm"])

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                script.print_results(results, list_presets=True)
            self.assertIn("Duplicate preset entries", output.getvalue())

    def test_jpeg_metadata_helpers_format_and_resolve_without_pillow(self) -> None:
        show_script = load_cli_module("pyt_jpeg_show_metadata")
        strip_script = load_cli_module("pyt_jpeg_strip_metadata")

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            show_script.print_metadata({}, full_values=False)
        self.assertIn("No embedded metadata found.", output.getvalue())

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "images"
            folder.mkdir()
            (folder / "a.jpg").touch()
            (folder / ".hidden.jpg").touch()
            (folder / "b.png").touch()

            self.assertEqual(
                [path.name for path in strip_script.iter_jpeg_files(folder, include_hidden=False)], ["a.jpg"]
            )
            with self.assertRaises(ValueError):
                strip_script.resolve_output_folder(folder.resolve(), folder)

    def test_batch_mp4_distinguishes_existing_outputs_from_failures(self) -> None:
        script = load_cli_module("pyt_mp4_transcribe_batch")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            mp4_path = folder / "video.mp4"
            mp4_path.touch()
            (folder / "video.txt").write_text("existing", encoding="utf-8")

            summary = script.process_folder(
                folder,
                output_folder=None,
                overwrite=False,
                include_hidden=False,
                language="en-US",
            )
            self.assertEqual(summary.skipped, 1)
            self.assertEqual(summary.failed, 0)

            (folder / "video.txt").unlink()

            def fail_transcription(_path: Path, *, language: str) -> str:
                raise common.ScriptError("transcription failed")

            with patch.object(script, "transcribe_mp4_to_text", side_effect=fail_transcription):
                summary = script.process_folder(
                    folder,
                    output_folder=None,
                    overwrite=False,
                    include_hidden=False,
                    language="en-US",
                )
            self.assertEqual(summary.skipped, 0)
            self.assertEqual(summary.failed, 1)

    def test_mp4_file_validation_guards_existing_outputs(self) -> None:
        script = load_cli_module("pyt_mp4_transcribe")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            mp4_path = folder / "video.mp4"
            mp4_path.touch()
            output_path = folder / "video.txt"
            output_path.write_text("existing", encoding="utf-8")

            args = argparse.Namespace(mp4_file=mp4_path, output=None, overwrite=False)
            with self.assertRaises(common.ScriptError):
                script.validate_args(args)

            args.overwrite = True
            resolved_mp4_path, resolved_output_path = script.validate_args(args)
            self.assertEqual(resolved_mp4_path, mp4_path.resolve())
            self.assertEqual(resolved_output_path, output_path.resolve())

    def test_batch_pdf_distinguishes_existing_outputs_from_failures(self) -> None:
        script = load_cli_module("pyt_pdf_extract_selectable_text_batch")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            pdf_path = folder / "doc.pdf"
            pdf_path.touch()
            (folder / "doc.txt").write_text("existing", encoding="utf-8")

            summary = script.process_folder(
                folder,
                output_folder=None,
                overwrite=False,
                include_hidden=False,
                password="",
            )
            self.assertEqual(summary.skipped, 1)
            self.assertEqual(summary.failed, 0)

            (folder / "doc.txt").unlink()

            def fail_open_pdf(_path: Path, _password: str) -> NoReturn:
                raise common.ScriptError("pdf failed")

            with patch.object(script, "open_pdf_reader", side_effect=fail_open_pdf):
                summary = script.process_folder(
                    folder,
                    output_folder=None,
                    overwrite=False,
                    include_hidden=False,
                    password="",
                )
            self.assertEqual(summary.skipped, 0)
            self.assertEqual(summary.failed, 1)

    def test_batch_pdf_closes_reader_after_processing(self) -> None:
        script = load_cli_module("pyt_pdf_extract_selectable_text_batch")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            pdf_path = folder / "doc.pdf"
            pdf_path.touch()
            reader = type("Reader", (), {"close": lambda self: setattr(self, "closed", True)})()
            reader.closed = False

            with (
                patch.object(script, "open_pdf_reader", return_value=reader),
                patch.object(script, "extract_text", return_value=("text", 0)),
            ):
                summary = script.process_folder(
                    folder,
                    output_folder=None,
                    overwrite=False,
                    include_hidden=False,
                    password="",
                )

            self.assertEqual(summary.written, 1)
            self.assertTrue(reader.closed)

    def test_mp4_split_rejects_non_finite_duration_and_closes_clip(self) -> None:
        script = load_cli_module("pyt_mp4_split_chunks")

        class FakeClip:
            duration = float("nan")

            def __init__(self) -> None:
                self.closed = False

            def close(self) -> None:
                self.closed = True

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            video_path = folder / "video.mp4"
            video_path.touch()
            clip = FakeClip()
            with patch.object(script, "VideoFileClip", return_value=clip):
                with self.assertRaises(common.ScriptError):
                    script.split_video(video_path, folder / "chunks", chunk_seconds=30, overwrite=False)

            self.assertTrue(clip.closed)

    def test_pdf_file_validation_guards_existing_outputs(self) -> None:
        script = load_cli_module("pyt_pdf_extract_selectable_text")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            pdf_path = folder / "doc.pdf"
            pdf_path.touch()
            output_path = folder / "doc.txt"
            output_path.write_text("existing", encoding="utf-8")

            args = argparse.Namespace(pdf_file=pdf_path, output=None, overwrite=False)
            with self.assertRaises(common.ScriptError):
                script.validate_args(args)

            args.overwrite = True
            resolved_pdf_path, resolved_output_path = script.validate_args(args)
            self.assertEqual(resolved_pdf_path, pdf_path.resolve())
            self.assertEqual(resolved_output_path, output_path.resolve())


if __name__ == "__main__":
    unittest.main()
