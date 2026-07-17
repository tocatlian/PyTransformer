# Changelog

All notable changes to PyTransformer will be documented in this file.

This project follows the spirit of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses semantic versioning for public releases.

## [Unreleased]

### Added

- Added tox environments for local CI-style checks.
- Added optional PDF and JPEG smoke targets with generated fixtures.

### Fixed

- Finalize macOS-generated files through a visible final-name write so Finder reliably discovers M4A-to-MP3 output, including folders nested inside File Provider locations.
- Removed copied Pillow image info when writing stripped JPEGs so JPEG comments are not preserved in cleaned output.

## [1.0.0] - 2026-06-26

### Added

- Added `pyt-help` to list available PyTransformer console commands.

### Changed

- Standardized command modules around `build_parser()`, `--quiet`, `-o`/`--output-folder` for folder outputs, and `--include-hidden` for batch folder commands.
- Added consistent `Examples:` sections to every command's `-h`/`--help` output.
- Renamed command modules and console commands to the short `pyt_domain_verb_object[_batch]` / `pyt-domain-verb-object[-batch]` convention.

## [0.1.0] - 2026-06-17

### Added

- Standard `src/pytransformer` package layout.
- Console entry points for all PyTransformer commands.
- PDF, JPEG, MP4, filename, and text command modules.
- Optional dependency groups for PDF, JPEG, MP4, OCR, all, and development workflows.
- Makefile targets for validation, smoke testing, linting, and cleanup.
- Git attributes configuration for line-ending normalization and binary media handling.
- GitHub Actions CI workflow.
- Public documentation for commands, privacy, architecture, security, and contribution standards.
- Support, code of conduct, and release checklist guidance.
- Dependabot configuration for public repository maintenance.
- PEP 561 `py.typed` marker for typed consumers.
- Mypy configuration and validation target for static type checking.
- Coverage.py configuration and validation target with an enforced coverage floor.
- Pre-commit configuration for local formatting, linting, metadata, and type-checking hooks.

### Changed

- Reworked the original flat script collection into an installable Python package.
- Standardized Python module names with lowercase `snake_case`.
- Standardized command-line names with the `pytransformer-` prefix and hyphenated command names.
- Hardened scripts with safer path validation, overwrite guards, deterministic directory ordering, and clearer exit behavior.
- Centralized JPEG metadata inspection in `pytransformer.core.jpeg_metadata`.
- Expanded validation to check formatting, installed entry points, package builds, metadata, public repo files, and executable script bits.
- Tightened optional dependency shims so static type checks can run without installing every media/PDF dependency.
- Replaced the JPEG variant counter's dictionary-shaped analysis result with a typed dataclass.
- Expanded standard-library behavior tests for validation guards, dry runs, duplicate detection, and text handling.
- Removed redundant `requirements-*.txt` files so `pyproject.toml` is the single dependency source of truth.
- Simplified packaging by removing the package manifest and folding dependency and release guidance into the README and contributing guide.

### Security

- Added explicit privacy notes for metadata, transcripts, rendered PDFs, and external speech recognition.
- Added `SECURITY.md` with vulnerability reporting guidance.
