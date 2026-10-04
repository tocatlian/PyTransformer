# Security Policy

## Supported Versions

PyTransformer uses semantic versioning. Security fixes are handled on the latest public release and the default development branch.

## Reporting a Vulnerability

Please report security concerns privately before opening a public issue.

Preferred contact:

- Paul Tocatlian: <https://www.tocatlian.com>

Include:

- A clear description of the issue.
- The affected command or module.
- Steps to reproduce when safe to share.
- The expected and actual behavior.
- Any relevant sample files, with private metadata removed.

## Security Scope

PyTransformer processes local user-provided files and can create derived artifacts such as extracted text, transcripts, JPEG copies, rendered pages, and chunked videos.

The [privacy guide](docs/privacy.md) owns external-service disclosure, sensitive output handling, and precautions for untrusted files. The [product requirements](docs/requirements.md#file-safety) and [command guide](docs/commands.md) own file safety behavior and command-specific controls.

## Disclosure

If a vulnerability is confirmed, the project will aim to:

1. Reproduce and understand the issue.
2. Prepare a fix or mitigation.
3. Document the behavior change.
4. Credit the reporter if desired.
5. Publish the fix with release notes.
