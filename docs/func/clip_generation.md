# Clip Generation

**Module:** `src/clips_generator.py`

### Class: `ClipsGenerator`

**Function:** `__init__(min_clip_duration: int = 30, max_clip_duration: int = 90)`
- **Purpose:** Initialize clip generator with ClipsAI
- **Inputs:**
  - `min_clip_duration: int` (minimum seconds per clip)
  - `max_clip_duration: int` (maximum seconds per clip)
- **Outputs:** None (initializes ClipsAI ClipFinder)

**Function:** `generate_clips(transcript_path: str, min_clips: int = 3, max_clips: int = 10) -> Optional[List[Dict]]`
- **Purpose:** Detects clip boundaries using AI topic change detection
- **Inputs:**
  - `transcript_path: str` (path to WhisperX transcript JSON)
  - `min_clips: int` (minimum clips expected)
  - `max_clips: int` (maximum clips to generate)
- **Outputs:**
  ```python
  [
    {
      "clip_id": 1,
      "start_time": 0.0,      # seconds
      "end_time": 45.5,       # seconds
      "duration": 45.5,       # seconds
      "text_preview": "First words...",
      "full_text": "Complete transcript text for this clip",
      "method": "clipsai"  # or "fixed_time" if fallback
    },
    ...
  ]
  ```
- **Returns:** `None` if error
- **Side Effects:** Uses ClipsAI to analyze transcript

**Function:** `save_clips_metadata(clips: List[Dict], video_id: str, output_path: Optional[str] = None) -> Optional[str]`
- **Purpose:** Saves clip metadata to JSON file
- **Inputs:**
  - `clips: List[Dict]` (clips from `generate_clips()`)
  - `video_id: str`
  - `output_path: Optional[str]` (default: `temp/{video_id}_clips.json`)
- **Outputs:** `str` (path to saved JSON) or `None` if error
- **Output Format:**
  ```json
  {
    "video_id": "video_abc123",
    "num_clips": 10,
    "min_clip_duration": 30,
    "max_clip_duration": 90,
    "clips": [...]
  }
  ```

**Function:** `load_clips_metadata(metadata_path: str) -> Optional[Dict]`
- **Purpose:** Loads previously saved clip metadata
- **Inputs:** `metadata_path: str`
- **Outputs:** `Dict` (metadata) or `None` if error
