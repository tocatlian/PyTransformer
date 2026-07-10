# SPDX-License-Identifier: MIT
# Copyright (c) 2023-2026 Paul Tocatlian

"""Audio extraction and transcription helpers for PyTransformer MP4 commands."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path
from typing import Any

from pytransformer.core.common import ScriptError

sr: Any | None
AudioFileClip: Any | None
SPEECH_RECOGNITION_IMPORT_ERROR: ImportError | None
MOVIEPY_IMPORT_ERROR: ImportError | None

try:
    sr = importlib.import_module("speech_recognition")
except ImportError as exc:
    sr = None
    SPEECH_RECOGNITION_IMPORT_ERROR = exc
else:
    SPEECH_RECOGNITION_IMPORT_ERROR = None

try:
    moviepy_editor = importlib.import_module("moviepy.editor")
except ImportError as first_import_error:
    try:
        moviepy_module = importlib.import_module("moviepy")
    except ImportError:
        AudioFileClip = None
        MOVIEPY_IMPORT_ERROR = first_import_error
    else:
        AudioFileClip = moviepy_module.AudioFileClip
        MOVIEPY_IMPORT_ERROR = None
else:
    AudioFileClip = moviepy_editor.AudioFileClip
    MOVIEPY_IMPORT_ERROR = None


def require_transcription_dependencies() -> None:
    """Raise a clear error when MP4 transcription dependencies are missing."""
    if MOVIEPY_IMPORT_ERROR is not None:
        raise ScriptError("moviepy is required. Install it with: pip install moviepy")
    if SPEECH_RECOGNITION_IMPORT_ERROR is not None:
        raise ScriptError("SpeechRecognition is required. Install it with: pip install SpeechRecognition")


def extract_wav(mp4_path: Path, wav_path: Path) -> None:
    """Extract MP4 audio into a temporary WAV file for speech recognition."""
    audio_clip_cls = AudioFileClip
    if audio_clip_cls is None:
        raise ScriptError("moviepy is required. Install it with: pip install moviepy")

    clip: Any | None = None
    try:
        try:
            clip = audio_clip_cls(str(mp4_path))
            clip.write_audiofile(str(wav_path), codec="pcm_s16le", logger=None)
        except Exception as exc:
            raise ScriptError(f"Could not extract audio from '{mp4_path}': {exc}") from exc
    finally:
        if clip is not None:
            clip.close()


def transcribe_wav(wav_path: Path, *, language: str) -> str:
    """Transcribe a WAV file with Google Web Speech API."""
    recognition_module = sr
    if recognition_module is None:
        raise ScriptError("SpeechRecognition is required. Install it with: pip install SpeechRecognition")

    recognizer = recognition_module.Recognizer()
    try:
        with recognition_module.AudioFile(str(wav_path)) as source:
            audio_data = recognizer.record(source)
    except Exception as exc:
        raise ScriptError(f"Could not read extracted audio '{wav_path}': {exc}") from exc

    try:
        return recognizer.recognize_google(audio_data, language=language)
    except recognition_module.UnknownValueError:
        return "Google Speech Recognition could not understand the audio."
    except recognition_module.RequestError as exc:
        raise ScriptError(f"Google Speech Recognition request failed: {exc}") from exc
    except Exception as exc:
        raise ScriptError(f"Google Speech Recognition failed: {exc}") from exc


def transcribe_mp4_to_text(mp4_path: Path, *, language: str) -> str:
    """Extract and transcribe MP4 audio, cleaning up temporary files automatically."""
    require_transcription_dependencies()
    with tempfile.TemporaryDirectory(prefix="pyt-audio-") as temp_dir:
        wav_path = Path(temp_dir) / f"{mp4_path.stem}.wav"
        extract_wav(mp4_path, wav_path)
        return transcribe_wav(wav_path, language=language)
