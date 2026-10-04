# Privacy Guide

PyTransformer works with files that often contain sensitive information. Treat generated outputs with the same care as source files.

## JPEG Metadata

JPEG metadata may include:

- GPS coordinates.
- Camera make, model, and serial-like identifiers.
- Capture timestamps.
- Editing software details.
- Captions, comments, and other descriptive fields.

Recommended workflow:

1. Inspect with `pyt-jpeg-show-metadata`.
2. Create cleaned copies with `pyt-jpeg-strip-metadata`.
3. Review the cleaned output before publishing.

## MP4 Transcription

MP4 transcription commands use Google Web Speech API through the `SpeechRecognition` package.

Do not use transcription commands on sensitive audio unless sending audio to that service is acceptable for your use case.

## PDF And Text Outputs

PDF commands may extract or render sensitive content into new files:

- Extracted `.txt` files.
- Extraction logs.
- Rendered JPEG pages.

Text concatenation can combine separate files into a single artifact that may be easier to share accidentally.

## Working With Untrusted Files

Avoid running file-processing commands on untrusted files in privileged environments. Use a disposable folder or sandbox when evaluating unknown inputs.

## Development Fixtures And Diagnostics

Use small synthetic fixtures for tests, examples, smoke checks, and bug reports. Do not include private PDFs, media, transcripts, logs, local paths, or JPEG metadata in committed examples or fixtures. Review diagnostics for sensitive content before sharing them.

Generated media, extraction logs, cleanup inventories, and validation reports can contain source contents or private paths. Local retention and cleanup belong in [Operations](operations.md#verification-evidence-and-retention). Suspected vulnerabilities should follow [SECURITY.md](../SECURITY.md).
