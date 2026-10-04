# Product Requirements

This page owns product scope and requirements shared across commands. The [command guide](commands.md) owns command-specific behavior, arguments, defaults, outputs, and documented exceptions. [CONTRIBUTING.md](../CONTRIBUTING.md) owns implementation and testing conventions.

## Scope

PyTransformer is a small, predictable, command-line-first Python package for transforming PDFs, M4A and MP4 media, images and JPEG metadata, filenames, and plain-text files. Users must be able to discover installed commands through `pyt-help` and inspect each command through `--help`.

The base install must have no runtime dependencies. Standard-library commands must remain usable without installing optional media or PDF packages. Optional features must give direct installation guidance when their dependencies are missing, and every command must still display help.

## File Safety

- Validate input and output paths before processing.
- Skip symlinks in batch operations unless a command documents a justified exception.
- Avoid recursion unless it is explicitly part of the documented command behavior.
- Avoid overwriting existing output unless the user explicitly enables it through the command's documented controls.
- Bulk renaming must offer a preview through `--dry-run` and require confirmation or explicit confirmation bypass.
- Batch folder commands skip hidden dotfiles by default and offer `--include-hidden` when inclusion is supported.
- Preserve source files and keep generated outputs separate where practical. The command guide identifies intentional sibling outputs and rename behavior.

Changes to these safeguards require updating the affected command contract and validating the file behavior under CONTRIBUTING's testing expectations.

## Data Handling

The [privacy guide](privacy.md) owns external-service disclosure and sensitive-data handling. Document the privacy implications of new outputs or network behavior there and reference it from the relevant command. Do not rely on chat context to tell users whether their data leaves the machine.

## Current And Future Requirements

These requirements consolidate the existing product principles and safety defaults. They do not introduce a new feature roadmap. Add accepted lasting product changes here or in the relevant command contract, and record consequential rationale in [the decision log](lessons-learned.md).
