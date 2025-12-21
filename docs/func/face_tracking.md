# Face Tracking & Dynamic Reframing

**Module:** `src/reframer.py`

### Overview

Face tracking intelligently keeps faces in frame when converting videos from horizontal (16:9) to vertical (9:16) aspect ratios. Instead of static center cropping (which cuts off faces when speakers move), this feature uses MediaPipe face detection to dynamically adjust the crop position frame-by-frame.

**Key Features:**
- **Dynamic Face Tracking**: Detects largest face in each frame and adjusts crop position
- **Aspect Ratio Conversion**: Converts 16:9 → 9:16 while keeping face visible
- **Two Strategies**: "keep_in_frame" (minimal movement) or "centered" (always centered)
- **Performance Optimized**: Frame sampling (process every N frames) for 3x speedup
- **Fallback Support**: Falls back to center crop if no face detected

**Use Case:** Perfect for converting talking-head videos (podcasts, interviews, tutorials) to vertical format for TikTok/Reels/Shorts without losing the speaker's face.

### Class: `FaceReframer`

**Function:** `__init__(frame_sample_rate: int = 3, strategy: str = "keep_in_frame", safe_zone_margin: float = 0.15, min_detection_confidence: float = 0.5)`
- **Purpose:** Initialize face tracking reframer with MediaPipe
- **Inputs:**
  - `frame_sample_rate: int` (process every N frames, default: 3 for 3x speedup)
  - `strategy: str` 
    - `"keep_in_frame"` (default): Only moves crop when face exits safe zone (minimal jitter, professional look)
    - `"centered"`: Always centers face (more movement, can be jittery)
  - `safe_zone_margin: float` (0.15 = 15% margin on each side, total 30% breathing room)
  - `min_detection_confidence: float` (MediaPipe threshold, default: 0.5)
- **Outputs:** None (initializes MediaPipe face detector)
- **Technical Details:**
  - Uses MediaPipe Face Detection (model_selection=1 for full-range detection)
  - Detects largest face in frame (handles multi-person shots)
  - Safe zone prevents unnecessary crop movement

**Function:** `reframe_video(input_path: str, output_path: str, target_resolution: Tuple[int, int], start_time: Optional[float] = None, end_time: Optional[float] = None) -> str`
- **Purpose:** Generates reframed video with dynamic face tracking for aspect ratio conversion
- **Inputs:**
  - `input_path: str` (source video path, typically 16:9)
  - `output_path: str` (output video path, will be 9:16)
  - `target_resolution: Tuple[int, int]` (width, height) e.g., (1080, 1920) for 9:16
  - `start_time: Optional[float]` (start timestamp in seconds, for clip processing)
  - `end_time: Optional[float]` (end timestamp in seconds, for clip processing)
- **Outputs:** `str` (path to reframed video file)
- **Side Effects:** 
  - Creates temporary reframed video file
  - Uses FFmpeg subprocess for encoding (handles macOS M4 compatibility)
- **Process:**
  1. Opens source video with OpenCV
  2. Scales video to ensure sufficient resolution for vertical crop
  3. For each frame (with sampling):
     - Detects largest face using MediaPipe
     - Calculates optimal crop position based on strategy
     - Applies crop (vertical center, horizontal dynamic)
  4. Writes reframed frames to output video
  5. Falls back to center crop if no face detected for 10+ frames
- **Performance:** 
  - ~3.3ms per frame detection (MediaPipe)
  - 3x speedup with frame sampling (process every 3 frames)
  - ~11px average movement between sampled frames (acceptable)

**Internal Methods (used by reframe_video):**

**Function:** `_detect_largest_face(frame) -> Optional[Dict]`
- **Purpose:** Detects largest face in frame using MediaPipe
- **Inputs:** `frame` (OpenCV BGR frame)
- **Outputs:**
  ```python
  {
    'x': int,           # bounding box x
    'y': int,           # bounding box y
    'width': int,       # bounding box width
    'height': int,      # bounding box height
    'center_x': int,    # face center X coordinate
    'center_y': int     # face center Y coordinate
  }
  ```
- **Returns:** `None` if no face detected

**Function:** `_calculate_crop_keep_in_frame(face: Dict, frame_width: int, frame_height: int, target_width: int, target_height: int) -> int`
- **Purpose:** Calculates crop X position using "keep_in_frame" strategy
- **Logic:** Only moves crop when face exits safe zone (15% margins)
- **Inputs:** Face dict, frame dimensions, target dimensions
- **Outputs:** `int` (crop X position in pixels)

**Function:** `_calculate_crop_centered(face: Dict, frame_width: int, target_width: int) -> int`
- **Purpose:** Calculates crop X position using "centered" strategy
- **Logic:** Always centers face horizontally
- **Inputs:** Face dict, frame width, target width
- **Outputs:** `int` (crop X position in pixels)

### Integration with Video Export

Face tracking is automatically used when:
- `enable_face_tracking=True` in `VideoExporter.export_clips()`
- `aspect_ratio="9:16"` (vertical format)
- Creates temporary reframed video before adding subtitles/logo

**Workflow:**
```
Original Video (16:9)
  ↓
FaceReframer.reframe_video() → temp_reframed.mp4 (9:16 with face tracking)
  ↓
FFmpeg adds subtitles/logo → Final output (9:16)
```

### Helper Class: `FFmpegVideoWriter`

**Module:** `src/reframer.py`

**Function:** `__init__(output_path: str, width: int, height: int, fps: float, codec: str = 'libx264', preset: str = 'fast', crf: int = 23)`
- **Purpose:** VideoWriter using FFmpeg subprocess (for macOS M4 compatibility)
- **Inputs:** Video properties and encoding settings
- **Outputs:** None (initializes FFmpeg subprocess)
- **Why:** cv2.VideoWriter fails on macOS M4, FFmpeg subprocess uses native arm64 FFmpeg

**Function:** `write(frame: np.ndarray) -> bool`
- **Purpose:** Writes frame to video via FFmpeg stdin
- **Inputs:** `frame` (NumPy array, BGR format, uint8)
- **Outputs:** `bool` (success)

**Function:** `release()`
- **Purpose:** Closes FFmpeg subprocess and finalizes video
- **Inputs:** None
- **Outputs:** None
