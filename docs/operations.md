# Operations

This page owns deployment, verification, cleanup, and retention procedures. [AGENTS.md](../AGENTS.md) owns Codex authorization constraints. [CONTRIBUTING.md](../CONTRIBUTING.md) owns contribution and release validation.

## Deployment Scope

The repository's configured deployment is static HTML documentation through GitHub Pages. `.github/workflows/pages.yml` builds with `scripts/build_docs.py`, uploads `docs/html/`, and deploys to the `github-pages` environment. It runs on matching documentation changes pushed to `main` and supports manual workflow dispatch.

The public documentation address recorded by the archived deployment audit is [PyTransformer on GitHub Pages](https://tocatlian.github.io/PyTransformer/). Confirm the current Pages configuration before publishing or reconciling deployment. No package-registry publication workflow or application service deployment is configured in this repository. Do not infer a package publication procedure from the documentation workflow.

The Python CI workflow rebuilds HTML before `make validate`, so its documentation checks use the proposed Markdown and generator changes. Generated HTML remains excluded from contribution commits under CONTRIBUTING. Local generated files can therefore differ from the tracked snapshots after a source-only documentation commit. Preserve those useful local outputs and report them as remaining generated changes rather than discarding them or claiming a clean working tree.

For authorized publication:

1. Complete the validation and release-readiness steps in CONTRIBUTING. Build and check the HTML locally.
2. Follow the authorized branch and pull request workflow. The Pages workflow publishes eligible merged documentation changes from `main`. Do not push directly to the protected branch.
3. Check the Pages workflow result, deployment status, and public URL. Do not equate a successful local build with successful publication.
4. Verify the affected public pages against the intended generated output. Capture the source revision, deployment identifier, verification time, and any differences in the task's evidence.

### Deployment Reconciliation

Read-only inspection uses the repository's GitHub tooling:

```bash
gh auth status
gh api repos/tocatlian/PyTransformer/pages
gh run list --repo tocatlian/PyTransformer --workflow pages.yml --limit 5
gh api 'repos/tocatlian/PyTransformer/deployments?environment=github-pages&per_page=5'
```

Use the deployment statuses endpoint to establish success. Compare the deployed source and generated site with the desired validated contents before deciding to publish. The archived cleanup audit found flattened local Git history, so different commit hashes alone did not imply different deployed content. If histories differ, compare source trees and public files by relative path, size, and SHA-256. A comparison must account for the full generated file inventory, including additions and removals. Recheck current deployment state if it changes during verification.

Past chat findings and local logs are historical evidence. Always establish today's release state before claiming deployment is current. Remote cleanup needs an explicit target, ownership evidence, and retention policy. None is currently defined for deleting Pages deployments or artifacts.

### Authenticated Tooling Recovery

Use the supported authenticated GitHub path first. Check `gh auth status`. If the intended account has a valid keyring login but the wrong account is active, select it with `gh auth switch`. If login is required, use `gh auth login --hostname github.com` and the supported browser authorization flow. Ask the user only for steps requiring their credentials, MFA, passkey, CAPTCHA, or another action the agent cannot perform. Do not print tokens or copy credentials into documentation or logs.

### macOS Development Tool Recovery

If `make` selects an Xcode installation whose license has not been accepted, check whether separately installed Command Line Tools can run the project's Make targets. Use a command-scoped selection rather than changing the system toolchain:

```bash
DEVELOPER_DIR=/Library/Developer/CommandLineTools make validate
```

This requires working Command Line Tools at that path. It does not accept the Xcode license or establish that Xcode-only tools and simulator operations are available. If neither toolchain can run the required gate, preserve the changes and request the missing user action before committing. Do not bypass validation or accept legal terms on the user's behalf.

## Local Cleanup

Inspect Git state and file ownership before cleanup. Ignored or untracked files are not automatically disposable. Preserve source files, original media, credentials, intentional working-tree edits, and useful current verification or recovery evidence.

`make clean` removes Python bytecode, caches, coverage output, tox environments, build output, and package metadata. Its recursive `find . -name '*.pyc' -delete` also reaches nested virtual environments. Inspect the target list and repository contents before running it. Use an exact list of verified disposable paths when broad cleanup would affect an environment or evidence that should be retained.

- Retain tracked generated HTML paired with Markdown sources. Regenerate it through the documentation builder instead of deleting it as an orphan.
- Regenerate caches and package metadata when needed. Removing editable-install metadata may require reinstalling the development package.
- Treat temporary backups and command output as possible user data until ownership and disposability are established.
- Keep cleanup within the repository unless the user specifically authorizes another location or remote target.
- Record what was removed, why it was disposable, and what validation followed. A cleanup task does not by itself authorize Git synchronization under AGENTS.md.

### Disk Space Maintenance

Measure before selecting cleanup targets with `df -h .`, `du -k -d 2 .`, and `git count-objects -vH`. Check branch history and all refs before considering Git changes. The 2026-10-03 inspection found that local branch history was already flattened to one commit and the entire project occupied about 2 MiB. Further history rewriting would offer negligible relief and could damage recovery context. Preserve Git metadata and intentional working-tree changes.

Remove verified disposable Python bytecode, tool caches, obsolete coverage output, and empty build directories. For numbered copies under `docs/html/`, compare against the canonical generated files and Markdown sources first. Identical copies or confirmed obsolete generated versions can be removed when they are untracked and have no consumers. Keep canonical HTML and regenerate it through `make docs` after Markdown changes.

The old `project-cleanup*.log` files and coverage output were removed during this inspection after confirming the earlier cleanup had completed successfully and its lasting procedures were already documented. This is a specific obsolescence assessment, not an automatic expiration policy for future logs or backups. No backup archives or local virtual environments were present in the project.

Use `PYTHONDONTWRITEBYTECODE=1` for documentation checks and ordinary test runs when avoiding new bytecode is useful. Install only the dependency groups needed for current work, following [the README setup guidance](../README.md#dependency-groups). Inspect shared package caches, simulator data, other worktrees, and backups separately when project-local savings are too small. Deleting outside this repository requires explicit authorization for those locations. Shared caches can be downloaded again, while simulator and worktree data may contain unique work and need their own recovery checks.

#### Authorized Shared Storage Cleanup

The user explicitly extended the 2026-10-03 cleanup to the identified shared storage locations. That run removed about 612 MiB of remaining allocated cache and log files. Larger caches had already disappeared between inspections and were not counted as removals by this run. Reinspect current sizes before each cleanup rather than reusing an earlier estimate.

For an authorized shared cleanup, inspect running processes and open files with `ps` and `lsof`. Preserve active installations under `~/.npm/_npx`, Playwright browser installations with open files, Playwright session records, and open Codex cache journals. Remove only verified disposable closed cache files and unused hook environments. Prefer the hook tool's supported cache cleaner when available. If all hook environments have been removed manually, verify that every generated cache-registry entry is orphaned and remove the unused registry too, so future hooks do not reuse missing paths. Keep Codex application support data, authentication, chats, and settings outside cache deletion plans.

For shut-down simulators, distinguish disposable `data/Library/Caches` and diagnostic logs from installed apps, app containers, documents, photos, device definitions, and downloaded system assets. Preserve the latter during cache-only cleanup. Simulator `data/Library/Logs` can be a symlink outside the device directory. Never follow it during a recursive sweep without separately reviewing and authorizing its resolved target. Compare protected files before and after cleanup, and skip candidates that change during inspection.

Use supported `xcrun simctl` operations for a full simulator reset or deletion after authorization to discard its app data and photos. If Xcode refuses because its license has not been accepted, the user must review and accept the license in Xcode or with `sudo xcodebuild -license`. Do not accept legal terms on the user's behalf or replace a blocked reset with raw device-directory deletion. Cache-file removal does not verify simulator runtime behavior.

## Verification Evidence And Retention

The prior cleanup used ignored `project-cleanup*.log` files and `.coverage` for local evidence. Those files can explain a completed operation but do not own durable requirements. Promote any lasting discovery into this page, architecture, the command guide, or the decision log before deleting its only evidence.

Retain useful evidence while it supports current verification, unresolved failures, or recovery. There is no automatic age-based retention policy. Future cleanup should assess each record before removal. Do not commit private paths, file contents, metadata, transcripts, credentials, or raw diagnostic exports. Use the [privacy guide](privacy.md) for data handling and [SECURITY.md](../SECURITY.md) for suspected vulnerabilities.

## Archived Chat Removal

When the user requests deletion of project archives, use the installed Codex CLI's `codex delete <chat-id>` command. Check `codex delete --help` for the available options. For an explicitly authorized deletion by UUID, `codex delete --force <chat-id>` deletes without an interactive prompt.

Before deleting, enumerate every page of archived chats and confirm project association from the working directory or project identity. Include verified project worktrees when applicable. Preserve lasting knowledge using [the documentation ownership map](knowledge.md) before removing its only conversational source. Delete only the matching archived UUIDs, then enumerate the archives again to verify that no project matches remain. Report the deleted chat titles and any failures.

This procedure does not authorize automatic deletion. Current chats and archives belonging to other projects remain outside a project archive deletion request.
