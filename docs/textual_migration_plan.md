# Textual Migration Plan - COMPLETED

> **Status:** This migration has been completed. The TUI is now the primary interface and the legacy CLI has been removed. This document is preserved for historical reference.

## Summary

CLIPER migrated from a Rich-based CLI to a Textual TUI interface. The migration is complete as of Task 16.

## What Was Achieved

### Architecture
- Event-driven core (`src/core/`) separates business logic from UI
- `JobRunner` emits events (`LogEvent`, `ProgressEvent`, `JobStatusEvent`)
- UI subscribes to events and updates accordingly
- Same core can power future GUI implementations

### TUI Features Implemented
- Video library with multi-select
- Add videos (YouTube URL or local files)
- Job queue with progress tracking
- Real-time log streaming
- Settings modal (schema-driven)
- Keyboard shortcuts

### Entry Point
```bash
uv run python src/tui/app.py
```

## Migration Milestones (All Completed)

1. **Milestone 0:** Core refactoring - video registry utilities, settings objects
2. **Milestone 1:** Basic Textual app with video library
3. **Milestone 2:** Add Videos modal
4. **Milestone 3:** Jobs + Progress tracking
5. **Milestone 4:** Batch jobs + Queue
6. **Milestone 5:** UX polish, keyboard shortcuts

## Future Considerations

If building additional interfaces:
- **Desktop GUI (Qt/PySide6):** Same core, different UI layer
- **Web GUI (FastAPI + React):** Put core behind REST API with WebSocket events
- The event-driven architecture supports both approaches

## Related Files

- `src/tui/app.py` - Main TUI application
- `src/core/job_runner.py` - Event-driven job orchestration
- `src/core/events.py` - Event definitions
- `src/core/models.py` - JobSpec, JobState enums
