# Cleanup & Utilities

**Module:** `src/cleanup_manager.py`

### Class: `CleanupManager`

**Function:** `__init__(downloads_dir: str = "downloads", temp_dir: str = "temp", output_dir: str = "output")`
- **Purpose:** Initialize cleanup manager
- **Inputs:** Directory paths (optional)
- **Outputs:** None

**Function:** `get_video_artifacts(video_key: str) -> Dict[str, Dict]`
- **Purpose:** Lists all artifacts for a video
- **Inputs:** `video_key: str`
- **Outputs:**
  ```python
  {
    'download': {
      'path': Path,
      'exists': bool,
      'size': int,  # bytes
      'type': str
    },
    'transcript': {...},
    'clips_metadata': {...},
    'output': {
      'path': Path,
      'exists': bool,
      'size': int,
      'type': 'directory',
      'clip_count': int
    },
    'temp_files': {...}
  }
  ```

**Function:** `delete_video_artifacts(video_key: str, artifact_types: Optional[List[str]] = None, dry_run: bool = False) -> Dict[str, bool]`
- **Purpose:** Deletes specific artifacts for a video
- **Inputs:**
  - `video_key: str`
  - `artifact_types: Optional[List[str]]` (["download", "transcript", "clips_metadata", "output", "temp_files"] or None for all)
  - `dry_run: bool` (simulate without deleting)
- **Outputs:** `Dict[str, bool]` (result for each artifact type)

**Function:** `delete_all_project_data(dry_run: bool = False) -> Dict[str, bool]`
- **Purpose:** Deletes all project data (fresh start)
- **Inputs:** `dry_run: bool`
- **Outputs:** `Dict[str, bool]` (result for each directory: downloads, temp, output, cache, state)

## Utilities

**Module:** `src/utils/logger.py`
- **Functions:** `setup_logger(name: str = "cliper", level=logging.INFO, log_file: Optional[str] = None)`, `get_logger(name: str)`, `default_logger`
- **Purpose:** Centralized logger setup used across modules (console formatter + optional file handler).

**Module:** `src/utils/__init__.py`
- **Exports:** `setup_logger`, `default_logger`, `StateManager`, `get_state_manager`
- **Purpose:** Convenience imports for modules/CLI to share logger and state manager instances.
