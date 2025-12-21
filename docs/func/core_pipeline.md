# Core Pipeline Functions

### Main Entry Point
**File:** `cliper.py`

**Function:** `main()`
- **Purpose:** Main CLI loop orchestrating all operations
- **Inputs:** None (reads from CLI)
- **Outputs:** None (interactive menu)
- **Dependencies:** All modules below

**Function:** `escanear_videos() -> List[Dict[str, str]]`
- **Purpose:** Scans `downloads/` folder for MP4 videos
- **Inputs:** None
- **Outputs:** 
  ```python
  [
    {
      "filename": "video.mp4",
      "path": "downloads/video.mp4",
      "video_id": "video_abc123"
    }
  ]
  ```
