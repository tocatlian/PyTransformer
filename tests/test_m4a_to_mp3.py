# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pytransformer.cli import pyt_m4a_to_mp3
from pytransformer.core.common import ScriptError


class M4aToMp3UnitTests(unittest.TestCase):
    def test_build_parser_accepts_one_or_more_inputs(self) -> None:
        args = pyt_m4a_to_mp3.build_parser().parse_args(["first.m4a", "second.M4A"])

        self.assertEqual(args.m4a_files, [Path("first.m4a"), Path("second.M4A")])
        self.assertEqual(args.quality, pyt_m4a_to_mp3.DEFAULT_QUALITY)
        self.assertIsNone(args.bitrate)

    def test_build_parser_accepts_quality_and_bitrate_options(self) -> None:
        quality_args = pyt_m4a_to_mp3.build_parser().parse_args(["--quality", "0", "recording.m4a"])
        bitrate_args = pyt_m4a_to_mp3.build_parser().parse_args(["--bitrate", "192", "recording.m4a"])

        self.assertEqual(quality_args.quality, 0)
        self.assertEqual(bitrate_args.bitrate, "192k")

    def test_build_parser_rejects_non_standard_bitrate(self) -> None:
        with self.assertRaises(SystemExit):
            pyt_m4a_to_mp3.build_parser().parse_args(["--bitrate", "200k", "recording.m4a"])

    def test_normalize_bitrate_rejects_malformed_value(self) -> None:
        with self.assertRaisesRegex(ScriptError, "optional 'k' suffix"):
            pyt_m4a_to_mp3.normalize_bitrate("192kbps")

    def test_build_output_path_replaces_source_suffix_with_mp3(self) -> None:
        self.assertEqual(
            pyt_m4a_to_mp3.build_output_path(Path("/tmp/recording.m4a")),
            Path("/tmp/recording.mp3"),
        )

    def test_validate_args_resolves_one_output_per_input(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            first = folder / "first.m4a"
            second = folder / "second.m4a"
            first.write_bytes(b"m4a")
            second.write_bytes(b"m4a")
            args = pyt_m4a_to_mp3.build_parser().parse_args([str(first), str(second)])

            paths = pyt_m4a_to_mp3.validate_args(args)

            self.assertEqual(
                paths,
                [
                    (first.resolve(), (folder / "first.mp3").resolve()),
                    (second.resolve(), (folder / "second.mp3").resolve()),
                ],
            )

    def test_validate_args_rejects_duplicate_inputs(self) -> None:
        with TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "recording.m4a"
            input_path.write_bytes(b"m4a")
            args = pyt_m4a_to_mp3.build_parser().parse_args([str(input_path), str(input_path)])

            with self.assertRaisesRegex(ScriptError, "only once"):
                pyt_m4a_to_mp3.validate_args(args)

    def test_validate_args_rejects_empty_input(self) -> None:
        with TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "empty.m4a"
            input_path.touch()
            args = pyt_m4a_to_mp3.build_parser().parse_args([str(input_path)])

            with self.assertRaisesRegex(ScriptError, "empty"):
                pyt_m4a_to_mp3.validate_args(args)

    def test_validate_args_reports_input_stat_failure(self) -> None:
        input_path = Path("recording.m4a")
        args = pyt_m4a_to_mp3.build_parser().parse_args([str(input_path)])

        with (
            patch.object(pyt_m4a_to_mp3, "require_existing_file", return_value=input_path),
            patch.object(Path, "stat", side_effect=OSError("stat unavailable")),
        ):
            with self.assertRaisesRegex(ScriptError, "Could not inspect M4A file"):
                pyt_m4a_to_mp3.validate_args(args)

    def test_validate_args_rejects_existing_output_without_overwrite(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            input_path = folder / "recording.m4a"
            output_path = folder / "recording.mp3"
            input_path.write_bytes(b"m4a")
            output_path.write_bytes(b"existing")

            args = pyt_m4a_to_mp3.build_parser().parse_args([str(input_path)])
            with self.assertRaises(ScriptError):
                pyt_m4a_to_mp3.validate_args(args)

    def test_require_ffmpeg_reports_missing_executable(self) -> None:
        with patch.object(pyt_m4a_to_mp3.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ScriptError, "FFmpeg is required"):
                pyt_m4a_to_mp3.require_ffmpeg()

    def test_build_ffmpeg_command_uses_quality_and_cover_art_mapping(self) -> None:
        command = pyt_m4a_to_mp3.build_ffmpeg_command(
            "/usr/local/bin/ffmpeg",
            Path("recording.m4a"),
            Path("recording.mp3"),
            quality=2,
            bitrate=None,
        )

        self.assertIn("-q:a", command)
        self.assertIn("2", command)
        self.assertIn("0:v:0?", command)
        self.assertIn("attached_pic", command)
        self.assertIn("-map_metadata", command)

    def test_build_ffmpeg_command_uses_constant_bitrate(self) -> None:
        command = pyt_m4a_to_mp3.build_ffmpeg_command(
            "ffmpeg",
            Path("recording.m4a"),
            Path("recording.mp3"),
            quality=2,
            bitrate="192k",
        )

        bitrate_index = command.index("-b:a")
        self.assertEqual(command[bitrate_index + 1], "192k")
        self.assertNotIn("-q:a", command)

    def test_convert_writes_sibling_mp3_and_uses_ffmpeg(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            input_path = folder / "recording.m4a"
            output_path = folder / "recording.mp3"
            input_path.write_bytes(b"m4a")

            def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                Path(command[-1]).write_bytes(b"mp3")
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with patch.object(pyt_m4a_to_mp3.subprocess, "run", side_effect=fake_run) as run_mock:
                pyt_m4a_to_mp3.convert_m4a_to_mp3(
                    input_path,
                    output_path,
                    quality=0,
                    ffmpeg_path="/usr/local/bin/ffmpeg",
                )

            self.assertEqual(output_path.read_bytes(), b"mp3")
            command = run_mock.call_args.args[0]
            self.assertEqual(command[0], "/usr/local/bin/ffmpeg")
            self.assertIn("-map", command)
            self.assertIn("0:a:0", command)
            self.assertIn("libmp3lame", command)

    def test_convert_failure_preserves_existing_output_and_cleans_temporary_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            input_path = folder / "recording.m4a"
            output_path = folder / "recording.mp3"
            input_path.write_bytes(b"m4a")
            output_path.write_bytes(b"original")

            failure = subprocess.CompletedProcess([], 1, stdout="", stderr="invalid audio")
            with patch.object(pyt_m4a_to_mp3.subprocess, "run", return_value=failure):
                with self.assertRaisesRegex(ScriptError, "invalid audio"):
                    pyt_m4a_to_mp3.convert_m4a_to_mp3(input_path, output_path, ffmpeg_path="ffmpeg")

            self.assertEqual(output_path.read_bytes(), b"original")
            self.assertEqual(list(folder.glob(".recording-*.mp3")), [])

    def test_convert_failure_uses_exit_status_when_ffmpeg_has_no_error_text(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            input_path = folder / "recording.m4a"
            output_path = folder / "recording.mp3"
            input_path.write_bytes(b"m4a")
            failure = subprocess.CompletedProcess([], 3, stdout="", stderr="")

            with patch.object(pyt_m4a_to_mp3.subprocess, "run", return_value=failure):
                with self.assertRaisesRegex(ScriptError, "status 3"):
                    pyt_m4a_to_mp3.convert_m4a_to_mp3(input_path, output_path, ffmpeg_path="ffmpeg")

    def test_convert_reports_output_stat_failure(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            input_path = folder / "recording.m4a"
            output_path = folder / "recording.mp3"
            input_path.write_bytes(b"m4a")

            def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                Path(command[-1]).write_bytes(b"mp3")
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with (
                patch.object(pyt_m4a_to_mp3.subprocess, "run", side_effect=fake_run),
                patch.object(Path, "stat", side_effect=OSError("stat unavailable")),
            ):
                with self.assertRaisesRegex(ScriptError, "did not create an MP3"):
                    pyt_m4a_to_mp3.convert_m4a_to_mp3(input_path, output_path, ffmpeg_path="ffmpeg")

    def test_convert_reports_ffmpeg_process_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            input_path = folder / "recording.m4a"
            output_path = folder / "recording.mp3"
            input_path.write_bytes(b"m4a")

            with patch.object(pyt_m4a_to_mp3.subprocess, "run", side_effect=OSError("process unavailable")):
                with self.assertRaisesRegex(ScriptError, "Could not run FFmpeg"):
                    pyt_m4a_to_mp3.convert_m4a_to_mp3(input_path, output_path, ffmpeg_path="ffmpeg")

    def test_convert_rejects_empty_success_output_and_preserves_existing_output(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            input_path = folder / "recording.m4a"
            output_path = folder / "recording.mp3"
            input_path.write_bytes(b"m4a")
            output_path.write_bytes(b"original")

            def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                Path(command[-1]).touch()
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with patch.object(pyt_m4a_to_mp3.subprocess, "run", side_effect=fake_run):
                with self.assertRaisesRegex(ScriptError, "empty MP3"):
                    pyt_m4a_to_mp3.convert_m4a_to_mp3(input_path, output_path, ffmpeg_path="ffmpeg")

            self.assertEqual(output_path.read_bytes(), b"original")

    def test_run_continues_after_one_conversion_failure(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            first = folder / "first.m4a"
            second = folder / "second.m4a"
            first.write_bytes(b"m4a")
            second.write_bytes(b"m4a")
            args = pyt_m4a_to_mp3.build_parser().parse_args([str(first), str(second)])

            def fake_convert(m4a_path: Path, _output_path: Path, **_kwargs: object) -> None:
                if m4a_path == second.resolve():
                    raise ScriptError("invalid audio")

            with (
                patch.object(pyt_m4a_to_mp3, "require_ffmpeg", return_value="ffmpeg"),
                patch.object(pyt_m4a_to_mp3, "convert_m4a_to_mp3", side_effect=fake_convert) as convert_mock,
            ):
                result = pyt_m4a_to_mp3.run(args)

            self.assertEqual(result, 1)
            self.assertEqual(convert_mock.call_count, 2)

    def test_main_converts_script_errors_to_exit_code(self) -> None:
        with patch.object(pyt_m4a_to_mp3, "fail", return_value=2) as fail_mock:
            result = pyt_m4a_to_mp3.main(["missing.m4a"])

        self.assertEqual(result, 2)
        fail_mock.assert_called_once()


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required for the integration test.")
class M4aToMp3IntegrationTests(unittest.TestCase):
    def test_run_converts_multiple_m4a_files_with_ffmpeg(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            input_paths = [folder / "first.m4a", folder / "second.m4a"]
            for index, input_path in enumerate(input_paths, start=1):
                subprocess.run(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        f"sine=frequency={900 + index * 100}:duration=0.1",
                        "-c:a",
                        "aac",
                        str(input_path),
                    ],
                    check=True,
                )

            args = pyt_m4a_to_mp3.build_parser().parse_args([str(path) for path in input_paths])

            self.assertEqual(pyt_m4a_to_mp3.run(args), 0)
            self.assertTrue((folder / "first.mp3").is_file())
            self.assertTrue((folder / "second.mp3").is_file())


if __name__ == "__main__":
    unittest.main()
