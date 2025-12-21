# Notes for GUI/CLI Development

1. **State Management**: Always check `StateManager.get_video_state()` before operations
2. **Progress Tracking**: Use Rich Progress bars (see `VideoExporter.export_clips()`)
3. **Error Display**: Check return values and display errors from logs
4. **Configuration**: Use `content_presets` for default settings
5. **File Paths**: All paths are relative to project root or absolute
6. **Async Operations**: Transcription and export are CPU-intensive (consider async/threading)
7. **Cleanup**: Use `CleanupManager` for disk space management
8. **Face Tracking**: 
   - Only enable when `aspect_ratio="9:16"` (vertical format)
   - Best for talking-head content (podcasts, interviews, tutorials)
   - "keep_in_frame" strategy recommended for professional look (less jittery)
   - Frame sampling (default: 3) provides 3x speedup with minimal quality loss
   - Falls back gracefully to center crop if no face detected
   - Creates temporary files that are auto-deleted after export
