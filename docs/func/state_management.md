# State Management

**Module:** `src/utils/state_manager.py`

### Class: `StateManager`

**Function:** `__init__(state_file: str = "temp/project_state.json")`
- **Purpose:** Initialize state manager
- **Inputs:** `state_file: str` (optional)
- **Outputs:** None (loads existing state or creates new)

**Function:** `register_video(video_id: str, filename: str, content_type: str = "tutorial", preset: Dict = None) -> None`
- **Purpose:** Registers a new video in project state
- **Inputs:**
  - `video_id: str`
  - `filename: str`
  - `content_type: str` (optional: "podcast", "tutorial", "livestream", etc.)
  - `preset: Dict` (optional configuration preset)
- **Outputs:** None (updates state file)

**Function:** `mark_transcribed(video_id: str, transcription_path: str) -> None`
- **Purpose:** Marks video as transcribed
- **Inputs:**
  - `video_id: str`
  - `transcription_path: str`
- **Outputs:** None (updates state)

**Function:** `mark_clips_generated(video_id: str, clips: List[Dict], clips_metadata_path: Optional[str] = None) -> None`
- **Purpose:** Marks clips as generated
- **Inputs:**
  - `video_id: str`
  - `clips: List[Dict]` (clip data)
  - `clips_metadata_path: Optional[str]` (path to metadata JSON)
- **Outputs:** None (updates state)

**Function:** `mark_clips_exported(video_id: str, exported_paths: List[str], aspect_ratio: Optional[str] = None) -> None`
- **Purpose:** Marks clips as exported
- **Inputs:**
  - `video_id: str`
  - `exported_paths: List[str]` (list of exported file paths)
  - `aspect_ratio: Optional[str]` ("9:16", "1:1", etc.)
- **Outputs:** None (updates state)

**Function:** `get_video_state(video_id: str) -> Optional[Dict]`
- **Purpose:** Gets state for a specific video
- **Inputs:** `video_id: str`
- **Outputs:**
  ```python
  {
    "filename": str,
    "downloaded": bool,
    "transcribed": bool,
    "transcript_path": Optional[str],
    "clips_generated": bool,
    "clips": List[Dict],
    "clips_metadata_path": Optional[str],
    "clips_exported": bool,
    "exported_clips": List[str],
    "export_aspect_ratio": Optional[str],
    "content_type": str,
    "preset": Dict,
    "last_updated": str
  }
  ```

**Function:** `get_all_videos() -> Dict`
- **Purpose:** Gets all videos in project state
- **Inputs:** None
- **Outputs:** `Dict` (mapping video_id → video_state)

**Function:** `get_next_step(video_id: str) -> str`
- **Purpose:** Determines next pipeline step for video
- **Inputs:** `video_id: str`
- **Outputs:** `str` ("transcribe", "generate_clips", "export", "done", "unknown")

**Function:** `is_transcribed(video_id: str) -> bool`
- **Purpose:** Checks if a video has been transcribed
- **Inputs:** `video_id: str`
- **Outputs:** `bool` (True if video is transcribed)

**Function:** `clear_video_state(video_id: str) -> None`
- **Purpose:** Removes video state from project state (useful when deleting video)
- **Inputs:** `video_id: str`
- **Outputs:** None (updates state file)

### Helper Function

**Function:** `get_state_manager() -> StateManager`
- **Purpose:** Gets singleton StateManager instance
- **Inputs:** None
- **Outputs:** `StateManager` instance
