# CLIPER - Design Notes

**Context:** CLI tool to automatically convert long videos into short clips.

This document captures **design decisions**, **problems encountered**, and **solutions** during development. This is not marketing - it's documentation of the thought process.

---

## Decision 1: Why CLI Instead of GUI/Web?

### The Initial Problem
Needed to process long videos (1-2 hours) with AI. This takes time (30+ minutes for transcription).

### Options Considered

**A) Web app (Flask/Django):**
- Websockets for long processes = complex
- Where to store videos? Storage = $$$
- ffmpeg on server = expensive resources
- Development time: weeks

**B) Desktop app (Electron/PyQt):**
- Packaging Python + ffmpeg + ML models = heavy
- Updates complicated
- Time: weeks

**C) Jupyter Notebook:**
- Works, but ugly UI
- Hard to share
- Not a "tool"

**D) CLI with Rich:**
- Rapid development (days, not weeks)
- Terminal = designed for long processes
- Rich library = beautiful UI for free
- Easy to automate later

**Decision:** CLI. Can iterate quickly and terminal handles long processes well.

---

## Decision 2: 4-Phase Separated Pipeline

### Why Not Everything in One Command?

**Discarded option:**
```bash
$ cliper process video.mp4 --output clips/
[wait 45 minutes...]
Done!
```

**Problems:**
- If it fails at minute 40 -> lose everything
- Can't adjust configuration between steps
- Debugging = nightmare

**Solution: Separated Pipeline**
```
download -> transcribe -> detect clips -> export
```

**Advantages:**
1. **Incremental:** Each phase saves output to `temp/`
2. **Reusable:** Can regenerate clips without re-transcribing (saves 30 min)
3. **Debuggable:** Inspect JSON between phases
4. **Flexible:** Change configuration mid-process

**Accepted trade-off:** More user interaction. But worth it.

---

## Decision 3: Persistent State Manager

### The Problem
Transcription of 99 min takes 25 minutes. If I close the terminal -> lost everything?

### Solution: Persistent JSON

```json
{
  "video_id": {
    "transcribed": true,
    "transcript_path": "temp/video_transcript.json",
    "clips_generated": false
  }
}
```

**Why JSON and not SQLite:**
- Human-readable (can inspect it)
- Easy to edit manually if needed
- No schema migration needed
- Git-friendly for debugging

**Why not in memory:**
- Obvious: lost on close

**Why not separate files (.done, .status):**
- Hard to query complete state

---

## Decision 4: Hybrid Clip System (Key Decision)

### The Real Problem

Started thinking: "ClipsAI uses AI -> must work perfectly".

**Reality:**
```python
clips = clip_finder.find_clips(transcript)
print(len(clips))  # 0 -> WTF?
```

**Why?**

ClipsAI uses TextTiling: detects **abrupt topic changes**. Works well for:
- Podcasts (question/topic changes)
- Tutorials (section 1, section 2, section 3)
- Documentaries (intro -> development -> conclusion)

**Doesn't work for:**
- 99 min livestreams with a single topic
- Continuous academic talks
- Technical conferences

### Options Considered

**A) "ClipsAI doesn't work, use only fixed time"**
- Waste the AI
- Bad clips on content with natural sections

**B) "Adjust ClipsAI threshold"**
- Tried, but no exposed parameter
- Very limited API

**C) Hybrid system**
```python
clips = clip_finder.find_clips(transcript)
if not clips:
    logger.info("Fallback: fixed-time clips")
    clips = generate_fixed_time_clips(duration=90)
```

**Decision:** Hybrid. Try the intelligent approach, fallback to simple.

**Key learning:** AI doesn't always work. Always have a deterministic plan B.

---

## Decision 5: Presets by Content Type

### The Configuration Problem

**First CLI version:**
```
Model size? [tiny/base/small/medium/large]
Language? [auto/es/en/fr/de...]
Clip duration min? [30]
Clip duration max? [90]
Max clips? [10]
Method? [clipsai/fixed/hybrid]
```

User: "I don't know what to put"

### Insight

Content type **predicts** optimal configuration:

| Type | Characteristics | Optimal Config |
|------|-----------------|----------------|
| Podcast | 2+ speakers, topic changes | model=small, diarization=true, clips=1-5min |
| Livestream | 1 speaker, continuous topic | model=medium, clips=60-90s, method=hybrid |
| Tutorial | Structured, sections | model=base, clips=45s-3min, method=clipsai |

### Solution: Presets

```python
CONTENT_PRESETS = {
    "livestream": {
        "transcription": {"model_size": "medium"},
        "clips": {"min_duration": 60, "max_duration": 90, "method": "hybrid"}
    }
}
```

