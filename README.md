# 🎬 CLIPER

> **Production-Grade Agentic AI Pipeline for Automated Viral Clip Generation**

Transform long-form video content into publication-ready social media clips using an enterprise-grade hybrid AI architecture that combines specialized ML models, intelligent orchestration, and strategic LLM integration.

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/opino-tech/cliper.git
cd cliper
uv sync
```

### 2. Configure (Interactive Setup)

```bash
python setup.py
```

This interactive script will guide you through all settings:
- ✓ API key setup
- ✓ Transcription preferences
- ✓ Clip duration settings
- ✓ AI caption configuration
- ✓ Video export quality

**Custom output path?** Use `--output`:
```bash
python setup.py --output=.env.demo
```

### 3. Run CLIPER

**CLI:**
```bash
uv run cliper.py
```

**GUI (Recommended for beginners):**
```bash
python cliper_gui.py
```

---

## What CLIPER Does

- **Intelligent Segmentation** - Understands narrative structure to identify natural clip boundaries
- **Agentic Caption Generation** - Multi-step AI reasoning for contextually appropriate captions
- **Quality Assurance** - Validates outputs against brand and content guidelines
- **Computer Vision Optimization** - ML-based intelligent framing for vertical video
- **Subtitle Synchronization** - Precise word-level timing
- **Batch Processing** - Handles 30+ clips simultaneously

Result: Publication-ready clips for TikTok, Instagram Reels, YouTube Shorts, and more.

---

## System Requirements

- Python 3.9+
- FFmpeg
- macOS or Linux (Docker available)

---

## Documentation

New to CLIPER? Start here:

- **[Getting Started](docs/GETTING_STARTED.md)** - Setup guide, configuration, troubleshooting
- **[Architecture](docs/ARCHITECTURE.md)** - Technical details, system design, implementation

---

## Key Features

### Local-First Intelligence
Core ML models run locally for privacy and efficiency. Only strategic reasoning uses cloud APIs.

### Graceful Degradation
Better to publish 27 excellent clips than 30 mediocre ones. Validation gates ensure quality.

### Modular Design
Each stage can be updated independently without affecting the pipeline.

### Production Resilience
- Handle edge cases and partial failures
- Resume from any stage if interrupted
- Complete state visibility and logging

---

## Output Structure

```
output/
├── viral/          # High-engagement clips
├── educational/    # Educational content
└── storytelling/   # Narrative-driven content
```

Each clip includes video, subtitles, and metadata.

---

## Configuration

Use the interactive setup script:
```bash
python setup.py
```

Or manually configure `.env`:
```bash
cp .env.example .env
# Edit .env with your settings
```

**Required:**
- `GOOGLE_API_KEY` - Get free at https://aistudio.google.com/app/apikey

**Optional (sensible defaults provided):**
- `WHISPER_MODEL` - tiny, base, small, medium, large
- `MIN_CLIP_DURATION` - Minimum clip length
- `MAX_CLIP_DURATION` - Maximum clip length
- `GEMINI_MODEL` - Model choice
- `COPY_STYLE` - Caption style (auto, viral, educational, storytelling)
- `VIDEO_CRF` - Video quality (18-28)

---

## Workflow

1. **Input** - YouTube URL or local video
2. **Processing** - Automatic pipeline execution
3. **Review** - Clips organized by style in output/
4. **Publish** - Ready for social platforms

---

## Docker Deployment

```bash
docker-compose build
docker-compose run cliper
```

---

## Troubleshooting

**"API key not found"** → Run `python setup.py` to reconfigure

**"Transcription failed"** → Check FFmpeg: `ffmpeg -version`

**"No clips generated"** → Adjust `MIN_CLIP_DURATION` and `MAX_CLIP_DURATION`

**"GUI won't start"** → Install tkinter: `apt install python3-tk` or `brew install python-tk`

For more help, see [Getting Started](docs/GETTING_STARTED.md#troubleshooting).

---

## Architecture

CLIPER's 7-stage pipeline:

1. **Transcription & Analysis** - Word-level timing with WhisperX
2. **Semantic Understanding** - Narrative structure analysis
3. **Intelligent Segmentation** - Natural clip boundary detection
4. **Agentic Caption Generation** - Multi-step AI reasoning via LangGraph
5. **Quality Validation** - Brand compliance & content guidelines
6. **Computer Vision Optimization** - ML-based intelligent reframing
7. **Video Engineering** - Final export with codec optimization

See [full architecture docs](docs/ARCHITECTURE.md).

---

## Technology Stack

**Local Processing:** WhisperX, ClipsAI, FFmpeg, OpenCV

**Cloud APIs:** Google Gemini (caption generation)

**Architecture:** LangGraph (agentic reasoning), Pydantic (validation)

---

## Advanced Features

- **Resume Capability** - Continue from last successful stage
- **Batch Processing** - 30+ clips simultaneously
- **Custom Validation** - Define brand guidelines
- **State Management** - Complete visibility into processing

---

## Development & Customization

CLIPER is modular and extensible:

- Configure for specific use cases
- Extend with custom logic
- Integrate into larger systems
- Modify for specialized workflows

Check the [Architecture guide](docs/ARCHITECTURE.md#extensibility) for details.

### Versioning

Update the project version in `pyproject.toml`:

```bash
uv run bump2version patch   # or: minor / major
```

If you use Docker, you can also run:

```bash
make bump PART=patch   # or: minor / major
```

---

## License

MIT License

---

## About

**CLIPER** is a production-grade AI system developed by **opino.tech**, powered by **AI CDMX**.

This is professional infrastructure designed for production use at scale—not a tutorial or demo.

**Ready to transform your video content?** Run `python setup.py` and get started.

---

For questions or custom implementations, reach out to the opino.tech team.

Built with production systems in mind.
