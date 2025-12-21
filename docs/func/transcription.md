# Transcription

**Module:** `src/transcriber.py`

### Class: `Transcriber`

**Function:** `__init__(model_size: str = "base", device: str = "auto", compute_type: str = "int8")`
- **Purpose:** Initialize WhisperX transcriber
- **Inputs:**
  - `model_size: str` ("tiny", "base", "small", "medium", "large-v2")
  - `device: str` ("auto", "cpu", "mps")
  - `compute_type: str` ("int8", "float16")
- **Outputs:** None (loads Whisper model)

**Function:** `transcribe(video_path: str, language: Optional[str] = None, skip_if_exists: bool = True) -> Optional[str]`
- **Purpose:** Transcribes video audio to text with word-level timestamps
- **Inputs:**
  - `video_path: str` (path to video file)
  - `language: Optional[str]` (ISO code: "es", "en", None for auto-detect)
  - `skip_if_exists: bool` (if True, returns existing transcript if found)
- **Outputs:** `str` (path to JSON transcript file) or `None` if error
- **Side Effects:** 
  - Creates `temp/{video_id}_audio.wav` (extracted audio)
  - Creates `temp/{video_id}_transcript.json` (transcription)
- **Output Format:**
  ```json
  {
    "video_id": "video_abc123",
    "video_path": "downloads/video.mp4",
    "audio_path": "temp/video_abc123_audio.wav",
    "language": "es",
    "segments": [
      {
        "start": 0.0,
        "end": 5.2,
        "text": "Hola mundo",
        "words": [
          {"word": "Hola", "start": 0.0, "end": 0.5},
          {"word": "mundo", "start": 0.5, "end": 1.0}
        ]
      }
    ],
    "word_segments": [...]
  }
  ```

**Function:** `load_transcript(transcript_path: str) -> Optional[Dict]`
- **Purpose:** Loads existing transcript JSON
- **Inputs:** `transcript_path: str`
- **Outputs:** `Dict` (transcript data) or `None` if error

**Function:** `get_transcript_summary(transcript_path: str) -> Optional[Dict]`
- **Purpose:** Gets summary statistics without loading full transcript
- **Inputs:** `transcript_path: str`
- **Outputs:**
  ```python
  {
    "language": str,
    "num_segments": int,
    "total_duration": float,  # seconds
    "total_words": int,
    "first_text": str  # first 100 chars
  }
  ```
