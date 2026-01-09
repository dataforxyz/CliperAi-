# Speech Edge Clip

**Module:** `src/speech_edge_clip.py`

## Overview

Speech-aware clipping utilities for trimming audio edges (leading/trailing silence) around speech boundaries using WhisperX word timestamps.

## Functions

### `compute_speech_aware_boundaries`

**Signature:**
```python
compute_speech_aware_boundaries(
    *,
    transcript_path: str,
    clip_start: float,
    clip_end: float,
    trim_ms_start: int = 0,
    trim_ms_end: int = 0,
) -> tuple[float, float]
```

#### Purpose

Trim excess silence from a clip window using WhisperX word timestamps. This is the main function used by the export pipeline.

#### Parameters

- `transcript_path: str` - Path to WhisperX transcript JSON file
- `clip_start: float` - Clip start timestamp in seconds
- `clip_end: float` - Clip end timestamp in seconds
- `trim_ms_start: int` - Maximum silence buffer to keep before speech (ms)
- `trim_ms_end: int` - Maximum silence buffer to keep after speech (ms)

#### Behavior

- `trim_ms_start` / `trim_ms_end` represent the **maximum** silence to keep, not the amount to remove
- If leading/trailing silence is less than the buffer, that side is left unchanged
- A value of `0` disables trimming for that side

#### Examples

With `trim_ms_start=1000` (1 second buffer):
- Speech starts at 0.5s -> keep all 0.5s (silence < buffer)
- Speech starts at 2.0s -> trim to start at 1.0s (1s before speech)
- Speech ends at 8.5s, clip ends at 10s -> trim to end at 9.5s (1s after speech)

---

### `clip_speech_edges`

**Signature:**
```python
clip_speech_edges(
    *,
    start_time: float,
    end_time: float,
    trim_ms_start: int = 0,
    trim_ms_end: int = 0,
) -> tuple[float, float]
```

#### Purpose

Simple fixed-trim utility that removes a fixed amount from clip boundaries. Does not use transcript data.

#### Parameters

- `start_time: float` - Clip start timestamp in seconds
- `end_time: float` - Clip end timestamp in seconds
- `trim_ms_start: int` - Milliseconds to trim from the beginning
- `trim_ms_end: int` - Milliseconds to trim from the end

---

### `load_transcript_segments`

**Signature:**
```python
load_transcript_segments(transcript_path: str) -> tuple[list, list]
```

#### Purpose

Load a WhisperX transcript JSON and return `(segments, word_segments)`.

---

### `find_speech_boundaries`

**Signature:**
```python
find_speech_boundaries(
    segments: list,
    clip_start: float,
    clip_end: float,
    *,
    word_segments: list | None = None,
) -> tuple[float, float] | None
```

#### Purpose

Find the first and last speech timestamps inside a clip window using word-level timestamps.

---

## Edge Cases Handled

| Case | Behavior |
|------|----------|
| No transcript file | No trimming (preserve original) |
| Empty segments array | No trimming |
| No words in segments | No trimming |
| No speech in clip range | Keep original boundaries |
| Computed duration <= 0 | Fallback to original |
| trim_ms = 0 | Disabled (no trimming) |

## Integration

Used by `src/video_exporter.py` in `export_full_video()` to apply speech-aware trimming during clip export.
