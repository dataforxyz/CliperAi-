# Dependencies

## External Libraries
- `yt-dlp` - YouTube download
- `whisperx` - Transcription
- `clipsai` - Clip detection
- `langchain_google_genai` - AI copy generation
- `mediapipe` - Face detection
- `opencv-python` - Video processing
- `ffmpeg` - Video encoding (system dependency)
- `pydantic` - Data validation
- `langgraph` - Workflow orchestration
- `python-dotenv` - Environment variable loading
- `rich` - CLI UI components
- `ffmpeg-python`, `tqdm`, `typer`, `loguru`, `faster-whisper` - supporting tooling/utilities

## Internal Dependencies
- `StateManager` - Used by all modules for state tracking
- `SubtitleGenerator` - Used by `VideoExporter`
- `FaceReframer` - Used by `VideoExporter` (optional)
- `content_presets` - Used by CLI for configuration
