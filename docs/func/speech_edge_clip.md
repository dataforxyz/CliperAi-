# Speech Edge Clip

**Module:** `src/speech_edge_clip.py`

## Function: `clip_speech_edges`

**Signature:**
`clip_speech_edges(*, start_time: float, end_time: float, trim_ms_start: int = 0, trim_ms_end: int = 0) -> tuple[float, float]`

### Purpose

Define the reusable API for trimming audio (or clip) boundaries at known speech start/stop timestamps by a fixed number of milliseconds at the beginning and end.

This is **scaffolding only**: the function currently raises `NotImplementedError`. The signature and behavior rules are documented now so the export pipeline can be wired to accept the parameters without requiring future caller changes.

### Parameters

- `start_time: float`
  - Speech (or clip) start timestamp in **seconds**.
- `end_time: float`
  - Speech (or clip) end timestamp in **seconds**.
- `trim_ms_start: int`
  - Milliseconds to trim from the start edge.
- `trim_ms_end: int`
  - Milliseconds to trim from the end edge.

### Expected Behavior (when implemented)

- Convert milliseconds to seconds as `trim_s = trim_ms / 1000.0`.
- Apply trims to compute:
  - `new_start = start_time + max(trim_ms_start, 0) / 1000.0`
  - `new_end = end_time - max(trim_ms_end, 0) / 1000.0`
- Return `(new_start, new_end)` in seconds.

### Edge-Case Rules

- **Negative trims**: `trim_ms_start < 0` and/or `trim_ms_end < 0` are treated as `0` (trims never expand the window).
- **Bounds**: the returned `(new_start, new_end)` must not extend outside the original `(start_time, end_time)` window (i.e., trims only move inward).
- **Overflow**: if `trim_ms_start + trim_ms_end` is larger than the available window duration, the result collapses to a zero-length window by setting `new_start == new_end`.
- **Invalid or inverted inputs**: if `start_time >= end_time` after normalization, the result collapses to a zero-length window (`new_start == new_end`).

