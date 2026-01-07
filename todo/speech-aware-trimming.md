# Plan: Implement Speech-Aware Auto-Trimming

## Problem
The current auto-trimming settings in the Shift+P modal are misleading:
- **UI says**: "Dead Space Trimming" / "Trim X milliseconds"
- **Implementation does**: Blindly trims fixed milliseconds from boundaries
- **User wants**: Intelligent trimming using WhisperX speech timestamps with configurable max silence buffer

## Solution
Implement speech-aware trimming that uses word-level timestamps from WhisperX transcripts to find where speech actually starts/ends, then trim excess silence while preserving a configurable buffer.

**Behavior with 1000ms (1 second) buffer:**
- Speech starts at 0.5s → keep all 0.5s (silence < buffer)
- Speech starts at 2.0s → trim to start at 1.0s (1s before speech)
- Speech ends at 8.5s, clip ends at 10s → trim to end at 9.5s (1s after speech)

---

## Files to Modify

### 1. `src/speech_edge_clip.py` - Core Logic
Replace the NotImplementedError scaffold with actual implementation:

- `load_transcript_segments(transcript_path)` - Load WhisperX JSON
- `find_speech_boundaries(segments, clip_start, clip_end)` - Find first/last word timestamps
- `compute_speech_aware_boundaries(...)` - Apply max silence buffer logic

### 2. `src/video_exporter.py` - Integration
In `export_full_video()` (line ~274):
- Add `transcript_path: Optional[str] = None` parameter
- Replace fixed `-ss`/`-t` FFmpeg args with speech-aware calculation
- Fallback to no trimming if transcript unavailable

### 3. `src/core/job_runner.py` - Pass Transcript
In `_step_export_shorts()` (line ~603):
- Pass `transcript_path=str(transcript_path)` to `export_full_video()`

### 4. `src/config/settings_schema.py` - Fix Settings (lines 373-392)
```python
# Change:
default=0  →  default=1000
placeholder="0"  →  placeholder="1000"
label="Trim from start (ms):"  →  label="Max silence at start (ms):"
help_text="Milliseconds of dead space to trim..."  →  help_text="Maximum silence before speech. Trims if exceeded (0=disabled)."
```

### 5. `config/app_settings.json` - Update Defaults
```json
"trim_ms_start": 1000,
"trim_ms_end": 1000,
```

### 6. `src/tui/app.py` - Fix UI Labels (lines 208-218)
```python
# Change:
"Dead Space Trimming"  →  "Speech Boundary Trimming"
"Trim silence/dead space..."  →  "Trim excess silence using speech detection"
"Trim from start (milliseconds):"  →  "Max silence at start (ms):"
"Trim from end (milliseconds):"  →  "Max silence at end (ms):"
placeholder="0"  →  placeholder="1000"
value=False (checkbox)  →  value=True (enable by default)
```

---

## Implementation Order

1. **speech_edge_clip.py** - Implement core functions
2. **video_exporter.py** - Add transcript_path param, use speech-aware logic
3. **job_runner.py** - Pass transcript_path
4. **settings_schema.py** - Update defaults and labels
5. **app_settings.json** - Update default values
6. **app.py** - Update UI labels

---

## Edge Cases Handled

| Case | Behavior |
|------|----------|
| No transcript file | No trimming (preserve original) |
| Empty segments array | No trimming |
| No words in segments | No trimming |
| No speech in clip range | Keep original boundaries |
| Computed duration ≤ 0 | Fallback to original |
| trim_ms = 0 | Disabled (no trimming) |
