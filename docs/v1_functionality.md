# CLIPER v1 - Main Functionality Reference

This document catalogs all main functionality functions in CLIPER to facilitate development of new CLI and GUI interfaces.

**Note:** This document has been split into feature-specific files for better organization. Each section below links to its detailed documentation.

## Table of Contents
1. [CLI Workflow](./func/cli_workflow.md)
2. [Core Pipeline Functions](./func/core_pipeline.md)
3. [Video Download](./func/video_download.md)
4. [Transcription](./func/transcription.md)
5. [Clip Generation](./func/clip_generation.md)
6. [AI Copy Generation](./func/ai_copy_generation.md)
7. [Video Export](./func/video_export.md)
8. [Face Tracking & Dynamic Reframing](./func/face_tracking.md)
9. [Subtitle Generation](./func/subtitle_generation.md)
10. [State Management](./func/state_management.md)
11. [Cleanup & Utilities](./func/cleanup_utilities.md)
12. [Configuration](./func/configuration.md)
13. [Prompt System Architecture](./func/prompt_system.md)
14. [Data Flow Summary](./func/data_flow.md)
15. [Dependencies](./func/dependencies.md)
16. [Error Handling Patterns](./func/error_handling.md)
17. [Notes for GUI/CLI Development](./func/development_notes.md)
18. [Future Enhancements](./func/future_enhancements.md)

---

## Quick Reference

### Main Entry Points
- **CLI:** `cliper.py` → `main()` - Interactive menu system
- **Video Download:** `src/downloader.py` → `YoutubeDownloader`
- **Transcription:** `src/transcriber.py` → `Transcriber`
- **Clip Generation:** `src/clips_generator.py` → `ClipsGenerator`
- **AI Copy Generation:** `src/copys_generator.py` → `CopysGenerator`
- **Video Export:** `src/video_exporter.py` → `VideoExporter`
- **Face Tracking:** `src/reframer.py` → `FaceReframer`
- **Subtitle Generation:** `src/subtitle_generator.py` → `SubtitleGenerator`
- **State Management:** `src/utils/state_manager.py` → `StateManager`
- **Cleanup:** `src/cleanup_manager.py` → `CleanupManager`

### Key Data Files
- **Project State:** `temp/project_state.json`
- **Transcripts:** `temp/{video_id}_transcript.json`
- **Clips Metadata:** `temp/{video_id}_clips.json`
- **AI Copies:** `output/{video_id}/copys/clips_copys.json`
- **Exported Clips:** `output/{video_id}/{clip_id}.mp4`

For detailed documentation on each feature, please refer to the linked files above.
