# Lessons Learned

Use this page before audits, release preparation, command additions, or documentation updates. It captures the project practices that have proven useful so future work can build on the existing shape instead of rediscovering it.

## Operating Principles

- Keep PyTransformer small, predictable, and command-line first.
- Preserve the base install with no runtime dependencies; add optional extras only for domains that need them.
- Keep command modules thin. Argument parsing, summaries, and exit codes belong in `pytransformer.cli`; reusable behavior belongs in `pytransformer.core`.
- Treat documentation as part of the product surface. Command behavior, dependency requirements, privacy implications, and validation steps should be reflected in Markdown.
- Prefer conservative file behavior over convenience when a command writes, renames, extracts, renders, or transcribes user data.

## Command Design

- Use importable Python module names such as `pyt_pdf_extract_text.py` and expose installed hyphenated commands such as `pyt-pdf-extract-text`.
- Every command module should expose `build_parser() -> argparse.ArgumentParser` and `main() -> int`.
- Every help screen should include an `Examples:` section that uses installed command names rather than module invocations.
- Use `-o`/`--output` for one output file, `-o`/`--output-folder` for folder output, `--overwrite` for clobbering, `--quiet` for reduced logging, and `--include-hidden` when hidden dotfiles can be included.
- Batch commands should process a flat folder by default, skip symlinks, skip hidden dotfiles unless requested, and sort entries deterministically.
- Optional dependency imports should be lazy or guarded so standard-library commands, help output, type checking, and package metadata validation continue to work from a base install.

## Documentation Practices

- Markdown is the source of truth. Generated HTML under `docs/html/` should not be hand-edited.
- Use `make docs` after Markdown changes and `make docs-check` before committing documentation work.
- Use `make docs-watch` during longer writing sessions when repeated rebuilds are useful.
- Keep one canonical docs generator. If the docs workflow changes, update the Makefile targets, `scripts/build_docs.py`, CI, GitHub Pages, README instructions, project instructions, and generated HTML in the same change.
- Keep `README.md` useful for first-time users, `docs/commands.md` useful for command-by-command behavior, `docs/privacy.md` useful for data-risk review, and `docs/architecture.md` useful for implementation decisions.
- Command pages under `docs/html/commands/` are generated from `### \`pyt-...\`` sections in `docs/commands.md`; keep those headings stable.

## Testing Considerations

- `make validate` is the broad pre-commit check. It covers compilation, linting, formatting, type checks, pre-commit config validation, generated docs, command help, installed entry points, unit tests, coverage, and package build metadata.
- Keep standard-library tests strong because they run without optional PDF, JPEG, MP4, OCR, or network dependencies.
- Add tests around shared helpers when behavior is reused across commands; this prevents command behavior from drifting.
- Help and entry point checks protect discoverability. Run them after adding, renaming, or removing a command.
- Optional-domain smoke tests should use small generated fixtures instead of private user files.
- MP4 transcription depends on FFmpeg and network speech recognition, so keep network-dependent behavior documented and avoid making it mandatory for normal validation.
- For write-heavy commands, test non-overwrite behavior, output path separation, missing input errors, and empty-folder behavior.

## Implementation Patterns

New command recipe:

1. Add `src/pytransformer/cli/pyt_<domain>_<verb>_<object>.py`.
2. Include the standard module header fields used by existing commands.
3. Expose `build_parser()` and `main()`.
4. Reuse helpers from `pytransformer.core.common` for parsers, paths, logging, confirmation, deterministic folder ordering, and user-facing errors.
5. Add a `[project.scripts]` entry in `pyproject.toml`.
6. Update `README.md`, `docs/commands.md`, and `docs/privacy.md` when behavior, dependencies, or data exposure changes.
7. Add tests that run without optional external services where possible.
8. Run `make docs`, then run the relevant validation target.

Optional dependency recipe:

1. Put the dependency in the smallest matching optional extra in `pyproject.toml`.
2. Guard imports or load them lazily.
3. Return a direct installation hint when the package is missing.
4. Add missing-import configuration for type checking when needed.
5. Keep `--help` and unrelated commands working without the extra installed.

Safe file-output recipe:

1. Resolve and validate input paths before processing.
2. Refuse to write over an existing file unless `--overwrite` is passed.
3. Refuse to use the same path for input and output.
4. Create output folders only after validation succeeds.
5. Keep generated artifacts separate from source files when practical.
6. Summarize written, skipped, planned, and failed items at the end of batch work.

## Technical Discoveries

- Console commands can use shell-friendly hyphenated names while their Python modules stay importable with underscores.
- PyMuPDF is imported as `fitz`, so missing dependency messages should name the user-facing package and the install extra clearly.
- JPEG metadata can come from EXIF, GPS EXIF, XMP, IPTC, ICC profiles, comments, and Pillow `info` fields; raw binary metadata should be summarized rather than printed directly.
- `defusedxml` lets Pillow parse XMP more safely, but JPEG commands should still behave predictably when it is absent.
- Preserving JPEG visual orientation, color profile, quantization tables, and subsampling is separate from preserving private descriptive metadata.
- SpeechRecognition's Google Web Speech API uses network access. Documentation and privacy notes must make that clear.
- Generated HTML can drift silently if Markdown changes are committed without running the docs build; keep `make docs-check` in validation.

## Avoid Repeating

- Do not add a second documentation generator unless the old workflow is removed or wrapped in the same change.
- Do not hand-edit files under `docs/html/` to fix documentation content.
- Do not import optional runtime dependencies at module import time when a lazy import keeps the base package usable.
- Do not use private PDFs, videos, transcripts, logs, local paths, or JPEG metadata in tests or examples.
- Do not broaden recursion, symlink following, overwrite behavior, or hidden-file inclusion without documenting and testing the safety impact.
- Do not put shared validation, ordering, or output rules in one CLI module when another command already needs the same behavior.

## Quick Audit Checklist

- Command naming, parser shape, examples, and entry point are consistent.
- Optional dependencies are isolated to the right extra and have clear missing-package messages.
- Write behavior is guarded by validation, `--overwrite`, `--dry-run`, or confirmation as appropriate.
- Batch behavior is deterministic and avoids hidden files, symlinks, and recursion unless documented.
- README, command docs, privacy docs, architecture docs, and generated HTML are current.
- Tests cover reusable logic and the highest-risk file behavior.
- Validation has been run at the level appropriate to the change.
