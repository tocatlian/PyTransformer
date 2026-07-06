#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""Build the static HTML documentation from the markdown sources."""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
HTML_DIR = DOCS_DIR / "html"
COMMANDS_SOURCE = DOCS_DIR / "commands.md"


@dataclass(frozen=True)
class MarkdownPage:
    source: Path
    output_name: str
    title: str
    nav_label: str


@dataclass(frozen=True)
class CommandPage:
    command: str
    category: str
    markdown: str

    @property
    def output_name(self) -> str:
        return f"commands/{self.command}.html"


MARKDOWN_PAGES = [
    MarkdownPage(ROOT / "README.md", "index.html", "PyTransformer", "Home"),
    MarkdownPage(COMMANDS_SOURCE, "commands.html", "Command Guide", "Commands"),
    MarkdownPage(DOCS_DIR / "architecture.md", "architecture.html", "Architecture", "Architecture"),
    MarkdownPage(DOCS_DIR / "lessons-learned.md", "lessons-learned.html", "Lessons Learned", "Lessons"),
    MarkdownPage(DOCS_DIR / "privacy.md", "privacy.html", "Privacy", "Privacy"),
]

CSS = """
:root {
  color-scheme: light;
  --bg: #fafafa;
  --surface: #ffffff;
  --text: #1d2733;
  --muted: #5f6b7a;
  --border: #d9dee7;
  --accent: #1c6b5a;
  --accent-soft: #e7f3ee;
  --code-bg: #f1f4f8;
  --shadow: 0 1px 2px rgba(29, 39, 51, 0.08);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family:
    ui-sans-serif,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
  line-height: 1.58;
}

a {
  color: var(--accent);
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.2em;
}

.site-shell {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  min-height: 100vh;
}

.site-nav {
  border-right: 1px solid var(--border);
  background: var(--surface);
  padding: 28px 24px;
  position: sticky;
  top: 0;
  align-self: start;
  height: 100vh;
  overflow-y: auto;
}

.brand {
  display: block;
  margin-bottom: 8px;
  color: var(--text);
  font-size: 1.08rem;
  font-weight: 700;
  text-decoration: none;
}

.tagline {
  color: var(--muted);
  font-size: 0.92rem;
  margin: 0 0 24px;
}

.nav-section-title {
  color: var(--muted);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  margin: 24px 0 8px;
  text-transform: uppercase;
}

.nav-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-list a {
  border-radius: 6px;
  color: var(--text);
  display: block;
  font-size: 0.94rem;
  padding: 6px 8px;
  text-decoration: none;
}

.nav-list a:hover,
.nav-list a[aria-current="page"] {
  background: var(--accent-soft);
  color: var(--accent);
}

.site-main {
  min-width: 0;
  padding: 48px 36px 72px;
}

.content {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow);
  margin: 0 auto;
  max-width: 980px;
  padding: 42px min(6vw, 64px);
}

.source-note {
  color: var(--muted);
  font-size: 0.9rem;
  margin: 0 0 24px;
}

h1,
h2,
h3,
h4 {
  line-height: 1.22;
  margin: 1.6em 0 0.58em;
}

h1 {
  font-size: clamp(2rem, 5vw, 3.6rem);
  margin-top: 0;
}

h2 {
  border-top: 1px solid var(--border);
  font-size: 1.6rem;
  padding-top: 1.2em;
}

h3 {
  font-size: 1.22rem;
}

p,
ul,
ol,
table,
pre {
  margin: 0 0 1.05rem;
}

ul,
ol {
  padding-left: 1.4rem;
}

li + li {
  margin-top: 0.25rem;
}

code {
  background: var(--code-bg);
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 0.92em;
  padding: 0.12em 0.32em;
}

pre {
  background: #18202b;
  border-radius: 8px;
  color: #edf3f8;
  overflow-x: auto;
  padding: 16px 18px;
}

pre code {
  background: transparent;
  color: inherit;
  display: block;
  font-size: 0.9rem;
  padding: 0;
}

.table-wrap {
  overflow-x: auto;
}

table {
  border-collapse: collapse;
  font-size: 0.92rem;
  width: 100%;
}

th,
td {
  border: 1px solid var(--border);
  padding: 0.58rem 0.72rem;
  text-align: left;
  vertical-align: top;
}

th {
  background: var(--code-bg);
}

.command-card-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  list-style: none;
  margin: 0 0 1.4rem;
  padding: 0;
}

.command-card-grid li {
  margin: 0;
}

.command-card-grid a {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  display: block;
  min-height: 74px;
  padding: 14px 16px;
  text-decoration: none;
}

.command-card-grid a:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.command-card-grid span {
  color: var(--muted);
  display: block;
  font-size: 0.84rem;
  margin-top: 3px;
}

.command-page-link {
  font-size: 0.86rem;
  font-weight: 600;
  margin-left: 0.5rem;
}

.breadcrumb {
  color: var(--muted);
  font-size: 0.9rem;
  margin: 0 0 20px;
}

@media (max-width: 820px) {
  .site-shell {
    display: block;
  }

  .site-nav {
    border-bottom: 1px solid var(--border);
    border-right: 0;
    height: auto;
    position: static;
  }

  .site-main {
    padding: 24px 16px 48px;
  }

  .content {
    padding: 28px 20px;
  }
}
""".strip()


