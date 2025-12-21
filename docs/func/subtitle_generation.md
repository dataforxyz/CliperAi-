# Subtitle Generation

**Module:** `src/subtitle_generator.py`

### Class: `SubtitleGenerator`

**Function:** `generate_srt_from_transcript(transcript_path: str, output_path: Optional[str] = None, max_chars_per_line: int = 42, max_duration: float = 5.0) -> Optional[str]`
- **Purpose:** Generates SRT file from full transcript
- **Inputs:**
  - `transcript_path: str` (WhisperX transcript JSON)
  - `output_path: Optional[str]` (default: same as transcript with .srt)
  - `max_chars_per_line: int` (characters per subtitle line)
  - `max_duration: float` (max seconds per subtitle)
- **Outputs:** `str` (path to SRT file) or `None` if error

**Function:** `generate_srt_for_clip(transcript_path: str, clip_start: float, clip_end: float, output_path: str, max_chars_per_line: int = 42, max_duration: float = 5.0) -> Optional[str]`
- **Purpose:** Generates SRT file for a specific clip (timestamps adjusted)
- **Inputs:**
  - `transcript_path: str` (full transcript JSON)
  - `clip_start: float` (clip start time in seconds)
  - `clip_end: float` (clip end time in seconds)
  - `output_path: str` (output SRT path)
  - `max_chars_per_line: int`
  - `max_duration: float`
- **Outputs:** `str` (path to SRT file) or `None` if error
