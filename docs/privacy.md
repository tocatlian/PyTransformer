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