class MarkdownRenderer:
    def __init__(
        self,
        *,
        source_path: Path,
        output_path: Path,
        html_root: Path,
        markdown_outputs: dict[Path, Path],
        command_pages: Sequence[CommandPage],
        link_command_headings: bool = False,
    ) -> None:
        self.source_path = source_path
        self.output_path = output_path
        self.html_root = html_root
        self.markdown_outputs = markdown_outputs
        self.command_pages = {command.command: command for command in command_pages}
        self.link_command_headings = link_command_headings

    def render(self, markdown_text: str) -> str:
        lines = markdown_text.splitlines()
        html_blocks: list[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                index += 1
                continue

            if line.startswith("```"):
                block, index = self._render_code_fence(lines, index)
                html_blocks.append(block)
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading_match:
                html_blocks.append(self._render_heading(heading_match))
                index += 1
                continue

            if self._is_table_start(lines, index):
                block, index = self._render_table(lines, index)
                html_blocks.append(block)
                continue

            if line.startswith("- "):
                block, index = self._render_unordered_list(lines, index)
                html_blocks.append(block)
                continue

            if re.match(r"^\d+\.\s+", line):
                block, index = self._render_ordered_list(lines, index)
                html_blocks.append(block)
                continue

            block, index = self._render_paragraph(lines, index)
            html_blocks.append(block)

        return "\n".join(html_blocks)

    def _render_code_fence(self, lines: Sequence[str], start: int) -> tuple[str, int]:
        info = lines[start][3:].strip()
        language = info.split(maxsplit=1)[0] if info else ""
        code_lines: list[str] = []
        index = start + 1
        while index < len(lines):
            if lines[index].startswith("```"):
                index += 1
                break
            code_lines.append(lines[index])
            index += 1

        class_name = f' class="language-{html.escape(language)}"' if language else ""
        code = html.escape("\n".join(code_lines))
        return f"<pre><code{class_name}>{code}</code></pre>", index

    def _render_heading(self, heading_match: re.Match[str]) -> str:
        level = len(heading_match.group(1))
        raw_text = heading_match.group(2)
        text = raw_text.strip()
        slug = slugify(strip_inline_markup(text))
        rendered_text = self._render_inline(text)

        command_name = command_from_heading(text)
        page_link = ""
        if command_name and self.link_command_headings and command_name in self.command_pages:
            command_page = self.html_root / self.command_pages[command_name].output_name
            href = relative_href(self.output_path, command_page)
            page_link = f' <a class="command-page-link" href="{html.escape(href)}">Command page</a>'

        return f'<h{level} id="{html.escape(slug)}">{rendered_text}{page_link}</h{level}>'

    def _render_table(self, lines: Sequence[str], start: int) -> tuple[str, int]:
        header_cells = split_table_row(lines[start])
        index = start + 2
        body_rows: list[list[str]] = []
        while index < len(lines) and lines[index].strip().startswith("|"):
            body_rows.append(split_table_row(lines[index]))
            index += 1

        header = "".join(f"<th>{self._render_inline(cell.strip())}</th>" for cell in header_cells)
        rows = ["<thead><tr>" + header + "</tr></thead>"]
        body_html = []
        for row in body_rows:
            cells = row + [""] * (len(header_cells) - len(row))
            rendered_cells = "".join(
                f"<td>{self._render_inline(cell.strip())}</td>" for cell in cells[: len(header_cells)]
            )
            body_html.append("<tr>" + rendered_cells + "</tr>")
        if body_html:
            rows.append("<tbody>" + "".join(body_html) + "</tbody>")
        return '<div class="table-wrap"><table>' + "".join(rows) + "</table></div>", index

    def _render_unordered_list(self, lines: Sequence[str], start: int) -> tuple[str, int]:
        items: list[str] = []
        index = start
        while index < len(lines) and lines[index].startswith("- "):
            items.append(f"<li>{self._render_inline(lines[index][2:].strip())}</li>")
            index += 1
        return "<ul>" + "".join(items) + "</ul>", index

    def _render_ordered_list(self, lines: Sequence[str], start: int) -> tuple[str, int]:
        items: list[str] = []
        index = start
        while index < len(lines):
            match = re.match(r"^\d+\.\s+(.+)$", lines[index])
            if not match:
                break
            items.append(f"<li>{self._render_inline(match.group(1).strip())}</li>")
            index += 1
        return "<ol>" + "".join(items) + "</ol>", index

    def _render_paragraph(self, lines: Sequence[str], start: int) -> tuple[str, int]:
        paragraph_lines: list[str] = []
        index = start
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                break
            if (
                line.startswith("```")
                or re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
                or self._is_table_start(lines, index)
                or line.startswith("- ")
                or re.match(r"^\d+\.\s+", line)
            ):
                break
            paragraph_lines.append(line.strip())
            index += 1
        return f"<p>{self._render_inline(' '.join(paragraph_lines))}</p>", index

    def _render_inline(self, text: str) -> str:
        escaped = html.escape(text)

        escaped = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", self._replace_image, escaped)
        escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", self._replace_link, escaped)
        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        return escaped

    def _replace_image(self, match: re.Match[str]) -> str:
        alt = match.group(1)
        target = html.unescape(match.group(2))
        return f'<img alt="{alt}" src="{html.escape(self._resolve_href(target))}">'

    def _replace_link(self, match: re.Match[str]) -> str:
        label = match.group(1)
        target = html.unescape(match.group(2))
        return f'<a href="{html.escape(self._resolve_href(target))}">{label}</a>'

    def _resolve_href(self, target: str) -> str:
        if is_external_href(target):
            return target

        target_path_text, separator, anchor = target.partition("#")
        source_dir = self.source_path.parent
        if target_path_text:
            target_source = (source_dir / target_path_text).resolve()
        else:
            target_source = self.source_path.resolve()

        markdown_output = self.markdown_outputs.get(target_source)
        if markdown_output:
            href = relative_href(self.output_path, markdown_output)
        elif target_path_text.endswith(".md"):
            href = target_path_text.removesuffix(".md") + ".html"
        elif target_path_text:
            href = relative_href(self.output_path, target_source)
        else:
            href = ""

        if separator:
            href = f"{href}#{anchor}"
        return href

    @staticmethod
    def _is_table_start(lines: Sequence[str], index: int) -> bool:
        if index + 1 >= len(lines):
            return False
        separator_pattern = r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$"
        return lines[index].strip().startswith("|") and bool(re.match(separator_pattern, lines[index + 1]))


def command_from_heading(text: str) -> str | None:
    match = re.fullmatch(r"`(pyt-[a-z0-9-]+)`", text.strip())
    return match.group(1) if match else None


def split_table_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def strip_inline_markup(text: str) -> str:
    return re.sub(r"[`*_]", "", text)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def is_external_href(target: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9+.-]*:", target)) or target.startswith("mailto:")


def relative_href(from_file: Path, to_file: Path) -> str:
    return relpath(from_file.parent, to_file)


def relpath(from_dir: Path, to_file: Path) -> str:
    return Path(os.path.relpath(to_file, from_dir)).as_posix()


def discover_markdown_outputs(html_root: Path) -> dict[Path, Path]:
    return {page.source.resolve(): (html_root / page.output_name).resolve() for page in MARKDOWN_PAGES}


def extract_command_pages(markdown_text: str) -> list[CommandPage]:
    pages: list[CommandPage] = []
    current_category = ""
    current_command: str | None = None
    current_lines: list[str] = []

    for line in markdown_text.splitlines():
        category_match = re.match(r"^##\s+(.+?)\s*$", line)
        command_match = re.match(r"^###\s+`(pyt-[a-z0-9-]+)`\s*$", line)

        if category_match:
            if current_command:
                pages.append(CommandPage(current_command, current_category, "\n".join(current_lines).strip() + "\n"))
                current_command = None
                current_lines = []
            current_category = category_match.group(1)
            continue

        if command_match:
            if current_command:
                pages.append(CommandPage(current_command, current_category, "\n".join(current_lines).strip() + "\n"))
            current_command = command_match.group(1)
            current_lines = [f"# `{current_command}`"]
            continue

        if current_command:
            current_lines.append(line)

    if current_command:
        pages.append(CommandPage(current_command, current_category, "\n".join(current_lines).strip() + "\n"))

    return pages


def command_grid(command_pages: Sequence[CommandPage], current_output: Path, html_root: Path) -> str:
    cards = []
    for command_page in command_pages:
        href = relative_href(current_output, html_root / command_page.output_name)
        cards.append(
            '<li><a href="'
            + html.escape(href)
            + '"><code>'
            + html.escape(command_page.command)
            + "</code><span>"
            + html.escape(command_page.category)
            + "</span></a></li>"
        )
    return '<ul class="command-card-grid">' + "".join(cards) + "</ul>"


def build_nav(current_output: Path, html_root: Path, command_pages: Sequence[CommandPage]) -> str:
    home_href = html.escape(relative_href(current_output, html_root / "index.html"))
    sections = [
        f'<a class="brand" href="{home_href}">PyTransformer</a>',
        '<p class="tagline">HTML docs generated from markdown.</p>',
        '<p class="nav-section-title">Docs</p>',
        '<ul class="nav-list">',
    ]

    for page in MARKDOWN_PAGES:
        target = html_root / page.output_name
        current = ' aria-current="page"' if target.resolve() == current_output.resolve() else ""
        sections.append(
            '<li><a href="'
            + html.escape(relative_href(current_output, target))
            + '"'
            + current
            + ">"
            + html.escape(page.nav_label)
            + "</a></li>"
        )
    sections.append("</ul>")
    sections.append('<p class="nav-section-title">Command Pages</p>')
    sections.append('<ul class="nav-list">')
    for command_page in command_pages:
        target = html_root / command_page.output_name
        current = ' aria-current="page"' if target.resolve() == current_output.resolve() else ""
        sections.append(
            '<li><a href="'
            + html.escape(relative_href(current_output, target))
            + '"'
            + current
            + ">"
            + html.escape(command_page.command)
            + "</a></li>"
        )
    sections.append("</ul>")
    return "\n".join(sections)


def wrap_page(
    *,
    title: str,
    body: str,
    source_label: str,
    output_path: Path,
    html_root: Path,
    command_pages: Sequence[CommandPage],
) -> str:
    css_href = relative_href(output_path, html_root / "styles.css")
    nav = build_nav(output_path, html_root, command_pages)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{html.escape(title)} - PyTransformer</title>\n"
        f'  <link rel="stylesheet" href="{html.escape(css_href)}">\n'
        "</head>\n"
        "<body>\n"
        '<div class="site-shell">\n'
        f'<nav class="site-nav" aria-label="Documentation navigation">{nav}</nav>\n'
        '<main class="site-main">\n'
        '<article class="content">\n'
        f'<p class="source-note">Generated from {html.escape(source_label)}.</p>\n'
        f"{body}\n"
        "</article>\n"
        "</main>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


def build_site(html_root: Path = HTML_DIR) -> list[Path]:
    commands_markdown = COMMANDS_SOURCE.read_text(encoding="utf-8")
    command_pages = extract_command_pages(commands_markdown)
    markdown_outputs = discover_markdown_outputs(html_root)

    if html_root.exists():
        shutil.rmtree(html_root)
    html_root.mkdir(parents=True)
    (html_root / "commands").mkdir()
    (html_root / "styles.css").write_text(CSS + "\n", encoding="utf-8")

    written = [html_root / "styles.css"]
    for page in MARKDOWN_PAGES:
        source_text = page.source.read_text(encoding="utf-8")
        output_path = html_root / page.output_name
        renderer = MarkdownRenderer(
            source_path=page.source.resolve(),
            output_path=output_path.resolve(),
            html_root=html_root.resolve(),
            markdown_outputs=markdown_outputs,
            command_pages=command_pages,
            link_command_headings=page.source == COMMANDS_SOURCE,
        )
        body = renderer.render(source_text)
        if page.source == COMMANDS_SOURCE:
            body = body.replace(
                '<h2 id="discovery-command">Discovery Command</h2>',
                '<h2 id="command-pages">Command Pages</h2>\n'
                + command_grid(command_pages, output_path.resolve(), html_root.resolve())
                + '\n<h2 id="discovery-command">Discovery Command</h2>',
            )
        output_path.write_text(
            wrap_page(
                title=page.title,
                body=body,
                source_label=page.source.relative_to(ROOT).as_posix(),
                output_path=output_path.resolve(),
                html_root=html_root.resolve(),
                command_pages=command_pages,
            ),
            encoding="utf-8",
        )
        written.append(output_path)

    for command_page in command_pages:
        output_path = html_root / command_page.output_name
        renderer = MarkdownRenderer(
            source_path=COMMANDS_SOURCE.resolve(),
            output_path=output_path.resolve(),
            html_root=html_root.resolve(),
            markdown_outputs=markdown_outputs,
            command_pages=command_pages,
        )
        body = (
            '<p class="breadcrumb"><a href="'
            + html.escape(relative_href(output_path.resolve(), html_root / "commands.html"))
            + '">Command Guide</a> / '
            + html.escape(command_page.category)
            + "</p>\n"
            + renderer.render(command_page.markdown)
        )
        output_path.write_text(
            wrap_page(
                title=command_page.command,
                body=body,
                source_label=f"{COMMANDS_SOURCE.relative_to(ROOT).as_posix()}#{command_page.command}",
                output_path=output_path.resolve(),
                html_root=html_root.resolve(),
                command_pages=command_pages,
            ),
            encoding="utf-8",
        )
        written.append(output_path)

    return sorted(written)


def collect_files(root: Path) -> dict[Path, bytes]:
    if not root.exists():
        return {}
    return {path.relative_to(root): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def check_site() -> int:
    with tempfile.TemporaryDirectory(prefix=".html-check-", dir=DOCS_DIR) as temp_dir:
        temp_root = Path(temp_dir)
        build_site(temp_root)
        expected = collect_files(temp_root)
        actual = collect_files(HTML_DIR)

    if expected == actual:
        print("HTML documentation is current.")
        return 0

    expected_paths = set(expected)
    actual_paths = set(actual)
    missing = sorted(expected_paths - actual_paths)
    extra = sorted(actual_paths - expected_paths)
    changed = sorted(path for path in expected_paths & actual_paths if expected[path] != actual[path])

    print("HTML documentation is out of date. Run `make docs`.")
    for label, paths in [("Missing", missing), ("Extra", extra), ("Changed", changed)]:
        if paths:
            print(f"{label}:")
            for path in paths[:20]:
                print(f"  {path.as_posix()}")
            if len(paths) > 20:
                print(f"  ... and {len(paths) - 20} more")
    return 1


def markdown_sources() -> list[Path]:
    return [ROOT / "README.md", *sorted(DOCS_DIR.glob("*.md"))]


def snapshot_mtimes(paths: Iterable[Path]) -> dict[Path, int]:
    return {path: path.stat().st_mtime_ns for path in paths}


def watch(interval_seconds: float) -> int:
    sources = markdown_sources()
    print("Watching markdown documentation. Press Ctrl+C to stop.")
    build_site(HTML_DIR)
    last_snapshot = snapshot_mtimes(sources)
    try:
        while True:
            time.sleep(interval_seconds)
            current_snapshot = snapshot_mtimes(sources)
            if current_snapshot != last_snapshot:
                build_site(HTML_DIR)
                print("Rebuilt HTML documentation.")
                last_snapshot = current_snapshot
    except KeyboardInterrupt:
        print("\nStopped watching documentation.")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build PyTransformer HTML documentation from markdown.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify docs/html matches the generated output without updating it.",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Rebuild docs/html whenever a markdown source changes.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds for --watch.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    if args.check and args.watch:
        parser.error("--check and --watch cannot be used together")

    if args.check:
        return check_site()
    if args.watch:
        return watch(args.interval)

    written = build_site(HTML_DIR)
    print(f"Wrote {len(written)} HTML documentation files to {HTML_DIR.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
