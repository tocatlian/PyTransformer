# Codex Project Instructions

## Documentation

- Archived chats are temporary working context. The repository must retain all lasting requirements, decisions, conventions, constraints, configuration rules, and procedures needed by future sessions.
- Read [the documentation ownership map](docs/knowledge.md) before adding durable information. Update its authoritative source instead of creating independent copies, and reference that source elsewhere.
- Promoting lasting chat decisions into documentation is part of completing the work. Update affected documentation alongside implementation, consolidate conflicts, and explicitly replace obsolete decisions. Record important rationale in [the decision log](docs/lessons-learned.md).
- Follow [CONTRIBUTING.md](CONTRIBUTING.md) for development conventions and testing expectations. Keep Codex-specific instructions here and technical requirements in their designated documents.
- Treat Markdown documentation as the source of truth. Generated HTML documentation belongs under `docs/html/` and should not be hand-edited except to repair the generator.
- When Markdown docs change, regenerate the HTML version with `make docs` or `python3 scripts/build_docs.py`. For longer documentation sessions, use `make docs-watch` or `python3 scripts/build_docs.py --watch`.
- Run `make docs-check` after documentation changes. Register new documentation pages in `MARKDOWN_PAGES` in `scripts/build_docs.py` so they have generated HTML and navigation.

## Product Design Context

- Keep Product Design context project-scoped. If a future run creates or updates Product Design context for this project, save it inside this repository, preferably at `docs/product-design/user-context.md` with visual references in `docs/product-design/assets/`, instead of the global Product Design plugin state at `~/.codex/state/plugins/product-design/`.
- Each Codex project can have its own design language, UI conventions, UX decisions, and reference screenshots. Do not reuse or overwrite another project's Product Design context unless the user explicitly asks.

## GitHub Workflow

- Do not create commits, branches, pull requests, pushes, merges, or any other GitHub synchronization unless the user explicitly requests that action.
- When the user does explicitly request a Git operation, do not push project changes directly to the protected `main` branch.
- Keep generated files and unrelated working-tree changes out of any user-requested commits.
- When Git work is authorized, follow the branch and review procedure in [CONTRIBUTING.md](CONTRIBUTING.md#github-workflow). Deployment and cleanup procedures belong in [docs/operations.md](docs/operations.md).
