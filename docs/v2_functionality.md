# CLIPER v2 - Functionality

CLIPER v2 focuses on supporting multiple processing paths and bulk processing for all paths.

## Processing Paths

### 1) Long-Form to Shorts (Clipper v1-style)
Process a long-form video into multiple short clips.

- Process the video transcript
- Use AI to find clip candidates
- Create clips with subtitles and a logo
- Export

**Status:** Fully implemented

### 2) Shorts Processing
Take an existing short and get it ready to publish.

- Transcribe
- Remove preamble and postamble (speech-aware trimming)
- Add subtitles and a logo
- Export

**Status:** Implemented via Shift+P custom shorts modal

### 3) Long-Form Processing
Take an existing long-form video and get it ready to publish.

- Transcribe
- Remove preamble and postamble (speech-aware trimming)
- Add subtitles and a logo
- Export

**Status:** Implemented

---

## Feature Status

### Implemented
- Flexible video input (process from any path)
- Bulk/batch video processing
- Speech-aware auto-trimming using WhisperX timestamps
- Subtitle styling (font, color, size selection)
- Logo selection and overlay
- Settings system with TUI modal
- Prompt management in organized directory structure

### Planned
- Fully automated CLI mode (all settings as command-line args)
- Custom output directory configuration
- Clickable video links in terminal output
- Caption review and editing workflow
- Advanced subtitle types (word-by-word, highlight current word)
- Human-in-the-loop review points
- Full installation build for offline environments

See [docs/todo.md](./todo.md) for the complete task list.
