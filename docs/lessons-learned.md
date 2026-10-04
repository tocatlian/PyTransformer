# Decision Log And Lessons Learned

This page owns important project decisions and their rationale. Current requirements live in the topic owners listed in [the documentation map](knowledge.md). Link to those owners instead of maintaining a second copy of their rules.

## Recording Decisions

For a new consequential choice, record a descriptive heading, decision date, status, context, rationale, consequences, and links to the current owners. Use statuses such as accepted, proposed, or superseded. When superseding a decision, link both entries and revise the current owner in the same task.

The existing choices below were recovered from repository documentation and implementation during the 2026-10-03 review. Their original decision dates were not recorded. They describe the current implemented design, not newly approved features.

## Small CLI Package With Optional Domains

Status: accepted, original date not recorded.

A focused CLI package keeps each tool discoverable and scriptable. Keeping the base dependency-free avoids making simple filename and text operations depend on PDF or media libraries. Thin command orchestration and focused shared helpers reduce behavior drift without creating a large framework.

Consequences: optional domains require extra setup, and optional imports must permit base installation, help, tests, and type checks to work. Current scope belongs in [product requirements](requirements.md), the implementation strategy in [architecture](architecture.md), and setup in [README](../README.md#dependency-groups).

## Importable Modules And Shell Commands

Status: accepted, original date not recorded.

Python identifiers need underscores, while hyphenated terminal commands are idiomatic for shell users. The short `pyt-*` prefix and inventory command make a growing command suite easier to discover.

Consequences: module names and console entry points must stay aligned. The authoritative convention is in [CONTRIBUTING.md](../CONTRIBUTING.md#naming-standards), and exact entry points belong in `pyproject.toml`.

## One Markdown Source Per Topic

Status: accepted, original date not recorded.

Independent README, command, privacy, architecture, and HTML definitions can drift. Keeping Markdown as the authoring source and generating HTML lets the same knowledge serve repository readers and browser users.

Consequences: new pages must be registered in the existing generator, and generated files must be checked after source changes. [Architecture](architecture.md#documentation-build) owns the build description. [AGENTS.md](../AGENTS.md#documentation) owns Codex's documentation obligations.

## Finder Visible Output

Status: accepted, original date not recorded.

Finder and File Provider folders can miss a hidden temporary file renamed into place, including ordinary nested folders whose provider metadata is unavailable. This led to completed media output being difficult to discover in Finder.

The shared helper uses a visible final-name copy on macOS rather than relying on provider detection alone. Consequence: that path trades atomic replacement for reliable discovery and uses backup and cleanup handling to mitigate copy failures. [Architecture](architecture.md#output-finalization) owns the implementation description, and the [M4A command contract](commands.md#pyt-m4a-to-mp3) owns user-facing behavior.

## Repository Knowledge Survives Chat Removal

Date: 2026-10-03. Status: accepted.

The user requires archived chats to remain disposable without losing lasting project knowledge. Repository documentation therefore owns requirements, instructions, procedures, and decisions. The work is incomplete until lasting chat outcomes have been promoted to their topic owners.

Consequences: [the ownership map](knowledge.md) routes new information, [AGENTS.md](../AGENTS.md) enforces the agent workflow, and this log retains rationale. Historical operation evidence is handled under [Operations](operations.md#verification-evidence-and-retention), not treated as current policy or deployment status.

## Measure Storage Before Rewriting History

Date: 2026-10-03. Status: accepted.

The user needs aggressive disk space recovery on a nearly full MacBook. Inspection showed this project occupied about 2 MiB and its branch history already contained a single flattened commit. Further Git rewriting would recover little space while risking useful metadata and local recovery. Verified disposable caches, obsolete cleanup evidence, and redundant generated HTML were removed instead, while source, canonical documentation, and intentional edits were preserved.

Consequences: [Operations](operations.md#disk-space-maintenance) owns the measured cleanup procedure and the boundary between project cleanup and separately authorized shared storage cleanup. Larger storage targets must be inspected outside this small repository rather than assuming Git history is responsible for disk pressure.

## Technical Discoveries

- PyMuPDF is imported as `fitz`. Its user-facing dependency name and install extra need to be clear in diagnostics.
- JPEG metadata can come from EXIF, GPS EXIF, XMP, IPTC, ICC profiles, comments, and Pillow `info` fields. Summarizing raw binary metadata makes inspection usable.
- Preserving JPEG visual orientation, color profile, quantization tables, and subsampling is separate from preserving private descriptive metadata. The [JPEG command contracts](commands.md#jpeg-commands) own the behavior.
- Copying Pillow image info can retain comments during metadata stripping. The fix is recorded in [CHANGELOG.md](../CHANGELOG.md#unreleased).
- SpeechRecognition's external service affects data handling as well as dependencies. The [privacy guide](privacy.md#mp4-transcription) owns the disclosure.
- Different Git commit histories can describe the same source tree. The archived deployment cleanup established this after local history had been flattened. [Operations](operations.md#deployment-reconciliation) owns verification guidance.

These discoveries explain existing choices. If a discovery becomes a new recurring implementation requirement, place that requirement in its topic owner and link to it here.
