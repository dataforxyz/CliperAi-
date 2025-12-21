# Data Flow Summary

## Complete Pipeline Flow

```
1. Download Video
   YoutubeDownloader.download(url) 
   → downloads/{video_name}_{id}.mp4
   → StateManager.register_video()

2. Transcribe Video
   Transcriber.transcribe(video_path)
   → temp/{video_id}_audio.wav
   → temp/{video_id}_transcript.json
   → StateManager.mark_transcribed()

3. Generate Clips
   ClipsGenerator.generate_clips(transcript_path)
   → List[Dict] (clips with timestamps)
   → ClipsGenerator.save_clips_metadata()
   → temp/{video_id}_clips.json
   → StateManager.mark_clips_generated()

4. Generate AI Copies (Optional)
   CopysGenerator.generate()
   → output/{video_id}/copys/clips_copys.json
   → (includes classifications and copies)

5. Export Clips
   VideoExporter.export_clips(video_path, clips, ...)
   
   For each clip:
   
   a. Face Tracking (if enable_face_tracking=True and aspect_ratio="9:16")
      FaceReframer.reframe_video()
      → temp/{clip_id}_reframed_temp.mp4 (9:16 with face tracking)
      → Keeps face in frame during 16:9 → 9:16 conversion
   
   b. Subtitle Generation (if add_subtitles=True)
      SubtitleGenerator.generate_srt_for_clip()
      → output/{video_id}/{clip_id}.srt
   
   c. Video Processing
      FFmpeg processes:
      - Face-tracked video (if step a) OR original video
      - Adds subtitles (if step b)
      - Adds logo overlay (if add_logo=True)
      - Applies aspect ratio (if not done in step a)
      → output/{video_id}/{clip_id}.mp4
   
   → StateManager.mark_clips_exported()
```

**Face Tracking Flow (Detailed):**
```
Original Video (16:9, e.g., 1920x1080)
  ↓
FaceReframer.reframe_video()
  ├─ OpenCV reads frames
  ├─ MediaPipe detects face in each frame (sampled)
  ├─ Calculates crop position (keep_in_frame or centered strategy)
  ├─ Applies dynamic crop (vertical center, horizontal follows face)
  └─ FFmpegVideoWriter encodes → temp_reframed.mp4 (9:16, e.g., 1080x1920)
  ↓
FFmpeg adds subtitles/logo to reframed video
  ↓
Final Output: {clip_id}.mp4 (9:16 with face tracking + subtitles + logo)
```

## File Structure

```
project_root/
├── downloads/          # Source videos
│   └── {video_name}_{id}.mp4
├── temp/              # Intermediate files
│   ├── {video_id}_audio.wav
│   ├── {video_id}_transcript.json
│   ├── {video_id}_clips.json
│   └── project_state.json
└── output/            # Final clips
    └── {video_id}/
        ├── 1.mp4
        ├── 1.srt
        ├── 2.mp4
        ├── copys/
        │   └── clips_copys.json
        └── {style}/   # If organized by style
            └── 3.mp4
```
