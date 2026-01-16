"""
Speech-edge clipping utilities.

This module defines the public API surface for trimming audio "edges" (leading/trailing)
around known speech start/stop timestamps. It supports both a fixed-trim utility
(`clip_speech_edges`) and speech-aware trimming driven by WhisperX word timestamps
(`compute_speech_aware_boundaries`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.utils.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable

Seconds = float

logger = get_logger(__name__)


@dataclass(frozen=True)
class SpeechEdgeTrimConfig:
    """
    Configuration for trimming audio at speech boundaries.

    Attributes:
        trim_ms_start: Milliseconds to trim from the start of the speech window.
        trim_ms_end: Milliseconds to trim from the end of the speech window.
    """

    trim_ms_start: int = 0
    trim_ms_end: int = 0


def load_transcript_segments(
    transcript_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Load a WhisperX transcript JSON and return `(segments, word_segments)`.

    WhisperX timestamps are expected to be absolute seconds from the original media.
    """
    transcript_file = Path(str(transcript_path))
    if not transcript_file.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_file}")

    with open(transcript_file, encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments") or []
    word_segments = data.get("word_segments") or []
    if not isinstance(segments, list):
        segments = []
    if not isinstance(word_segments, list):
        word_segments = []
    return segments, word_segments


def _iter_words(
    segments: list[dict[str, Any]], word_segments: list[dict[str, Any]] | None = None
) -> Iterable[dict[str, Any]]:
    for seg in segments:
        words = seg.get("words") if isinstance(seg, dict) else None
        if isinstance(words, list):
            for w in words:
                if isinstance(w, dict):
                    yield w
    if isinstance(word_segments, list):
        for w in word_segments:
            if isinstance(w, dict):
                yield w


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def find_speech_boundaries(
    segments: list[dict[str, Any]],
    clip_start: Seconds,
    clip_end: Seconds,
    *,
    word_segments: list[dict[str, Any]] | None = None,
) -> tuple[Seconds, Seconds] | None:
    """
    Find the first and last speech timestamps inside a clip window.

    Returns absolute (original-timeline) seconds.
    """
    if clip_end <= clip_start:
        return None

    first: float | None = None
    last: float | None = None

    for word in _iter_words(segments, word_segments):
        word_start = _coerce_float(word.get("start"))
        word_end = _coerce_float(word.get("end"))
        if word_start is None or word_end is None:
            continue
        if word_end <= word_start:
            continue

        # Skip words that do not overlap the window.
        if word_end <= clip_start or word_start >= clip_end:
            continue

        # If speech is already happening at the boundary (word overlaps it),
        # treat the boundary as the speech edge to avoid trimming into speech.
        effective_start = clip_start if word_start < clip_start else word_start
        effective_end = clip_end if word_end > clip_end else word_end

        first = effective_start if first is None else min(first, effective_start)
        last = effective_end if last is None else max(last, effective_end)

    if first is None or last is None:
        return None
    if last <= first:
        return None
    return float(first), float(last)


def compute_speech_aware_boundaries(
    *,
    transcript_path: str,
    clip_start: Seconds,
    clip_end: Seconds,
    trim_ms_start: int = 0,
    trim_ms_end: int = 0,
) -> tuple[Seconds, Seconds]:
    """
    Trim excess silence from a clip window using WhisperX word timestamps.

    `trim_ms_start` / `trim_ms_end` represent the maximum silence buffer to keep before/after speech.
    If leading/trailing silence is less than the buffer, that side is left unchanged.
    A value of `0` disables trimming for that side.
    """
    if clip_end <= clip_start:
        return clip_start, clip_end

    max_silence_start = max(0, int(trim_ms_start)) / 1000.0
    max_silence_end = max(0, int(trim_ms_end)) / 1000.0
    if max_silence_start == 0 and max_silence_end == 0:
        return clip_start, clip_end

    try:
        segments, word_segments = load_transcript_segments(transcript_path)
    except Exception as e:
        logger.debug(f"Speech-aware trimming disabled (failed to load transcript): {e}")
        return clip_start, clip_end

    speech = find_speech_boundaries(
        segments, clip_start, clip_end, word_segments=word_segments
    )
    if not speech:
        return clip_start, clip_end

    speech_start, speech_end = speech
    new_start = clip_start
    new_end = clip_end

    if max_silence_start > 0:
        leading_silence = speech_start - clip_start
        if leading_silence > max_silence_start:
            new_start = speech_start - max_silence_start

    if max_silence_end > 0:
        trailing_silence = clip_end - speech_end
        if trailing_silence > max_silence_end:
            new_end = speech_end + max_silence_end

    new_start = max(clip_start, min(new_start, clip_end))
    new_end = min(clip_end, max(new_end, clip_start))
    if new_end <= new_start:
        return clip_start, clip_end

    return float(new_start), float(new_end)


def clip_speech_edges(
    *,
    start_time: Seconds,
    end_time: Seconds,
    trim_ms_start: int = 0,
    trim_ms_end: int = 0,
) -> tuple[Seconds, Seconds]:
    """
    Compute adjusted clip boundaries by trimming a fixed amount at both speech edges.

    This function applies ms-based trims to `start_time` and `end_time` and returns
    a normalized (start, end) tuple suitable for downstream clipping (e.g., FFmpeg).

    Args:
        start_time: Speech (or clip) start timestamp in seconds.
        end_time: Speech (or clip) end timestamp in seconds.
        trim_ms_start: Milliseconds to trim from the beginning (>= 0).
        trim_ms_end: Milliseconds to trim from the end (>= 0).

    Returns:
        A `(new_start_time, new_end_time)` tuple in seconds.

    Notes:
        This is the fixed-trim utility. Speech-aware trimming is implemented in
        `compute_speech_aware_boundaries()`.
    """
    trim_start = max(0, int(trim_ms_start)) / 1000.0
    trim_end = max(0, int(trim_ms_end)) / 1000.0

    if end_time <= start_time:
        return float(start_time), float(start_time)

    new_start = start_time + trim_start
    new_end = end_time - trim_end

    new_start = max(start_time, min(new_start, end_time))
    new_end = max(start_time, min(new_end, end_time))
    if new_end < new_start:
        return float(new_start), float(new_start)

    return float(new_start), float(new_end)