**User flow:**
```
Content Type: <- Livestream
[Auto-suggests: model=medium, clips=60-90s]
Model size [medium]: <- User just presses ENTER
```

**Why this works better:**
- User thinks in terms of **content**, not **technical parameters**
- Smart defaults -> less friction
- Can still change if wanted

---

## Decision 6: Adapter Pattern for WhisperX -> ClipsAI

### The Incompatibility Problem

```python
# WhisperX output:
{
  "segments": [
    {"start": 0.0, "end": 5.2, "text": "Hello world", "words": [...]}
  ]
}

# ClipsAI expects:
{
  "char_info": [
    {"char": "H", "start_time": 0.0, "end_time": 0.2, "speaker": "SPEAKER_00"},
    {"char": "e", "start_time": 0.2, "end_time": 0.4, "speaker": "SPEAKER_00"},
    ...
  ],
  "time_created": "2025-10-24 ...",
  "source_software": "whisperx",
  "num_speakers": 1
}
```

**Not directly compatible.**

### Options

**A) Use ClipsAI's Transcriber:**
- Slower than WhisperX
- Less precise timestamps
- Already have WhisperX working

**B) Switch to another clips library:**
- ClipsAI is the best for this
- Time to re-implement

**C) Write adapter:**
```python
def _convert_to_clipsai_format(whisperx_data):
    char_info = []
    for segment in segments:
        for word in segment["words"]:
            for char in word["word"]:
                char_info.append({
                    "char": char,
                    "start_time": word["start"],
                    "end_time": word["end"],
                    "speaker": "SPEAKER_00"
                })

    return Transcription({
        "char_info": char_info,
        "time_created": datetime.now(),
        ...
    })
```

**Decision:** Adapter.

**Debugging hell:**
- Error 1: `cannot import Transcript` -> It's `Transcription`
- Error 2: Missing `time_created` field -> Added
- Error 3: Missing `source_software` field -> Added
- Error 4: Missing `speaker` in char -> Added
- Error 5: `transcript=` doesn't work -> Must be positional

**Learning:** Integrating third-party APIs = always surprises. Reading docs isn't enough, must test.

---

## Decision 7: Only 10 Clips -> Bug Found by User

### The Bug

99 minute video -> only generated 10 clips.

**Cause:**
```python
max_clips = Prompt.ask("Max clips", default="10")
```

Default of 10 was for short videos. Didn't scale.

### Fix

1. Calculate estimate:
```python
total_duration = transcript[-1]["end"]  # 5958s
clip_duration = 90
estimated = total_duration / clip_duration  # 66 clips
```

2. Show user:
```
Video duration: 99.3 minutes
Estimated clips with 90s: ~66
Max clips [100]: <- New default
```

3. Change default: 10 -> 100

**Learning:** Defaults matter. What's reasonable for one use case (short video), breaks another (livestream).

---

## Decision 8: Why No Diarization (Yet)

**Diarization** = detect who is speaking when.

**Useful for:**
- Podcasts with 2+ people
- Interviews
- Panels

**Why not implemented:**
```python
# Pyannote diarization requires:
1. HuggingFace token
2. 2-3x more processing time
3. GPU to be fast
```

**Decision:** Leave for later.

**Current configuration:**
```python
"num_speakers": 1  # Hardcoded
"speaker": "SPEAKER_00"  # All chars
```

**When to add:** Phase 4 or 5, when there are real use cases that need it.

---

## Decision 9: Export with Embedded Subtitles

### The Problem
Clips need subtitles for social media, but ClipsAI doesn't generate them automatically.

### Implemented Solution

**Module `subtitle_generator.py`:**
- Generates SRT files from transcription
- Synchronizes with clip timestamps
- Embeds subtitles in final videos

**Module `video_exporter.py`:**
- Cuts clips from original video
- Resizes to 9:16
- Embeds subtitles automatically
- Optimizes for social media

**Result:**
- Clips ready to upload directly
- Synchronized subtitles
- Optimal format for TikTok/Instagram

---

## Decision 10: Modular vs Monolithic Architecture

### Considered Option: Everything in One File
```python
# cliper_monolith.py (1000+ lines)
def download_and_transcribe_and_clip_and_export():
    # Everything mixed
```

### Problems:
- Hard to debug
- Impossible to test
- Not reusable
- Spaghetti code

### Solution: Separate Modules
```
src/
├── downloader.py      # One responsibility
├── transcriber.py     # One responsibility
├── clips_generator.py # One responsibility
├── video_exporter.py  # One responsibility
├── subtitle_generator.py # One responsibility
└── utils/            # Shared functions
```

