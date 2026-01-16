# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLIPER is a production-grade AI pipeline that transforms long-form video into publication-ready social media clips. It uses a hybrid architecture combining local ML models (WhisperX, ClipsAI, MediaPipe) with strategic cloud API use (Google Gemini for caption generation).

## Development Commands

This project uses **uv** as the package manager. All Python commands should be run through `uv run`.

### Running the Application

```bash
# TUI interface
uv run python src/tui/app.py
make tui

# Interactive setup
python setup.py
```

### Make Commands

```bash
make help           # Show all available commands

# Docker workflow
make build          # Build Docker images
make dev            # Start development mode (interactive, attached)
make prod           # Start production mode (detached)
make stop           # Stop containers without removing
make down           # Stop and remove containers
make restart        # Restart services
make logs           # View container logs (follow mode)
make shell          # Open bash shell inside container
make ps             # Show running containers

# Code quality (runs inside Docker container)
make test           # Run pytest -v
make format         # Run black and isort
make lint           # Run black --check, isort --check, mypy src/

# Version management
make bump PART=patch   # Bump version (patch|minor|major)

# Cleanup
make clean          # Remove containers, volumes, Docker images
make clean-cache    # Remove __pycache__, .pyc, .egg-info files
```

### Running Tests Locally

```bash
uv run pytest -v                    # All tests
uv run pytest tests/test_foo.py -v  # Single test file
uv run pytest -k "test_name" -v     # Tests matching pattern
```

### Rover Task Testing

Test inside isolated rover task workspaces:

```bash
make test-task TASK=134                                      # Run all tests in task workspace
make test-task TASK=134 ARGS="tests/test_misspellings.py"    # Run specific test file
make test-task TASK=134 ARGS="-v --tb=short"                 # Pass pytest flags
make test-task TASK=134 ARGS="tests/test_foo.py -v -k bar"   # Combine file + flags
```

## Architecture

7-stage pipeline:

1. **Transcription** (WhisperX - local) → Word-level timestamps
2. **Semantic Understanding** (LLM) → Topic boundaries, narrative structure
3. **Segmentation** (ClipsAI - local) → Natural clip boundaries
4. **Caption Generation** (LangGraph + Gemini) → 10-node agentic workflow
5. **Validation** (Pydantic) → Brand compliance, content guidelines
6. **Reframing** (MediaPipe + OpenCV) → Face tracking for vertical video
7. **Export** (FFmpeg) → Final encoding with subtitle sync

### Key Integration Points

- `src/video_exporter.py` - Main integration hub coordinating FFmpeg, subtitles, reframing, logo overlay
- `src/copys_generator.py` - LangGraph workflow with 10 nodes for caption generation
- `src/core/job_runner.py` - Event-driven job orchestration (emits JobStatusEvent, ProgressEvent, LogEvent)
- `src/utils/state_manager.py` - JSON state persistence enabling resume capability

### Source Structure

```
src/
├── downloader.py          # yt-dlp wrapper
├── transcriber.py         # WhisperX transcription
├── clips_generator.py     # ClipsAI segmentation
├── video_exporter.py      # FFmpeg orchestration
├── copys_generator.py     # LangGraph caption flow
├── subtitle_generator.py  # SRT generation
├── reframer.py            # MediaPipe face tracking
├── core/
│   ├── job_runner.py      # Event-driven orchestration
│   ├── models.py          # JobSpec, JobState enums
│   └── events.py          # Event definitions
├── models/
│   └── copy_schemas.py    # Pydantic validation
├── prompts/               # Modular prompts by style
├── config/
│   └── settings_schema.py # Settings registry
├── tui/
│   └── app.py             # Textual TUI
└── utils/
    ├── logger.py          # loguru wrapper
    ├── state_manager.py   # JSON state persistence
    └── video_registry.py  # Video file discovery
```

## Code Conventions

- **Type hints everywhere** - Use Pydantic models for data validation
- **Logging** - Use loguru via `src/utils/logger.py`
- **Configuration** - Use `settings_schema.py`, not hardcoded values
- **Error handling** - Specific exceptions, never bare `except:`
- **Spanish comments** - Codebase uses Spanish for comments/docstrings, English for class names

## Testing Philosophy

**Never write special-case code to make tests pass.** Tests should verify real behavior. If a test fails, either:
1. The code has a bug that needs fixing
2. The test is wrong and needs updating

Do not add conditionals, mocks, or workarounds in production code solely to satisfy tests.

## Design Principles

- **Local-first**: Core ML runs locally (WhisperX, ClipsAI, MediaPipe). Cloud APIs only for strategic reasoning
- **Graceful degradation**: Better 27 excellent clips than 30 mediocre ones. Validation failures skip individual clips, not the entire batch
- **Event-driven UI**: JobRunner emits events allowing multiple UI implementations (TUI, CLI, future web)
- **Resume capability**: State saved at each stage for recovery from interruptions
