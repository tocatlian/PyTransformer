# Codex Project Instructions

## Documentation

- Treat Markdown documentation as the source of truth. Generated HTML documentation belongs under `docs/html/` and should not be hand-edited except to repair the generator.
- When Markdown docs change, regenerate the HTML version with `make docs` or `python3 scripts/build_docs.py`. For longer documentation sessions, use `make docs-watch` or `python3 scripts/build_docs.py --watch`.

## Product Design Context

- Keep Product Design context project-scoped. If a future run creates or updates Product Design context for this project, save it inside this repository, preferably at `docs/product-design/user-context.md` with visual references in `docs/product-design/assets/`, instead of the global Product Design plugin state at `~/.codex/state/plugins/product-design/`.
- Each Codex project can have its own design language, UI conventions, UX decisions, and reference screenshots. Do not reuse or overwrite another project's Product Design context unless the user explicitly asks.

## GitHub Workflow

- The `main` branch is protected on GitHub.
- Do not push project changes directly to `main`.
- Create a focused `codex/<description>` branch, commit only the intended changes, push the branch, and open a pull request targeting `main`.
- Wait for all required CI checks to pass, then squash-merge the pull request. Merged branches are deleted automatically.
- Keep generated files and unrelated working-tree changes out of commits.
