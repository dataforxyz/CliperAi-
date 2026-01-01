# Video Export

**Module:** `src/video_exporter.py`

### Class: `VideoExporter`

**Function:** `__init__(output_dir: str = "output")`
- **Purpose:** Initialize video exporter
- **Inputs:** `output_dir: str` (optional, default: "output")
- **Outputs:** None (creates output directory)

**Function:** `export_clips(video_path: str, clips: List[Dict], aspect_ratio: Optional[str] = None, video_name: Optional[str] = None, add_subtitles: bool = False, transcript_path: Optional[str] = None, subtitle_style: str = "default", organize_by_style: bool = False, clip_styles: Optional[Dict[int, str]] = None, enable_face_tracking: bool = False, face_tracking_strategy: str = "keep_in_frame", face_tracking_sample_rate: int = 3, add_logo: bool = False, logo_path: Optional[str] = "assets/logo.png", logo_position: str = "top-right", logo_scale: float = 0.1, trim_ms_start: int = 0, trim_ms_end: int = 0) -> List[str]`
- **Purpose:** Exports clips to video files with optional processing (face tracking, subtitles, logos)
- **Inputs:**
  - `video_path: str` (path to source video)
  - `clips: List[Dict]` (from `ClipsGenerator.generate_clips()`)
  - `aspect_ratio: Optional[str]` ("9:16", "1:1", "16:9", or None for original)
  - `video_name: Optional[str]` (base name for output files)
  - `add_subtitles: bool` (burn subtitles into video)
  - `transcript_path: Optional[str]` (required if `add_subtitles=True`)
  - `subtitle_style: str` ("default", "bold", "yellow", "tiktok", "small", "tiny")
  - `organize_by_style: bool` (create subfolders: viral/educational/storytelling)
  - `clip_styles: Optional[Dict[int, str]]` (mapping clip_id → style)
  - **Face Tracking Parameters:**
    - `enable_face_tracking: bool` (enable dynamic face tracking for aspect ratio conversion)
      - **Only works with `aspect_ratio="9:16"`** (vertical format)
      - Automatically keeps faces in frame when converting 16:9 → 9:16
      - Uses MediaPipe for face detection
    - `face_tracking_strategy: str` 
      - `"keep_in_frame"` (default): Minimal crop movement, professional look
      - `"centered"`: Always centers face, more movement
    - `face_tracking_sample_rate: int` (process every N frames, default: 3 for 3x speedup)
  - **Logo Parameters:**
    - `add_logo: bool` (overlay logo on video)
    - `logo_path: Optional[str]` (path to logo image, default: "assets/logo.png")
    - `logo_position: str` ("top-right", "top-left", "bottom-right", "bottom-left")
    - `logo_scale: float` (0.1 = 10% of video height)
  - `trim_ms_start: int` (speech-edge trim in ms at clip start; scaffold only, not applied yet)
  - `trim_ms_end: int` (speech-edge trim in ms at clip end; scaffold only, not applied yet)
- **Outputs:** `List[str]` (paths to exported clip files)
- **Processing Pipeline:**
  1. If `enable_face_tracking=True` and `aspect_ratio="9:16"`:
     - Calls `FaceReframer.reframe_video()` to create temp reframed video
     - Temp video has face tracking applied (9:16 format)
     - Uses temp video as input for subsequent steps
  2. If `add_subtitles=True`:
     - Generates SRT file for clip using `SubtitleGenerator`
     - Burns subtitles into video with FFmpeg
  3. If `add_logo=True`:
     - Overlays logo using FFmpeg filter_complex
  4. Applies aspect ratio conversion (if not already done by face tracking)
  5. Exports final clip to `output/{video_name}/{clip_id}.mp4`
- **Side Effects:**
  - Creates `output/{video_name}/{clip_id}.mp4` for each clip
  - Creates `output/{video_name}/{clip_id}.srt` if subtitles enabled
  - Creates temporary reframed video if face tracking enabled (auto-deleted)
  - Creates subfolders if `organize_by_style=True`
- **Face Tracking Integration:**
  - Face tracking happens BEFORE subtitles/logo are added
  - Creates `{clip_id}_reframed_temp.mp4` temporarily
  - Falls back to static center crop if face detection fails
- **File Structure:**
  ```
  output/
    {video_name}/
      1.mp4
      1.srt
      2.mp4
      2.srt
      ...
      viral/
        3.mp4
        5.mp4
      educational/
        1.mp4
        2.mp4
  ```

**Function:** `get_video_info(video_path: str) -> Dict`
- **Purpose:** Gets video metadata using ffprobe
- **Inputs:** `video_path: str`
- **Outputs:**
  ```python
  {
    'duration': float,  # seconds
    'width': int,
    'height': int,
    'fps': float,
    'codec': str
  }
  ```
