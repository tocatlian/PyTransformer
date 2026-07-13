# Lessons Learned

Use this page for rationale, discoveries, and project-specific reminders. It supplements the current requirements in the [README](../README.md), [command guide](commands.md), [privacy guide](privacy.md), [architecture guide](architecture.md), and [CONTRIBUTING.md](../CONTRIBUTING.md); it is not a second source of current command or contributor rules.

## Documentation Map

- First-time users: [README](../README.md)
- Command behavior: [command guide](commands.md)
- Privacy and data handling: [privacy guide](privacy.md)
- Implementation structure: [architecture guide](architecture.md)
- Development and release requirements: [CONTRIBUTING.md](../CONTRIBUTING.md)
- Security reporting: [SECURITY.md](../SECURITY.md)

Markdown is the source of truth. Generated pages under `docs/html/` are built from these sources and should not be edited directly.

## Operating Principles

- Keep PyTransformer small, predictable, and command-line first.
- Preserve the base install with no runtime dependencies; add optional extras only for domains that need them.
- Keep command modules thin and place reusable behavior in `pytransformer.core`.
- Prefer conservative file behavior over convenience when a command writes, renames, extracts, renders, or transcribes user data.

These principles explain why the project separates command orchestration, shared helpers, optional dependencies, and privacy guidance across the documents above.

## Why The Command Conventions Exist

Hyphenated installed commands, importable underscore-named modules, standard help output, explicit output options, deterministic batch behavior, and guarded writes make the tools easier to discover, automate, and review. The current conventions and exceptions belong in the [command guide](commands.md) and [contributor standards](../CONTRIBUTING.md).

## Why The Documentation Workflow Exists

Keeping one Markdown source for each topic prevents README, command, privacy, architecture, and generated HTML content from drifting apart. Run `make docs` after Markdown changes and `make docs-check` before committing; the latter verifies both generated output and local links.

## Testing Considerations

The repository-wide `make validate` gate protects package structure, command discoverability, generated docs, links, and the 80% coverage requirement. Shared helpers deserve focused tests because a small change there can affect several commands. Optional-domain smoke checks should use generated fixtures and only be required when the affected dependency or system tool is available; see [validation expectations](../CONTRIBUTING.md#validation-expectations).

## Technical Discoveries

- Console commands can use shell-friendly hyphenated names while their Python modules remain importable with underscores.
- PyMuPDF is imported as `fitz`, so missing dependency messages should name the user-facing package and install extra clearly.
- JPEG metadata can come from EXIF, GPS EXIF, XMP, IPTC, ICC profiles, comments, and Pillow `info` fields; raw binary metadata should be summarized rather than printed directly.
- Preserving JPEG visual orientation, color profile, quantization tables, and subsampling is separate from preserving private descriptive metadata.
- SpeechRecognition's Google Web Speech API uses network access; this is a privacy decision, not just an implementation detail.
- File-provider and iCloud-backed folders may require staged output finalization so Finder and the provider see the completed file reliably.

## Avoid Repeating

- Do not add a second documentation generator or hand-edit `docs/html/`.
- Do not import optional runtime dependencies at module import time when a guarded or lazy import keeps the base package usable.
- Do not use private PDFs, videos, transcripts, logs, local paths, or JPEG metadata in tests or examples.
- Do not broaden recursion, symlink following, overwrite behavior, or hidden-file inclusion without documenting and testing the safety impact.
- Do not copy current command standards into this page; update the authoritative document and link to it instead.

## Quick Audit Checklist

- README points users to the authoritative guide for each topic.
- Every command is represented in `docs/commands.md` and has generated HTML output.
- Privacy-sensitive behavior is documented in `docs/privacy.md`.
- Implementation rules are documented in `docs/architecture.md` or `CONTRIBUTING.md`, not repeated here.
- `make docs-check` passes after Markdown changes.
- Tests cover reusable logic and the highest-risk file behavior.
