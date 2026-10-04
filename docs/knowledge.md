# Durable Project Knowledge

Archived chats are temporary working context. A future contributor or Codex session must be able to understand lasting project knowledge from this repository. This page owns the documentation map and maintenance process.

## Authoritative Locations

| Information | Authoritative source | Boundary |
| --- | --- | --- |
| Product scope and shared behavior requirements | [Product requirements](requirements.md) | Command-specific arguments, defaults, outputs, and exceptions belong in the command guide. |
| Command behavior | [Command guide](commands.md) | Owns each command's public contract and examples. |
| Codex instructions and authorization constraints | [AGENTS.md](../AGENTS.md) | Owns agent-specific rules, including Git authorization and project-scoped design context. |
| Development conventions and testing expectations | [CONTRIBUTING.md](../CONTRIBUTING.md) | Owns naming, CLI standards, validation, contribution workflow, and release readiness. |
| Current architecture and implementation boundaries | [Architecture](architecture.md) | Owns package responsibilities, optional import strategy, and shared output finalization. |
| Important decisions and architectural rationale | [Decision log and lessons learned](lessons-learned.md) | Owns why a choice was made, its consequences, and supersession history. Current rules stay in their topic owners. |
| Installation, environment, and dependency setup | [README installation and dependency groups](../README.md#installation) | Owns supported Python and runtime setup. CONTRIBUTING owns the developer setup. Command-specific dependency needs stay in the command guide. |
| Dependency versions, console entry points, and tool configuration | `pyproject.toml` | Executable configuration owns exact values. Docs explain purpose and usage without maintaining competing version lists. |
| Validation and automation execution | `Makefile`, `tox.ini`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml` | Each file owns its respective execution configuration. CONTRIBUTING owns human testing expectations. |
| Deployment and operational procedures | [Operations](operations.md) | Owns publishing, deployment verification, cleanup, retention, and tooling recovery. `.github/workflows/pages.yml` owns deployment execution. |
| Privacy and data handling | [Privacy guide](privacy.md) | Owns external service disclosure, sensitive outputs, and private fixture handling. |
| Vulnerability reporting and disclosure | [SECURITY.md](../SECURITY.md) | Owns security reporting, supported versions, and disclosure. References privacy guidance. |
| Support and collaboration | [SUPPORT.md](../SUPPORT.md), [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | Own issue reporting and community conduct respectively. |
| Release history | [CHANGELOG.md](../CHANGELOG.md) | Records historical changes, not current requirements. |
| Documentation generation | [Architecture documentation build](architecture.md#documentation-build) | Owns the build description. `scripts/build_docs.py` owns rendering and page registration. HTML is derived output. |

If Product Design work is introduced, its project context belongs at `docs/product-design/user-context.md` and assets under `docs/product-design/assets/`, as directed by AGENTS.md. That document does not yet exist. Create it only when there is actual design context to preserve.

## Maintaining Knowledge

1. Identify the lasting requirement, decision, configuration, or procedure before closing the task. Discard transient debugging narrative and one-time command output unless it explains a lasting choice.
2. Read the existing owner above and update it. Create a new owner only when an existing topic cannot reasonably contain the information, then update this map.
3. Keep the full definition in one place. Other pages should link to it. Short onboarding summaries and historical changelog entries may repeat context, but must defer to the current owner.
4. When a choice has meaningful tradeoffs, add a dated decision entry with status, context, rationale, consequences, and links to current requirements. Do not invent a historical decision date or turn an unaccepted proposal into a requirement.
5. When implementation invalidates documentation, revise both in the same task. Mark replaced decisions as superseded and link to the replacement. Remove stale normative text rather than asking future readers to reconcile versions.
6. Regenerate HTML with `make docs` and verify it with `make docs-check`. Follow CONTRIBUTING for the remaining validation required by the change.
7. Report which authoritative files changed and any unresolved knowledge gaps. Do not treat an archived conversation as an acceptance criterion or operating dependency.

The person or agent completing the change owns these updates. Documentation is part of completion, including decisions made during reviews and follow-up conversations.

## Conversation Review Scope

On 2026-10-03, the review covered the repository documentation, the current conversation, and both project chats found across all 467 archived Codex chat summaries available on the local host: "Clean up project deployment" and "Remove obsolete project files". Both chats were read through their available turns.

Their lasting deployment verification and cleanup guidance is now captured in [Operations](operations.md). Their Git authorization constraint was already present in AGENTS.md and has been preserved. One-time test counts, removed cache counts, approval attempts, and past deployment hashes are historical evidence, not current policy or proof of today's release state. Useful local verification logs may be retained under the Operations guidance.

The recent active-chat listing contained only this project's current chat. Older active chats outside that listing, other hosts, and unavailable or deleted conversations were not reviewed. Newly discovered lasting information should be promoted through the process above.
