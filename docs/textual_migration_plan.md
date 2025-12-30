# Textual Migration Plan (CLIPER TUI → Future GUI)

## Goals

- Replace the current prompt-loop CLI (`cliper.py`) with a real TUI built on Textual.
- Keep the pipeline logic (download → transcribe → clip detect → export) UI-agnostic.
- Introduce a job/queue model that can be reused later by a desktop GUI (Qt) or a web GUI.
- Preserve existing state (`temp/project_state.json`) and outputs (`output/`, `temp/`).

## Non-Goals (for the first milestone)

- Rewriting pipeline internals (WhisperX, ClipsAI, ffmpeg) beyond small interface changes.
- Adding networked multi-user features.
- Perfect UI/UX polish; focus is correctness + a solid architecture.

## Why Textual

- App-like terminal UX: multi-pane layout, keyboard navigation, live progress, logs.
- Event-driven UI aligns with the same architecture you’ll want in a future GUI.
- Easy to embed Rich rendering and keep existing status output patterns.

## Target Architecture (UI-agnostic Core)

### 1) Core Layer (`src/core/…`)

**Responsibilities**
- Define a stable API for “jobs” and “pipeline steps”.
- Provide progress + log events.
- Read/write project state via `StateManager`.

**Suggested modules**
- `src/core/models.py`
  - `VideoRef(id, filename, path, content_type, preset)`
  - `JobSpec(video_id(s), steps, settings)`
  - `JobStatus(state, progress, started_at, finished_at, error)`
- `src/core/job_runner.py`
  - `run_job(job: JobSpec, emit: Callable[[Event], None])`
  - Uses existing pipeline classes (`YoutubeDownloader`, `Transcriber`, `ClipsGenerator`, `VideoExporter`)
- `src/core/events.py`
  - `LogEvent(level, message, video_id, job_id)`
  - `ProgressEvent(current, total, label, video_id, job_id)`
  - `StateEvent(video_id, updates)`

### 2) UI Layer (Textual App)

**Responsibilities**
- Video selection & batch selection UI.
- Job creation (“what steps to run + shared settings”).
- Queue management (start/stop/cancel/retry).
- Display progress, logs, and results paths.

### 3) Optional Future Layer (API)

If you want a web GUI later, put the core behind `FastAPI`:
- `POST /jobs` create job(s)
- `GET /jobs/{id}` status
- WebSocket for events/logs

Textual can either call the core directly (simpler) or call the API (more future-proof).

## Proposed TUI Layout

### Screens

1) **Library Screen** (default)
- Left: Video list (registered videos, filter/search, multi-select)
- Right: Video details (path, content type, status: transcribed/clips/exported)
- Bottom: Quick actions bar (Add, Batch, Transcribe, Clips, Export, Cleanup)

2) **Add Videos Modal**
- Add by:
  - YouTube URL
  - File(s)
  - Folder (toggle include subfolders)
- Shows a preview list before confirming “Add”.

3) **Batch Job Builder**
- Choose steps:
  - Transcribe
  - Generate clips
  - Export
- Shared settings per step (same concept you implemented in the CLI batch flow).

4) **Queue / Jobs Screen**
- List of jobs, status, per-video progress
- Controls: Start, Pause, Cancel, Retry failed

5) **Logs Drawer / Panel**
- Live log stream (filter by job/video, level)

## Implementation Plan (Milestones)

### Milestone 0: Prep (small refactor, no UX change)

- Extract “input parsing + video registry” utilities from `cliper.py` into a reusable module:
  - e.g. `src/utils/video_registry.py` (or `src/core/library.py`)
- Ensure the core functions can be called without Rich prompts.
- Standardize settings objects for:
  - transcription settings (model, language, skip_done)
  - clip settings (min/max seconds, max_clips, skip_done)
  - export settings (aspect, subtitles, style, logo, face tracking, max_per_video)

### Milestone 1: Minimal Textual App (read-only library)

- Add `src/tui/app.py` (Textual app entry).
- Show the video library table + details panel.
- Load videos via `StateManager` (`video_path` support already exists).

Deliverable
- `python -m src.tui.app` shows videos and their state.

### Milestone 2: Add Videos (interactive)

- Add “Add Videos” modal:
  - YouTube URL → calls downloader → registers video
  - Local files/folder → registers videos
- Refresh library view after add.

Deliverable
- Add videos without leaving the UI.

### Milestone 3: Jobs + Progress (single video)

- Implement `JobRunner` in core that emits events.
- In Textual, run jobs in background worker threads/processes.
- Render progress per job/video.

Deliverable
- Run “Transcribe” for one video and watch progress + logs.

### Milestone 4: Batch Jobs + Queue

- Multi-select videos.
- Build a batch job with shared settings.
- Queue multiple jobs (or one job containing multiple videos).

Deliverable
- Batch transcribe / clips / export from the TUI.

### Milestone 5: UX polish + parity

- Search/filter videos.
- “Open output folder” hint (print path; in terminal we can’t reliably open it cross-platform without extra work).
- Keyboard shortcuts, confirmations, error dialogs.

## Concurrency Model

Pipeline steps are heavy (ffmpeg, WhisperX, ML).

Recommended approach:
- Keep Textual responsive by running work in background threads.
- Limit concurrency (default 1 job at a time) with a setting for advanced users.
- If WhisperX/ffmpeg are CPU/GPU heavy, consider process-based execution later.

## Data Model / Compatibility

- Continue using `temp/project_state.json`.
- Additive state fields are OK (already added `video_path`).
- Avoid breaking existing keys (`transcribed`, `clips_generated`, `exported_clips`, etc.).

## Risks & Mitigations

- **Refactor churn:** Keep UI rewrite separate; don’t rewrite pipeline internals.
- **Progress visibility:** Wrap long steps with coarse progress events first; refine later.
- **Dependency footprint:** Textual adds a dependency; keep CLI as fallback initially.
- **OS-specific file pickers:** Textual doesn’t provide native pickers; use path input + directory scanning (like now).

## Suggested Repo Changes

- Add Textual as a dependency (likely in `pyproject.toml`):
  - `textual>=0.80` (version can be adjusted)
- Add a new entry point:
  - `python -m src.tui.app`
- Keep `cliper.py` for now as “legacy CLI” until Textual reaches parity.

## Next Decision Points (you choose)

1) Should the future GUI be **desktop** (Qt/PySide6) or **web** (FastAPI + React)?
2) For batch processing, should we model:
   - one job containing many videos, or
   - one job per video (simpler retries / parallelism)?
3) Should the Textual app directly call the core, or call a local API service?