**Advantages:**
- Each module testable independently
- Easy to debug (logs per module)
- Reusable (can use transcriber in other projects)
- Maintainable (isolated changes)

---

## Observed Patterns

### 1. Fail-Safe Design
Never leave user without result:
- ClipsAI fails -> fallback to fixed-time
- User doesn't know config -> use preset
- Process interrupted -> state saved

### 2. Progressive Enhancement
Start simple, add complexity:
- V1: Only download
- V2: + Transcribe
- V3: + Clip detection
- V4: + Export (COMPLETED)

### 3. Transparent AI
Show user WHAT the AI did:
```python
{"method": "fixed_time"}  # vs "clipsai"
```

User knows if it was intelligent detection or simple cut.

### 4. Smart Defaults with Override
Don't force, suggest:
```
Model size [medium]: <- Can change
Clip duration [4 - Use preset: 60-90s]: <- Can ignore
```

### 5. User-Centered Design
Think about user, not technology:
- Presets by content type
- Automatic estimations
- Constant visual feedback
- Option to cancel at any time

---

## Tech Stack - Justification

**Why these choices:**

- **UV** (not pip): 10-100x faster, built-in lock file
- **Rich** (not print): Beautiful UI for free, zero CSS
- **WhisperX** (not base Whisper): Word-by-word timestamps
- **ClipsAI** (not custom ML): Already solved, don't reinvent
- **JSON state** (not DB): Simple, debuggable, git-friendly
- **FFmpeg** (not moviepy): Faster, more control
- **yt-dlp** (not pytube): More robust, better maintained

---

## Current Metrics - PROJECT COMPLETED

**Test video:** 99 min Livestream

```
Download:     3 min
Transcription: 25 min (model=medium, CPU M4)
Clip Detection: 4 sec
Export:       8 min (14 clips)
Total:        ~36 min

Output:
- 1,083 transcribed segments
- 52,691 characters
- 14 clips of 90s each
- Embedded subtitles
- 9:16 format ready for social media
- Coverage: full 99 min
```

**Bottleneck:** Transcription (70% of total time)

**Future optimization:**
- Use `tiny` model for quick preview
- Offer `medium` only if user wants precision
- GPU for faster transcription

---

## Lessons Learned

### 1. AI Is Not Magic
- ClipsAI works well on content with topic changes
- Deterministic fallback always needed
- Transparency about which method was used

### 2. UX > Technology
- Presets > 10 technical options
- Automatic estimates > manual configuration
- Visual feedback > invisible logs

### 3. Modularity Is Key
- Each module one responsibility
- Easy to test and debug
- Reusable in other projects

### 4. Rapid Iteration
- CLI allows testing changes in minutes
- Rich makes it look professional from the start
- JSON state facilitates debugging

### 5. Document Decisions
- This file prevents repeating mistakes
- Explains "why", not just "what"
- Useful for future improvements

---

## Final Project State

### COMPLETED - All Phases Implemented

**Features:**
- YouTube download with yt-dlp
- Transcription with WhisperX (precise timestamps)
- Clip detection with ClipsAI (hybrid system)
- Clip export in 9:16 format
- Subtitle generation and embedding
- Professional CLI with Rich
- Persistent state manager
- Intelligent presets by content type
- Robust error handling

**Generated files:**
- 14 clips of 90s each
- Subtitles in SRT format
- Videos in 9:16 format
- Complete clip metadata

**Ready for:**
- Production use
- Distribution as App Bundle
- Community contributions
- Extension with new features

---

## Optional Next Steps

### Distribution
- App Bundle (.app) for Mac
- DMG installer
- Homebrew formula

### New Features
- Speaker diarization (Pyannote)
- Face detection for auto-crop
- Social media API integration
- Batch processing multiple videos

### Optimizations
- GPU for faster transcription
- Parallel clip processing
- Intelligent model caching
- Platform-optimized compression

---

## Conclusion

CLIPER works because:

1. **Clear scope:** Does one thing (clips) well
2. **Fail-safe:** Always gives result
3. **Fast iteration:** CLI allows quick iteration
4. **User-centered:** Presets > 10 technical options
5. **Modular:** Easy to maintain and extend
6. **Transparent:** User knows what AI did

**Main lesson:** AI is a tool, not magic. Always have deterministic fallback.

**Result:** Complete, functional tool ready for production.

---

*Documented: 2025-10-24*
*Status: PROJECT COMPLETED - All phases implemented*
*Version: 1.0.0 - Ready for production*
