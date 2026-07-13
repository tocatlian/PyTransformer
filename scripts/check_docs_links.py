#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""Check local Markdown and generated HTML documentation links."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
DOCS_DIR = ROOT / "docs"
HTML_DIR = DOCS_DIR / "html"

sys.path.insert(0, str(SCRIPT_DIR))

from build_docs import slugify, strip_inline_markup  # noqa: E402


MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_TARGET_PATTERN = re.compile(r'\b(?:href|src)="([^"]+)"')
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*$")
ID_PATTERN = re.compile(r'\bid="([^"]+)"')


def markdown_sources() -> list[Path]:
    paths = [*sorted(ROOT.glob("*.md")), *sorted(DOCS_DIR.glob("*.md"))]
    return list(dict.fromkeys(path.resolve() for path in paths))


def is_external_target(target: str) -> bool:
    return target.startswith("//") or bool(urlsplit(target).scheme)


def parse_target(raw_target: str) -> tuple[str, str | None]:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    target = target.split(maxsplit=1)[0]
    path, separator, anchor = target.partition("#")
    return unquote(path), anchor if separator else None


def markdown_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            anchors.add(slugify(strip_inline_markup(match.group(1))))
    return anchors


def report_missing(
    errors: list[str],
    source: Path,
    line_number: int,
    target: str,
    detail: str,
) -> None:
    errors.append(f"{source.relative_to(ROOT)}:{line_number}: {target!r} {detail}")


def check_markdown_links(errors: list[str]) -> None:
    for source in markdown_sources():
        in_code_fence = False
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            if line.startswith("```"):
                in_code_fence = not in_code_fence
                continue
            if in_code_fence:
                continue

            for match in MARKDOWN_LINK_PATTERN.finditer(line):
                raw_target = match.group(1)
                path_text, anchor = parse_target(raw_target)
                if is_external_target(path_text) or not path_text and not anchor:
                    continue

                target_path = (source.parent / path_text).resolve() if path_text else source.resolve()
                if not target_path.is_file():
                    report_missing(errors, source, line_number, raw_target, "points to a missing file")
                    continue

                if anchor and target_path.suffix.lower() == ".md" and anchor not in markdown_anchors(target_path):
                    report_missing(errors, source, line_number, raw_target, "points to a missing heading")


def html_ids(path: Path) -> set[str]:
    return set(ID_PATTERN.findall(path.read_text(encoding="utf-8")))


def check_html_links(errors: list[str]) -> None:
    if not HTML_DIR.is_dir():
        errors.append("docs/html: generated HTML directory is missing; run `make docs`")
        return

    for source in sorted(HTML_DIR.rglob("*.html")):
        content = source.read_text(encoding="utf-8")
        ids = html_ids(source)
        for raw_target in HTML_TARGET_PATTERN.findall(content):
            path_text, anchor = parse_target(raw_target)
            if is_external_target(path_text) or path_text.startswith(("data:", "javascript:")):
                continue

            target_path = (source.parent / path_text).resolve() if path_text else source.resolve()
            if not target_path.is_file():
                report_missing(errors, source, 1, raw_target, "points to a missing generated file")
                continue

            if anchor and target_path == source.resolve() and anchor not in ids:
                report_missing(errors, source, 1, raw_target, "points to a missing generated heading")


def main() -> int:
    errors: list[str] = []
    check_markdown_links(errors)
    check_html_links(errors)
    if errors:
        print("Documentation link check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Documentation links are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
