# -*- coding: utf-8 -*-
"""
Speech-edge clipping utilities.

This module defines the public API surface for trimming audio "edges" (leading/trailing)
around known speech start/stop timestamps. The actual trimming logic is intentionally
not implemented yet; the goal is to provide a stable interface that can be wired into
the export pipeline without requiring future caller changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

Seconds = float


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


def clip_speech_edges(
    *,
    start_time: Seconds,
    end_time: Seconds,
    trim_ms_start: int = 0,
    trim_ms_end: int = 0,
) -> Tuple[Seconds, Seconds]:
    """
    Compute adjusted clip boundaries by trimming a fixed amount at both speech edges.

    This function is the single, reusable entrypoint for speech-edge trimming. A future
    implementation will apply ms-based trims to `start_time` and `end_time` and return
    a normalized (start, end) tuple suitable for downstream clipping (e.g., FFmpeg).

    Args:
        start_time: Speech (or clip) start timestamp in seconds.
        end_time: Speech (or clip) end timestamp in seconds.
        trim_ms_start: Milliseconds to trim from the beginning (>= 0).
        trim_ms_end: Milliseconds to trim from the end (>= 0).

    Returns:
        A `(new_start_time, new_end_time)` tuple in seconds.

    Raises:
        NotImplementedError: Always, until speech-edge trimming is implemented.
    """

    raise NotImplementedError("Speech-edge clipping is not implemented yet.")

