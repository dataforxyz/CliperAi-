# CLIPER Todo List

## High Priority

- [ ] Full installation build - Create `make install-full` that downloads all dependencies upfront (Whisper models, MediaPipe, etc.) for Docker builds and offline environments
- [ ] Clickable video links - Show clickable file:// URLs for exported videos in terminal output
- [ ] Custom output directory - Add `--output-dir` flag and `CLIPER_OUTPUT_DIR` environment variable
- [ ] Terminal automation - Allow passing all settings as terminal vars for fully automated start-to-finish processing

## Medium Priority

- [ ] Caption review workflow - Add a way to easily double-check and fix AI-generated captions before export
- [ ] Human-in-the-loop points - Identify and add review/approval steps throughout pipeline (clip boundaries, classifications, captions)
- [ ] Trim-only mode - Option to remove preamble/postamble without AI clip detection

## Subtitle Enhancements

- [ ] Subtitle segmentation control - Max/min characters and words per subtitle, line break rules
- [ ] Subtitle display types:
  - Word-by-word (karaoke style)
  - Key words only (AI-extracted important words)
  - Multi-word with highlight (highlight current word dynamically)

## Audio Processing

- [ ] Silence removal - Cut down silence if > N milliseconds (SpeechBrain VAD)
- [ ] Audio normalization - Prevent peaks and valleys in audio levels
- [ ] Speaker diarization - Different color subtitles per speaker (WhisperX/Pyannote)

## Output & Organization

- [ ] Auto-name shorts - Name clips based on transcription content
- [ ] Fix output directory structure - Simplify the nested output directories
- [ ] Replace AICDMX logo - Ship with a generic demo logo instead

## Analytics (Future)

- [ ] Copy stats command - `show-copys-stats` to view engagement metrics
- [ ] Filter clips by metadata
- [ ] Export CSV reports
- [ ] Compare multiple generations
